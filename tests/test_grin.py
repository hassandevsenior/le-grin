"""Tests des règles qui font l'identité du Grin. Lancer : python manage.py test"""

import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from collabs.models import Commitment, HelpRequest
from core.models import Notification, Tech
from debates.models import Debate, Stance
from paths.models import MAX_STEPS, Path, Step
from projects.models import Pin, Project

User = get_user_model()
MEDIA = tempfile.mkdtemp()


def png(width=800, height=600):
    buffer = BytesIO()
    Image.new("RGB", (width, height), "#c8502b").save(buffer, "PNG")
    return SimpleUploadedFile("capture.png", buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class GrinTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.awa = User.objects.create_user("awa", "awa@test.bf", "motdepasse-solide")
        self.issa = User.objects.create_user("issa", "issa@test.bf", "motdepasse-solide")

    def make_project(self, owner=None, **extra):
        data = {"title": "Sugu", "tagline": "Un carnet", "stage": "live", "repo_url": "https://github.com/x/y",
                "screenshot": png(), "techs_text": "Django, django, Vue.js"}
        data.update(extra)
        self.client.force_login(owner or self.awa)
        return self.client.post(reverse("projects:create"), data)


class TechTests(TestCase):
    def test_from_text_deduplicates_and_limits(self):
        techs = Tech.from_text("Django, django ; C++, C#, , Vue.js", limit=3)
        self.assertEqual([t.name for t in techs], ["Django", "C++", "C#"])
        self.assertEqual(Tech.objects.count(), 3)


class AccountTests(GrinTestCase):
    def test_login_with_email_or_username(self):
        self.assertTrue(self.client.login(username="AWA@test.bf", password="motdepasse-solide"))
        self.client.logout()
        self.assertTrue(self.client.login(username="awa", password="motdepasse-solide"))
        self.assertFalse(self.client.login(username="awa", password="faux"))

    def test_signup_rejects_duplicate_email(self):
        response = self.client.post(reverse("accounts:signup"), {
            "username": "autre", "email": "AWA@test.bf", "level": "junior",
            "password1": "un-mot-2-passe!", "password2": "un-mot-2-passe!"})
        self.assertContains(response, "Un compte existe déjà")

    def test_public_pages_render(self):
        for name in ["core:home", "core:members", "projects:list", "collabs:list", "paths:list", "debates:list",
                     "accounts:signup", "accounts:login"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(self.awa.get_absolute_url()).status_code, 200)

    def test_private_pages_require_login(self):
        for name in ["projects:create", "collabs:create", "paths:create", "accounts:edit", "core:notifications"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_security_headers(self):
        response = self.client.get("/")
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])


class StarterDebateTests(TestCase):
    def test_home_shows_the_starter_debate(self):
        page = self.client.get(reverse("core:home"))
        self.assertContains(page, "L&#x27;IA va-t-elle remplacer les développeurs ?")


class DebateTests(GrinTestCase):
    def setUp(self):
        super().setUp()
        self.debate = Debate.objects.create(question="L'IA ?", slug="ia", featured=True)

    def test_anonymous_vote_is_published_at_signup(self):
        self.client.post(reverse("debates:vote", args=["ia"]), {"choice": "no", "back": "home"})
        self.assertEqual(Stance.objects.count(), 0)
        response = self.client.post(reverse("accounts:signup"), {
            "username": "nouveau", "email": "n@test.bf", "level": "learning", "techs_text": "Python",
            "password1": "un-mot-2-passe!", "password2": "un-mot-2-passe!"})
        self.assertRedirects(response, self.debate.get_absolute_url() + "#voter", fetch_redirect_response=False)
        stance = Stance.objects.get()
        self.assertEqual((stance.user.username, stance.choice), ("nouveau", "no"))

    def test_anonymous_vote_is_published_at_login(self):
        self.client.post(reverse("debates:vote", args=["ia"]), {"choice": "yes"})
        self.client.post(reverse("accounts:login"), {"username": "awa", "password": "motdepasse-solide"})
        self.assertEqual(Stance.objects.get().user, self.awa)

    def test_one_stance_per_member_and_tally(self):
        self.client.force_login(self.awa)
        url = reverse("debates:vote", args=["ia"])
        self.client.post(url, {"choice": "yes", "text": "Parce que."})
        self.client.post(url, {"choice": "no"})  # changer d'avis ne doit pas effacer l'argument
        stance = Stance.objects.get()
        self.assertEqual((stance.choice, stance.text), ("no", "Parce que."))
        self.assertEqual([o["percent"] for o in self.debate.tally()], [0, 0, 100])

    def test_invalid_choice_is_ignored(self):
        self.client.force_login(self.awa)
        self.client.post(reverse("debates:vote", args=["ia"]), {"choice": "peut-etre"})
        self.assertEqual(Stance.objects.count(), 0)

    def test_only_one_featured_debate(self):
        Debate.objects.create(question="Autre ?", slug="autre", featured=True)
        self.assertEqual(Debate.objects.filter(featured=True).count(), 1)


class ProjectTests(GrinTestCase):
    def test_create_reencodes_screenshot_and_sets_techs(self):
        response = self.make_project(screenshot=png(3000, 9000))
        project = Project.objects.get()
        self.assertRedirects(response, project.get_absolute_url())
        self.assertTrue(project.screenshot.name.endswith(".webp"))
        with Image.open(project.screenshot.path) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.width, 1440)
            self.assertLessEqual(image.height, 1440 * 1.6 + 1)
        self.assertEqual(project.techs.count(), 2)

    def test_screenshot_must_be_a_real_image(self):
        fake = SimpleUploadedFile("capture.png", b"<script>alert(1)</script>", content_type="image/png")
        response = self.make_project(screenshot=fake)
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_only_screenshot_and_name_are_required(self):
        response = self.make_project(repo_url="", tagline="", techs_text="")
        project = Project.objects.get()
        self.assertRedirects(response, project.get_absolute_url())
        self.assertContains(self.client.get(reverse("projects:list")), "sugu")  # nom affiché à la place du lien

    def test_screenshot_or_terminal_is_required(self):
        response = self.make_project(screenshot="")
        self.assertContains(response, "Ajoute une capture")
        self.assertEqual(Project.objects.count(), 0)

    def test_terminal_output_becomes_the_screenshot(self):
        response = self.make_project(screenshot="", terminal="$ sugu sync\n✔ 128 ventes synchronisées\n" + "x" * 300)
        project = Project.objects.get()
        self.assertRedirects(response, project.get_absolute_url())
        with Image.open(project.screenshot.path) as image:
            self.assertEqual((image.format, image.width), ("WEBP", 1440))

    def test_slugs_are_unique(self):
        self.make_project()
        self.make_project(owner=self.issa)
        self.assertEqual(sorted(Project.objects.values_list("slug", flat=True)), ["sugu", "sugu-2"])

    def test_only_owner_can_edit_or_delete(self):
        self.make_project()
        self.client.force_login(self.issa)
        self.assertEqual(self.client.get(reverse("projects:edit", args=["sugu"])).status_code, 403)
        self.assertEqual(self.client.post(reverse("projects:delete", args=["sugu"])).status_code, 403)
        self.assertEqual(Project.objects.count(), 1)

    def test_pin_lifecycle(self):
        self.make_project()
        url = reverse("projects:pin_create", args=["sugu"])
        self.client.logout()
        self.assertEqual(self.client.post(url, {"x": 10, "y": 10, "kind": "bug", "text": "Cassé ici"}).status_code, 401)

        self.client.force_login(self.issa)
        self.assertEqual(self.client.post(url, {"x": 140, "y": 10, "kind": "bug", "text": "Hors image"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"x": 10, "y": 10, "kind": "bug", "text": " "}).status_code, 400)
        response = self.client.post(url, {"x": 42.5, "y": 10, "kind": "bug", "text": "Cassé ici"})
        self.assertEqual(response.status_code, 201)
        pin = Pin.objects.get()
        self.assertEqual(response.json()["pin"]["x"], 42.5)
        self.assertTrue(Notification.objects.filter(recipient=self.awa).exists())

        # L'auteur du retour ne peut pas le déclarer traité lui-même, le porteur du projet oui.
        resolve = reverse("projects:pin_resolve", args=[pin.pk])
        self.assertEqual(self.client.post(resolve).status_code, 403)
        self.client.force_login(self.awa)
        self.assertTrue(self.client.post(resolve).json()["resolved"])
        self.assertTrue(self.client.post(reverse("projects:pin_delete", args=[pin.pk])).json()["deleted"])

    def test_pin_text_is_escaped_in_page(self):
        self.make_project()
        project = Project.objects.get()
        Pin.objects.create(project=project, author=self.issa, x=1, y=1, text="</script><script>alert(1)</script>")
        html = self.client.get(project.get_absolute_url()).content.decode()
        self.assertNotIn("<script>alert(1)", html)

    def test_applause_toggles(self):
        self.make_project()
        self.client.force_login(self.issa)
        url = reverse("projects:applaud", args=["sugu"])
        self.assertEqual(self.client.post(url).json(), {"active": True, "count": 1})
        self.assertEqual(self.client.post(url).json(), {"active": False, "count": 0})
        self.assertEqual(self.client.get(url).status_code, 405)


class CollabTests(GrinTestCase):
    def setUp(self):
        super().setUp()
        self.request_ = HelpRequest.objects.create(author=self.awa, title="Bloqué", details="Détails", size="days")
        self.commit_url = reverse("collabs:commit", args=[self.request_.pk])
        self.valid = {"days": 3, "message": "Je regarde", "understood": "on", "available": "on"}

    def test_commitment_requires_both_confirmations(self):
        self.client.force_login(self.issa)
        self.client.post(self.commit_url, {"days": 3, "understood": "on"})
        self.assertEqual(Commitment.objects.count(), 0)
        self.client.post(self.commit_url, self.valid)
        commitment = Commitment.objects.get()
        self.assertTrue(commitment.is_running)
        self.assertAlmostEqual((commitment.ends_at - timezone.now()).days, 2, delta=1)

    def test_author_cannot_commit_to_own_request(self):
        self.client.force_login(self.awa)
        self.assertEqual(self.client.post(self.commit_url, self.valid).status_code, 403)

    def test_commitment_expires_and_can_be_renewed(self):
        commitment = Commitment.objects.create(request=self.request_, user=self.issa, days=1)
        Commitment.objects.filter(pk=commitment.pk).update(ends_at=timezone.now() - timedelta(hours=1))
        commitment.refresh_from_db()
        self.assertTrue(commitment.is_expired)
        self.assertFalse(commitment.is_running)
        self.client.force_login(self.issa)
        self.client.post(self.commit_url, self.valid)
        self.assertTrue(Commitment.objects.get().is_running)

    def test_only_author_confirms_kept_and_it_counts_on_profile(self):
        commitment = Commitment.objects.create(request=self.request_, user=self.issa, days=3)
        url = reverse("collabs:kept", args=[self.request_.pk, commitment.pk])
        self.client.force_login(self.issa)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.awa)
        self.client.post(url)
        self.assertEqual(self.issa.kept_count, 1)

    def test_thread_is_reserved_to_people_involved(self):
        url = reverse("collabs:update", args=[self.request_.pk])
        self.client.force_login(self.issa)
        self.assertEqual(self.client.post(url, {"text": "Coucou"}).status_code, 403)
        Commitment.objects.create(request=self.request_, user=self.issa, days=3)
        self.assertEqual(self.client.post(url, {"text": "J'avance"}).status_code, 302)
        self.assertEqual(self.request_.updates.count(), 1)

    def test_release(self):
        Commitment.objects.create(request=self.request_, user=self.issa, days=3)
        self.client.force_login(self.issa)
        self.client.post(reverse("collabs:release", args=[self.request_.pk]))
        self.assertEqual(Commitment.objects.get().status, "released")
        self.assertEqual(self.client.get(self.request_.get_absolute_url()).status_code, 200)


class PathTests(GrinTestCase):
    def setUp(self):
        super().setUp()
        self.path = Path.objects.create(author=self.awa, title="Apprendre Git")

    def add_step(self, title="Une étape"):
        return self.client.post(reverse("paths:add_step", args=[self.path.pk]), {"title": title})

    def test_steps_are_capped(self):
        self.client.force_login(self.issa)
        for number in range(MAX_STEPS + 2):
            self.add_step(f"Étape {number}")
        self.assertEqual(self.path.steps.count(), MAX_STEPS)
        self.assertEqual(list(self.path.steps.values_list("position", flat=True)), list(range(1, MAX_STEPS + 1)))

    def test_explanation_must_be_a_real_summary(self):
        self.client.force_login(self.issa)
        self.add_step()
        step = Step.objects.get()
        url = reverse("paths:explain", args=[step.pk])
        self.client.post(url, {"summary": "Voir le lien", "resource_url": "https://exemple.bf"})
        self.assertEqual(step.explanations.count(), 0)
        self.client.post(url, {"summary": "Un commit est une photo complète du projet, reliée à la précédente."})
        self.assertEqual(step.explanations.count(), 1)

    def test_done_toggle_reports_progress_and_thanks_rules(self):
        self.client.force_login(self.issa)
        self.add_step("A")
        self.add_step("B")
        first = self.path.steps.first()
        result = self.client.post(reverse("paths:done", args=[first.pk])).json()
        self.assertEqual((result["done"], result["total"], result["percent"]), (1, 2, 50))
        self.client.post(reverse("paths:explain", args=[first.pk]), {"summary": "x" * 60})
        thank = reverse("paths:thank", args=[first.explanations.get().pk])
        self.assertEqual(self.client.post(thank).status_code, 400)  # pas de merci à soi-même
        self.client.force_login(self.awa)
        self.assertEqual(self.client.post(thank).json(), {"active": True, "count": 1})
        self.assertEqual(self.client.get(self.path.get_absolute_url()).status_code, 200)

    def test_path_author_does_not_trace_steps(self):
        self.client.force_login(self.awa)
        page = self.client.get(self.path.get_absolute_url())
        self.assertNotContains(page, "Ajouter l'étape")
        self.assertContains(page, "Tu n'as rien à faire")
        self.add_step()
        self.assertEqual(self.path.steps.count(), 0)
        self.client.force_login(self.issa)
        self.add_step()
        step = Step.objects.get()
        self.client.force_login(self.awa)
        self.assertNotContains(self.client.get(self.path.get_absolute_url()), "Expliquer cette étape")
        self.client.post(reverse("paths:explain", args=[step.pk]), {"summary": "x" * 60})
        self.assertEqual(step.explanations.count(), 0)

    def test_only_path_author_reorders(self):
        self.client.force_login(self.issa)
        self.add_step("A")
        self.add_step("B")
        second = self.path.steps.last()
        url = reverse("paths:move_step", args=[second.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.awa)
        self.client.post(url)
        self.assertEqual([s.title for s in self.path.steps.all()], ["B", "A"])

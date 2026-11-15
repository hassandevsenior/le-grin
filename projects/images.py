"""
Traitement des captures d'écran envoyées par les membres.

On ne stocke jamais le fichier reçu tel quel : il est ouvert, vérifié, réduit
puis réencodé en WebP. Ça écarte les faux fichiers image, supprime les
métadonnées, et allège les pages pour les connexions lentes.
"""

import uuid
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_WIDTH = 1440
MAX_RATIO = 1.6  # hauteur maximale = 1,6 x la largeur : on garde le haut d'une longue page
MAX_SOURCE_PIXELS = 40_000_000
MIN_WIDTH = 320
TARGET_MAX_BYTES = 220 * 1024  # cible de compression WebP (~220 Ko) pour garder le mur rapide
PAPER_BG = (245, 249, 238)


def _flatten_to_rgb(image):
    """Aplatit proprement la transparence sur le papier clair du Grin au lieu d'un fond noir."""
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode in ("RGBA", "LA"):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (*PAPER_BG, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def _encode_webp(image, initial_quality=78, min_quality=58):
    """Compresse en WebP (method=6) et ajuste la qualité si l'image reste volumineuse."""
    quality = initial_quality
    data = b""
    while quality >= min_quality:
        buffer = BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=6)
        data = buffer.getvalue()
        if len(data) <= TARGET_MAX_BYTES:
            break
        quality -= 8
    return ContentFile(data, name=f"{uuid.uuid4().hex}.webp")


def process_screenshot(upload):
    """Valide `upload`, nettoie les métadonnées EXIF et renvoie un ContentFile WebP allégé."""
    if upload.size > settings.MAX_SCREENSHOT_BYTES:
        raise ValidationError("Cette image est trop lourde (5 Mo maximum).")
    try:
        upload.seek(0)
        image = Image.open(upload)
        if image.width * image.height > MAX_SOURCE_PIXELS:
            raise ValidationError("Cette image est trop grande.")
        image.load()
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("Ce fichier n'est pas une image lisible (PNG, JPEG ou WebP).")

    if image.width < MIN_WIDTH:
        raise ValidationError("Cette capture est trop petite pour être lisible (320 px minimum).")

    image = _flatten_to_rgb(image)
    max_height = int(image.width * MAX_RATIO)
    if image.height > max_height:
        image = image.crop((0, 0, image.width, max_height))
    if image.width > MAX_WIDTH:
        image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)), Image.LANCZOS)

    return _encode_webp(image, initial_quality=78, min_quality=58)


# ---------- Projets sans interface graphique ----------
# Une API, une bibliothèque ou un outil en ligne de commande n'a pas d'écran à capturer.
# Le membre colle une sortie de terminal ou un extrait de code, et on en fait une
# « capture » de terminal : le mur reste visuel et les retours s'y épinglent comme ailleurs.

from pathlib import Path as _Path  # noqa: E402
import textwrap  # noqa: E402

from PIL import ImageDraw, ImageFont  # noqa: E402

TERMINAL_FONT = _Path(__file__).resolve().parent / "fonts" / "JetBrainsMono-Regular.ttf"
TERMINAL_MAX_LINES = 60
TERMINAL_WIDTH = 1440
_BG, _BAR, _INK, _DIM = (14, 20, 11), (28, 38, 22), (220, 236, 208), (122, 216, 90)
_SUBSTITUTES = {"✔": "✓", "✖": "✗", "❌": "✗", "✅": "✓", "⚡": "!"}


def _glyph(font, char, cache, missing):
    """Retire un caractère absent de la police (émoji…) au lieu d'afficher un carré vide."""
    if char not in cache:
        probe = Image.new("L", (64, 64))
        ImageDraw.Draw(probe).text((4, 4), char, font=font, fill=255)
        cache[char] = char if char.isspace() or probe.tobytes() != missing else ""
    return cache[char]


def render_terminal(text):
    """Dessine `text` dans une fenêtre de terminal et renvoie un ContentFile WebP."""
    size, pad, bar = 26, 56, 64
    font = ImageFont.truetype(str(TERMINAL_FONT), size)
    char_width = font.getlength("M")
    columns = int((TERMINAL_WIDTH - 2 * pad) // char_width)
    line_height = round(size * 1.55)

    probe = Image.new("L", (64, 64))
    ImageDraw.Draw(probe).text((4, 4), "\U0010FFFD", font=font, fill=255)
    missing, cache = probe.tobytes(), {}
    text = "".join(_glyph(font, _SUBSTITUTES.get(c, c), cache, missing) for c in text.expandtabs(4))

    lines = []
    for raw in text.splitlines() or [""]:
        indent = " " * (len(raw) - len(raw.lstrip(" ")))
        lines.extend(textwrap.wrap(raw.strip(" "), columns, initial_indent=indent,
                                   subsequent_indent=indent + "  ") or [""])
    if len(lines) > TERMINAL_MAX_LINES:
        lines = lines[: TERMINAL_MAX_LINES - 1] + ["…"]

    height = max(round(TERMINAL_WIDTH * 0.62), bar + 2 * pad + line_height * len(lines))
    image = Image.new("RGB", (TERMINAL_WIDTH, height), _BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, TERMINAL_WIDTH, bar), fill=_BAR)
    for index, colour in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 36 + index * 34
        draw.ellipse((cx - 9, bar // 2 - 9, cx + 9, bar // 2 + 9), fill=colour)
    for index, line in enumerate(lines):
        is_prompt = line.lstrip().startswith(("$", ">", "#", "❯"))
        draw.text((pad, bar + pad + index * line_height), line, font=font, fill=_DIM if is_prompt else _INK)

    return _encode_webp(image, initial_quality=80, min_quality=65)

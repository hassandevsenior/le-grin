/* Le Grin — JavaScript natif, sans dépendance.
   Chaque bloc améliore une page qui fonctionne déjà sans lui (sauf la pose de retours). */
(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const loggedIn = Boolean(document.body.dataset.user);

  function goToLogin() {
    const next = encodeURIComponent(location.pathname + location.hash);
    location.href = `${document.body.dataset.loginUrl}?next=${next}`;
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  /** POST vers le serveur ; renvoie le JSON, ou lève une Error avec un message lisible. */
  async function post(url, data) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: data ? new URLSearchParams(data) : null,
        credentials: "same-origin",
      });
    } catch {
      throw new Error("Connexion perdue. Vérifie ton réseau et réessaie.");
    }
    if (response.status === 401) {
      goToLogin();
      throw new Error("Connexion requise.");
    }
    const json = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(json.error || "Ça n'a pas marché. Réessaie.");
    return json;
  }

  function toast(text, isError = false) {
    let box = $(".toasts");
    if (!box) {
      box = document.createElement("div");
      box.className = "toasts";
      box.setAttribute("role", "status");
      document.body.append(box);
    }
    const item = document.createElement("p");
    item.className = `toast${isError ? " toast-error" : ""}`;
    item.textContent = text;
    box.append(item);
    dismissLater(item);
  }

  function dismissLater(item) {
    setTimeout(() => {
      item.classList.add("is-leaving");
      setTimeout(() => item.remove(), 450);
    }, 5000);
  }
  $$(".toast").forEach(dismissLater);

  /* ---------- Boutons à bascule : bravo, merci, étape franchie ---------- */
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-toggle-url]");
    if (!button) return;
    if (!loggedIn) return goToLogin();
    button.disabled = true;
    try {
      const result = await post(button.dataset.toggleUrl);
      button.setAttribute("aria-pressed", String(result.active));
      const count = $("[data-count]", button);
      if (count && "count" in result) count.textContent = result.count;
      if (result.active) {
        button.classList.remove("is-pop");
        void button.offsetWidth; // relance l'animation
        button.classList.add("is-pop");
      }
      if ("stepToggle" in button.dataset) updateProgress(button, result);
    } catch (error) {
      toast(error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  function updateProgress(button, result) {
    button.closest(".step").classList.toggle("is-done", result.active);
    const bar = $("[data-progress-bar]");
    const text = $("[data-progress-text]");
    if (bar) bar.style.width = `${result.percent}%`;
    if (text) text.textContent = `${result.done} sur ${result.total}`;
    if (result.active && result.done === result.total) toast("Parcours terminé. Bravo, vraiment.");
  }

  /* ---------- Petits conforts ---------- */
  $$("[data-autosubmit]").forEach((select) => select.addEventListener("change", () => select.form.submit()));

  document.addEventListener("submit", (event) => {
    const message = event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });

  document.addEventListener("click", (event) => {
    $$("details.menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });

  // Compteur discret sur les zones de texte limitées.
  $$("textarea[maxlength]").forEach((area) => {
    const label = area.id && $(`label[for="${area.id}"]`);
    if (!label) return;
    const counter = document.createElement("span");
    counter.className = "counter";
    label.append(counter);
    const refresh = () => {
      const left = area.maxLength - area.value.length;
      counter.textContent = left <= area.maxLength * 0.3 ? `${left} restants` : "";
    };
    area.addEventListener("input", refresh);
    refresh();
  });

  /* ---------- Dépôt de la capture : glisser, coller ou choisir ---------- */
  const drop = $("[data-drop]");
  if (drop) {
    const input = $("input[type=file]", drop);
    const preview = $("[data-drop-preview]", drop);
    const MAX_BYTES = 5 * 1024 * 1024;

    const show = () => {
      const file = input.files[0];
      if (!file) return;
      if (file.size > MAX_BYTES) {
        input.value = "";
        return toast("Cette image dépasse 5 Mo. Essaie une capture plus légère.", true);
      }
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
      $("[data-drop-text]", drop).innerHTML = "<small>Clique, dépose ou colle pour changer de capture.</small>";
    };
    input.addEventListener("change", show);
    ["dragenter", "dragover"].forEach((type) => drop.addEventListener(type, () => drop.classList.add("is-over")));
    ["dragleave", "drop"].forEach((type) => drop.addEventListener(type, () => drop.classList.remove("is-over")));

    document.addEventListener("paste", (event) => {
      const file = [...event.clipboardData.files].find((item) => item.type.startsWith("image/"));
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      show();
    });
  }

  /* ---------- Retours épinglés sur la capture ---------- */
  const board = $("[data-board]");
  if (board) {
    const canvas = $("[data-canvas]", board);
    const layer = $("[data-layer]", board);
    const composer = $("[data-composer]", board);
    const composerError = $("[data-composer-error]", board);
    const toggle = $("[data-pin-toggle]", board);
    const hint = $("[data-hint]", board);
    const list = $("[data-pin-list]");
    const isOwner = board.dataset.owner === "1";
    let pins = JSON.parse($("#pins-data").textContent);
    let draft = null; // { x, y, marker } pendant la rédaction

    function el(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }

    function makeMarker(x, y, label, className) {
      const marker = el("button", `marker ${className}`);
      marker.type = "button";
      marker.style.left = `${x}%`;
      marker.style.top = `${y}%`;
      marker.append(el("span", "", label));
      return marker;
    }

    function render() {
      layer.replaceChildren();
      list.replaceChildren();
      pins.forEach((pin, index) => {
        const number = index + 1;
        const state = pin.resolved ? " is-resolved" : "";

        const marker = makeMarker(pin.x, pin.y, number, `kind-${pin.kind}${state}`);
        marker.dataset.pin = pin.id;
        marker.setAttribute("aria-label", `Retour ${number} de ${pin.author} : ${pin.text}`);
        layer.append(marker);

        const item = el("li", `pin-item kind-${pin.kind}${state}`);
        item.id = `pin-${pin.id}`;
        item.dataset.pin = pin.id;
        const body = el("div");
        body.append(el("p", "", pin.text), el("small", "", `${pin.author} · ${pin.kindLabel}`));
        const tools = el("div", "pin-tools");
        if (isOwner) tools.append(toolButton(pin.resolved ? "Rouvrir" : "Pris en compte", "resolve"));
        if (isOwner || pin.mine) tools.append(toolButton("Supprimer", "delete"));
        if (tools.children.length) body.append(tools);
        item.append(el("span", "pin-dot", number), body);
        list.append(item);
      });
      $("[data-pin-total]").textContent = pins.length;
      $("[data-pin-empty]").hidden = pins.length > 0;
    }

    function toolButton(label, action) {
      const button = el("button", "", label);
      button.type = "button";
      button.dataset.action = action;
      return button;
    }

    function activate(id, scrollTo) {
      $$(".is-active", board.parentElement).forEach((node) => node.classList.remove("is-active"));
      const marker = $(`.marker[data-pin="${id}"]`, layer);
      const item = $(`.pin-item[data-pin="${id}"]`, list);
      if (!marker || !item) return;
      marker.classList.add("is-active");
      item.classList.add("is-active");
      (scrollTo === "marker" ? marker : item).scrollIntoView({ block: "nearest", behavior: "smooth" });
    }

    function setPinning(on) {
      board.classList.toggle("is-pinning", on);
      toggle.setAttribute("aria-pressed", String(on));
      $("[data-pin-toggle-label]", toggle).textContent = on ? "Annuler" : "Poser un retour";
      hint.hidden = !on;
      if (!on) closeComposer();
    }

    function closeComposer() {
      composer.hidden = true;
      composerError.hidden = true;
      if (draft) draft.marker.remove();
      draft = null;
    }

    function openComposer(event) {
      const box = canvas.getBoundingClientRect();
      const px = event.clientX - box.left;
      const py = event.clientY - box.top;
      if (draft) draft.marker.remove();
      draft = {
        x: Math.round((px / box.width) * 1000) / 10,
        y: Math.round((py / box.height) * 1000) / 10,
        marker: makeMarker(0, 0, "+", "is-draft"),
      };
      draft.marker.style.left = `${draft.x}%`;
      draft.marker.style.top = `${draft.y}%`;
      layer.append(draft.marker);

      composer.hidden = false;
      const width = composer.offsetWidth;
      const height = composer.offsetHeight;
      const left = Math.max(8, Math.min(px - width / 2, box.width - width - 8));
      // Sous l'épingle si la place existe, sinon au-dessus.
      const top = py + height + 16 < box.height ? py + 12 : Math.max(8, py - height - 44);
      composer.style.left = `${left}px`;
      composer.style.top = `${top}px`;
      composer.elements.text.focus();
    }

    toggle.addEventListener("click", () => {
      if (!loggedIn) return goToLogin();
      setPinning(!board.classList.contains("is-pinning"));
    });

    canvas.addEventListener("click", (event) => {
      const marker = event.target.closest(".marker[data-pin]");
      if (marker) return activate(marker.dataset.pin, "item");
      if (event.target.closest("[data-composer]")) return;
      if (board.classList.contains("is-pinning")) openComposer(event);
    });

    $("[data-composer-cancel]", composer).addEventListener("click", closeComposer);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && board.classList.contains("is-pinning")) setPinning(false);
    });

    composer.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = $("button:not([type=button])", composer);
      submit.disabled = true;
      try {
        const result = await post(board.dataset.createUrl, {
          x: draft.x,
          y: draft.y,
          kind: composer.elements.kind.value,
          text: composer.elements.text.value,
        });
        pins.push(result.pin);
        composer.reset();
        setPinning(false);
        render();
        activate(result.pin.id, "item");
        toast("Retour posé. Merci pour le coup d'œil.");
      } catch (error) {
        composerError.textContent = error.message;
        composerError.hidden = false;
      } finally {
        submit.disabled = false;
      }
    });

    list.addEventListener("click", async (event) => {
      const item = event.target.closest(".pin-item");
      if (!item) return;
      const id = Number(item.dataset.pin);
      const action = event.target.dataset.action;
      if (!action) return activate(id, "marker");
      const target = pins.find((pin) => pin.id === id);
      try {
        if (action === "resolve") {
          const result = await post(target.resolveUrl);
          target.resolved = result.resolved;
        } else if (window.confirm("Supprimer ce retour ?")) {
          await post(target.deleteUrl);
          pins = pins.filter((pin) => pin.id !== id);
        }
        render();
      } catch (error) {
        toast(error.message, true);
      }
    });

    render();
    const linked = location.hash.match(/^#pin-(\d+)$/);
    if (linked) activate(linked[1], "marker");
  }
})();

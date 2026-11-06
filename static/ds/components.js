/* Design system perso — comportements des composants.
   Sans dépendance. Tout passe par des attributs HTML :
   - Thème       : <button data-ds-theme-toggle>                 (sombre ⇄ clair, mémorisé)
   - Menu        : <div class="ds-dropdown"><button aria-haspopup="menu" aria-expanded="false" aria-controls="m1">…</button>
                   <div class="ds-menu" id="m1" role="menu" hidden>…</div></div>
   - Onglets     : <div data-ds-tabs><div class="ds-tabs-list" role="tablist"><button class="ds-tab" role="tab" aria-controls="p1">…
   - Fenêtre     : <button data-ds-open="id-du-dialog">  et dans le <dialog> : <button data-ds-close>
   - Notification: DS.flag({ title, message, type: "success" | "warning" | "danger" | "info" })
   - Segmenté    : <div class="ds-segmented" role="group"><button aria-pressed="true">…
   - Étiquette   : bouton [data-ds-remove] dans .ds-tag : retire l'étiquette */
(function () {
  const root = document.documentElement;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");

  /* Joue l'animation de sortie (attribut data-closing / data-leaving), puis termine */
  function animateOut(el, attr, done) {
    if (reduced.matches) { done(); return; }
    el.setAttribute(attr, "");
    let finished = false;
    const end = () => { if (finished) return; finished = true; el.removeAttribute(attr); done(); };
    el.addEventListener("animationend", end, { once: true });
    setTimeout(end, 400); // filet de sécurité
  }

  /* ---------- Thème ---------- */
  function setTheme(theme, remember) {
    root.dataset.theme = theme;
    if (remember) { try { localStorage.setItem("ds-theme", theme); } catch (e) {} }
    document.querySelectorAll("[data-ds-theme-toggle]").forEach(btn => {
      btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
      const label = btn.querySelector("[data-ds-theme-label]");
      if (label) label.textContent = theme === "light" ? "Thème sombre" : "Thème clair";
      const use = btn.querySelector("use");
      if (use) use.setAttribute("href", theme === "light" ? "#ds-icon-moon" : "#ds-icon-sun");
    });
    document.dispatchEvent(new CustomEvent("ds:themechange", { detail: { theme } }));
  }
  let saved = null;
  try { saved = localStorage.getItem("ds-theme"); } catch (e) {}
  if (!root.dataset.theme) setTheme(saved || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"), false);

  /* ---------- Menus ---------- */
  function closeMenus(except) {
    document.querySelectorAll('[aria-haspopup="menu"][aria-expanded="true"]').forEach(btn => {
      if (btn === except) return;
      btn.setAttribute("aria-expanded", "false");
      const menu = document.getElementById(btn.getAttribute("aria-controls"));
      if (menu && !menu.hidden) animateOut(menu, "data-closing", () => { if (btn.getAttribute("aria-expanded") !== "true") menu.hidden = true; });
    });
  }
  function menuItems(menu) { return [...menu.querySelectorAll('.ds-menu-item:not([disabled])')]; }

  document.addEventListener("click", e => {
    const trigger = e.target.closest('[aria-haspopup="menu"]');
    if (trigger) {
      const menu = document.getElementById(trigger.getAttribute("aria-controls"));
      const open = trigger.getAttribute("aria-expanded") !== "true";
      closeMenus(trigger);
      trigger.setAttribute("aria-expanded", String(open));
      if (menu) {
        if (open) { menu.removeAttribute("data-closing"); menu.hidden = false; menuItems(menu)[0]?.focus(); }
        else animateOut(menu, "data-closing", () => { menu.hidden = true; });
      }
      return;
    }
    const item = e.target.closest(".ds-menu .ds-menu-item");
    if (item) {
      if (item.getAttribute("role") === "menuitemradio") {
        item.closest(".ds-menu").querySelectorAll('[role="menuitemradio"]').forEach(i => i.setAttribute("aria-checked", String(i === item)));
      }
      const menu = item.closest(".ds-menu");
      const btn = document.querySelector('[aria-controls="' + menu.id + '"]');
      if (btn && !menu.classList.contains("ds-menu--static")) { closeMenus(); btn.focus(); }
      return;
    }
    if (!e.target.closest(".ds-menu")) closeMenus();
  });

  document.addEventListener("keydown", e => {
    const menu = e.target.closest(".ds-menu");
    if (menu && ["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      const items = menuItems(menu);
      const i = items.indexOf(document.activeElement);
      const next = { ArrowDown: (i + 1) % items.length, ArrowUp: (i - 1 + items.length) % items.length, Home: 0, End: items.length - 1 }[e.key];
      items[next]?.focus();
    }
    if (e.key === "Escape") {
      const open = document.querySelector('[aria-haspopup="menu"][aria-expanded="true"]');
      if (open) { closeMenus(); open.focus(); }
    }
  });

  /* ---------- Onglets ---------- */
  function selectTab(tab, focus) {
    const list = tab.closest('[role="tablist"]');
    list.querySelectorAll('[role="tab"]').forEach(t => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !on;
    });
    if (focus) tab.focus();
    placeIndicator(list);
  }

  /* ---------- Indicateur glissant (onglets, boutons segmentés) ---------- */
  function placeIndicator(box, instant) {
    const current = box.querySelector('[aria-selected="true"], [aria-pressed="true"]');
    if (!current) return;
    let ind = box.querySelector(":scope > .ds-indicator");
    if (!ind) {
      ind = document.createElement("span");
      ind.className = "ds-indicator";
      ind.setAttribute("aria-hidden", "true");
      box.prepend(ind);
      box.setAttribute("data-indicator", "");
      instant = true;
    }
    ind.toggleAttribute("data-instant", !!instant);
    ind.style.width = current.offsetWidth + "px";
    ind.style.height = current.offsetHeight + "px";
    ind.style.transform = "translate(" + current.offsetLeft + "px, " + current.offsetTop + "px)";
    if (instant) requestAnimationFrame(() => ind.removeAttribute("data-instant"));
  }
  function initIndicators() {
    document.querySelectorAll(".ds-tabs-list, .ds-segmented").forEach(box => {
      placeIndicator(box, true);
      if ("ResizeObserver" in window) new ResizeObserver(() => placeIndicator(box, true)).observe(box);
    });
  }
  document.addEventListener("click", e => {
    const tab = e.target.closest('[role="tab"]');
    if (tab) selectTab(tab, false);
  });
  document.addEventListener("keydown", e => {
    const tab = e.target.closest('[role="tab"]');
    if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const tabs = [...tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]')];
    const i = tabs.indexOf(tab);
    const next = { ArrowRight: (i + 1) % tabs.length, ArrowLeft: (i - 1 + tabs.length) % tabs.length, Home: 0, End: tabs.length - 1 }[e.key];
    selectTab(tabs[next], true);
  });

  /* ---------- Fenêtres (<dialog>) ---------- */
  document.addEventListener("click", e => {
    const opener = e.target.closest("[data-ds-open]");
    if (opener) {
      const dlg = document.getElementById(opener.dataset.dsOpen);
      if (dlg?.showModal) dlg.showModal();
      return;
    }
    const closer = e.target.closest("[data-ds-close]");
    if (closer) { const d = closer.closest("dialog"); if (d) closeDialog(d, closer.value || ""); return; }
    // Clic sur le voile : ferme la fenêtre
    if (e.target instanceof HTMLDialogElement && e.target.open) {
      const r = e.target.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (!inside) closeDialog(e.target, "");
    }
  });
  function closeDialog(dlg, value) {
    if (!dlg.open || dlg.hasAttribute("data-closing")) return;
    animateOut(dlg, "data-closing", () => dlg.close(value));
  }
  document.addEventListener("cancel", e => {
    if (e.target instanceof HTMLDialogElement) { e.preventDefault(); closeDialog(e.target, ""); }
  }, true);
  document.addEventListener("submit", e => {
    const form = e.target;
    const dlg = form.closest("dialog");
    if (dlg && form.method === "dialog") { e.preventDefault(); closeDialog(dlg, e.submitter?.value || ""); }
  }, true);

  /* ---------- Boutons segmentés ---------- */
  document.addEventListener("click", e => {
    const btn = e.target.closest(".ds-segmented button");
    if (!btn) return;
    btn.parentElement.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b === btn)));
    placeIndicator(btn.parentElement);
  });

  /* ---------- Étiquettes retirables ---------- */
  document.addEventListener("click", e => {
    const btn = e.target.closest(".ds-tag [data-ds-remove]");
    if (btn) { const tag = btn.closest(".ds-tag"); animateOut(tag, "data-leaving", () => tag.remove()); }
  });

  /* ---------- Thème : bouton ---------- */
  document.addEventListener("click", e => {
    if (e.target.closest("[data-ds-theme-toggle]")) setTheme(root.dataset.theme === "light" ? "dark" : "light", true);
  });
  document.addEventListener("DOMContentLoaded", () => { setTheme(root.dataset.theme, false); initIndicators(); });
  window.addEventListener("load", () => document.querySelectorAll(".ds-tabs-list, .ds-segmented").forEach(b => placeIndicator(b, true)));

  /* ---------- Notifications ---------- */
  const FLAG_ICON = { success: "success", warning: "warning", danger: "error", info: "info" };
  function flag({ title, message = "", type = "info", duration = 6000 } = {}) {
    let region = document.querySelector(".ds-flag-region");
    if (!region) {
      region = document.createElement("div");
      region.className = "ds-flag-region";
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      document.body.append(region);
    }
    const el = document.createElement("div");
    el.className = "ds-flag ds-flag--" + type;
    el.innerHTML = '<svg class="ds-icon" aria-hidden="true"><use href="#ds-icon-' + FLAG_ICON[type] + '"></use></svg>'
      + '<div><strong></strong><p></p></div>'
      + '<button class="ds-button ds-button--subtle ds-button--sm ds-icon-button" type="button" aria-label="Fermer"><svg class="ds-icon ds-icon--sm" aria-hidden="true"><use href="#ds-icon-close"></use></svg></button>';
    el.querySelector("strong").textContent = title;
    const p = el.querySelector("p");
    if (message) p.textContent = message; else p.remove();
    const remove = () => { if (el.isConnected && !el.hasAttribute("data-leaving")) animateOut(el, "data-leaving", () => el.remove()); };
    el.querySelector("button").addEventListener("click", remove);
    region.append(el);
    if (duration) setTimeout(remove, duration);
    return el;
  }

  window.DS = { flag, setTheme, closeDialog, placeIndicator };
})();

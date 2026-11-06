/* NovaServices : client de l'API, session, formats et petits outils partagés par toutes les pages. */
const Nova = (() => {
  const TOKEN_KEY = "nova-token";
  const NBSP = " ";
  // Le bloc JSON est placé avant ce script dans le <head> : il est déjà lisible.
  const meta = JSON.parse(document.getElementById("nova-meta").textContent);
  let user = null;

  /* ---------- Session ---------- */
  const store = {
    get() { try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; } },
    set(token) { try { localStorage.setItem(TOKEN_KEY, token); } catch (e) {} },
    clear() { try { localStorage.removeItem(TOKEN_KEY); } catch (e) {} },
  };

  function goToLogin() {
    const next = location.pathname + location.search;
    location.replace("/connexion" + (next !== "/" ? "?suite=" + encodeURIComponent(next) : ""));
  }

  function logout() {
    store.clear();
    location.href = "/connexion";
  }

  class ApiError extends Error {
    constructor(status, body) {
      super((body && body.erreur) || "Le serveur ne répond pas. Réessaie dans un instant.");
      this.status = status;
      this.fields = (body && body.champs) || {};
    }
  }

  async function api(path, { method = "GET", body, auth = true } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const token = store.get();
    if (auth && token) headers.Authorization = "Bearer " + token;
    let response;
    try {
      response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (e) {
      throw new ApiError(0, null);
    }
    if (response.status === 401 && auth) {
      store.clear();
      goToLogin();
      throw new ApiError(401, null);
    }
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(response.status, data);
    return data;
  }

  /* Vérifie la session, remplit la coque et renvoie l'utilisateur. */
  async function boot({ admin = false } = {}) {
    if (!store.get()) { goToLogin(); return new Promise(() => {}); }
    user = await api("/api/auth/me");
    const shell = document.querySelector("[data-shell]");
    document.querySelectorAll("[data-user-name]").forEach((el) => { el.textContent = user.name; });
    document.querySelectorAll("[data-user-role]").forEach((el) => { el.textContent = meta.roles[user.role]; });
    document.querySelectorAll("[data-user-initials]").forEach((el) => { el.textContent = initials(user.name); });
    if (user.role === "admin") {
      document.querySelectorAll("[data-admin-only]").forEach((el) => { el.hidden = false; });
      document.querySelectorAll("[data-admin-text]").forEach((el) => { el.textContent = el.dataset.adminText; });
    }
    if (shell) shell.hidden = false;
    if (admin && user.role !== "admin") {
      document.getElementById("contenu").innerHTML = emptyState("lock", "Page réservée au support",
        "Cette page sert aux administrateurs. Tes demandes sont dans l'accueil.", '<a class="ds-button" href="/">Retour à l\'accueil</a>');
      return new Promise(() => {});
    }
    return user;
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-logout]")) { e.preventDefault(); logout(); }
    const toggle = e.target.closest("[data-nav-toggle]");
    if (toggle) {
      const open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
    }
  });

  /* ---------- Formats ---------- */
  const dateFmt = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });
  const timeFmt = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const numFmt = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

  const parse = (iso) => (iso ? new Date(iso) : null);
  const fmt = {
    num: (n) => numFmt.format(n),
    date: (iso) => dateFmt.format(parse(iso)),
    time: (iso) => timeFmt.format(parse(iso)),
    dateTime: (iso) => `${dateFmt.format(parse(iso))} à ${timeFmt.format(parse(iso))}`,
    /* « à l'instant », « il y a 12 min », « il y a 3 h », « hier », « il y a 4 j », puis la date */
    ago(iso) {
      const minutes = Math.round((Date.now() - parse(iso)) / 60000);
      if (minutes < 1) return "à l'instant";
      if (minutes < 60) return `il y a ${minutes}${NBSP}min`;
      const hours = Math.round(minutes / 60);
      if (hours < 24) return `il y a ${hours}${NBSP}h`;
      const days = Math.round(hours / 24);
      if (days === 1) return "hier";
      if (days < 30) return `il y a ${days}${NBSP}j`;
      return `le ${dateFmt.format(parse(iso))}`;
    },
    /* Une durée en heures : « 45 min », « 6 h », « 1 j 13 h » */
    hours(h) {
      if (h == null) return "—";
      if (h < 1) return `${Math.round(h * 60)}${NBSP}min`;
      if (h < 24) return `${Math.round(h)}${NBSP}h`;
      const days = Math.floor(h / 24), rest = Math.round(h % 24);
      return rest ? `${days}${NBSP}j ${rest}${NBSP}h` : `${days}${NBSP}j`;
    },
    plural: (n, one, many) => `${numFmt.format(n)}${NBSP}${n > 1 ? many : one}`,
  };

  /* ---------- Rendu ---------- */
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const icon = (name, cls = "") => `<svg class="ds-icon ${cls}" aria-hidden="true"><use href="#ds-icon-${name}"></use></svg>`;
  const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
  const label = (kind, key) => (meta[kind] && meta[kind][key]) || key;

  /* Statut : un mot sur fond gris, comme le veut le design system. */
  const STATUS_ICON = { ouvert: "info", en_cours: "clock", en_attente: "send", resolu: "check", ferme: "check" };
  function statusLozenge(status) {
    return `<span class="ds-lozenge">${icon(STATUS_ICON[status] || "info")}${esc(label("statuses", status))}</span>`;
  }
  function priorityLozenge(priority) {
    if (priority === "critique") return `<span class="ds-lozenge ds-lozenge--critique">${icon("warning")}Critique</span>`;
    return `<span class="ds-lozenge">${esc(label("priorities", priority))}</span>`;
  }

  function emptyState(iconName, title, text, actions = "") {
    return `<div class="ds-empty">${icon(iconName)}<h3>${esc(title)}</h3><p>${esc(text)}</p>${actions ? `<div class="ds-inline">${actions}</div>` : ""}</div>`;
  }

  /* Erreur dans le bloc qui a échoué, avec un bouton pour réessayer. */
  function blockError(el, error, retry) {
    el.innerHTML = `<p class="block-error">${icon("error")}<span>${esc(error.message)}</span><button class="ds-button ds-button--subtle ds-button--sm" type="button">Réessayer</button></p>`;
    el.querySelector("button").addEventListener("click", retry);
  }

  /* Affiche les erreurs renvoyées par l'API sous chaque champ (name="…"). */
  function showErrors(form, error) {
    form.querySelectorAll("[aria-invalid]").forEach((f) => f.removeAttribute("aria-invalid"));
    form.querySelectorAll(".ds-error-message[data-for]").forEach((m) => { m.hidden = true; });
    let first = null;
    for (const [name, message] of Object.entries(error.fields || {})) {
      const field = form.elements[name];
      const slot = form.querySelector(`.ds-error-message[data-for="${name}"]`);
      if (field) { field.setAttribute("aria-invalid", "true"); first = first || field; }
      if (slot) { slot.querySelector("span").textContent = message; slot.hidden = false; }
    }
    const general = form.querySelector("[data-form-error]");
    if (general) {
      general.hidden = Boolean(first);
      general.querySelector("span").textContent = error.message;
    }
    if (first) first.focus();
  }

  function busy(button, on) {
    button.setAttribute("aria-busy", String(on));
    button.disabled = on;
  }

  const flag = (title, message, type = "success") => window.DS && DS.flag({ title, message, type });

  return {
    api, boot, logout, store, ApiError, fmt, esc, icon, initials, label, statusLozenge, priorityLozenge,
    emptyState, blockError, showErrors, busy, flag,
    meta,
    get user() { return user; },
  };
})();

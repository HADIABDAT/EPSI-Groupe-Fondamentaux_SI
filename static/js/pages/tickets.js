/* Liste des tickets : filtres dans l'adresse (on peut partager un lien filtré), compteurs par statut, pages. */
(async () => {
  const { api, fmt, esc, label, statusLozenge, priorityLozenge, emptyState, blockError } = Nova;
  const user = await Nova.boot();
  const isAdmin = user.role === "admin";
  const form = document.querySelector("[data-filters]");
  const rows = document.querySelector("[data-rows]");
  const PER_PAGE = 20;
  const FIELDS = ["q", "priority", "category", "assigned", "sort"];

  document.querySelector("[data-title]").textContent = isAdmin ? "Tickets" : "Mes demandes";
  document.title = (isAdmin ? "Tickets" : "Mes demandes") + " · NovaServices";

  // Les administrateurs peuvent filtrer par technicien.
  if (isAdmin) {
    const admins = await api("/api/users?role=admin&active=1").catch(() => []);
    form.elements.assigned.insertAdjacentHTML("beforeend",
      admins.filter((a) => a.id !== user.id).map((a) => `<option value="${a.id}">Assignés à ${esc(a.name)}</option>`).join(""));
  }

  const params = new URLSearchParams(location.search);
  const state = { status: params.get("status") || "actifs", page: Number(params.get("page")) || 1 };
  for (const f of FIELDS) state[f] = params.get(f) || "";
  for (const f of FIELDS) if (form.elements[f]) form.elements[f].value = state[f] || (f === "sort" ? "recent" : "");

  function syncUrl() {
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries(state)) if (v && !(k === "page" && v === 1) && !(k === "sort" && v === "recent")) query.set(k, v);
    history.replaceState(null, "", "/tickets" + (query.toString() ? "?" + query : ""));
  }

  async function loadCounts() {
    try {
      const counts = await api("/api/tickets/counts");
      counts.actifs = Nova.meta.open_statuses.reduce((sum, s) => sum + counts[s], 0);
      for (const [k, v] of Object.entries(counts)) {
        const el = document.querySelector(`[data-count="${k}"]`);
        if (el) el.textContent = fmt.num(v);
      }
    } catch (e) { /* les compteurs sont secondaires : la liste reste utilisable */ }
  }

  async function load() {
    document.querySelectorAll("[data-status]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.status === state.status)));
    syncUrl();
    const query = new URLSearchParams({ per_page: PER_PAGE, page: state.page, status: state.status });
    for (const f of FIELDS) if (state[f]) query.set(f, state[f]);
    rows.innerHTML = Array.from({ length: 5 }, () => `<tr>${'<td><span class="skeleton-line"></span></td>'.repeat(6)}</tr>`).join("");
    let data;
    try {
      data = await api("/api/tickets?" + query);
    } catch (error) {
      rows.innerHTML = '<tr><td colspan="6"></td></tr>';
      blockError(rows.querySelector("td"), error, load);
      return;
    }
    state.page = data.page;
    const statusName = state.status === "actifs" ? "actif" : label("statuses", state.status).toLowerCase();
    document.querySelector("[data-summary]").textContent = data.total
      ? `${fmt.plural(data.total, "ticket", "tickets")} ${state.status === "actifs" ? (data.total > 1 ? "actifs" : "actif") : "au statut « " + statusName + " »"}${FIELDS.some((f) => f !== "sort" && state[f]) ? " avec ces filtres" : ""}.`
      : "Aucun ticket ne correspond.";

    if (!data.items.length) {
      const filtered = FIELDS.some((f) => f !== "sort" && state[f]);
      rows.innerHTML = `<tr><td colspan="6">${emptyState("search",
        filtered ? "Aucun ticket avec ces filtres" : "Aucun ticket ici",
        filtered ? "Retire un filtre ou change de statut." : (isAdmin ? "Les nouvelles demandes apparaîtront ici." : "Quand quelque chose ne marche pas, décris-le au support."),
        filtered ? '<button class="ds-button" type="button" data-reset>Retirer les filtres</button>' : (isAdmin ? "" : '<a class="ds-button" href="/tickets/nouveau">Nouvelle demande</a>'))}</td></tr>`;
      document.querySelector("[data-foot]").hidden = true;
      return;
    }

    rows.innerHTML = data.items.map((t) => `
      <tr data-href="/tickets/${t.id}">
        <td class="num subtle" data-phone="hide">#${t.id}</td>
        <td class="cell-title"><a href="/tickets/${t.id}"><strong>${esc(t.title)}</strong></a>
          <small>${isAdmin ? esc(t.created_by.name) + " · " : ""}${esc(label("categories", t.category))}${t.comment_count ? " · " + fmt.plural(t.comment_count, "message", "messages") : ""}</small></td>
        <td>${priorityLozenge(t.priority)}</td>
        <td>${statusLozenge(t.status)}</td>
        <td data-phone="hide">${t.assigned_to ? esc(t.assigned_to.name) : '<span class="subtle">—</span>'}</td>
        <td class="num subtle" title="${esc(fmt.dateTime(t.updated_at))}">${esc(fmt.ago(t.updated_at))}</td>
      </tr>`).join("");

    const first = (data.page - 1) * data.per_page + 1;
    document.querySelector("[data-range]").textContent = `${fmt.num(first)}–${fmt.num(first + data.items.length - 1)} sur ${fmt.num(data.total)}`;
    document.querySelector("[data-foot]").hidden = false;
    const pages = [];
    for (let p = 1; p <= data.pages; p++) {
      if (p === 1 || p === data.pages || Math.abs(p - data.page) <= 1) pages.push(p);
      else if (pages.at(-1) !== "…") pages.push("…");
    }
    document.querySelector("[data-pages]").innerHTML =
      `<li><button type="button" data-page="${data.page - 1}" ${data.page === 1 ? "disabled" : ""} aria-label="Page précédente">${Nova.icon("chevron-left", "ds-icon--sm")}</button></li>` +
      pages.map((p) => (p === "…" ? "<li><span>…</span></li>" : `<li><button type="button" data-page="${p}" ${p === data.page ? 'aria-current="page"' : ""}>${p}</button></li>`)).join("") +
      `<li><button type="button" data-page="${data.page + 1}" ${data.page === data.pages ? "disabled" : ""} aria-label="Page suivante">${Nova.icon("chevron-right", "ds-icon--sm")}</button></li>`;
  }

  document.addEventListener("click", (e) => {
    const status = e.target.closest("[data-status]");
    if (status) { state.status = status.dataset.status; state.page = 1; load(); return; }
    const page = e.target.closest("[data-page]");
    if (page && !page.disabled) { state.page = Number(page.dataset.page); load(); window.scrollTo({ top: 0 }); return; }
    if (e.target.closest("[data-reset]")) {
      for (const f of FIELDS) { state[f] = ""; if (form.elements[f]) form.elements[f].value = f === "sort" ? "recent" : ""; }
      state.page = 1; load(); return;
    }
    const row = e.target.closest("tr[data-href]");
    if (row && !e.target.closest("a")) location.href = row.dataset.href;
  });

  let timer;
  form.addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      for (const f of FIELDS) if (form.elements[f]) state[f] = form.elements[f].value === "recent" ? "" : form.elements[f].value.trim();
      state.page = 1;
      load();
    }, e.target.name === "q" ? 250 : 0);
  });
  form.addEventListener("submit", (e) => e.preventDefault());

  loadCounts();
  load();
})();

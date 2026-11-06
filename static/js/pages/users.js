/* Comptes : recherche, filtre par rôle, création, changement de rôle et désactivation. */
(async () => {
  const { api, fmt, esc, icon, label, blockError, showErrors, busy, flag } = Nova;
  const me = await Nova.boot({ admin: true });
  const rows = document.querySelector("[data-rows]");
  const form = document.querySelector("[data-filters]");
  const state = { q: "", role: "" };
  let users = [];

  function render() {
    const admins = users.filter((u) => u.role === "admin").length;
    document.querySelector("[data-summary]").textContent = state.q || state.role
      ? `${fmt.plural(users.length, "compte trouvé", "comptes trouvés")}.`
      : `${fmt.plural(users.length, "compte", "comptes")}, dont ${fmt.plural(admins, "administrateur", "administrateurs")}.`;
    if (!users.length) {
      rows.innerHTML = `<tr><td colspan="8">${Nova.emptyState("users", "Aucun compte trouvé", "Essaie un autre nom ou un autre filtre.")}</td></tr>`;
      return;
    }
    rows.innerHTML = users.map((u) => {
      const self = u.id === me.id;
      const menu = self ? "" : `
        <div class="ds-dropdown">
          <button class="ds-button ds-button--subtle ds-button--sm ds-icon-button" type="button" aria-label="Actions pour ${esc(u.name)}" aria-haspopup="menu" aria-expanded="false" aria-controls="menu-${u.id}">${icon("more", "ds-icon--sm")}</button>
          <div class="ds-menu ds-menu--end" id="menu-${u.id}" role="menu" hidden>
            <button class="ds-menu-item" role="menuitem" type="button" data-set="${u.id}" data-role="${u.role === "admin" ? "user" : "admin"}">${icon("users")}${u.role === "admin" ? "Passer en utilisateur" : "Passer en administrateur"}</button>
            <button class="ds-menu-item ${u.active ? "ds-menu-item--danger" : ""}" role="menuitem" type="button" data-set="${u.id}" data-active="${!u.active}">${icon(u.active ? "lock" : "check")}${u.active ? "Désactiver le compte" : "Réactiver le compte"}</button>
          </div>
        </div>`;
      return `<tr>
        <td class="cell-title"><strong>${esc(u.name)}${self ? ' <span class="subtle">(toi)</span>' : ""}</strong><small>${esc(u.email)}</small></td>
        <td data-phone="hide" data-tablet="hide">${u.service ? esc(u.service) : '<span class="subtle">—</span>'}</td>
        <td>${esc(label("roles", u.role))}</td>
        <td>${u.active ? '<span class="ds-lozenge">Actif</span>' : `<span class="ds-lozenge">${icon("lock")}Désactivé</span>`}</td>
        <td class="num" data-phone="hide">${fmt.num(u.open_requests)}</td>
        <td class="num" data-phone="hide">${u.role === "admin" ? fmt.num(u.open_assigned) : '<span class="subtle">—</span>'}</td>
        <td class="num subtle" data-phone="hide" data-tablet="hide">${esc(fmt.date(u.created_at))}</td>
        <td class="num">${menu}</td>
      </tr>`;
    }).join("");
  }

  async function load() {
    const query = new URLSearchParams();
    if (state.q) query.set("q", state.q);
    if (state.role) query.set("role", state.role);
    try {
      users = await api("/api/users?" + query);
      render();
    } catch (error) {
      rows.innerHTML = '<tr><td colspan="8"></td></tr>';
      blockError(rows.querySelector("td"), error, load);
    }
  }

  let timer;
  form.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { state.q = form.elements.q.value.trim(); load(); }, 250); });
  form.addEventListener("submit", (e) => e.preventDefault());
  document.querySelector("[data-role-filter]").addEventListener("click", (e) => {
    const b = e.target.closest("[data-role]");
    if (b) { state.role = b.dataset.role; load(); }
  });

  rows.addEventListener("click", async (e) => {
    const item = e.target.closest("[data-set]");
    if (!item) return;
    const body = item.dataset.role ? { role: item.dataset.role } : { active: item.dataset.active === "true" };
    try {
      const updated = await api(`/api/users/${item.dataset.set}`, { method: "PATCH", body });
      flag(body.role ? `${updated.name} est maintenant ${label("roles", updated.role).toLowerCase()}` : `Compte de ${updated.name} ${updated.active ? "réactivé" : "désactivé"}`);
      load();
    } catch (error) {
      flag("Modification refusée", error.message, "danger");
    }
  });

  const dialog = document.getElementById("user-dialog");
  const userForm = document.getElementById("user-form");
  userForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const button = userForm.querySelector('[type="submit"]');
    const body = Object.fromEntries(["name", "email", "service", "role", "password"].map((f) => [f, userForm.elements[f].value]));
    busy(button, true);
    try {
      const created = await api("/api/users", { method: "POST", body });
      DS.closeDialog(dialog, "");
      userForm.reset();
      showErrors(userForm, { fields: {} });
      flag(`Compte de ${created.name} créé`, "Transmets-lui son mot de passe provisoire.");
      load();
    } catch (error) {
      showErrors(userForm, error);
    }
    busy(button, false);
  });

  load();
})();

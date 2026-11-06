/* Accueil : la vue du support (file d'attente, ancienneté, volumes) ou celle de l'utilisateur (ses demandes). */
(async () => {
  const { api, fmt, esc, label, statusLozenge, priorityLozenge, emptyState, blockError, flag } = Nova;
  const user = await Nova.boot();
  const view = document.querySelector(`[data-view="${user.role === "admin" ? "admin" : "user"}"]`);
  view.hidden = false;
  // Une seule vue dans la page : l'autre (et son h1) est retirée.
  document.querySelector(`[data-view="${user.role === "admin" ? "user" : "admin"}"]`).remove();
  const $ = (sel) => view.querySelector(sel);
  const setKpi = (key, value) => { const el = $(`[data-k="${key}"]`); if (el) el.innerHTML = value; };

  function ticketRow(t, { meta, end }) {
    return `<li class="row">
      <a href="/tickets/${t.id}" class="row-main" style="min-width:0;text-decoration:none;color:inherit">
        <span class="row-title"><span class="id">#${t.id}</span>${esc(t.title)}</span>
        <span class="row-meta">${meta}</span>
      </a>
      <span class="row-end">${end}</span>
    </li>`;
  }

  async function loadAdmin() {
    let s;
    try {
      s = await api("/api/stats");
    } catch (error) {
      blockError($("[data-finding]"), error, loadAdmin);
      return;
    }
    $("[data-stamp]").textContent = `Mis à jour à ${fmt.time(s.generated_at)}`;

    // La phrase sous le titre dit ce qui demande de l'attention maintenant.
    const oldest = s.queue[0];
    let finding = "Tous les tickets ouverts sont pris en charge.";
    if (s.unassigned) {
      finding = `${fmt.plural(s.unassigned, "ticket attend", "tickets attendent")} une prise en charge ; le plus ancien est arrivé ${fmt.ago(oldest.created_at)}.`;
    }
    if (s.critical_open) finding += ` ${fmt.plural(s.critical_open, "ticket critique est ouvert", "tickets critiques sont ouverts")}.`;
    if (!s.total) finding = "Aucun ticket pour l'instant. Les demandes des utilisateurs arriveront ici.";
    $("[data-finding]").textContent = finding;

    setKpi("open", fmt.num(s.open));
    setKpi("unassigned", fmt.num(s.unassigned));
    setKpi("critical_open", fmt.num(s.critical_open));
    setKpi("resolved_7d", fmt.num(s.resolved_7d));
    setKpi("avg", s.avg_resolution_hours == null ? '<span class="subtle">—</span>' : esc(fmt.hours(s.avg_resolution_hours)));
    if (s.avg_resolution_hours == null) $('[data-k-hint="avg"]').textContent = "aucun ticket résolu en 30 jours";

    // File d'attente : la prise en charge se fait d'un clic.
    $("[data-queue]").innerHTML = s.queue.length
      ? s.queue.map((t) => ticketRow(t, {
          meta: `${esc(t.created_by.name)} · ${esc(label("categories", t.category))} · arrivé ${fmt.ago(t.created_at)}`,
          end: `${priorityLozenge(t.priority)}<button class="ds-button ds-button--sm" type="button" data-take="${t.id}">Prendre</button>`,
        })).join("")
      : `<li class="empty-inline">Personne n'attend : chaque ticket ouvert a un technicien.</li>`;

    // Ancienneté : un carré par ticket ouvert, en couleur s'il n'est pas pris en charge.
    $("[data-ages]").innerHTML = s.ages.map((a) => `
      <div class="age">
        <h3>${esc(a.label)}</h3>
        <span class="count">${fmt.num(a.tickets.length)}</span>
        <div class="cells">${a.tickets.length
          ? a.tickets.map((t) => `<a class="cell${t.assigned ? "" : " cell--free"}" href="/tickets/${t.id}" title="#${t.id} ${esc(t.title)}${t.assigned ? "" : " (non assigné)"}" aria-label="Ticket ${t.id} : ${esc(t.title)}${t.assigned ? "" : ", non assigné"}"></a>`).join("")
          : '<span class="cell-empty" aria-hidden="true"></span>'}</div>
      </div>`).join("");

    const byName = (a, b) => b.value - a.value || a.label.localeCompare(b.label);
    Charts.barList($("[data-workload]"), s.workload.map((w) => ({ label: w.name, value: w.open })).sort(byName), { thin: true });
    Charts.barList($("[data-categories]"), Object.entries(s.by_category).map(([k, v]) => ({ label: label("categories", k), value: v })).sort(byName), { thin: true });

    const labels = s.daily.map((d, i) => (i === s.daily.length - 1 ? "Auj." : new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" }).format(new Date(d.date + "T12:00:00"))));
    Charts.bars($("[data-daily]"), {
      labels,
      values: s.daily.map((d) => d.created),
      format: Charts.fmt.int,
      integer: true,
      // Le turquoise est réservé aux tickets non assignés : le volume quotidien reste neutre.
      colour: getComputedStyle(document.documentElement).getPropertyValue("--ds-text-subtlest").trim(),
      // Le graphique prend la hauteur de la carte voisine, pour que la rangée finisse au même niveau.
      height: () => Math.max(200, $("[data-split]").offsetHeight - 92),
      xAt: labels.map((_, i) => i).filter((i) => i % 3 === 1 || i === labels.length - 1),
    });
  }

  async function loadUser() {
    let s;
    try {
      s = await api("/api/stats");
    } catch (error) {
      blockError($("[data-finding]"), error, loadUser);
      return;
    }
    const active = s.open;
    let finding = active
      ? `Tu as ${fmt.plural(active, "demande en cours", "demandes en cours")}.`
      : "Aucune demande en cours.";
    if (s.waiting_reply) finding += ` ${fmt.plural(s.waiting_reply, "attend", "attendent")} ta réponse.`;
    $("[data-finding]").textContent = finding;
    setKpi("active", fmt.num(active));
    setKpi("waiting_reply", fmt.num(s.waiting_reply));
    setKpi("resolved_30d", fmt.num(s.resolved_30d));

    const who = (t) => (t.assigned_to ? `pris en charge par ${esc(t.assigned_to.name)}` : "en attente d'un technicien");
    $("[data-active]").innerHTML = s.active.length
      ? s.active.map((t) => ticketRow(t, {
          meta: `${who(t)} · mis à jour ${fmt.ago(t.updated_at)}`,
          end: statusLozenge(t.status),
        })).join("")
      : `<li>${emptyState("check", "Rien en cours", "Quand quelque chose ne marche pas, décris-le : le support prend le relais.", '<a class="ds-button" href="/tickets/nouveau">Nouvelle demande</a>')}</li>`;
    $("[data-closed]").innerHTML = s.recently_closed.length
      ? s.recently_closed.map((t) => ticketRow(t, { meta: `résolue ${fmt.ago(t.resolved_at)}`, end: "" })).join("")
      : `<li class="empty-inline">Aucune demande résolue pour l'instant.</li>`;
  }

  view.addEventListener("click", async (e) => {
    const take = e.target.closest("[data-take]");
    if (take) {
      Nova.busy(take, true);
      try {
        await api(`/api/tickets/${take.dataset.take}`, { method: "PATCH", body: { assigned_to_id: user.id } });
        flag(`Ticket #${take.dataset.take} pris en charge`, "Il passe en cours et sort de la file.");
        loadAdmin();
      } catch (error) {
        flag("Impossible de prendre le ticket", error.message, "danger");
        Nova.busy(take, false);
      }
    }
    if (e.target.closest("[data-refresh]")) loadAdmin();
  });

  user.role === "admin" ? loadAdmin() : loadUser();
})();

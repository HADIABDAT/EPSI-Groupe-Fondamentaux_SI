/* Détail d'un ticket. Le support change le traitement (enregistré à chaque modification) ;
   le demandeur répond, ferme sa demande ou la rouvre quand elle est résolue. */
(async () => {
  const { api, fmt, esc, label, icon, statusLozenge, priorityLozenge, emptyState, showErrors, busy, flag } = Nova;
  const user = await Nova.boot();
  const isAdmin = user.role === "admin";
  const root = document.querySelector("[data-ticket]");
  const id = root.dataset.ticket;
  const $ = (sel) => root.querySelector(sel);
  let admins = [];
  let ticket;

  if (!isAdmin) $("[data-parent]").textContent = "Mes demandes";

  const options = (choices, current) => Object.entries(choices).map(([k, v]) => `<option value="${k}" ${k === current ? "selected" : ""}>${esc(v)}</option>`).join("");

  /* Une ligne d'historique en mots. */
  function describe(e) {
    const who = `<strong>${esc(e.actor.name)}</strong>`;
    switch (e.kind) {
      case "created": return `${who} a ouvert le ticket`;
      case "status": return `${who} a changé le statut : ${esc(label("statuses", e.old))} → ${esc(label("statuses", e.new))}`;
      case "priority": return `${who} a changé la priorité : ${esc(label("priorities", e.old))} → ${esc(label("priorities", e.new))}`;
      case "category": return `${who} a changé la catégorie : ${esc(label("categories", e.old))} → ${esc(label("categories", e.new))}`;
      case "assigned": return e.new ? `${who} a assigné le ticket à ${esc(e.new)}` : `${who} a retiré l'assignation${e.old ? " de " + esc(e.old) : ""}`;
      default: return who;
    }
  }

  function render() {
    const t = ticket;
    document.title = `#${t.id} ${t.title} · NovaServices`;
    $("[data-title]").textContent = t.title;
    $("[data-meta]").textContent = `Ouvert par ${t.created_by.name} le ${fmt.dateTime(t.created_at)}`;
    $("[data-description]").textContent = t.description;

    $("[data-thread-count]").textContent = t.comments.length ? fmt.plural(t.comments.length, "message", "messages") : "";
    $("[data-thread]").innerHTML = t.comments.length
      ? t.comments.map((c) => `
        <li class="message">
          <span class="ds-avatar">${esc(Nova.initials(c.author.name))}</span>
          <div>
            <header><strong>${esc(c.author.name)}</strong>${c.author_role === "admin" ? '<span class="ds-lozenge">Support</span>' : ""}<time datetime="${c.created_at}" title="${esc(fmt.dateTime(c.created_at))}">${esc(fmt.ago(c.created_at))}</time></header>
            <p>${esc(c.body)}</p>
          </div>
        </li>`).join("")
      : `<li class="empty-inline">${isAdmin ? "Aucun échange pour l'instant. Une question au demandeur ? Écris-la ci-dessous." : "Aucun échange pour l'instant. Le support te répondra ici."}</li>`;

    const closed = t.status === "ferme";
    const composer = $("[data-composer]");
    composer.elements.body.disabled = closed;
    composer.querySelector('[type="submit"]').disabled = closed;
    $("[data-composer-help]").textContent = closed
      ? "Ce ticket est fermé. Pour un nouveau problème, ouvre une nouvelle demande."
      : isAdmin ? "Le demandeur verra ta réponse dans son ticket." : t.status === "en_attente" ? "Ta réponse relance le traitement." : "";

    // Traitement : des listes pour le support, du texte pour le demandeur.
    const assignee = t.assigned_to ? esc(t.assigned_to.name) : '<span class="subtle">Personne pour l\'instant</span>';
    $("[data-props]").innerHTML = isAdmin ? `
      <div><dt><label for="p-status">Statut</label></dt><dd><select class="ds-select" id="p-status" data-field="status">${options(Nova.meta.statuses, t.status)}</select></dd></div>
      <div><dt><label for="p-assigned">Pris en charge par</label></dt><dd><select class="ds-select" id="p-assigned" data-field="assigned_to_id">
        <option value="">Personne</option>${admins.map((a) => `<option value="${a.id}" ${t.assigned_to && t.assigned_to.id === a.id ? "selected" : ""}>${esc(a.name)}${a.id === user.id ? " (moi)" : ""}</option>`).join("")}</select></dd></div>
      <div><dt><label for="p-priority">Priorité</label></dt><dd><select class="ds-select" id="p-priority" data-field="priority">${options(Nova.meta.priorities, t.priority)}</select></dd></div>
      <div><dt><label for="p-category">Catégorie</label></dt><dd><select class="ds-select" id="p-category" data-field="category">${options(Nova.meta.categories, t.category)}</select></dd></div>
      <div><dt>Demandeur</dt><dd>${esc(t.created_by.name)}</dd></div>
      ${t.resolved_at ? `<div><dt>Résolu</dt><dd>le ${esc(fmt.dateTime(t.resolved_at))}</dd></div>` : ""}` : `
      <div><dt>Statut</dt><dd>${statusLozenge(t.status)}</dd></div>
      <div><dt>Pris en charge par</dt><dd>${assignee}</dd></div>
      <div><dt>Priorité</dt><dd>${priorityLozenge(t.priority)}</dd></div>
      <div><dt>Catégorie</dt><dd>${esc(label("categories", t.category))}</dd></div>
      ${t.resolved_at ? `<div><dt>Résolu</dt><dd>le ${esc(fmt.dateTime(t.resolved_at))}</dd></div>` : ""}`;

    const actions = [];
    if (isAdmin) {
      if (!t.assigned_to || t.assigned_to.id !== user.id) actions.push('<button class="ds-button" type="button" data-take>Me l\'assigner</button>');
      actions.push('<button class="ds-button ds-button--subtle ds-button--danger" type="button" data-ds-open="delete-dialog">' + icon("trash", "ds-icon--sm") + "Supprimer le ticket</button>");
    } else if (t.status === "resolu") {
      actions.push('<button class="ds-button" type="button" data-status-to="ferme">' + icon("check", "ds-icon--sm") + "Confirmer, c'est réglé</button>");
      actions.push('<button class="ds-button ds-button--subtle" type="button" data-status-to="ouvert">Le problème persiste</button>');
    } else if (!closed) {
      actions.push('<button class="ds-button ds-button--subtle" type="button" data-status-to="ferme">Fermer ma demande</button>');
    }
    $("[data-actions]").innerHTML = actions.join("");
    $("[data-actions]").hidden = !actions.length;

    $("[data-history]").innerHTML = t.events.slice().reverse().map((e) =>
      `<li><span>${describe(e)}</span><time datetime="${e.created_at}" title="${esc(fmt.dateTime(e.created_at))}">${esc(fmt.ago(e.created_at))}</time></li>`).join("");
  }

  async function update(body, done) {
    try {
      ticket = await api(`/api/tickets/${id}`, { method: "PATCH", body });
      render();
      $("[data-saved]").textContent = "Enregistré";
      setTimeout(() => { $("[data-saved]").textContent = ""; }, 2500);
      if (done) flag(done);
    } catch (error) {
      flag("Modification refusée", error.message, "danger");
      render();
    }
  }

  try {
    [ticket, admins] = await Promise.all([api(`/api/tickets/${id}`), isAdmin ? api("/api/users?role=admin&active=1") : []]);
  } catch (error) {
    root.innerHTML = error.status === 404
      ? emptyState("search", "Ce ticket n'existe pas", "Il a peut-être été supprimé, ou il appartient à quelqu'un d'autre.", '<a class="ds-button" href="/tickets">Retour à la liste</a>')
      : emptyState("error", "Impossible de charger le ticket", error.message, '<button class="ds-button" type="button" onclick="location.reload()">Réessayer</button>');
    return;
  }
  render();

  root.addEventListener("change", (e) => {
    const field = e.target.closest("[data-field]");
    if (!field) return;
    const value = field.dataset.field === "assigned_to_id" ? (field.value ? Number(field.value) : null) : field.value;
    update({ [field.dataset.field]: value });
  });

  root.addEventListener("click", (e) => {
    if (e.target.closest("[data-take]")) update({ assigned_to_id: user.id }, "Ticket pris en charge");
    const to = e.target.closest("[data-status-to]");
    if (to) update({ status: to.dataset.statusTo }, to.dataset.statusTo === "ferme" ? "Demande fermée" : "Demande rouverte");
  });

  $("[data-composer]").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const button = form.querySelector('[type="submit"]');
    if (!form.elements.body.value.trim()) {
      showErrors(form, { message: "", fields: { body: "Écris un message avant d'envoyer." } });
      return;
    }
    busy(button, true);
    try {
      ticket = await api(`/api/tickets/${id}/comments`, { method: "POST", body: { body: form.elements.body.value } });
      form.reset();
      showErrors(form, { fields: {} });
      render();
    } catch (error) {
      showErrors(form, error);
      if (!Object.keys(error.fields).length) flag("Message non envoyé", error.message, "danger");
    }
    busy(button, false);
    render();
  });

  document.getElementById("delete-dialog").addEventListener("close", async (e) => {
    if (e.target.returnValue !== "delete") return;
    try {
      await api(`/api/tickets/${id}`, { method: "DELETE" });
      location.href = "/tickets";
    } catch (error) {
      flag("Suppression impossible", error.message, "danger");
    }
  });
})();

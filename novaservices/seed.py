"""Données de démonstration (SEED_DEMO=1) : des comptes et un mois de tickets fictifs."""

import os
import random
from datetime import timedelta

from .models import Comment, Event, Ticket, User, db, utcnow

DEMO_USERS = [
    ("camille.martin@novaservices.fr", "Camille Martin", "Support informatique", "admin"),
    ("yanis.benali@novaservices.fr", "Yanis Benali", "Support informatique", "admin"),
    ("lea.fournier@novaservices.fr", "Léa Fournier", "Comptabilité", "user"),
    ("hugo.lambert@novaservices.fr", "Hugo Lambert", "Commercial", "user"),
    ("ines.moreau@novaservices.fr", "Inès Moreau", "Ressources humaines", "user"),
    ("thomas.girard@novaservices.fr", "Thomas Girard", "Logistique", "user"),
    ("sarah.dubois@novaservices.fr", "Sarah Dubois", "Direction", "user"),
]

# (sujet, description, catégorie, priorité)
DEMO_TICKETS = [
    ("Imprimante du 2e étage hors ligne", "L'imprimante HP du couloir n'apparaît plus dans la liste depuis ce matin.", "materiel", "normale"),
    ("Accès VPN refusé depuis le domicile", "Le client VPN affiche « authentification échouée » alors que mon mot de passe fonctionne sur le poste.", "acces", "haute"),
    ("Demande de second écran", "Je travaille sur des tableaux larges, un second écran 24 pouces m'aiderait.", "materiel", "basse"),
    ("Outlook ne synchronise plus le calendrier", "Les rendez-vous ajoutés sur le téléphone n'apparaissent pas dans Outlook.", "messagerie", "normale"),
    ("Logiciel de paie : erreur à l'export", "L'export des bulletins de novembre s'arrête avec le code E-204.", "logiciel", "critique"),
    ("Wi-Fi instable en salle Rivoli", "La connexion coupe toutes les dix minutes pendant les réunions.", "reseau", "haute"),
    ("Compte bloqué après changement de mot de passe", "Je ne peux plus ouvrir de session depuis le changement imposé ce matin.", "acces", "haute"),
    ("Installer Power BI Desktop", "J'ai besoin de Power BI pour le reporting mensuel des ventes.", "logiciel", "basse"),
    ("Le badge n'ouvre plus la porte du local serveur", "Mon badge est refusé au lecteur du sous-sol depuis lundi.", "acces", "normale"),
    ("Clavier qui double les frappes", "Certaines touches s'affichent deux fois, surtout le E et le espace.", "materiel", "basse"),
    ("Boîte mail pleine", "Message « boîte aux lettres pleine », je ne reçois plus rien de l'extérieur.", "messagerie", "haute"),
    ("Partage réseau Compta inaccessible", "Le lecteur S: renvoie « chemin introuvable » sur deux postes de l'équipe.", "reseau", "critique"),
    ("Écran qui scintille", "L'écran du portable scintille quand il est sur la station d'accueil.", "materiel", "normale"),
    ("Teams : pas de son en réunion", "Les autres participants ne m'entendent pas, le micro est pourtant détecté.", "logiciel", "normale"),
    ("Création de compte pour une arrivée lundi", "Nouvelle assistante RH : compte, messagerie et accès au SIRH.", "acces", "normale"),
    ("Lenteurs sur l'ERP en fin de journée", "Les écrans de commande mettent plus de trente secondes à s'afficher après 17 h.", "logiciel", "haute"),
    ("Téléphone IP sans tonalité", "Le poste fixe du bureau 214 n'a plus de tonalité.", "reseau", "normale"),
    ("Mot de passe Wi-Fi invités", "Quel est le mot de passe du réseau invités pour la visite client de jeudi ?", "reseau", "basse"),
    ("Mise à jour Windows bloquée à 30 %", "Le portable reste sur l'écran de mise à jour depuis une heure.", "logiciel", "haute"),
    ("Souris sans fil introuvable", "La souris fournie avec le poste ne s'appaire plus.", "materiel", "basse"),
    ("Signature mail à mettre à jour", "Changement de poste : ma signature doit afficher Responsable logistique.", "messagerie", "basse"),
    ("Scanner : PDF illisibles", "Les numérisations sortent noires sur la moitié de la page.", "materiel", "normale"),
    ("Accès au dossier Direction", "J'ai besoin d'un accès en lecture au dossier Direction/Budget 2027.", "acces", "normale"),
    ("Antivirus : alerte sur une pièce jointe", "Une pièce jointe d'un fournisseur a été mise en quarantaine, est-ce sûr ?", "messagerie", "haute"),
    ("Poste qui redémarre seul", "Le PC redémarre sans prévenir deux ou trois fois par jour.", "materiel", "haute"),
    ("Excel plante à l'ouverture d'un fichier", "Le fichier des stocks fait planter Excel à chaque ouverture.", "logiciel", "normale"),
    ("Projecteur salle Vendôme sans signal", "Le projecteur affiche « pas de signal » avec l'adaptateur HDMI.", "materiel", "normale"),
    ("Double authentification : changement de téléphone", "J'ai changé de téléphone et je n'ai plus l'application d'authentification.", "acces", "haute"),
    ("Imprimer en recto verso par défaut", "Comment régler l'impression recto verso par défaut sur mon poste ?", "autre", "basse"),
    ("Coupure réseau bâtiment B", "Plus de réseau filaire dans tout le bâtiment B depuis 9 h 10.", "reseau", "critique"),
    ("Licence Adobe expirée", "Acrobat Pro demande une licence depuis ce matin.", "logiciel", "normale"),
    ("Demande de casque pour le télétravail", "Mon casque actuel grésille, est-il possible d'en avoir un nouveau ?", "materiel", "basse"),
    ("Message d'erreur certificat sur l'intranet", "Le navigateur signale un certificat expiré sur l'intranet.", "reseau", "haute"),
    ("Restaurer un fichier supprimé", "J'ai supprimé par erreur le fichier Planning_Q4.xlsx du partage commun hier.", "autre", "normale"),
]

STAFF_REPLIES = [
    "Je prends le ticket, je regarde ça dans la matinée.",
    "Peux-tu me dire si le problème apparaît aussi sur un autre poste ?",
    "C'est corrigé de notre côté. Peux-tu vérifier et me confirmer ?",
    "J'ai relancé le service concerné. Dis-moi si ça recommence.",
]
USER_REPLIES = [
    "Oui, même chose sur le poste de ma collègue.",
    "C'est bon, tout fonctionne. Merci.",
    "Toujours le même problème ce matin.",
]


def seed_demo():
    """Remplit une base vide. Ne fait rien si des tickets existent déjà."""
    if Ticket.query.first():
        return
    rng = random.Random(42)
    password = os.environ.get("DEMO_PASSWORD", "novaservices")
    users = {}
    for email, name, service, role in DEMO_USERS:
        user = User.query.filter_by(email=email).first() or User(email=email, name=name, service=service, role=role)
        user.set_password(password)
        db.session.add(user)
        users[email] = user
    db.session.flush()
    staff = [u for u in users.values() if u.is_admin]
    requesters = [u for u in users.values() if not u.is_admin]

    now = utcnow()
    count = len(DEMO_TICKETS)
    for index, (title, description, category, priority) in enumerate(DEMO_TICKETS):
        # Du plus ancien (il y a 28 jours) au plus récent (il y a quelques heures).
        age = timedelta(days=28 * (count - 1 - index) / (count - 1), hours=rng.randint(1, 6))
        created = now - age
        # Les demandes les plus récentes reviennent d'abord à Léa Fournier, le compte de démo affiché à la connexion.
        author = requesters[(count - 1 - index) % len(requesters)]
        ticket = Ticket(
            title=title, description=description, category=category, priority=priority,
            created_by=author, created_at=created, updated_at=created,
        )
        db.session.add(ticket)
        ticket.events.append(Event(actor=author, kind="created", created_at=created))

        days_old = age.days
        if days_old >= 6:
            final = rng.choice(["resolu", "resolu", "ferme", "ferme", "ferme", "ferme", "ferme", "en_attente"])
        elif days_old >= 2:
            final = rng.choice(["en_cours", "en_attente", "resolu"])
        else:
            final = rng.choice(["ouvert", "ouvert", "en_cours"])
        if final == "ouvert":
            continue

        agent = rng.choice(staff)
        moment = created + timedelta(hours=rng.randint(1, 5))
        ticket.assigned_to = agent
        ticket.events.append(Event(actor=agent, kind="assigned", new_value=agent.name, created_at=moment))
        ticket.events.append(Event(actor=agent, kind="status", old_value="ouvert", new_value="en_cours", created_at=moment))
        ticket.status = "en_cours"
        ticket.comments.append(Comment(author=agent, body=STAFF_REPLIES[0], created_at=moment))

        def later(low, high):
            # Les étapes suivantes s'enchaînent en quelques heures, sans dépasser maintenant.
            return min(moment + timedelta(hours=rng.randint(low, high)), now - timedelta(minutes=30))

        if final in ("en_attente", "resolu", "ferme"):
            moment = later(2, 20)
            ticket.comments.append(Comment(author=agent, body=rng.choice(STAFF_REPLIES[1:3]), created_at=moment))
            if final == "en_attente":
                ticket.events.append(Event(actor=agent, kind="status", old_value="en_cours", new_value="en_attente", created_at=moment))
                ticket.status = "en_attente"
        if final in ("resolu", "ferme"):
            moment = later(3, 40)
            ticket.events.append(Event(actor=agent, kind="status", old_value="en_cours", new_value="resolu", created_at=moment))
            ticket.status, ticket.resolved_at = "resolu", moment
            if final == "ferme":
                moment = later(1, 24)
                ticket.comments.append(Comment(author=author, body=USER_REPLIES[1], created_at=moment))
                ticket.events.append(Event(actor=author, kind="status", old_value="resolu", new_value="ferme", created_at=moment))
                ticket.status = "ferme"
        ticket.updated_at = moment
    db.session.commit()

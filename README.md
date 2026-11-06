# NovaServices : helpdesk du support informatique (TP CI/CD)

Application Flask de ticketing : les utilisateurs envoient et suivent leurs demandes, le support les
prend en charge, répond et les résout. Connexion par JWT, deux rôles (utilisateur et administrateur),
un tableau de bord par rôle. Autour, une chaîne CI/CD : tests, image Docker, publication sur GHCR,
déploiement sur une VM de préproduction, retour arrière.

## Fiche de choix du binôme (étape 1)

| Rubrique | Valeur |
|---|---|
| Application et besoin métier | **NovaServices** : helpdesk du support informatique. Fonctionnalités : comptes et connexion JWT, tickets, échanges, historique, tableaux de bord utilisateur et administrateur |
| Source du projet | URL du dépôt GitHub du binôme |
| Exécution | `python app.py` (dev) / `gunicorn app:app` (conteneur), port interne **8000** |
| Validation | `GET /health` → 200 ; `GET /api/tickets` sans jeton → 401, avec jeton → liste JSON ; URL inconnue → 404 (102 tests en tout) |
| Identification | `GET /version` → `{"version": APP_VERSION, "commit": GIT_COMMIT}` |

## Rôles

| | Utilisateur | Administrateur (support) |
|---|---|---|
| Tickets visibles | les siens | tous |
| Créer un ticket, répondre | oui | oui |
| Changer statut, priorité, catégorie, assignation | fermer sa demande, ou la rouvrir quand elle est résolue | oui |
| Supprimer un ticket | non | oui |
| Gérer les comptes | non | oui |

Le rôle est relu en base à chaque requête : un compte rétrogradé ou désactivé perd ses droits tout de suite,
même avec un jeton encore valide.

## Pages

| Adresse | Écran |
|---|---|
| `/connexion`, `/inscription` | Connexion et création de compte |
| `/` | Administrateur : file d'attente, ancienneté des tickets ouverts, volumes, charge par technicien. Utilisateur : ses demandes en cours |
| `/tickets` | Liste avec compteurs par statut, recherche, filtres, tri et pages |
| `/tickets/nouveau` | Nouvelle demande |
| `/tickets/<id>` | Détail : description, échanges, traitement, historique |
| `/utilisateurs` | Gestion des comptes (administrateurs) |
| `/compte` | Profil, mot de passe, thème |

Les pages utilisent le design system perso, copié depuis `~/Documents/design-system` dans `static/ds/`.
Elles chargent leurs données par l'API ; c'est l'API qui contrôle les droits.

## API

Toutes les routes `/api` sauf l'inscription et la connexion demandent l'en-tête `Authorization: Bearer <jeton>`.

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/auth/register` | Créer un compte utilisateur, renvoie `{token, user}` |
| POST | `/api/auth/login` | Se connecter, renvoie `{token, user}` |
| GET, PATCH | `/api/auth/me` | Lire ou modifier son profil (nom, service) |
| POST | `/api/auth/me/password` | Changer son mot de passe |
| GET | `/api/tickets` | Liste : `status` (ou `actifs`), `priority`, `category`, `assigned` (`moi`, `aucun`, id), `q`, `sort` (`recent`, `ancien`, `priorite`), `page`, `per_page` |
| GET | `/api/tickets/counts` | Nombre de tickets par statut |
| POST | `/api/tickets` | Créer un ticket |
| GET, PATCH, DELETE | `/api/tickets/<id>` | Détail, mise à jour, suppression (administrateur) |
| POST | `/api/tickets/<id>/comments` | Ajouter un message |
| GET | `/api/stats` | Chiffres du tableau de bord, limités aux tickets visibles |
| GET, POST | `/api/users` | Lister ou créer des comptes (administrateur) |
| PATCH | `/api/users/<id>` | Changer le rôle ou désactiver un compte (administrateur) |
| GET | `/health` | Contrôle de disponibilité (`503` si `FAIL_HEALTH=1`) |
| GET | `/version` | Version et commit Git de l'image |

## Structure

```
app.py                       point d'entrée (charge .env, crée l'application)
novaservices/                modèles, authentification JWT, API, statistiques, pages, données de démo
templates/                   pages HTML (Jinja)
static/ds/                   design system (tokens, composants, icônes)
static/app.css, static/js/   mise en page de l'application, client de l'API, graphiques, scripts des pages
tests/                       tests pytest (auth, droits, tickets, comptes, statistiques, pages)
requirements.txt             dépendances (versions fixées)
Dockerfile                   image de l'application
deploy.sh                    déploiement sur la VM + rollback
.github/workflows/ci-cd.yml  pipeline GitHub Actions
```

## En local (étapes 2 à 5)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env               # puis remplace JWT_SECRET et ADMIN_PASSWORD
python app.py                      # http://localhost:8000
python -m pytest -q
```

Avec `SEED_DEMO=1`, une base vide est remplie au premier démarrage : deux administrateurs, cinq utilisateurs
et 34 tickets répartis sur un mois. Les comptes de démo ont le mot de passe `novaservices` (ou `DEMO_PASSWORD`),
par exemple `camille.martin@novaservices.fr` (compte administrateur) et `lea.fournier@novaservices.fr`.
La base locale est dans `instance/novaservices.db` ; supprime ce fichier pour repartir de zéro.

## Docker (étape 9)

```bash
docker build -t application-tp:local .
docker run -d --name application-tp-local -p 8080:8000 -e SEED_DEMO=1 -e JWT_SECRET=dev application-tp:local
curl -f http://localhost:8080/health
docker logs application-tp-local
docker rm -f application-tp-local
```

## Pipeline (étapes 7, 10, 12)

| Événement | Comportement |
|---|---|
| Pull request vers `main` | Tests + construction + contrôle `/health` du conteneur ; **ni publication ni déploiement** |
| Push / fusion sur `main` | Tests, construction, publication sur GHCR (tag = SHA du commit, digest conservé), déploiement par digest |
| Test ou build en échec | Arrêt de la chaîne, aucun déploiement |
| Contrôle HTTP après déploiement en échec | Journaux du conteneur + retour automatique à l'image précédente ; le job reste rouge |

### Configuration GitHub à faire (étape 11)

Dans *Settings → Environments*, créer l'environnement **`preprod`**, puis :

**Variables** (`Settings → Secrets and variables → Actions → Variables`)

| Nom | Exemple |
|---|---|
| `DEPLOY_HOST` | `10.0.0.12` |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_PORT` | `22` (optionnel) |
| `DEPLOY_APP_PORT` | `8080` (optionnel) |
| `DEPLOY_RUNNER` | `self-hosted` si la VM n'est joignable que depuis le réseau de l'école (optionnel) |

**Secrets**

| Nom | Contenu |
|---|---|
| `DEPLOY_SSH_KEY` | clé privée de déploiement (jamais dans Git) |
| `DEPLOY_KNOWN_HOSTS` | empreinte de la VM, ex. sortie de `ssh-keyscan -H 10.0.0.12` **vérifiée avec le formateur** |

**Sur la VM**, crée `~/novaservices/app.env` une fois (il n'est jamais dans Git) ; `deploy.sh` le passe au conteneur :

```
JWT_SECRET=<une longue valeur aléatoire>
ADMIN_EMAIL=admin@novaservices.fr
ADMIN_PASSWORD=<mot de passe du premier administrateur>
SEED_DEMO=1
```

La base SQLite est dans le volume Docker `novaservices-data` : elle survit aux déploiements et aux retours arrière.

**Registre** : le package GHCR est privé par défaut. Le rendre public (*Packages → Package settings → Change visibility*)
ou faire sur la VM un `docker login ghcr.io` avec un token `read:packages`.

**Protection de `main`** (étape 8) : *Settings → Branches → Add rule* → « Require status checks to pass » en cochant
`Tests` et `Image Docker`, et « Require a pull request before merging ». Sans cette règle, un job rouge n'empêche pas la fusion.

## Provoquer une régression (étape 8)

Par exemple, dans `visible_tickets()` (`novaservices/tickets.py`), remplacer `if not g.user.is_admin:` par
`if g.user.is_admin:`, committer et pousser : un utilisateur verrait les tickets des autres,
`test_un_utilisateur_ne_voit_que_ses_tickets` échoue et le pipeline passe au rouge. Corriger et repousser.

## V2 et retour arrière (étape 13)

1. Nouvelle branche, passer `APP_VERSION` à `"2.0.0"` dans `.github/workflows/ci-cd.yml`, PR puis fusion.
2. Vérifier `curl http://VM:8080/version` → `"version": "2.0.0"` et le nouveau commit.
3. Simuler une panne : *Actions → CI/CD → Run workflow* sur `main` en cochant **Simuler une panne**.
   Le conteneur démarre avec `/health` en 503, le job échoue, les journaux s'affichent et `deploy.sh`
   relance automatiquement l'image précédente.
4. Vérifier `/health` et `/version`.

Rollback manuel sur la VM : `bash ~/deploy.sh --rollback` (redéploie l'avant-dernière version fonctionnelle).
L'état est conservé dans `~/novaservices/current_image` et `~/novaservices/previous_image`.

# NovaServices — API de tickets (TP CI/CD)

Mini-API Flask de gestion de tickets informatiques, avec une chaîne CI/CD complète :
tests → image Docker → publication GHCR → déploiement sur VM de préproduction → rollback.

## Fiche de choix du binôme (étape 1)

| Rubrique | Valeur |
|---|---|
| Application et besoin métier | **NovaServices Tickets** : suivi des tickets du support informatique. Fonctionnalité modifiée : création de ticket + filtre par statut |
| Source du projet | URL du dépôt GitHub du binôme |
| Exécution | `python app.py` (dev) / `gunicorn app:app` (conteneur), port interne **8000** |
| Validation | `GET /health` → 200 ; `GET /tickets` → liste JSON des tickets ; URL inconnue → 404 |
| Identification | `GET /version` → `{"version": APP_VERSION, "commit": GIT_COMMIT}` |

## Routes

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/` | Interface web (liste, filtre, création de tickets) |
| GET | `/health` | Contrôle de disponibilité (`503` si `FAIL_HEALTH=1`) |
| GET | `/version` | Version et commit Git de l'image |
| GET | `/tickets?statut=ouvert` | Liste (filtre optionnel) |
| GET | `/tickets/<id>` | Un ticket |
| POST | `/tickets` | Création : `{"titre": "...", "priorite": "basse\|normale\|haute"}` |

## Structure

```
app.py                       application Flask
tests/test_app.py            tests pytest
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
cp .env.example .env               # lu par /version (non versionné)
python app.py                      # http://localhost:8000/health
python -m pytest -q
```

## Docker (étape 9)

```bash
docker build -t application-tp:local .
docker run -d --name application-tp-local -p 8080:8000 application-tp:local
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

**Registre** : le package GHCR est privé par défaut. Le rendre public (*Packages → Package settings → Change visibility*)
ou faire sur la VM un `docker login ghcr.io` avec un token `read:packages`.

**Protection de `main`** (étape 8) : *Settings → Branches → Add rule* → « Require status checks to pass » en cochant
`Tests` et `Image Docker`, et « Require a pull request before merging ». Sans cette règle, un job rouge n'empêche pas la fusion.

## Provoquer une régression (étape 8)

Par exemple, dans `app.py`, remplacer `return jsonify(status="ok")` par `return jsonify(status="ok"), 500`,
committer et pousser : `test_health_repond_200` échoue, le pipeline passe au rouge. Annuler la modification et repousser.

## V2 et retour arrière (étape 13)

1. Nouvelle branche, passer `APP_VERSION` à `"2.0.0"` dans `.github/workflows/ci-cd.yml`, PR puis fusion.
2. Vérifier `curl http://VM:8080/version` → `"version": "2.0.0"` et le nouveau commit.
3. Simuler une panne : *Actions → CI/CD → Run workflow* sur `main` en cochant **Simuler une panne**.
   Le conteneur démarre avec `/health` en 503, le job échoue, les journaux s'affichent et `deploy.sh`
   relance automatiquement l'image précédente.
4. Vérifier `/health` et `/version`.

Rollback manuel sur la VM : `bash ~/deploy.sh --rollback` (redéploie l'avant-dernière version fonctionnelle).
L'état est conservé dans `~/novaservices/current_image` et `~/novaservices/previous_image`.

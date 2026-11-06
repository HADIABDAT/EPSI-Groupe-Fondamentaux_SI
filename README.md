# NovaServices

Un helpdesk pour le support informatique. Les utilisateurs ouvrent des tickets et suivent leurs demandes. Les administrateurs du support les prennent en charge, répondent et les résolvent.

L'application est écrite en Flask, avec une connexion par JWT et un tableau de bord pour chaque rôle. À chaque push sur `main`, GitHub Actions lance les tests, construit l'image Docker, la publie sur GHCR et la déploie sur une VM de préproduction. Si la nouvelle version ne répond pas, la VM revient à la précédente.

## Lancer en local

Il faut Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

L'application tourne sur http://localhost:8000.

Avec `SEED_DEMO=1` (la valeur par défaut dans `.env`), la base est remplie au premier lancement avec des comptes et des tickets fictifs. Tu peux te connecter avec :

| Rôle | E-mail | Mot de passe |
|---|---|---|
| Administrateur | `camille.martin@novaservices.fr` | `novaservices` |
| Utilisateur | `lea.fournier@novaservices.fr` | `novaservices` |

## Lancer les tests

```bash
python -m pytest -q
```

## Lancer avec Docker

```bash
docker build -t novaservices .
docker run -p 8080:8000 -e SEED_DEMO=1 novaservices
```

L'application est alors sur http://localhost:8080.

## Déploiement

Le pipeline est dans `.github/workflows/ci-cd.yml` :

1. Une pull request lance les tests et construit l'image, sans rien publier.
2. Un push sur `main` publie l'image sur GHCR, puis `deploy.sh` la déploie sur la VM par SSH.
3. Si `/health` ne répond pas après le déploiement, `deploy.sh` relance la version précédente.

Sur la VM, `bash ~/deploy.sh --rollback` revient à la version précédente à la main.

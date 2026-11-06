"""Point d'entrée : `python app.py` en local, `gunicorn app:app` dans le conteneur."""

import os

from dotenv import load_dotenv

# Charge .env sans écraser les variables déjà définies (celles injectées par Docker et le pipeline priment).
load_dotenv()

from novaservices import create_app  # noqa: E402  (après load_dotenv : la config lit l'environnement)

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

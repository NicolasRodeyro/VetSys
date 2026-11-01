"""Aplicación web de VetSys.

Se usa el patrón "app factory" de Flask: la aplicación se crea dentro de una
función en lugar de ser una variable global. Así los tests pueden crear su
propia instancia con otra configuración.
"""

import os

from dotenv import load_dotenv
from flask import Flask


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev")

    @app.route("/")
    def inicio() -> str:
        return "VetSys funcionando"

    return app

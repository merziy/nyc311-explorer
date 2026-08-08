from flask import Flask

from app.config import settings
from app.extensions import cors, db, limiter, migrate


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})
    limiter.init_app(app)

    from app import models  # noqa: F401  (registers models with SQLAlchemy metadata)
    from app.routes import api_bp

    app.register_blueprint(api_bp)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

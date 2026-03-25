from datetime import datetime


def _load_app_and_db():
    """Best-effort loader to support both app factory and global app patterns."""
    try:
        from app import create_app, db  # type: ignore

        app = create_app()
        return app, db
    except Exception:
        pass

    try:
        from app import app, db  # type: ignore

        return app, db
    except Exception as e:
        raise RuntimeError(
            "Could not import Flask app/db. Expected either 'from app import create_app, db' "
            "or 'from app import app, db'."
        ) from e


def main():
    app, db = _load_app_and_db()

    with app.app_context():
        print("[Ad Stories DB] Starting db.create_all() ...")
        db.create_all()
        print("[Ad Stories DB] Done.")
        print("[Ad Stories DB] Timestamp:", datetime.utcnow().isoformat())


if __name__ == "__main__":
    main()

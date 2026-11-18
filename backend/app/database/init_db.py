"""Database initialization script to create all schema tables."""

from backend.app.database.session import Base, engine
import backend.app.models  # Ensure all models are registered with Base.metadata


def init_db(drop_first: bool = False):
    """Initializes the database, creating all tables."""
    if drop_first:
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    init_db()

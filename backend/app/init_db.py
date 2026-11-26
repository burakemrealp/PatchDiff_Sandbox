from sqlalchemy import inspect
from app.core.database import engine, Base
from app.models.entities import (  # noqa: F401
    AutoPatchDiff,
    Champion,
    ChampionSnapshot,
    Item,
    ItemSnapshot,
    PatchSimulationLog,
    PatchVersion,
    RecommendationFeedback,
    Rune,
)


def init_database() -> None:
    print("⏳ Connecting to PostgreSQL and creating database tables...")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ Success! Active database tables: {tables}")


if __name__ == "__main__":
    init_database()
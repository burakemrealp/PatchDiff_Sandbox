import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    ItemSnapshot,
    PatchVersion,
    Rune,
)


@pytest.fixture()
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def test_all_versioned_tables_are_registered(memory_db):
    _, engine = memory_db
    tables = set(inspect(engine).get_table_names())

    expected = {
        "champions",
        "items",
        "patch_logs",
        "patch_versions",
        "champion_snapshots",
        "item_snapshots",
        "runes",
        "auto_patch_diffs",
    }
    assert expected.issubset(tables)


def test_versioned_snapshot_crud_and_unique_constraints(memory_db):
    db, _ = memory_db

    v1 = PatchVersion(version="15.1.1", is_latest=False, sync_status="synced")
    v2 = PatchVersion(
        version="15.2.1", previous_version="15.1.1", is_latest=True, sync_status="synced"
    )
    db.add_all([v1, v2])
    db.flush()

    champ = ChampionSnapshot(
        patch_version="15.2.1",
        champion_key="Ahri",
        riot_id=103,
        name="Ahri",
        title="Dokuz Kuyruklu Tilki",
        tags=["Mage", "Assassin"],
        partype="Mana",
        base_stats={"base_hp": 590.0},
        abilities={"Q": {"base_damage": [80, 130, 180, 230, 280]}},
        abilities_source="cdragon",
    )
    item = ItemSnapshot(
        patch_version="15.2.1",
        item_id="3089",
        name="Rabadon'un Şapkası",
        gold_total=3600,
        is_completed=True,
        stats={"ap": 130.0, "ap_multiplier": 0.30},
        tags=["SpellDamage"],
        unique_groups=[],
    )
    rune = Rune(
        patch_version="15.2.1",
        rune_id=8112,
        key="Electrocute",
        name="Elektrik Ver",
        tree_id=8100,
        tree_key="Domination",
        tree_name="Hakimiyet",
        slot_index=0,
        is_keystone=True,
    )
    diff = AutoPatchDiff(
        from_version="15.1.1",
        to_version="15.2.1",
        entity_type="champion",
        entity_key="Ahri",
        entity_name="Ahri",
        direction="BUFF",
        diff_payload={"champion_key": "Ahri", "stat_deltas": [], "ability_deltas": []},
    )
    db.add_all([champ, item, rune, diff])
    db.commit()

    assert db.query(ChampionSnapshot).filter_by(patch_version="15.2.1", champion_key="Ahri").count() == 1
    assert db.query(ItemSnapshot).filter_by(patch_version="15.2.1", is_completed=True).count() == 1
    assert db.query(Rune).filter_by(patch_version="15.2.1", is_keystone=True).count() == 1
    assert db.query(AutoPatchDiff).filter_by(to_version="15.2.1", entity_key="Ahri").count() == 1

    # Duplicate champion snapshot for same patch version must violate UniqueConstraint
    dup_champ = ChampionSnapshot(
        patch_version="15.2.1",
        champion_key="Ahri",
        name="Ahri",
        base_stats={"base_hp": 590.0},
        abilities={},
    )
    db.add(dup_champ)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

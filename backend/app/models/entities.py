from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Champion(Base):
    """Stores base stats and ability coefficients for champions."""
    __tablename__ = "champions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # e.g., "Ahri", "Zed"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=True)
    patch_version: Mapped[str] = mapped_column(String(20), nullable=False, default="14.22.1")

    # Base stats and per-level growth coefficients (HP, AD, Armor, MR, Attack Speed, etc.)
    base_stats: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Base damage, cooldown, and scaling ratios (AP/AD/BonusAD) for Q, W, E, R abilities
    abilities: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Item(Base):
    """Stores gold costs and combat stats for in-game items."""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g., "3089" (Rabadon)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gold_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Normalized item stats dict (e.g., {"ap": 130, "magic_pen_flat": 15, ...})
    stats: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)


class PatchSimulationLog(Base):
    """Logs LLM-parsed patch notes and simulation summaries."""
    __tablename__ = "patch_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    champion_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    raw_patch_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_diff: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    simulation_result: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class PatchVersion(Base):
    """Tracks LoL patch versions synchronized from Riot Data Dragon and CommunityDragon."""
    __tablename__ = "patch_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    previous_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    sync_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    champions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ChampionSnapshot(Base):
    """Versioned champion base stats, metadata tags, and ability data for a specific patch."""
    __tablename__ = "champion_snapshots"
    __table_args__ = (
        UniqueConstraint("patch_version", "champion_key", name="uq_champ_snapshot_patch_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_version: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("patch_versions.version", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    champion_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    riot_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    partype: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    base_stats: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    abilities: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    abilities_source: Mapped[str] = mapped_column(String(30), default="seed", nullable=False)


class ItemSnapshot(Base):
    """Versioned item stats, gold cost, unique groups, passive text, and icon URL for a specific patch."""
    __tablename__ = "item_snapshots"
    __table_args__ = (
        UniqueConstraint("patch_version", "item_id", name="uq_item_snapshot_patch_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_version: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("patch_versions.version", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    item_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    gold_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    purchasable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stats: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    unique_groups: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    passive_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Rune(Base):
    """Versioned LoL rune trees, keystones, and minor rune data for a specific patch."""
    __tablename__ = "runes"
    __table_args__ = (
        UniqueConstraint("patch_version", "rune_id", name="uq_rune_patch_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_version: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("patch_versions.version", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rune_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tree_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tree_key: Mapped[str] = mapped_column(String(50), nullable=False)
    tree_name: Mapped[str] = mapped_column(String(100), nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_keystone: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    short_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    long_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effect_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)


class AutoPatchDiff(Base):
    """Automatically computed champion, item, and rune diffs between two patch versions (from_version -> to_version)."""
    __tablename__ = "auto_patch_diffs"
    __table_args__ = (
        UniqueConstraint(
            "from_version",
            "to_version",
            "entity_type",
            "entity_key",
            name="uq_auto_diff_ver_entity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_version: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    to_version: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("patch_versions.version", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # "champion" | "item" | "rune"
    entity_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_name: Mapped[str] = mapped_column(String(120), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # "BUFF" | "NERF" | "ADJUSTMENT"
    diff_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class RecommendationFeedback(Base):
    """User 1-5 star ratings and comments submitted for AI build & rune recommendations."""
    __tablename__ = "recommendation_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_version: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    champion_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="mid", nullable=False)
    game_map: Mapped[str] = mapped_column(String(20), default="sr", nullable=False)
    target_profile: Mapped[str] = mapped_column(String(20), default="squishy", nullable=False)
    playstyle: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    items_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rune_page_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    is_helpful: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

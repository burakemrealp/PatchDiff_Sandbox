from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class StatName(str, Enum):
    """Supported champion base stats and per-level growth attributes."""
    BASE_HP = "base_hp"
    HP_GROWTH = "hp_growth"
    BASE_MP = "base_mp"
    MP_GROWTH = "mp_growth"
    BASE_AD = "base_ad"
    AD_GROWTH = "ad_growth"
    BASE_ARMOR = "base_armor"
    ARMOR_GROWTH = "armor_growth"
    BASE_MR = "base_mr"
    MR_GROWTH = "mr_growth"
    BASE_ATTACK_SPEED = "base_attack_speed"
    ATTACK_SPEED_GROWTH = "attack_speed_growth"
    ATTACK_RANGE = "attack_range"
    MOVE_SPEED = "move_speed"
    BASE_HP_REGEN = "base_hp_regen"
    HP_REGEN_GROWTH = "hp_regen_growth"
    BASE_MP_REGEN = "base_mp_regen"
    MP_REGEN_GROWTH = "mp_regen_growth"


class AbilitySlot(str, Enum):
    """Champion ability slots."""
    PASSIVE = "P"
    Q = "Q"
    W = "W"
    E = "E"
    R = "R"


class DamageType(str, Enum):
    """In-game damage types."""
    PHYSICAL = "physical"
    MAGIC = "magic"
    TRUE = "true"


class ScalingStat(str, Enum):
    """Source stats that ability ratios scale with."""
    AP = "ap"
    TOTAL_AD = "total_ad"
    BONUS_AD = "bonus_ad"
    BONUS_HP = "bonus_hp"
    ARMOR = "armor"
    MR = "mr"
    TARGET_MAX_HP = "target_max_hp"


class ChangeDirection(str, Enum):
    """Net balance direction for UI color coding (green/red/amber)."""
    BUFF = "BUFF"
    NERF = "NERF"
    ADJUSTMENT = "ADJUSTMENT"


class StatDelta(BaseModel):
    """Base stat change schema (e.g., Base Armor 32 -> 29)."""
    stat_name: StatName = Field(description="Target base stat identifier")
    stat_label: Optional[str] = Field(default=None, description="Human-readable stat label")
    old_value: float = Field(description="Pre-patch value")
    new_value: float = Field(description="Post-patch value")
    direction: ChangeDirection = Field(default=ChangeDirection.ADJUSTMENT)
    delta_percent: float = Field(default=0.0, description="Percentage change ratio")

    @model_validator(mode="after")
    def compute_stat_metrics(self) -> "StatDelta":
        diff = self.new_value - self.old_value
        if self.old_value != 0:
            self.delta_percent = round((diff / self.old_value) * 100.0, 2)

        if diff > 0:
            self.direction = ChangeDirection.BUFF
        elif diff < 0:
            self.direction = ChangeDirection.NERF
        else:
            self.direction = ChangeDirection.ADJUSTMENT
        return self


class ScalingDelta(BaseModel):
    """Ability scaling ratio change (e.g., AP Ratio 0.60 -> 0.75)."""
    scaling_stat: ScalingStat = Field(description="Scaling source stat (ap, bonus_ad, etc.)")
    old_ratio: float = Field(description="Old scaling ratio (e.g., 0.60 for 60%)")
    new_ratio: float = Field(description="New scaling ratio (e.g., 0.75 for 75%)")


class AbilityDelta(BaseModel):
    """Ability (Q, W, E, R) base damage, cooldown, mana cost, and scaling ratio changes."""
    slot: AbilitySlot = Field(description="Ability keybind (P, Q, W, E, R)")
    ability_name: Optional[str] = Field(default=None, description="Ability name")
    damage_type: DamageType = Field(default=DamageType.MAGIC, description="Primary damage type")

    # 5-rank array for basic abilities (Q, W, E), 3-rank array for ultimate (R)
    old_base_damage: Optional[List[float]] = Field(
        default=None, description="Pre-patch base damage array by ability rank"
    )
    new_base_damage: Optional[List[float]] = Field(
        default=None, description="Post-patch base damage array by ability rank"
    )

    old_cooldown: Optional[List[float]] = Field(
        default=None, description="Pre-patch cooldown array by ability rank (seconds)"
    )
    new_cooldown: Optional[List[float]] = Field(
        default=None, description="Post-patch cooldown array by ability rank (seconds)"
    )

    old_mana_cost: Optional[List[float]] = Field(
        default=None, description="Pre-patch mana or resource cost array by ability rank"
    )
    new_mana_cost: Optional[List[float]] = Field(
        default=None, description="Post-patch mana or resource cost array by ability rank"
    )

    scaling_changes: List[ScalingDelta] = Field(
        default_factory=list, description="Scaling ratio changes (AP/AD/HP/Resist)"
    )
    direction: ChangeDirection = Field(default=ChangeDirection.ADJUSTMENT)

    @model_validator(mode="after")
    def evaluate_ability_direction(self) -> "AbilityDelta":
        """Infers BUFF/NERF direction from damage increases and cooldown/mana reductions."""
        score = 0

        # 1. Base damage check (increase = buff)
        if self.old_base_damage and self.new_base_damage:
            if sum(self.new_base_damage) > sum(self.old_base_damage):
                score += 1
            elif sum(self.new_base_damage) < sum(self.old_base_damage):
                score -= 1

        # 2. Scaling ratio check (increase = buff)
        for s in self.scaling_changes:
            if s.new_ratio > s.old_ratio:
                score += 1
            elif s.new_ratio < s.old_ratio:
                score -= 1

        # 3. Cooldown check (decrease = buff)
        if self.old_cooldown and self.new_cooldown:
            if sum(self.new_cooldown) < sum(self.old_cooldown):
                score += 1
            elif sum(self.new_cooldown) > sum(self.old_cooldown):
                score -= 1

        # 4. Mana cost check (decrease = buff, increase = nerf)
        if self.old_mana_cost and self.new_mana_cost:
            if sum(self.new_mana_cost) < sum(self.old_mana_cost):
                score += 1
            elif sum(self.new_mana_cost) > sum(self.old_mana_cost):
                score -= 1

        if score > 0:
            self.direction = ChangeDirection.BUFF
        elif score < 0:
            self.direction = ChangeDirection.NERF
        else:
            self.direction = ChangeDirection.ADJUSTMENT
        return self


class MechanicDelta(BaseModel):
    """Generic numeric diffs for shields, heals, summon health, passive ratios, and alternate forms."""
    spell_name: str = Field(description="Internal spell or form identifier (e.g., GalioW, AnnieR, AzirW, GnarBigQ)")
    spell_label: Optional[str] = Field(default=None, description="Player-friendly ability heading (e.g., Annie R — Tibbers)")
    field_name: str = Field(description="Changed parameter key (e.g., ShieldRatio, TibbersTotalHP)")
    field_label: Optional[str] = Field(default=None, description="Player-friendly parameter label (e.g., Aura Damage)")
    old_values: List[float] = Field(default_factory=list)
    new_values: List[float] = Field(default_factory=list)
    display_old: Optional[str] = Field(default=None, description="Formatted pre-patch value string")
    display_new: Optional[str] = Field(default=None, description="Formatted post-patch value string")
    direction: ChangeDirection = Field(default=ChangeDirection.ADJUSTMENT)


class ChampionPatchDiff(BaseModel):
    """Aggregated patch delta summary for a single champion."""
    champion_key: str = Field(description="Canonical champion key (e.g., Ahri, Zed, Jinx)")
    summary: Optional[str] = Field(default=None, description="One-sentence summary of patch changes")
    stat_deltas: List[StatDelta] = Field(default_factory=list)
    ability_deltas: List[AbilityDelta] = Field(default_factory=list)
    mechanic_deltas: List[MechanicDelta] = Field(default_factory=list)


class PatchPayload(BaseModel):
    """Root structured patch payload produced by the extractor and consumed by the simulation engine."""
    patch_version: str = Field(default="14.23", description="Target patch version")
    champions: List[ChampionPatchDiff] = Field(default_factory=list)

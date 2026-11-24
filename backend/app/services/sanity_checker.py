from typing import List, Tuple
from app.schemas.patch_contracts import (
    PatchPayload,
    ChampionPatchDiff,
    AbilitySlot,
    AbilityDelta,
    StatDelta,
)


class PatchSanityChecker:
    """
    Validates LLM-extracted PatchPayload objects against game physics constraints,
    automatically fixing percentage/decimal unit errors (e.g., 75.0 -> 0.75) and rank array lengths.
    """

    @classmethod
    def validate_and_sanitize(cls, payload: PatchPayload) -> Tuple[PatchPayload, List[str]]:
        warnings: List[str] = []
        sanitized_champions: List[ChampionPatchDiff] = []

        for champ in payload.champions:
            # 1. Base Stat Validation
            valid_stats: List[StatDelta] = []
            for st in champ.stat_deltas:
                if st.old_value <= 0 or st.new_value <= 0:
                    warnings.append(
                        f"[{champ.champion_key}] Ignored invalid non-positive stat delta ({st.stat_name.value})."
                    )
                    continue

                # Re-validate to recompute delta_percent and BUFF/NERF direction
                valid_stats.append(StatDelta.model_validate(st.model_dump()))

            # 2. Ability & Scaling Ratio Validation
            valid_abilities: List[AbilityDelta] = []
            for ab in champ.ability_deltas:
                expected_ranks = 3 if ab.slot == AbilitySlot.R else 5

                # Validate rank array length for base damage (e.g., expand scalar [100] to 5 ranks)
                if ab.old_base_damage:
                    ab.old_base_damage = cls._normalize_rank_array(
                        ab.old_base_damage, expected_ranks, champ.champion_key, ab.slot.value, "old_base_damage", warnings
                    )
                if ab.new_base_damage:
                    ab.new_base_damage = cls._normalize_rank_array(
                        ab.new_base_damage, expected_ranks, champ.champion_key, ab.slot.value, "new_base_damage", warnings
                    )

                # Validate rank array length for cooldowns
                if ab.old_cooldown:
                    ab.old_cooldown = cls._normalize_rank_array(
                        ab.old_cooldown, expected_ranks, champ.champion_key, ab.slot.value, "old_cooldown", warnings
                    )
                if ab.new_cooldown:
                    ab.new_cooldown = cls._normalize_rank_array(
                        ab.new_cooldown, expected_ranks, champ.champion_key, ab.slot.value, "new_cooldown", warnings
                    )

                # Fix scaling unit mismatches: if the LLM output '75.0' instead of '0.75', divide by 100
                for sc in ab.scaling_changes:
                    if sc.old_ratio > 5.0:
                        fixed_old = round(sc.old_ratio / 100.0, 4)
                        warnings.append(
                            f"[{champ.champion_key} {ab.slot.value}] Fixed old ratio unit: {sc.old_ratio} -> {fixed_old}"
                        )
                        sc.old_ratio = fixed_old

                    if sc.new_ratio > 5.0:
                        fixed_new = round(sc.new_ratio / 100.0, 4)
                        warnings.append(
                            f"[{champ.champion_key} {ab.slot.value}] Fixed new ratio unit: {sc.new_ratio} -> {fixed_new}"
                        )
                        sc.new_ratio = fixed_new

                # Recompute ability direction with sanitized values
                valid_abilities.append(AbilityDelta.model_validate(ab.model_dump()))

            sanitized_champions.append(
                ChampionPatchDiff(
                    champion_key=champ.champion_key,
                    summary=champ.summary,
                    stat_deltas=valid_stats,
                    ability_deltas=valid_abilities,
                )
            )

        clean_payload = PatchPayload(
            patch_version=payload.patch_version,
            champions=sanitized_champions,
        )
        return clean_payload, warnings

    @staticmethod
    def _normalize_rank_array(
        arr: List[float],
        expected_len: int,
        champ: str,
        slot: str,
        field_name: str,
        warnings: List[str],
    ) -> List[float]:
        # Clamp negative numbers to zero
        cleaned = [max(0.0, float(x)) for x in arr]

        if len(cleaned) == expected_len:
            return cleaned

        if len(cleaned) == 1:
            warnings.append(
                f"[{champ} {slot}] '{field_name}' arrived as scalar ({cleaned[0]}); expanded to {expected_len} ranks."
            )
            return cleaned * expected_len

        if len(cleaned) > expected_len:
            warnings.append(
                f"[{champ} {slot}] '{field_name}' had {len(cleaned)} items; trimmed to {expected_len} ranks."
            )
            return cleaned[:expected_len]

        # Pad short arrays by repeating the last rank value
        warnings.append(
            f"[{champ} {slot}] '{field_name}' had {len(cleaned)} items; padded to {expected_len} ranks."
        )
        padding = [cleaned[-1]] * (expected_len - len(cleaned))
        return cleaned + padding

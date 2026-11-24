import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.versioning import to_display_version
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.schemas.patch_contracts import (
    AbilityDelta,
    AbilitySlot,
    ChampionPatchDiff,
    ChangeDirection,
    DamageType,
    MechanicDelta,
    ScalingDelta,
    ScalingStat,
    StatDelta,
    StatName,
)
from app.services.readable_formatter import (
    format_field_label,
    format_readable_value_series,
    format_spell_label,
    format_stat_label,
)

FLOAT_EPSILON = 1e-4
SLOTS = ["Q", "W", "E", "R"]
VALID_SCALING_KEYS = {s.value for s in ScalingStat}

# Parameter keywords where a decrease represents a BUFF (e.g., cooldown, mana cost, cast time)
LOWER_IS_BETTER_TOKENS = ("cooldown", "cd", "cost", "mana", "energy", "delay", "casttime", "recharge", "lockout")

# Internal/visual DataValues keys that do not reflect gameplay balance changes
NOISE_FIELD_TOKENS = ("tooltip", "indicator", "vfx", "sfx", "anim", "debug", "color", "icon")

_NUM_TOKEN_RE = re.compile(r"%?\d+(?:\.\d+)?%?")


def _lists_differ(a: List[float], b: List[float], eps: float = 1e-3) -> bool:
    if len(a) != len(b):
        return True
    return any(abs(float(x) - float(y)) > eps for x, y in zip(a, b))


def _resolve_overall_direction(directions: List[ChangeDirection]) -> ChangeDirection:
    buffs = sum(1 for d in directions if d == ChangeDirection.BUFF)
    nerfs = sum(1 for d in directions if d == ChangeDirection.NERF)
    if buffs > 0 and nerfs == 0:
        return ChangeDirection.BUFF
    if nerfs > 0 and buffs == 0:
        return ChangeDirection.NERF
    if buffs > nerfs:
        return ChangeDirection.BUFF
    if nerfs > buffs:
        return ChangeDirection.NERF
    return ChangeDirection.ADJUSTMENT


def _infer_mechanic_direction(field_name: str, old_vals: List[float], new_vals: List[float]) -> ChangeDirection:
    old_sum = sum(old_vals)
    new_sum = sum(new_vals)
    if abs(new_sum - old_sum) <= FLOAT_EPSILON:
        return ChangeDirection.ADJUSTMENT

    lower_is_buff = any(tok in field_name.lower() for tok in LOWER_IS_BETTER_TOKENS)
    increased = new_sum > old_sum
    if lower_is_buff:
        return ChangeDirection.NERF if increased else ChangeDirection.BUFF
    return ChangeDirection.BUFF if increased else ChangeDirection.NERF


def _extract_passive_body(passive_text: Optional[str]) -> str:
    """Normalizes item passive/active description text by collapsing whitespace across lines."""
    if not passive_text:
        return ""
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in passive_text.splitlines() if ln.strip()]
    return " | ".join(lines)


def _extract_numeric_tokens(text: str) -> List[float]:
    nums: List[float] = []
    for tok in _NUM_TOKEN_RE.findall(text or ""):
        clean = tok.replace("%", "")
        try:
            nums.append(round(float(clean), 4))
        except ValueError:
            continue
    return nums


def _diff_text_numbers(old_text: str, new_text: str) -> Optional[Dict[str, Any]]:
    """Extracts numeric balance differences between two description strings (item passives or runes)."""
    norm_old = _extract_passive_body(old_text)
    norm_new = _extract_passive_body(new_text)
    if norm_old == norm_new:
        return None

    old_nums = _extract_numeric_tokens(norm_old)
    new_nums = _extract_numeric_tokens(norm_new)

    changed_pairs: List[Dict[str, float]] = []
    if len(old_nums) == len(new_nums):
        for o, n in zip(old_nums, new_nums):
            if abs(n - o) > FLOAT_EPSILON:
                changed_pairs.append({"old": o, "new": n})
    else:
        # Summarize when numeric token count changes across versions
        if old_nums != new_nums:
            changed_pairs.append(
                {
                    "old": round(sum(old_nums), 2) if old_nums else 0.0,
                    "new": round(sum(new_nums), 2) if new_nums else 0.0,
                }
            )

    if not changed_pairs:
        # Filter out pure wording/formatting edits when zero numeric values changed
        return None

    increases = sum(1 for p in changed_pairs if p["new"] > p["old"])
    decreases = sum(1 for p in changed_pairs if p["new"] < p["old"])
    if increases > decreases:
        direction = ChangeDirection.BUFF
    elif decreases > increases:
        direction = ChangeDirection.NERF
    else:
        direction = ChangeDirection.ADJUSTMENT

    return {
        "changed_numbers": changed_pairs[:8],
        "direction": direction.value,
        "old_snippet": norm_old[:220],
        "new_snippet": norm_new[:220],
    }


class PatchDiffEngine:
    """
    Computes patch-agnostic balance diffs between two versions (from_version -> to_version):
    - Champions: Base stats (including attack_range) + Q/W/E/R damage, cooldown, mana, scaling +
      mechanics across shields, heals, summons, and alternate forms (_raw_spells)
    - Items: Gold cost + stat deltas + CDragon passive DataValues and passive text numbers
    - Runes: CDragon effect coefficients (effect_values) and tooltip number changes

    Default DB snapshot summaries use 'tr_TR' labels matching primary snapshot names; non-Turkish
    locales are localized on read via `locale_service.localize_diff_payload`.
    """

    @staticmethod
    def _diff_raw_spells(
        old_raw_spells: Dict[str, Any],
        new_raw_spells: Dict[str, Any],
        champion_name: str = "",
        abilities: Optional[Dict[str, Any]] = None,
    ) -> List[MechanicDelta]:
        """Extracts human-readable MechanicDelta items from _raw_spells DataValues and mSpellCalculations."""
        deltas: List[MechanicDelta] = []
        common_spells = sorted(set(old_raw_spells.keys()) & set(new_raw_spells.keys()))

        for spell_name in common_spells:
            old_sp = old_raw_spells[spell_name] or {}
            new_sp = new_raw_spells[spell_name] or {}
            spell_label = format_spell_label(champion_name or spell_name, spell_name, abilities)

            # 1. DataValues diffs (slice [1:6] for 5-rank spells or [1:4] for 3-rank ultimates)
            old_dvs = old_sp.get("data_values") or {}
            new_dvs = new_sp.get("data_values") or {}
            is_ult = spell_name.lower().endswith("r")
            slice_end = 4 if is_ult else 6

            for dv_name in sorted(set(old_dvs.keys()) & set(new_dvs.keys())):
                if any(tok in dv_name.lower() for tok in NOISE_FIELD_TOKENS):
                    continue
                o_raw = old_dvs[dv_name]
                n_raw = new_dvs[dv_name]
                o_slice = [round(float(x), 4) for x in (o_raw[1:slice_end] if len(o_raw) >= slice_end else o_raw)]
                n_slice = [round(float(x), 4) for x in (n_raw[1:slice_end] if len(n_raw) >= slice_end else n_raw)]

                if o_slice and n_slice and _lists_differ(o_slice, n_slice, eps=1e-3):
                    o_compact = [o_slice[0]] if len(set(o_slice)) == 1 else o_slice
                    n_compact = [n_slice[0]] if len(set(n_slice)) == 1 else n_slice
                    direction = _infer_mechanic_direction(dv_name, o_slice, n_slice)
                    disp_old, disp_new = format_readable_value_series(dv_name, o_compact, n_compact)
                    deltas.append(
                        MechanicDelta(
                            spell_name=spell_name,
                            spell_label=spell_label,
                            field_name=dv_name,
                            field_label=format_field_label(dv_name),
                            old_values=o_compact,
                            new_values=n_compact,
                            display_old=disp_old,
                            display_new=disp_new,
                            direction=direction,
                        )
                    )

            # 2. mSpellCalculations numeric coefficient diffs
            old_calcs = old_sp.get("calculations") or {}
            new_calcs = new_sp.get("calculations") or {}
            for calc_name in sorted(set(old_calcs.keys()) & set(new_calcs.keys())):
                if calc_name.startswith("{") or any(tok in calc_name.lower() for tok in NOISE_FIELD_TOKENS):
                    continue
                o_sig = old_calcs[calc_name] or {}
                n_sig = new_calcs[calc_name] or {}

                changed_old: List[float] = []
                changed_new: List[float] = []
                for k in sorted(set(o_sig.keys()) & set(n_sig.keys())):
                    leaf = k.split(".")[-1].lower()
                    if leaf in ("mstat", "mstatformula", "mlevel", "meffectindex"):
                        continue
                    ov = round(float(o_sig[k]), 4)
                    nv = round(float(n_sig[k]), 4)
                    if abs(nv - ov) > 1e-3:
                        changed_old.append(ov)
                        changed_new.append(nv)

                if changed_old and changed_new:
                    direction = _infer_mechanic_direction(calc_name, changed_old, changed_new)
                    disp_old, disp_new = format_readable_value_series(
                        calc_name, changed_old[:5], changed_new[:5]
                    )
                    deltas.append(
                        MechanicDelta(
                            spell_name=spell_name,
                            spell_label=spell_label,
                            field_name=calc_name,
                            field_label=format_field_label(calc_name),
                            old_values=changed_old[:5],
                            new_values=changed_new[:5],
                            display_old=disp_old,
                            display_new=disp_new,
                            direction=direction,
                        )
                    )

        return deltas

    @classmethod
    def diff_champions(
        cls, old_champ: ChampionSnapshot, new_champ: ChampionSnapshot
    ) -> Optional[Tuple[ChampionPatchDiff, ChangeDirection]]:
        old_stats = old_champ.base_stats or {}
        new_stats = new_champ.base_stats or {}

        stat_deltas: List[StatDelta] = []
        for stat_enum in StatName:
            key = stat_enum.value
            if key not in old_stats or key not in new_stats:
                continue
            old_v = round(float(old_stats[key]), 4)
            new_v = round(float(new_stats[key]), 4)
            if abs(new_v - old_v) > FLOAT_EPSILON:
                stat_deltas.append(
                    StatDelta(
                        stat_name=stat_enum,
                        stat_label=format_stat_label(key),
                        old_value=old_v,
                        new_value=new_v,
                    )
                )

        old_abilities = old_champ.abilities or {}
        new_abilities = new_champ.abilities or {}
        ability_deltas: List[AbilityDelta] = []

        for slot in SLOTS:
            old_ab = old_abilities.get(slot)
            new_ab = new_abilities.get(slot)
            if not old_ab or not new_ab:
                continue

            old_dmg = [float(x) for x in (old_ab.get("base_damage") or [])]
            new_dmg = [float(x) for x in (new_ab.get("base_damage") or [])]
            dmg_changed = bool(old_dmg and new_dmg and _lists_differ(old_dmg, new_dmg))

            old_cd = [float(x) for x in (old_ab.get("cooldown") or [])]
            new_cd = [float(x) for x in (new_ab.get("cooldown") or [])]
            cd_changed = bool(old_cd and new_cd and _lists_differ(old_cd, new_cd))

            old_mana = [float(x) for x in (old_ab.get("mana_cost") or [])]
            new_mana = [float(x) for x in (new_ab.get("mana_cost") or [])]
            mana_changed = bool(old_mana and new_mana and _lists_differ(old_mana, new_mana))

            old_scaling = old_ab.get("scaling") or {}
            new_scaling = new_ab.get("scaling") or {}
            scaling_changes: List[ScalingDelta] = []

            for sc_key in sorted(set(old_scaling.keys()) | set(new_scaling.keys())):
                if sc_key not in VALID_SCALING_KEYS:
                    continue
                old_r = round(float(old_scaling.get(sc_key, 0.0)), 4)
                new_r = round(float(new_scaling.get(sc_key, 0.0)), 4)
                if abs(new_r - old_r) > FLOAT_EPSILON:
                    scaling_changes.append(
                        ScalingDelta(
                            scaling_stat=ScalingStat(sc_key),
                            old_ratio=old_r,
                            new_ratio=new_r,
                        )
                    )

            if dmg_changed or cd_changed or mana_changed or scaling_changes:
                raw_dmg_type = str(new_ab.get("damage_type", "magic")).lower()
                dmg_type = (
                    DamageType(raw_dmg_type)
                    if raw_dmg_type in {"physical", "magic", "true"}
                    else DamageType.MAGIC
                )
                ability_deltas.append(
                    AbilityDelta(
                        slot=AbilitySlot(slot),
                        ability_name=new_ab.get("name") or f"{slot} Ability",
                        damage_type=dmg_type,
                        old_base_damage=old_dmg if dmg_changed else None,
                        new_base_damage=new_dmg if dmg_changed else None,
                        old_cooldown=old_cd if cd_changed else None,
                        new_cooldown=new_cd if cd_changed else None,
                        old_mana_cost=old_mana if mana_changed else None,
                        new_mana_cost=new_mana if mana_changed else None,
                        scaling_changes=scaling_changes,
                    )
                )

        # Generic _raw_spells diffs (shields, heals, summons, alternate forms, custom DataValues)
        raw_mechanic_deltas = cls._diff_raw_spells(
            old_abilities.get("_raw_spells") or {},
            new_abilities.get("_raw_spells") or {},
            champion_name=new_champ.name or new_champ.champion_key,
            abilities=new_abilities,
        )

        # Deduplicate mechanic deltas already displayed cleanly inside AbilityDelta
        mechanic_deltas: List[MechanicDelta] = []
        seen_mech_keys = set()
        ab_by_slot = {a.slot.value: a for a in ability_deltas}

        def _extract_slot_from_label(label: Optional[str]) -> Optional[str]:
            if not label:
                return None
            m = re.search(r"\b([QWER])\b", label)
            return m.group(1) if m else None

        for md in raw_mechanic_deltas:
            slot = _extract_slot_from_label(md.spell_label)
            ab = ab_by_slot.get(slot) if slot else None
            is_dup = False
            if ab is not None:
                # Skip when base damage series matches AbilityDelta
                if (
                    ab.old_base_damage
                    and ab.new_base_damage
                    and not _lists_differ(ab.old_base_damage, md.old_values, eps=1e-2)
                    and not _lists_differ(ab.new_base_damage, md.new_values, eps=1e-2)
                ):
                    is_dup = True
                # Skip when scaling ratio matches AbilityDelta
                if not is_dup and len(md.old_values) == 1 and len(md.new_values) == 1:
                    for sc in ab.scaling_changes:
                        if (
                            abs(sc.old_ratio - md.old_values[0]) < 1e-3
                            and abs(sc.new_ratio - md.new_values[0]) < 1e-3
                        ):
                            is_dup = True
                            break
            dedup_key = (slot or md.spell_label, md.field_label, md.display_old, md.display_new)
            if is_dup or dedup_key in seen_mech_keys:
                continue
            seen_mech_keys.add(dedup_key)
            mechanic_deltas.append(md)

        if not stat_deltas and not ability_deltas and not mechanic_deltas:
            return None

        directions = (
            [s.direction for s in stat_deltas]
            + [a.direction for a in ability_deltas]
            + [m.direction for m in mechanic_deltas]
        )
        overall_dir = _resolve_overall_direction(directions)

        # Default Turkish summary for primary DB storage (localized on read via locale_service.py)
        parts: List[str] = []
        if stat_deltas:
            parts.append(f"{len(stat_deltas)} taban istatistik")
        if ability_deltas:
            slots_str = "/".join(a.slot.value for a in ability_deltas)
            parts.append(f"{len(ability_deltas)} yetenek ({slots_str})")
        if mechanic_deltas:
            uniq_spells = sorted({m.spell_name for m in mechanic_deltas})[:4]
            parts.append(f"{len(mechanic_deltas)} mekanik/parametre ({', '.join(uniq_spells)})")
        summary = f"Otomatik yama farkı: {', '.join(parts)} değişikliği."

        diff = ChampionPatchDiff(
            champion_key=new_champ.champion_key,
            summary=summary,
            stat_deltas=stat_deltas,
            ability_deltas=ability_deltas,
            mechanic_deltas=mechanic_deltas[:12],
        )
        return diff, overall_dir

    @staticmethod
    def diff_items(
        old_item: ItemSnapshot, new_item: ItemSnapshot
    ) -> Optional[Tuple[Dict[str, Any], ChangeDirection]]:
        directions: List[ChangeDirection] = []
        gold_change: Optional[Dict[str, Any]] = None

        if old_item.gold_total != new_item.gold_total:
            gold_diff = new_item.gold_total - old_item.gold_total
            g_dir = ChangeDirection.BUFF if gold_diff < 0 else ChangeDirection.NERF
            directions.append(g_dir)
            gold_change = {
                "old_gold": old_item.gold_total,
                "new_gold": new_item.gold_total,
                "delta": gold_diff,
                "direction": g_dir.value,
            }

        old_stats = {k: v for k, v in (old_item.stats or {}).items() if not k.startswith("_")}
        new_stats = {k: v for k, v in (new_item.stats or {}).items() if not k.startswith("_")}
        stat_changes: List[Dict[str, Any]] = []

        for key in sorted(set(old_stats.keys()) | set(new_stats.keys())):
            old_v = round(float(old_stats.get(key, 0.0)), 4)
            new_v = round(float(new_stats.get(key, 0.0)), 4)
            if abs(new_v - old_v) > FLOAT_EPSILON:
                s_dir = ChangeDirection.BUFF if new_v > old_v else ChangeDirection.NERF
                directions.append(s_dir)
                delta_pct = round(((new_v - old_v) / old_v) * 100.0, 2) if old_v != 0 else 100.0
                stat_changes.append(
                    {
                        "stat_name": key,
                        "old_value": old_v,
                        "new_value": new_v,
                        "delta_percent": delta_pct,
                        "direction": s_dir.value,
                    }
                )

        # 1. CDragon items.cdtb.bin.json engine passive values (e.g., PercentCurrentHPMelee 9 -> 8)
        old_pvals = (old_item.stats or {}).get("_passive_values") or {}
        new_pvals = (new_item.stats or {}).get("_passive_values") or {}
        passive_data_changes: List[Dict[str, Any]] = []
        for pkey in sorted(set(old_pvals.keys()) & set(new_pvals.keys())):
            if any(tok in pkey.lower() for tok in NOISE_FIELD_TOKENS):
                continue
            ov = round(float(old_pvals[pkey]), 4)
            nv = round(float(new_pvals[pkey]), 4)
            if abs(nv - ov) > FLOAT_EPSILON:
                p_dir = _infer_mechanic_direction(pkey, [ov], [nv])
                directions.append(p_dir)
                disp_old, disp_new = format_readable_value_series(pkey, [ov], [nv])
                passive_data_changes.append(
                    {
                        "field_name": pkey,
                        "field_label": format_field_label(pkey),
                        "old_value": ov,
                        "new_value": nv,
                        "display_old": disp_old,
                        "display_new": disp_new,
                        "direction": p_dir.value,
                    }
                )

        # 2. Fallback: numeric diff extracted from item passive tooltip text
        passive_change = (
            None
            if passive_data_changes
            else _diff_text_numbers(old_item.passive_text or "", new_item.passive_text or "")
        )
        if passive_change:
            directions.append(ChangeDirection(passive_change["direction"]))

        if not gold_change and not stat_changes and not passive_data_changes and not passive_change:
            return None

        overall_dir = _resolve_overall_direction(directions)
        summary_parts: List[str] = []
        if gold_change:
            sign = "+" if gold_change["delta"] > 0 else ""
            summary_parts.append(f"Altın {sign}{gold_change['delta']}g")
        if stat_changes:
            summary_parts.append(f"{len(stat_changes)} stat değişikliği")
        if passive_data_changes:
            pairs = ", ".join(
                f"{p.get('field_label') or p['field_name']}: {p.get('display_old', p['old_value'])} → {p.get('display_new', p['new_value'])}"
                for p in passive_data_changes[:3]
            )
            summary_parts.append(f"Pasif ({pairs})")
        elif passive_change:
            pairs = ", ".join(
                f"{p['old']}->{p['new']}" for p in passive_change["changed_numbers"][:3]
            )
            summary_parts.append(f"Pasif ({pairs})")

        payload = {
            "item_id": new_item.item_id,
            "name": new_item.name,
            "gold_change": gold_change,
            "stat_changes": stat_changes,
            "passive_data_changes": passive_data_changes,
            "passive_change": passive_change,
            "direction": overall_dir.value,
            "summary": ", ".join(summary_parts),
        }
        return payload, overall_dir

    @staticmethod
    def diff_runes(
        old_rune: Rune, new_rune: Rune
    ) -> Optional[Tuple[Dict[str, Any], ChangeDirection]]:
        """Detects rune engine coefficient (effect_values) and tooltip differences across two patches."""
        old_eff = old_rune.effect_values or {}
        new_eff = new_rune.effect_values or {}
        eff_changes: List[Dict[str, Any]] = []
        directions: List[ChangeDirection] = []

        for key in sorted(set(old_eff.keys()) & set(new_eff.keys())):
            if any(tok in key.lower() for tok in NOISE_FIELD_TOKENS):
                continue
            ov = round(float(old_eff[key]), 4)
            nv = round(float(new_eff[key]), 4)
            if abs(nv - ov) > FLOAT_EPSILON:
                r_dir = _infer_mechanic_direction(key, [ov], [nv])
                directions.append(r_dir)
                eff_changes.append(
                    {
                        "field_name": key,
                        "old_value": ov,
                        "new_value": nv,
                        "direction": r_dir.value,
                    }
                )

        if eff_changes:
            overall_dir = _resolve_overall_direction(directions)
            pairs = ", ".join(
                f"{format_field_label(c['field_name'])}: {c['old_value']} → {c['new_value']}"
                for c in eff_changes[:4]
            )
            payload = {
                "rune_id": new_rune.rune_id,
                "key": new_rune.key,
                "name": new_rune.name,
                "tree_name": new_rune.tree_name,
                "is_keystone": new_rune.is_keystone,
                "effect_changes": eff_changes,
                "direction": overall_dir.value,
                "summary": f"Rün değişikliği ({pairs})",
            }
            return payload, overall_dir

        old_desc = f"{old_rune.short_desc or ''} | {old_rune.long_desc or ''}"
        new_desc = f"{new_rune.short_desc or ''} | {new_rune.long_desc or ''}"
        change = _diff_text_numbers(old_desc, new_desc)
        if not change:
            return None

        overall_dir = ChangeDirection(change["direction"])
        pairs = ", ".join(f"{p['old']}->{p['new']}" for p in change["changed_numbers"][:4])
        payload = {
            "rune_id": new_rune.rune_id,
            "key": new_rune.key,
            "name": new_rune.name,
            "tree_name": new_rune.tree_name,
            "is_keystone": new_rune.is_keystone,
            "changed_numbers": change["changed_numbers"],
            "direction": overall_dir.value,
            "summary": f"Rün değer değişikliği ({pairs})",
        }
        return payload, overall_dir

    @classmethod
    def compute_and_store_diffs(
        cls, db: Session, from_version: str, to_version: str
    ) -> Dict[str, Any]:
        """Computes all champion, item, and rune diffs between two patch versions and persists them."""
        old_champs = {
            c.champion_key: c
            for c in db.query(ChampionSnapshot).filter_by(patch_version=from_version).all()
        }
        new_champs = {
            c.champion_key: c
            for c in db.query(ChampionSnapshot).filter_by(patch_version=to_version).all()
        }

        old_items = {
            i.item_id: i
            for i in db.query(ItemSnapshot)
            .filter_by(patch_version=from_version, is_completed=True)
            .all()
        }
        new_items = {
            i.item_id: i
            for i in db.query(ItemSnapshot)
            .filter_by(patch_version=to_version, is_completed=True)
            .all()
        }

        old_runes = {
            r.rune_id: r
            for r in db.query(Rune).filter_by(patch_version=from_version).all()
        }
        new_runes = {
            r.rune_id: r
            for r in db.query(Rune).filter_by(patch_version=to_version).all()
        }

        # Idempotent recomputation
        db.query(AutoPatchDiff).filter_by(
            from_version=from_version, to_version=to_version
        ).delete()
        db.flush()

        champs_changed = 0
        for key in sorted(set(old_champs.keys()) & set(new_champs.keys())):
            res = cls.diff_champions(old_champs[key], new_champs[key])
            if not res:
                continue
            champ_diff, overall_dir = res
            db.add(
                AutoPatchDiff(
                    from_version=from_version,
                    to_version=to_version,
                    entity_type="champion",
                    entity_key=key,
                    entity_name=new_champs[key].name,
                    direction=overall_dir.value,
                    diff_payload=champ_diff.model_dump(),
                )
            )
            champs_changed += 1

        items_changed = 0
        for iid in sorted(set(old_items.keys()) & set(new_items.keys())):
            res = cls.diff_items(old_items[iid], new_items[iid])
            if not res:
                continue
            item_diff, overall_dir = res
            db.add(
                AutoPatchDiff(
                    from_version=from_version,
                    to_version=to_version,
                    entity_type="item",
                    entity_key=iid,
                    entity_name=new_items[iid].name,
                    direction=overall_dir.value,
                    diff_payload=item_diff,
                )
            )
            items_changed += 1

        runes_changed = 0
        for rid in sorted(set(old_runes.keys()) & set(new_runes.keys())):
            res = cls.diff_runes(old_runes[rid], new_runes[rid])
            if not res:
                continue
            rune_diff, overall_dir = res
            db.add(
                AutoPatchDiff(
                    from_version=from_version,
                    to_version=to_version,
                    entity_type="rune",
                    entity_key=str(rid),
                    entity_name=new_runes[rid].name,
                    direction=overall_dir.value,
                    diff_payload=rune_diff,
                )
            )
            runes_changed += 1

        db.commit()
        return {
            "from_version": from_version,
            "to_version": to_version,
            "from_display_version": to_display_version(from_version),
            "to_display_version": to_display_version(to_version),
            "champions_changed": champs_changed,
            "items_changed": items_changed,
            "runes_changed": runes_changed,
            "total": champs_changed + items_changed + runes_changed,
        }

    @classmethod
    def compute_latest_diffs(cls, db: Session) -> Dict[str, Any]:
        """Automatically computes diffs between the latest patch and its previous version."""
        latest = db.query(PatchVersion).filter_by(is_latest=True).first()
        if not latest or not latest.previous_version:
            raise RuntimeError(
                "Could not find 2 patch versions to compare. Please run DDragon sync first."
            )
        return cls.compute_and_store_diffs(db, latest.previous_version, latest.version)


if __name__ == "__main__":
    session = SessionLocal()
    try:
        summary = PatchDiffEngine.compute_latest_diffs(session)
        print(
            f"🔍 Auto Diff Complete ({summary['from_display_version']} -> {summary['to_display_version']}): "
            f"{summary['champions_changed']} champions, {summary['items_changed']} items, {summary['runes_changed']} runes changed."
        )
        rows = (
            session.query(AutoPatchDiff)
            .filter_by(from_version=summary["from_version"], to_version=summary["to_version"])
            .order_by(AutoPatchDiff.entity_type, AutoPatchDiff.entity_name)
            .all()
        )
        for r in rows:
            print(f"  [{r.entity_type.upper():8s}] {r.entity_name:28s} -> {r.direction:10s} | {r.diff_payload.get('summary')}")
    finally:
        session.close()

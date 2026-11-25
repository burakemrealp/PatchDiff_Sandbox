from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.versioning import build_item_icon_url, to_display_version
from app.engine.build_optimizer import BuildOptimizerEngine, filter_candidate_items
from app.engine.combat_simulator import CombatSimulator
from app.engine.game_state_pivot_engine import GameStatePivotEngine
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.services.aram_balance_service import AramBalanceService


def _snapshot_items_to_dicts(rows: List[ItemSnapshot]) -> List[Dict[str, Any]]:
    return [
        {
            "item_id": i.item_id,
            "name": i.name,
            "gold_total": i.gold_total,
            "stats": i.stats or {},
            "tags": i.tags or [],
            "unique_groups": i.unique_groups or [],
            "passive_text": i.passive_text or "",
            "icon_url": i.icon_url or build_item_icon_url(i.patch_version, i.item_id),
        }
        for i in rows
    ]


def _pct_diff(new_val: float, old_val: float) -> float:
    if old_val <= 0:
        return 0.0
    return round(((new_val - old_val) / old_val) * 100.0, 2)


class MetaShiftAnalyzer:
    """
    Compares pre-patch (N-1) and post-patch (N) champion/item data to:
    1. Generate optimized candidate (Item + Full Rune Page) variations for the new patch,
    2. Compute how much each variation gained or lost compared to the previous patch,
    3. Benchmark new variations against the previous patch's baseline meta build.
    """

    @staticmethod
    def _evaluate_single_build(
        champion_key: str,
        base_stats: Dict[str, float],
        abilities: Dict[str, Any],
        items: List[Dict[str, Any]],
        keystone_key: Optional[str],
        target_profile_key: str,
        role: str = "mid",
        game_map: str = "sr",
    ) -> Dict[str, Any]:
        sim = CombatSimulator.run_simulation(
            champion_key=champion_key,
            base_stats=base_stats,
            base_abilities=abilities,
            patch_diff=None,
            items=items,
            target_profile_key=target_profile_key,
            keystone_key=keystone_key,
            role=role,
            game_map=game_map,
        )
        lvl11 = sim["level_curves"][10]
        lvl18 = sim["level_curves"][17]
        return {
            "lvl11_burst": lvl11["new_burst"],
            "lvl18_burst": lvl18["new_burst"],
            "lvl11_dps": lvl11["new_dps"],
            "lvl18_dps": lvl18["new_dps"],
            "lvl11_ttk_sec": lvl11["new_ttk_sec"],
            "lvl18_ttk_sec": lvl18["new_ttk_sec"],
            "total_gold": sum(int(i.get("gold_total", 0)) for i in items if i.get("item_id") != "rune_page_bonuses"),
        }

    @classmethod
    def analyze_snapshots(
        cls,
        champion_key: str,
        champion_name: str,
        from_version: str,
        to_version: str,
        old_base_stats: Dict[str, float],
        old_abilities: Dict[str, Any],
        new_base_stats: Dict[str, float],
        new_abilities: Dict[str, Any],
        old_items: List[Dict[str, Any]],
        new_items: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        partype: Optional[str] = None,
        target_profile_key: str = "squishy",
        champion_patch_diff: Optional[Dict[str, Any]] = None,
        role: Optional[str] = None,
        game_map: str = "sr",
        game_state: str = "even",
        db_runes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Produces a full 6/7-item + full rune page meta shift report across two patch snapshots."""
        # 1. Generate 3 full builds + full rune pages (Burst, DPS, Balanced) for the new patch
        new_opt = BuildOptimizerEngine.optimize_builds(
            champion_key=champion_key,
            base_stats=new_base_stats,
            base_abilities=new_abilities,
            candidate_items=new_items,
            tags=tags,
            partype=partype,
            champion_patch_diff=champion_patch_diff,
            target_profile_key=target_profile_key,
            role=role,
            game_map=game_map,
            game_state=game_state,
            db_runes=db_runes,
        )
        game_context = new_opt["game_context"]
        resolved_role = game_context["role"]

        # 2. Compute reference baseline full build from the previous patch
        old_opt = BuildOptimizerEngine.optimize_builds(
            champion_key=champion_key,
            base_stats=old_base_stats,
            base_abilities=old_abilities,
            candidate_items=old_items,
            tags=tags,
            partype=partype,
            target_profile_key=target_profile_key,
            role=resolved_role,
            game_map=game_map,
            db_runes=db_runes,
            beam_width=3,
            top_pool_size=10,
        )

        old_items_by_id = {str(i["item_id"]): i for i in old_items}
        new_items_by_id = {str(i["item_id"]): i for i in new_items}

        profile = new_opt["profile"]
        primary_style = (
            "balanced" if profile["is_tank"] else ("dps" if profile["is_marksman"] else "burst")
        )
        old_baseline_var = next(
            (v for v in old_opt["variations"] if v["playstyle"] == primary_style),
            old_opt["variations"][0] if old_opt["variations"] else None,
        )

        old_baseline_info: Optional[Dict[str, Any]] = None
        old_baseline_on_new_eval: Optional[Dict[str, Any]] = None
        old_baseline_sig = None

        if old_baseline_var:
            old_base_ids = [str(i["item_id"]) for i in old_baseline_var["items"]]
            old_base_ks = old_baseline_var["keystone"]["key"]
            old_baseline_sig = (tuple(sorted(old_base_ids)), old_base_ks)

            mapped_new_items = [
                new_items_by_id.get(iid, old_items_by_id[iid])
                for iid in old_base_ids
                if iid in new_items_by_id or iid in old_items_by_id
            ]
            old_rune_bonuses = (old_baseline_var.get("rune_page") or {}).get("stat_bonuses") or {}
            if old_rune_bonuses:
                mapped_new_items = mapped_new_items + [
                    {"item_id": "rune_page_bonuses", "name": "Rune Bonuses", "gold_total": 0, "stats": old_rune_bonuses}
                ]

            old_baseline_on_new_eval = cls._evaluate_single_build(
                champion_key=champion_key,
                base_stats=new_base_stats,
                abilities=new_abilities,
                items=mapped_new_items,
                keystone_key=old_base_ks,
                target_profile_key=target_profile_key,
                role=resolved_role,
                game_map=game_map,
            )
            old_baseline_info = {
                "playstyle": old_baseline_var["playstyle"],
                "items": old_baseline_var["items"],
                "keystone": old_baseline_var["keystone"],
                "rune_page": old_baseline_var.get("rune_page"),
                "total_gold": old_baseline_on_new_eval["total_gold"],
                "metrics_on_new_patch": old_baseline_on_new_eval,
            }

        # 3. For each new variation: (A) Old -> New patch delta & (B) Comparison vs old meta baseline
        enriched_variations: List[Dict[str, Any]] = []
        for var in new_opt["variations"]:
            var_item_ids = [str(i["item_id"]) for i in var["items"]]
            var_ks = var["keystone"]["key"]
            var_sig = (tuple(sorted(var_item_ids)), var_ks)

            old_mapped = [
                old_items_by_id.get(iid, new_items_by_id[iid])
                for iid in var_item_ids
                if iid in old_items_by_id or iid in new_items_by_id
            ]
            var_rune_bonuses = (var.get("rune_page") or {}).get("stat_bonuses") or {}
            if var_rune_bonuses:
                old_mapped = old_mapped + [
                    {"item_id": "rune_page_bonuses", "name": "Rune Bonuses", "gold_total": 0, "stats": var_rune_bonuses}
                ]

            old_eval = cls._evaluate_single_build(
                champion_key=champion_key,
                base_stats=old_base_stats,
                abilities=old_abilities,
                items=old_mapped,
                keystone_key=var_ks,
                target_profile_key=target_profile_key,
                role=resolved_role,
                game_map=game_map,
            )

            m = var["metrics"]
            burst_patch_delta = _pct_diff(m["lvl18_burst"], old_eval["lvl18_burst"])
            dps_patch_delta = _pct_diff(m["lvl18_dps"], old_eval["lvl18_dps"])
            ttk_patch_diff = round(m["lvl18_ttk_sec"] - old_eval["lvl18_ttk_sec"], 2)
            gold_patch_delta = int(var["total_gold"] - old_eval["total_gold"])

            avg_power_shift = round((burst_patch_delta + dps_patch_delta) / 2.0, 2)
            if avg_power_shift > 0.5 or gold_patch_delta < 0:
                shift_status = "GAINED"
            elif avg_power_shift < -0.5 or gold_patch_delta > 0:
                shift_status = "LOST"
            else:
                shift_status = "STABLE"

            patch_shift = {
                "from_version": from_version,
                "to_version": to_version,
                "lvl18_burst_delta_pct": burst_patch_delta,
                "lvl18_dps_delta_pct": dps_patch_delta,
                "lvl18_ttk_diff_sec": ttk_patch_diff,
                "gold_delta": gold_patch_delta,
                "avg_power_shift_pct": avg_power_shift,
                "status": shift_status,
            }

            vs_old_meta: Optional[Dict[str, Any]] = None
            is_new_discovery = False
            if old_baseline_on_new_eval:
                vs_burst = _pct_diff(m["lvl18_burst"], old_baseline_on_new_eval["lvl18_burst"])
                vs_dps = _pct_diff(m["lvl18_dps"], old_baseline_on_new_eval["lvl18_dps"])
                vs_ttk = round(m["lvl18_ttk_sec"] - old_baseline_on_new_eval["lvl18_ttk_sec"], 2)
                vs_gold = int(var["total_gold"] - old_baseline_on_new_eval["total_gold"])
                is_new_discovery = (var_sig != old_baseline_sig) and (
                    vs_burst > 0.5 or vs_dps > 0.5 or vs_gold <= -200
                )
                vs_old_meta = {
                    "burst_diff_pct": vs_burst,
                    "dps_diff_pct": vs_dps,
                    "ttk_diff_sec": vs_ttk,
                    "gold_diff": vs_gold,
                    "is_new_meta_discovery": is_new_discovery,
                }

            enriched_variations.append(
                {
                    **var,
                    "patch_shift": patch_shift,
                    "vs_old_meta": vs_old_meta,
                }
            )

        # Assign initial ordinal rank labels before optional AI re-ranking
        for idx, v in enumerate(enriched_variations, start=1):
            v["rank"] = idx

        filtered_for_pivot = filter_candidate_items(new_items, profile)
        pivot_bundle = GameStatePivotEngine.audit_traps_and_build_pivot_tree(
            champion_key=champion_key,
            base_stats=new_base_stats,
            base_abilities=new_abilities,
            all_items=new_items,
            filtered_items=filtered_for_pivot,
            profile=profile,
            rules=game_context,
            target_profile_key=target_profile_key,
            primary_variation=enriched_variations[0] if enriched_variations else None,
            active_game_state=game_state,
        )

        return {
            "champion_key": champion_key,
            "champion_name": champion_name,
            "from_version": from_version,
            "from_display_version": to_display_version(from_version),
            "to_version": to_version,
            "to_display_version": to_display_version(to_version),
            "target_profile": target_profile_key,
            "game_map": game_map,
            "game_state": game_state,
            "game_context": game_context,
            "aram_modifiers": AramBalanceService.get_champion_aram_modifiers(champion_key),
            "winrate_trap_warnings": pivot_bundle["winrate_trap_warnings"],
            "pivot_tree": pivot_bundle,
            "profile": profile,
            "champion_changed_in_patch": champion_patch_diff is not None,
            "champion_patch_diff": champion_patch_diff,
            "old_meta_baseline": old_baseline_info,
            "variations": enriched_variations,
        }

    @classmethod
    def analyze_champion_from_db(
        cls,
        db: Session,
        champion_key: str,
        target_profile_key: str = "squishy",
        to_version: Optional[str] = None,
        role: Optional[str] = None,
        game_map: str = "sr",
        game_state: str = "even",
    ) -> Dict[str, Any]:
        """Loads the latest two patch snapshots and runes from PostgreSQL to run MetaShiftAnalyzer."""
        if to_version:
            pv = db.query(PatchVersion).filter_by(version=to_version).first()
        else:
            pv = db.query(PatchVersion).filter_by(is_latest=True).first()

        if not pv:
            raise ValueError("No synchronized patch version found in the database.")

        target_ver = pv.version
        prev_ver = pv.previous_version or pv.version

        new_snap = (
            db.query(ChampionSnapshot)
            .filter_by(patch_version=target_ver, champion_key=champion_key)
            .first()
        )
        if not new_snap:
            raise ValueError(f"Champion '{champion_key}' not found in patch {target_ver}.")

        old_snap = (
            db.query(ChampionSnapshot)
            .filter_by(patch_version=prev_ver, champion_key=champion_key)
            .first()
            or new_snap
        )

        new_items_rows = (
            db.query(ItemSnapshot)
            .filter_by(patch_version=target_ver, is_completed=True)
            .all()
        )
        old_items_rows = (
            db.query(ItemSnapshot)
            .filter_by(patch_version=prev_ver, is_completed=True)
            .all()
            or new_items_rows
        )
        runes_rows = db.query(Rune).filter_by(patch_version=target_ver).all()
        db_runes = [
            {
                "rune_id": r.rune_id,
                "key": r.key,
                "name": r.name,
                "tree_key": r.tree_key,
                "tree_name": r.tree_name,
                "slot_index": r.slot_index,
            }
            for r in runes_rows
        ]

        diff_row = (
            db.query(AutoPatchDiff)
            .filter_by(
                from_version=prev_ver,
                to_version=target_ver,
                entity_type="champion",
                entity_key=champion_key,
            )
            .first()
        )

        return cls.analyze_snapshots(
            champion_key=new_snap.champion_key,
            champion_name=new_snap.name,
            from_version=prev_ver,
            to_version=target_ver,
            old_base_stats=old_snap.base_stats,
            old_abilities=old_snap.abilities,
            new_base_stats=new_snap.base_stats,
            new_abilities=new_snap.abilities,
            old_items=_snapshot_items_to_dicts(old_items_rows),
            new_items=_snapshot_items_to_dicts(new_items_rows),
            tags=new_snap.tags,
            partype=new_snap.partype,
            target_profile_key=target_profile_key,
            champion_patch_diff=diff_row.diff_payload if diff_row else None,
            role=role,
            game_map=game_map,
            game_state=game_state,
            db_runes=db_runes or None,
        )

import logging
import threading
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.entities import AutoPatchDiff, PatchVersion
from app.services.aram_balance_service import AramBalanceService
from app.services.cdragon_enricher import CDragonEnricherService
from app.services.ddragon_sync import DDragonSyncService
from app.services.patch_diff_engine import PatchDiffEngine

logger = logging.getLogger(__name__)


class PatchSyncOrchestrator:
    """
    Coordinates the Riot Data Dragon + CommunityDragon + Auto Patch Diff pipeline
    from a single thread-safe entry point protected by a concurrency lock.
    """

    _sync_lock = threading.Lock()
    _is_running = False

    @classmethod
    def is_syncing(cls) -> bool:
        return cls._is_running

    @classmethod
    def sync_if_needed(cls, db: Session, force: bool = False) -> Dict[str, Any]:
        """
        Checks Riot Data Dragon for the latest live patch; if a new patch is available
        (or force=True), runs the full DDragon + CDragon + AutoPatchDiff pipeline.
        """
        if not cls._sync_lock.acquire(blocking=False):
            return {
                "status": "already_running",
                "message": "Patch synchronization is currently running in the background.",
            }

        cls._is_running = True
        try:
            versions = DDragonSyncService.fetch_latest_versions(count=2)
            if not versions:
                return {"status": "error", "message": "Failed to fetch Riot patch version list."}

            latest_remote = versions[0]
            prev_remote = versions[1] if len(versions) >= 2 else None

            current_latest = db.query(PatchVersion).filter_by(is_latest=True).first()
            has_diffs = (
                bool(
                    current_latest
                    and current_latest.previous_version
                    and db.query(AutoPatchDiff)
                    .filter_by(
                        from_version=current_latest.previous_version,
                        to_version=current_latest.version,
                    )
                    .first()
                )
                if current_latest
                else False
            )

            if (
                not force
                and current_latest
                and current_latest.version == latest_remote
                and current_latest.sync_status == "synced"
                and has_diffs
            ):
                return {
                    "status": "up_to_date",
                    "latest_version": current_latest.version,
                    "previous_version": current_latest.previous_version,
                    "champions_count": current_latest.champions_count,
                    "items_count": current_latest.items_count,
                    "runes_count": current_latest.runes_count,
                }

            logger.info("Synchronizing new LoL patch: %s (previous: %s)", latest_remote, prev_remote)
            synced_versions = DDragonSyncService.sync_latest_two_patches(db)

            for pv in synced_versions:
                CDragonEnricherService.enrich_patch_champions(
                    db=db,
                    patch_version=pv.version,
                    update_legacy_tables=pv.is_latest,
                )
                CDragonEnricherService.enrich_patch_items_and_runes(
                    db=db,
                    patch_version=pv.version,
                )

            diff_summary: Dict[str, Any] = {"champions_changed": 0, "items_changed": 0, "total": 0}
            if len(synced_versions) >= 2:
                diff_summary = PatchDiffEngine.compute_latest_diffs(db)

            try:
                AramBalanceService.refresh_aram_overrides_file()
            except Exception as exc:
                logger.warning("Non-fatal error while refreshing ARAM overrides: %s", exc)

            latest_row = db.query(PatchVersion).filter_by(is_latest=True).first()
            return {
                "status": "synced",
                "latest_version": latest_row.version if latest_row else latest_remote,
                "previous_version": latest_row.previous_version if latest_row else prev_remote,
                "champions_count": latest_row.champions_count if latest_row else 0,
                "items_count": latest_row.items_count if latest_row else 0,
                "runes_count": latest_row.runes_count if latest_row else 0,
                "champions_changed": diff_summary.get("champions_changed", 0),
                "items_changed": diff_summary.get("items_changed", 0),
            }
        finally:
            cls._is_running = False
            cls._sync_lock.release()

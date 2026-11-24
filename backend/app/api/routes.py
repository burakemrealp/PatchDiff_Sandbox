import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.core.versioning import build_item_icon_url, to_display_version
from app.models.entities import (
    AutoPatchDiff,
    Champion,
    ChampionSnapshot,
    Item,
    ItemSnapshot,
    PatchSimulationLog,
    PatchVersion,
    RecommendationFeedback,
)
from app.schemas.api_schemas import (
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackSummaryResponse,
    ParsePatchRequest,
    ParsePatchResponse,
    RecommendBuildsRequest,
    RecommendBuildsResponse,
    SimulateRequest,
    SimulateResponse,
    ZeroDayRadarResponse,
)
from app.services.ai_build_advisor import AIBuildAdvisorService
from app.services.llm_extractor import PatchExtractorService
from app.services.locale_service import (
    get_ddragon_localization,
    localize_diff_payload,
    localize_game_context,
    localize_recommend_report,
    localize_target_label,
    localize_zero_day_radar,
    normalize_locale,
)
from app.services.meta_shift_analyzer import MetaShiftAnalyzer
from app.services.patch_sync_orchestrator import PatchSyncOrchestrator
from app.services.sanity_checker import PatchSanityChecker
from app.services.zero_day_oracle import ZeroDayOracleService
from app.engine.combat_simulator import CombatSimulator

router = APIRouter()

CACHE_TTL_SECONDS = 3600  # 1-hour Redis cache TTL


def _build_cache_key(req: SimulateRequest) -> str:
    """Builds a deterministic SHA-256 Redis cache key from simulation request parameters."""
    riot_locale, _, _ = normalize_locale(req.lang)
    canonical = {
        "champion_key": req.champion_key,
        "from_version": req.from_version,
        "keystone_key": req.keystone_key,
        "role": req.role,
        "game_map": req.game_map,
        "lang": riot_locale,
        "item_ids": sorted(req.item_ids),
        "target_profile": req.target_profile,
        "patch_diff": req.patch_diff.model_dump() if req.patch_diff else None,
    }
    raw_str = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:24]
    return f"patchdiff:sim:v2:{req.champion_key}:{digest}"


def _load_known_champions(db: Session) -> dict[str, str] | None:
    """Loads all champion keys and names from PostgreSQL into a normalized lookup map."""
    try:
        rows = db.query(Champion.key, Champion.name).all()
        if not rows:
            return None
        lookup: dict[str, str] = {}
        for key, name in rows:
            lookup[key.lower()] = key
            if name:
                lookup[name.lower()] = key
        return lookup
    except Exception:
        return None


@router.post("/parse-patch", response_model=ParsePatchResponse, tags=["Patch Analysis"])
def parse_patch(request: ParsePatchRequest, db: Session = Depends(get_db)):
    """Converts raw patch note text into a validated JSON payload via LLM + Sanity Checker pipeline."""
    known_champions = _load_known_champions(db)
    raw_payload, engine_used, latency_ms = PatchExtractorService.extract_patch_payload(
        raw_text=request.raw_text,
        patch_version=request.patch_version,
        known_champions=known_champions,
    )
    clean_payload, warnings = PatchSanityChecker.validate_and_sanitize(raw_payload)

    return ParsePatchResponse(
        patch_version=clean_payload.patch_version,
        engine_used=engine_used,
        latency_ms=latency_ms,
        payload=clean_payload,
        sanity_warnings=warnings,
    )


@router.post("/simulate", response_model=SimulateResponse, tags=["Simulation"])
def simulate_combat(request: SimulateRequest, db: Session = Depends(get_db)):
    """
    Runs deterministic Level 1-18 (or Level 1-20 for Top) Burst, DPS, and TTK simulations
    for a champion, item build, and patch delta. Identical requests are served from Redis cache.
    """
    cache_key = _build_cache_key(request)

    # 1. Check Redis cache
    try:
        cached_raw = redis_client.get(cache_key)
        if cached_raw:
            return SimulateResponse(
                cached=True,
                cache_key=cache_key,
                result=json.loads(cached_raw),
            )
    except Exception:
        pass

    # 2. Load champion data from DB (use N-1 snapshot when from_version is provided)
    champ_key = request.champion_key
    champ_base_stats = None
    champ_abilities = None

    if request.from_version:
        snap = (
            db.query(ChampionSnapshot)
            .filter(
                ChampionSnapshot.patch_version == request.from_version,
                ChampionSnapshot.champion_key == request.champion_key,
            )
            .first()
        )
        if snap:
            champ_key = snap.champion_key
            champ_base_stats = snap.base_stats
            champ_abilities = snap.abilities

    if champ_base_stats is None:
        champ = db.query(Champion).filter(Champion.key == request.champion_key).first()
        if not champ:
            raise HTTPException(
                status_code=404,
                detail=f"Champion '{request.champion_key}' was not found in the database. See /api/v1/champions for supported champions.",
            )
        champ_key = champ.key
        champ_base_stats = champ.base_stats
        champ_abilities = champ.abilities

    # 3. Load selected items from DB
    build_items = []
    if request.item_ids:
        items_db = db.query(Item).filter(Item.item_id.in_(request.item_ids)).all()
        build_items = [{"item_id": i.item_id, "name": i.name, "stats": i.stats} for i in items_db]

    # 4. Run NumPy combat simulation engine
    sim_result = CombatSimulator.run_simulation(
        champion_key=champ_key,
        base_stats=champ_base_stats,
        base_abilities=champ_abilities,
        patch_diff=request.patch_diff,
        items=build_items,
        target_profile_key=request.target_profile,
        keystone_key=request.keystone_key,
        role=request.role,
        game_map=request.game_map,
    )
    sim_result["target_label"] = localize_target_label(request.target_profile, request.lang)
    sim_result["game_context"] = localize_game_context(sim_result.get("game_context"), request.lang)

    # 5. Store result in Redis cache
    try:
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(sim_result, ensure_ascii=False))
    except Exception:
        pass

    # 6. Optional: Persist simulation record to PostgreSQL patch_logs table
    if request.patch_diff:
        try:
            log_entry = PatchSimulationLog(
                champion_key=champ_key,
                raw_patch_text=request.raw_patch_text or "API Simulation Request",
                extracted_diff=request.patch_diff.model_dump(),
                simulation_result=sim_result["summary"],
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()

    return SimulateResponse(
        cached=False,
        cache_key=cache_key,
        result=sim_result,
    )


@router.get("/patches/latest", tags=["Auto Patch Sync"])
def get_latest_patch(db: Session = Depends(get_db)):
    """Returns the latest synchronized LoL patch metadata and diff counts."""
    latest = db.query(PatchVersion).filter_by(is_latest=True).first()
    if not latest:
        return {
            "synced": False,
            "is_syncing": PatchSyncOrchestrator.is_syncing(),
            "patch": None,
        }

    champ_diffs = 0
    item_diffs = 0
    rune_diffs = 0
    if latest.previous_version:
        champ_diffs = (
            db.query(AutoPatchDiff)
            .filter_by(
                from_version=latest.previous_version,
                to_version=latest.version,
                entity_type="champion",
            )
            .count()
        )
        item_diffs = (
            db.query(AutoPatchDiff)
            .filter_by(
                from_version=latest.previous_version,
                to_version=latest.version,
                entity_type="item",
            )
            .count()
        )
        rune_diffs = (
            db.query(AutoPatchDiff)
            .filter_by(
                from_version=latest.previous_version,
                to_version=latest.version,
                entity_type="rune",
            )
            .count()
        )

    return {
        "synced": True,
        "is_syncing": PatchSyncOrchestrator.is_syncing(),
        "patch": {
            "version": latest.version,
            "display_version": to_display_version(latest.version),
            "previous_version": latest.previous_version,
            "previous_display_version": to_display_version(latest.previous_version),
            "sync_status": latest.sync_status,
            "champions_count": latest.champions_count,
            "items_count": latest.items_count,
            "runes_count": latest.runes_count,
            "champions_changed": champ_diffs,
            "items_changed": item_diffs,
            "runes_changed": rune_diffs,
            "synced_at": latest.synced_at.isoformat() if latest.synced_at else None,
        },
    }


@router.post("/patches/sync", tags=["Auto Patch Sync"])
def sync_patches(
    force: bool = Query(default=False, description="When True, re-syncs even if the latest version already exists"),
    db: Session = Depends(get_db),
):
    """Triggers the Riot Data Dragon + CommunityDragon + Auto Patch Diff pipeline."""
    return PatchSyncOrchestrator.sync_if_needed(db, force=force)


@router.get("/patches/zero-day-radar", response_model=ZeroDayRadarResponse, tags=["Zero-Day Meta Oracle"])
def get_zero_day_radar(
    to_version: str | None = Query(default=None, description="Target patch version (defaults to latest synced patch)"),
    target_profile: str = Query(
        default="squishy",
        pattern="^(squishy|bruiser|tank)$",
        description="Target dummy defensive profile",
    ),
    game_map: str = Query(
        default="sr",
        pattern="^(sr|aram|swiftplay)$",
        description="Map or game mode (sr, aram, swiftplay)",
    ),
    limit: int = Query(default=8, ge=1, le=25, description="Maximum champions returned per radar bucket"),
    lang: str = Query(default="tr_TR", description="Official League of Legends locale code"),
    db: Session = Depends(get_db),
):
    """
    Runs a full-roster Day-0 mathematical patch scan to uncover Hidden Winners/Losers,
    Patch Mythbusters (placebo buffs, paper-tiger nerfs, trap buffs, mode-only edits),
    and 25-locale share-card summaries before Day-1 match statistics exist.
    """
    resolved_ver = to_version
    if not resolved_ver:
        latest = db.query(PatchVersion).filter_by(is_latest=True).first()
        resolved_ver = latest.version if latest else "latest"

    riot_locale, _, _ = normalize_locale(lang)
    cache_key = (
        f"patchdiff:radar:v1:{resolved_ver}:{target_profile}:{game_map}:{limit}:{riot_locale}"
    )

    try:
        cached_raw = redis_client.get(cache_key)
        if cached_raw:
            cached_obj = json.loads(cached_raw)
            return ZeroDayRadarResponse(
                cached=True,
                cache_key=cache_key,
                latency_ms=0.0,
                radar=cached_obj,
            )
    except Exception:
        pass

    try:
        radar = ZeroDayOracleService.analyze_patch_radar(
            db=db,
            to_version=to_version,
            target_profile_key=target_profile,
            game_map=game_map,
            limit_per_bucket=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    localized = localize_zero_day_radar(radar, lang=riot_locale, version=resolved_ver)
    latency_ms = float(localized.get("scan_duration_ms", 0.0))

    try:
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(localized, ensure_ascii=False))
    except Exception:
        pass

    return ZeroDayRadarResponse(
        cached=False,
        cache_key=cache_key,
        latency_ms=latency_ms,
        radar=localized,
    )


@router.get("/patches/{version}/diffs", tags=["Auto Patch Sync"])
def get_patch_diffs(
    version: str,
    lang: str = Query(default="tr_TR", description="Official League of Legends locale code (e.g., tr_TR, en_US, de_DE)"),
    db: Session = Depends(get_db),
):
    """Returns all automatically computed champion, item, and rune diffs for a patch in the requested locale."""
    pv = db.query(PatchVersion).filter_by(version=version).first()
    if not pv:
        raise HTTPException(status_code=404, detail=f"Patch version not found: {version}")

    riot_locale, _, _ = normalize_locale(lang)
    loc = get_ddragon_localization(version, riot_locale) or {}
    champ_loc = loc.get("champions") or {}
    item_loc = loc.get("items") or {}
    rune_loc = loc.get("runes") or {}

    rows = (
        db.query(AutoPatchDiff)
        .filter_by(to_version=version)
        .order_by(AutoPatchDiff.entity_name.asc())
        .all()
    )

    item_icon_map = {
        iid: url
        for iid, url in (
            db.query(ItemSnapshot.item_id, ItemSnapshot.icon_url)
            .filter(ItemSnapshot.patch_version == version)
            .all()
        )
        if url
    }

    champions = []
    items = []
    runes = []
    for row in rows:
        localized_diff = localize_diff_payload(row.entity_type, row.diff_payload, riot_locale, loc)
        if row.entity_type == "champion":
            ent_name = (champ_loc.get(row.entity_key) or {}).get("name") or row.entity_name
            champions.append(
                {
                    "entity_key": row.entity_key,
                    "entity_name": ent_name,
                    "direction": row.direction,
                    "diff": localized_diff,
                }
            )
        elif row.entity_type == "item":
            ent_name = item_loc.get(row.entity_key) or row.entity_name
            items.append(
                {
                    "entity_key": row.entity_key,
                    "entity_name": ent_name,
                    "direction": row.direction,
                    "icon_url": item_icon_map.get(row.entity_key)
                    or build_item_icon_url(version, row.entity_key),
                    "diff": localized_diff,
                }
            )
        elif row.entity_type == "rune":
            ent_name = rune_loc.get(row.entity_key) or row.entity_name
            runes.append(
                {
                    "entity_key": row.entity_key,
                    "entity_name": ent_name,
                    "direction": row.direction,
                    "diff": localized_diff,
                }
            )

    return {
        "from_version": pv.previous_version,
        "from_display_version": to_display_version(pv.previous_version),
        "to_version": pv.version,
        "to_display_version": to_display_version(pv.version),
        "champions_count": len(champions),
        "items_count": len(items),
        "runes_count": len(runes),
        "champions": champions,
        "items": items,
        "runes": runes,
    }


@router.post("/recommend-builds", response_model=RecommendBuildsResponse, tags=["AI Build Lab"])
def recommend_builds(request: RecommendBuildsRequest, db: Session = Depends(get_db)):
    """
    Compares the latest two patch snapshots for a champion, discovers top 3 full item + full rune page
    variations using constrained Beam Search, and evaluates them through the AI/LLM sanity advisor.
    Results are cached in Redis.
    """
    resolved_ver = request.to_version
    if not resolved_ver:
        latest = db.query(PatchVersion).filter_by(is_latest=True).first()
        resolved_ver = latest.version if latest else "latest"

    riot_locale, _, _ = normalize_locale(request.lang)
    cache_key = (
        f"patchdiff:rec:v7:{resolved_ver}:{request.champion_key}:"
        f"{request.target_profile}:{request.role or 'auto'}:{request.game_map}:{int(request.use_ai)}:{riot_locale}"
    )

    try:
        cached_raw = redis_client.get(cache_key)
        if cached_raw:
            cached_obj = json.loads(cached_raw)
            return RecommendBuildsResponse(
                cached=True,
                cache_key=cache_key,
                engine_used=cached_obj.get("engine_used", "cached"),
                latency_ms=0.0,
                report=cached_obj["report"],
            )
    except Exception:
        pass

    try:
        meta_report = MetaShiftAnalyzer.analyze_champion_from_db(
            db=db,
            champion_key=request.champion_key,
            target_profile_key=request.target_profile,
            to_version=request.to_version,
            role=request.role,
            game_map=request.game_map,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    meta_report = localize_recommend_report(meta_report, lang=riot_locale, version=resolved_ver)

    if request.use_ai:
        final_report, engine_used, latency_ms = AIBuildAdvisorService.evaluate_report(
            meta_report, lang=riot_locale
        )
    else:
        final_report = meta_report
        engine_used = "math-optimizer-only"
        latency_ms = 0.0

    try:
        redis_client.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            json.dumps({"engine_used": engine_used, "report": final_report}, ensure_ascii=False),
        )
    except Exception:
        pass

    return RecommendBuildsResponse(
        cached=False,
        cache_key=cache_key,
        engine_used=engine_used,
        latency_ms=latency_ms,
        report=final_report,
    )


@router.post("/feedback", response_model=FeedbackCreateResponse, tags=["Feedback"])
def submit_feedback(request: FeedbackCreateRequest, db: Session = Depends(get_db)):
    """Saves a 1-5 star user rating and optional comment for a build/rune recommendation."""
    entry = RecommendationFeedback(
        patch_version=request.patch_version.strip(),
        champion_key=request.champion_key.strip(),
        role=request.role.strip(),
        game_map=request.game_map.strip(),
        target_profile=request.target_profile.strip(),
        playstyle=request.playstyle.strip(),
        items_json=request.items,
        rune_page_json=request.rune_page,
        rating=request.rating,
        is_helpful=request.is_helpful,
        comment=(request.comment or "").strip() or None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return FeedbackCreateResponse(
        id=entry.id,
        status="saved",
        rating=entry.rating,
        is_helpful=entry.is_helpful,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )


@router.get("/feedback/summary", response_model=FeedbackSummaryResponse, tags=["Feedback"])
def get_feedback_summary(
    champion_key: str | None = Query(default=None, description="Optional champion key filter"),
    patch_version: str | None = Query(default=None, description="Optional patch version filter"),
    db: Session = Depends(get_db),
):
    """Returns aggregated summary statistics for submitted user recommendation ratings."""
    q = db.query(RecommendationFeedback)
    if champion_key:
        q = q.filter(RecommendationFeedback.champion_key == champion_key.strip())
    if patch_version:
        q = q.filter(RecommendationFeedback.patch_version == patch_version.strip())

    rows = q.order_by(RecommendationFeedback.created_at.desc()).all()
    if not rows:
        return FeedbackSummaryResponse(
            total_count=0,
            avg_rating=0.0,
            helpful_rate_pct=0.0,
            by_playstyle={},
            recent_comments=[],
        )

    total = len(rows)
    avg_rating = round(sum(r.rating for r in rows) / total, 2)
    helpful_pct = round((sum(1 for r in rows if r.is_helpful) / total) * 100.0, 1)

    by_style: dict[str, dict[str, float | int]] = {}
    for r in rows:
        bucket = by_style.setdefault(r.playstyle, {"count": 0, "sum_rating": 0, "helpful": 0})
        bucket["count"] += 1
        bucket["sum_rating"] += r.rating
        bucket["helpful"] += 1 if r.is_helpful else 0

    formatted_styles = {
        style: {
            "count": data["count"],
            "avg_rating": round(data["sum_rating"] / data["count"], 2),
            "helpful_rate_pct": round((data["helpful"] / data["count"]) * 100.0, 1),
        }
        for style, data in by_style.items()
    }

    recent_comments = [
        {
            "id": r.id,
            "champion_key": r.champion_key,
            "playstyle": r.playstyle,
            "rating": r.rating,
            "is_helpful": r.is_helpful,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
        if r.comment
    ][:10]

    return FeedbackSummaryResponse(
        total_count=total,
        avg_rating=avg_rating,
        helpful_rate_pct=helpful_pct,
        by_playstyle=formatted_styles,
        recent_comments=recent_comments,
    )

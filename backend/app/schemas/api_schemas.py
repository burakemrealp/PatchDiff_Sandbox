from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from app.schemas.patch_contracts import PatchPayload, ChampionPatchDiff


class ParsePatchRequest(BaseModel):
    raw_text: str = Field(..., min_length=5, description="Raw patch note text (HTML, Markdown, or plain text)")
    patch_version: str = Field(default="14.23", description="Target patch version")


class ParsePatchResponse(BaseModel):
    patch_version: str
    engine_used: str
    latency_ms: float
    payload: PatchPayload
    sanity_warnings: List[str] = Field(default_factory=list)


class SimulateRequest(BaseModel):
    champion_key: str = Field(..., description="Champion key (e.g., Ahri, Zed, Jinx, Ornn)")
    item_ids: List[str] = Field(default_factory=list, description="Selected item IDs (e.g., ['3089', '4645'])")
    target_profile: Literal["squishy", "bruiser", "tank"] = Field(
        default="squishy", description="Target dummy defensive profile"
    )
    patch_diff: Optional[ChampionPatchDiff] = Field(
        default=None, description="Champion patch delta payload to simulate"
    )
    from_version: Optional[str] = Field(
        default=None,
        description="Optional baseline patch (N-1) snapshot version for automated diffs",
    )
    keystone_key: Optional[str] = Field(
        default=None,
        description="Optional keystone rune key to include in simulation (e.g., Electrocute, LethalTempo)",
    )
    role: Literal["top", "jungle", "mid", "adc", "support"] = Field(
        default="mid", description="Lane role for Season 16 Role Quest rules"
    )
    game_map: Literal["sr", "aram", "swiftplay"] = Field(
        default="sr", description="Map or game mode (sr, aram, swiftplay)"
    )
    lang: str = Field(default="tr_TR", description="Official League of Legends locale code (e.g., tr_TR, en_US, de_DE, ja_JP)")
    raw_patch_text: Optional[str] = Field(
        default=None, description="Optional raw patch text for database audit logging"
    )


class SimulateResponse(BaseModel):
    cached: bool = Field(default=False, description="Whether the result was served from Redis cache")
    cache_key: str
    result: Dict[str, Any]


class RecommendBuildsRequest(BaseModel):
    champion_key: str = Field(..., description="Champion key (e.g., Velkoz, Ahri, MasterYi)")
    target_profile: Literal["squishy", "bruiser", "tank"] = Field(
        default="squishy", description="Target dummy defensive profile"
    )
    role: Optional[Literal["top", "jungle", "mid", "adc", "support"]] = Field(
        default=None, description="Lane role (auto-inferred from champion tags if omitted)"
    )
    game_map: Literal["sr", "aram", "swiftplay"] = Field(
        default="sr", description="Map or game mode (sr, aram, swiftplay)"
    )
    to_version: Optional[str] = Field(
        default=None, description="Optional target patch version (defaults to latest synced patch)"
    )
    use_ai: bool = Field(
        default=True, description="When True, runs AI/LLM practicality review and rationale analysis"
    )
    lang: str = Field(default="tr_TR", description="Official League of Legends locale code (e.g., tr_TR, en_US, de_DE, ja_JP)")


class RecommendBuildsResponse(BaseModel):
    cached: bool = Field(default=False, description="Whether the result was served from Redis cache")
    cache_key: str
    engine_used: str
    latency_ms: float
    report: Dict[str, Any]


class FeedbackCreateRequest(BaseModel):
    patch_version: str = Field(..., min_length=1, max_length=30)
    champion_key: str = Field(..., min_length=1, max_length=50)
    role: str = Field(default="mid", max_length=20)
    game_map: str = Field(default="sr", max_length=20)
    target_profile: str = Field(default="squishy", max_length=20)
    playstyle: str = Field(..., min_length=1, max_length=20)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    rune_page: Optional[Dict[str, Any]] = None
    rating: int = Field(..., ge=1, le=5, description="User rating between 1 and 5")
    is_helpful: bool = Field(default=True, description="Whether the recommendation was helpful")
    comment: Optional[str] = Field(default=None, max_length=500, description="Optional short feedback comment")


class FeedbackCreateResponse(BaseModel):
    id: int
    status: str = "saved"
    rating: int
    is_helpful: bool
    created_at: str


class FeedbackSummaryResponse(BaseModel):
    total_count: int
    avg_rating: float
    helpful_rate_pct: float
    by_playstyle: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    recent_comments: List[Dict[str, Any]] = Field(default_factory=list)


class ZeroDayRadarResponse(BaseModel):
    cached: bool = Field(default=False, description="Whether the radar report was served from Redis cache")
    cache_key: str
    latency_ms: float
    radar: Dict[str, Any]

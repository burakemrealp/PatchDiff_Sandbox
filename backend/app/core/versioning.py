import re
from typing import Optional

_VER_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


def to_display_version(internal_version: Optional[str]) -> Optional[str]:
    """
    Converts internal Riot API patch version into official player-facing display version.
    Starting with 2025 (Season 15 -> 25.x) and 2026+ (Season 16 -> 26.x), Riot displays
    year-based patch numbers (major + 10) while preserving the season major in DDragon APIs.
    Example: '16.23.1' -> '26.23', '15.4.1' -> '25.4', '14.23.1' -> '14.23'
    """
    if not internal_version:
        return None
    m = _VER_RE.match(internal_version.strip())
    if not m:
        return internal_version
    major = int(m.group(1))
    minor = int(m.group(2))
    if major >= 15:
        return f"{major + 10}.{minor}"
    return f"{major}.{minor}"


DDRAGON_CDN_BASE = "https://ddragon.leagueoflegends.com/cdn"


def build_item_icon_url(
    version: Optional[str],
    item_id: str,
    image_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Builds a verified official Riot Data Dragon CDN icon URL for an item.
    Example: ('16.23.1', '3089', '3089.png') -> 'https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/3089.png'
    """
    clean_id = str(item_id or "").strip()
    if not clean_id or not version:
        return None
    filename = (image_filename or f"{clean_id}.png").strip()
    return f"{DDRAGON_CDN_BASE}/{version.strip()}/img/item/{filename}"

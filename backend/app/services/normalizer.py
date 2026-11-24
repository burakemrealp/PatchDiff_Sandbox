import re
from typing import Dict, List, Optional


# Default champion map used when database access is unavailable (offline/unit tests)
KNOWN_CHAMPIONS: Dict[str, str] = {
    "ahri": "Ahri",
    "zed": "Zed",
    "jinx": "Jinx",
    "ornn": "Ornn",
}


class PatchNormalizer:
    """Cleans raw HTML/Markdown patch notes and splits them into per-champion text blocks."""

    @staticmethod
    def clean_raw_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        text = raw_text

        # 1. Strip HTML tags (<p>, <div>, <strong>, etc.)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(p|div|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)

        # 2. Normalize diverse arrow glyphs (⇒, ➔, →, ==> etc.) into standard ' -> '
        text = re.sub(r"\s*(?:⇒|➔|→|⟶|==>|--+>|->)\s*", " -> ", text)

        # 3. Convert localized decimal commas (e.g., 3,4 or 0,75) into decimal dots (3.4, 0.75)
        text = re.sub(r"(\d+),(\d+)", r"\1.\2", text)

        # 4. Collapse excessive whitespace and empty lines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        cleaned_lines = [line for line in lines if line]

        return "\n".join(cleaned_lines)

    @classmethod
    def split_by_champion(
        cls, raw_text: str, known_champions: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Scans cleaned patch text and groups lines under canonical champion keys
        such as {'Ahri': '...', 'Zed': '...'}.
        `known_champions` can be populated dynamically from PostgreSQL.
        """
        champion_lookup = (
            {k.lower(): v for k, v in known_champions.items()}
            if known_champions
            else KNOWN_CHAMPIONS
        )
        # Match longer names first (e.g., "Lee Sin", "Aurelion Sol") before shorter prefixes
        ordered_champs = sorted(champion_lookup.items(), key=lambda kv: len(kv[0]), reverse=True)

        cleaned = cls.clean_raw_text(raw_text)
        lines = cleaned.splitlines()

        chunks: Dict[str, List[str]] = {}
        current_champ: str | None = None

        for line in lines:
            # Check whether the line is a champion heading
            clean_header = re.sub(r"^[#*\-\s]+|[#*\-:\s]+$", "", line).lower()

            matched_champ = None
            for key_lower, canonical_name in ordered_champs:
                # Match formats like "Ahri", "### Ahri", "Ahri - Nine-Tailed Fox"
                if clean_header == key_lower or clean_header.startswith(f"{key_lower} "):
                    matched_champ = canonical_name
                    break

            if matched_champ:
                current_champ = matched_champ
                if current_champ not in chunks:
                    chunks[current_champ] = []
                continue

            # Append lines belonging to the active champion block
            if current_champ:
                chunks[current_champ].append(line)

        # Fallback: if a user pasted single-champion changes without a heading line,
        # detect the first matching champion name in the text body.
        if not chunks and cleaned:
            lower_text = cleaned.lower()
            for key_lower, canonical_name in ordered_champs:
                if re.search(rf"\b{re.escape(key_lower)}\b", lower_text):
                    chunks[canonical_name] = lines
                    break

        return {champ: "\n".join(champ_lines) for champ, champ_lines in chunks.items() if champ_lines}

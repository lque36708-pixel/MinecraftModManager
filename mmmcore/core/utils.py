from difflib import SequenceMatcher

from .exceptions import ValidationError
from .api import KNOWN_LOADERS, api_get

def normalize_slug(name):
    return name.lower().replace(" ", "-")

def fuzzy_match(name, choices, threshold=0.6):
    best, best_score = None, 0
    for c in choices:
        score = SequenceMatcher(None, name.lower(), c.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best = c
    return best

def fmt_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def validate_loader(loader):
    if loader not in KNOWN_LOADERS:
        raise ValidationError(
            f"Invalid loader '{loader}'. "
            f"Supported: {', '.join(KNOWN_LOADERS)}"
        )

def validate_mc_version(mc):
    versions = api_get("/tag/game_version")
    if versions:
        valid_versions = [v["version"] for v in versions]
        if mc not in valid_versions:
            matches = [v for v in valid_versions if v.startswith(mc[:4])][:5]
            hint = f" Did you mean: {', '.join(matches)}?" if matches else ""
            raise ValidationError(
                f"Minecraft version '{mc}' is invalid or not supported by Modrinth.{hint}"
            )

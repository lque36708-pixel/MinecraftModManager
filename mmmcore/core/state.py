import json
import time
from pathlib import Path
from datetime import datetime, timezone

from .exceptions import ProfileNotFoundError
from .api import VERSION

# ── Profile ────────────────────────────────────────────────────────────────────

def profile_path(base=None):
    return (base or Path.cwd()) / "profile.json"

def load_profile(base=None):
    p = profile_path(base)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if data.get("mc_version") and data.get("loader"):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return None

def save_profile(mc_version, loader, base=None):
    data = {
        "mc_version": mc_version,
        "loader":     loader,
        "updated_at": _now_iso(),
    }
    profile_path(base).write_text(json.dumps(data, indent=2))
    return data

def require_profile(base=None):
    p = load_profile(base)
    if not p:
        raise ProfileNotFoundError(str(profile_path(base)))
    return p

# ── Metadata ───────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def metadata_path(base=None):
    return (base or Path.cwd()) / "metadata.json"

def _empty_metadata():
    return {
        "mmm_version": VERSION,
        "mc_version": "",
        "loader":     "",
        "updated_at": _now_iso(),
        "mods":       {},
    }

def _empty_mod_entry():
    return {
        "slug":        "",
        "title":       "",
        "description": "",
        "version_id":  "",
        "version":     "",
        "version_type": "",
        "file":        "",
        "sha512":      "",
        "size_bytes":  0,
        "project_id":  "",
        "source_url":  "",
        "license":     "",
        "categories":  [],
        "downloads":   0,
        "followers":   0,
        "icon_url":    "",
        "gallery":     [],
        "required_by": [],
        "requested":   False,
        "installed_at": _now_iso(),
    }

def load_metadata(base=None):
    p = metadata_path(base)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return _empty_metadata()

def save_metadata(data, base=None):
    data["updated_at"] = _now_iso()
    metadata_path(base).write_text(json.dumps(data, indent=2))

def upsert_mod(data, slug, **fields):
    if "mods" not in data:
        data["mods"] = {}
    entry = data["mods"].get(slug, _empty_mod_entry())
    entry["slug"] = slug
    for key, value in fields.items():
        if key == "required_by":
            existing = entry.get(key, [])
            for item in (value or []):
                if item and item not in existing:
                    existing.append(item)
            entry[key] = existing
        elif value or value == 0:
            entry[key] = value
    data["mods"][slug] = entry
    return data

def remove_mod_from_metadata(data, slug):
    if slug not in data.get("mods", {}):
        return data
    del data["mods"][slug]
    for mod in data["mods"].values():
        lst = mod.get("required_by", [])
        if slug in lst:
            lst.remove(slug)
    return data

def get_dependents_recursive(slug, mods, seen=None):
    if seen is None:
        seen = {slug}
    result = []
    for dep in mods.get(slug, {}).get("required_by", []):
        if dep not in seen:
            seen.add(dep)
            result.append(dep)
            result.extend(get_dependents_recursive(dep, mods, seen))
    return result

def is_orphaned(slug, mods, seen=None):
    entry = mods.get(slug, {})
    if entry.get("requested"):
        return False
    if seen is None:
        seen = set()
    seen.add(slug)
    for parent in entry.get("required_by", []):
        if parent in seen:
            continue
        if not is_orphaned(parent, mods, seen):
            return False
    return True

# ── Search cache ───────────────────────────────────────────────────────────────

def cache_path(base=None):
    return (base or Path.cwd()) / ".mmm_cache.json"

def save_cache(results, query="", base=None):
    cache_path(base).write_text(json.dumps({
        "query":   query,
        "results": results,
        "time":    time.time(),
    }, indent=2))

def load_cache(base=None):
    p = cache_path(base)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
        return data.get("results", [])
    except Exception:
        return None

def load_cache_meta(base=None):
    p = cache_path(base)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return {"query": "?", "results": data, "time": 0}
        return data
    except Exception:
        return None

import json
import urllib.request
import urllib.parse
import urllib.error
import hashlib
import time

from .exceptions import APIError, APIConnectionError, DownloadError, ChecksumError

VERSION = "0.1.0"
API_BASE = "https://api.modrinth.com/v2"
USER_AGENT = f"mmm-cli/{VERSION} (minecraft-mod-manager)"

KNOWN_LOADERS = ("fabric", "forge", "quilt", "neoforge")

LOADER_COLORS = {
    "fabric":   "",
    "forge":    "",
    "quilt":    "",
    "neoforge": "",
}

API_HINTS = {
    "fabric": ("fabric-api", "Fabric API"),
    "quilt":  ("qsl", "Quilt Standard Libraries (QSL)"),
}

def api_get(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise APIError(e.code, e.reason) from e
    except urllib.error.URLError as e:
        raise APIConnectionError(str(e.reason)) from e
    except Exception as e:
        raise APIConnectionError(str(e)) from e

def download_file(url, dest_path, sha512_expected=None, progress_callback=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            t0         = time.time()
            hasher     = hashlib.sha512()

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        pct    = downloaded * 100 // total
                        speed  = downloaded / max(time.time() - t0, 0.1)
                        progress_callback(pct, downloaded, total, speed, time.time() - t0)

            if sha512_expected:
                actual = hasher.hexdigest()
                if actual != sha512_expected:
                    dest_path.unlink(missing_ok=True)
                    raise ChecksumError()

            return True

    except ChecksumError:
        raise
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise DownloadError(str(e)) from e

def search_mods(query, mc_version=None, loader=None, no_filter=False, limit=10):
    facets = []
    if not no_filter:
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        if loader:
            facets.append([f"categories:{loader}"])
    facets.append(["project_type:mod"])
    data = api_get("/search", {"query": query, "facets": json.dumps(facets), "limit": limit})
    if data is None:
        return []
    return data.get("hits", [])

def get_project(slug_or_id):
    return api_get(f"/project/{slug_or_id}")

def get_best_version(slug, profile):
    data = api_get(f"/project/{slug}/version", {
        "loaders":       json.dumps([profile["loader"]]),
        "game_versions": json.dumps([profile["mc_version"]]),
    })
    if not data:
        return None
    for vtype in ("release", "beta", "alpha"):
        for v in data:
            if v.get("version_type") == vtype:
                return v
    return data[0] if data else None

def get_primary_file(version):
    files = version.get("files", [])
    for f in files:
        if f.get("primary"):
            return f
    return files[0] if files else None

def get_slug_from_name(name, profile, limit=5):
    hits = search_mods(name, mc_version=profile["mc_version"], loader=profile["loader"], limit=limit)
    for hit in hits:
        slug = hit.get("slug", "")
        if slug.lower() == name.lower().replace(" ", "-") or hit.get("title", "").lower() == name.lower():
            return slug, hit
    if hits:
        return hits[0]["slug"], hits[0]
    return None, None

def get_required_dependencies(slug, profile):
    version = get_best_version(slug, profile)
    if not version:
        return []

    result = []
    for dep in version.get("dependencies", []):
        if dep.get("dependency_type") != "required":
            continue
        project_id = dep.get("project_id")
        version_id = dep.get("version_id")
        if project_id:
            proj = get_project(project_id)
            if proj:
                result.append((proj["slug"], version_id))
    return result

#!/usr/bin/env python3
"""
3m — Minecraft Mod Manager
Download mods from Modrinth with automatic dependency resolution.
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import argparse
import time
import hashlib
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════════════

VERSION    = "3.0.0"
API_BASE   = "https://api.modrinth.com/v2"
USER_AGENT = f"3m-cli/{VERSION} (minecraft-mod-manager)"

KNOWN_LOADERS = ("fabric", "forge", "quilt", "neoforge")
# ══════════════════════════════════════════════════════════════════════════════
#  ANSI colors
# ══════════════════════════════════════════════════════════════════════════════

ESC = "\033["
def _c(*codes): return ESC + ";".join(str(c) for c in codes) + "m"

RESET   = _c(0)
BOLD    = _c(1)
DIM     = _c(2)
ITALIC  = _c(3)

RED     = _c(31); GREEN   = _c(32); YELLOW  = _c(33)
BLUE    = _c(34); CYAN    = _c(36); WHITE   = _c(37)

BRED    = _c(1,31); BGREEN  = _c(1,32); BYELLOW = _c(1,33)
BBLUE   = _c(1,34); BCYAN   = _c(1,36); BWHITE  = _c(1,37)

def fg(n): return f"\033[38;5;{n}m"
def bg(n): return f"\033[48;5;{n}m"

MINT    = fg(114)
GOLD    = fg(220)
PURPLE  = fg(141)
ORANGE  = fg(208)
PINK    = fg(213)
SLATE   = fg(245)
TEAL    = fg(43)
LIME    = fg(154)
ROSE    = fg(196)
SKY     = fg(117)
INDIGO  = fg(99)

def rst(s):    return f"{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"
def italic(s): return f"{ITALIC}{s}{RESET}"
def color(c, s): return f"{c}{s}{RESET}"

# ══════════════════════════════════════════════════════════════════════════════
#  Print helpers
# ══════════════════════════════════════════════════════════════════════════════

def err(msg):  print(f"{ROSE}  ✗  {RESET}{RED}{msg}{RESET}", file=sys.stderr)
def ok(msg):   print(f"{LIME}  ✔  {RESET}{GREEN}{msg}{RESET}")
def info(msg): print(f"{SKY}  ›  {RESET}{CYAN}{msg}{RESET}")
def warn(msg): print(f"{GOLD}  ⚠  {RESET}{YELLOW}{msg}{RESET}")
def step(msg): print(f"{MINT}  ↓  {RESET}{msg}")
def skip(msg): print(f"{SLATE}  ⊘  {RESET}{dim(msg)}")
def dep_tag(parent): print(f"  {INDIGO}  dep of {dim(parent)}{RESET}  ", end="")

def divider(char="─", width=62, c=SLATE):
    print(f"{c}{char * width}{RESET}")

def header(title, subtitle=None):
    print()
    divider("═", 62, MINT)
    print(f"  {BWHITE}{title}{RESET}")
    if subtitle:
        print(f"  {dim(subtitle)}")
    divider("═", 62, MINT)
    print()

def section(title):
    print(f"\n{TEAL}  ▸ {BWHITE}{title}{RESET}")
    print(f"  {SLATE}{'─' * 56}{RESET}")

# ══════════════════════════════════════════════════════════════════════════════
#  HTTP
# ══════════════════════════════════════════════════════════════════════════════

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
        err(f"API error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        err(f"Connection failed: {e.reason}")
        sys.exit(1)
    except Exception as e:
        err(f"Network error: {e}")
        sys.exit(1)

def download_file(url, dest_path, sha512_expected=None):
    """Download file with progress bar. Returns True on success."""
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
                    if total:
                        pct    = downloaded * 100 // total
                        filled = pct // 4
                        bar    = f"{MINT}{'█' * filled}{SLATE}{'░' * (25 - filled)}{RESET}"
                        speed  = downloaded / max(time.time() - t0, 0.1) / 1024
                        done   = f"{GOLD}{downloaded//1024:,}{RESET}KB"
                        tot_s  = f"{SLATE}/{total//1024:,}KB{RESET}"
                        spd    = f"{CYAN}{speed:5.0f}KB/s{RESET}"
                        pct_s  = f"{BYELLOW}{pct:3d}%{RESET}"
                        print(f"\r    {bar} {pct_s}  {done}{tot_s}  {spd} ", end="", flush=True)

        elapsed = time.time() - t0
        size_kb = downloaded // 1024
        print(f"\r    {MINT}{'█'*25}{RESET} {BYELLOW}100%{RESET}  {GOLD}{size_kb:,}KB{RESET}  {dim(f'{elapsed:.1f}s')}        ")

        # Verify checksum if provided
        if sha512_expected:
            actual = hasher.hexdigest()
            if actual != sha512_expected:
                err(f"Checksum mismatch! File may be corrupted.")
                Path(dest_path).unlink(missing_ok=True)
                return False

        return True

    except Exception as e:
        print()
        err(f"Download failed: {e}")
        Path(dest_path).unlink(missing_ok=True)
        return False

# ══════════════════════════════════════════════════════════════════════════════
#  Profile & Cache (Local to current directory)
# ══════════════════════════════════════════════════════════════════════════════

def profile_path():
    return Path.cwd() / "profile.json"

def cache_path():
    return Path.cwd() / ".3m_cache.json"

def load_profile():
    p = profile_path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if data.get("mc_version") and data.get("loader"):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return None

def save_profile(mc_version, loader):
    profile_path().write_text(json.dumps({
        "mc_version": mc_version,
        "loader":     loader,
        "updated_at": _now_iso(),
    }, indent=2))

def require_profile():
    p = load_profile()
    if not p:
        err("No profile set in this directory. Run first:")
        print(f"    {GOLD}3m set-profile 1.21.1 fabric{RESET}\n")
        sys.exit(1)
    return p

# ══════════════════════════════════════════════════════════════════════════════
#  Search cache
# ══════════════════════════════════════════════════════════════════════════════

def save_cache(results, query=""):
    cache_path().write_text(json.dumps({
        "query":   query,
        "results": results,
        "time":    time.time(),
    }, indent=2))

def load_cache():
    p = cache_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        # Support old list format
        if isinstance(data, list):
            return data
        return data.get("results", [])
    except Exception:
        return None

def load_cache_meta():
    p = cache_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return {"query": "?", "results": data, "time": 0}
        return data
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  Metadata  (./metadata.json in mod directory)
# ══════════════════════════════════════════════════════════════════════════════

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def metadata_path():
    return Path.cwd() / "metadata.json"

def _empty_metadata():
    return {
        "3m_version": VERSION,
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
        "required_by": [],   # list of slugs that depend on this mod
        "requested":   False,
        "installed_at": _now_iso(),
    }

def load_metadata():
    p = metadata_path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return _empty_metadata()

def save_metadata(data):
    data["updated_at"] = _now_iso()
    metadata_path().write_text(json.dumps(data, indent=2))

def upsert_mod(data, slug, **fields):
    """
    Insert or update a mod entry in metadata.
    Only overwrites non-empty fields; existing values are preserved when new value is falsy.
    """
    if "mods" not in data:
        data["mods"] = {}

    entry = data["mods"].get(slug, _empty_mod_entry())
    entry["slug"] = slug

    for key, value in fields.items():
        if key == "required_by":
            # Merge lists without duplicates
            existing = entry.get(key, [])
            for item in (value or []):
                if item and item not in existing:
                    existing.append(item)
            entry[key] = existing
        elif value or value == 0:
            # Only overwrite if new value is truthy (or explicitly 0)
            entry[key] = value

    data["mods"][slug] = entry
    return data

def remove_mod_from_metadata(data, slug):
    """Remove a mod and clean up all reverse-dependency references."""
    if slug not in data.get("mods", {}):
        return data
    del data["mods"][slug]
    for mod in data["mods"].values():
        lst = mod.get("required_by", [])
        if slug in lst:
            lst.remove(slug)
    return data

# ══════════════════════════════════════════════════════════════════════════════
#  Modrinth API helpers
# ══════════════════════════════════════════════════════════════════════════════

LOADER_COLORS = {
    "fabric":   MINT,
    "forge":    ORANGE,
    "quilt":    PURPLE,
    "neoforge": GOLD,
}

def loader_badge(loader):
    c = LOADER_COLORS.get(loader.lower(), CYAN)
    return f"{c}[{loader}]{RESET}"

def fmt_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

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

def search_mods(query, profile, limit=10):
    facets = json.dumps([
        [f"versions:{profile['mc_version']}"],
        [f"categories:{profile['loader']}"],
        ["project_type:mod"],
    ])
    data = api_get("/search", {"query": query, "facets": facets, "limit": limit})
    if data is None:
        return []
    return data.get("hits", [])

def get_project(slug_or_id):
    """Fetch full project metadata from Modrinth."""
    return api_get(f"/project/{slug_or_id}")

def get_best_version(slug, profile):
    """Return best matching version object for given profile."""
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
    """Resolve a user-typed name to a Modrinth slug."""
    hits = search_mods(name, profile, limit=limit)
    for hit in hits:
        slug = hit.get("slug", "")
        if slug.lower() == normalize_slug(name) or hit.get("title", "").lower() == name.lower():
            return slug, hit
    if hits:
        return hits[0]["slug"], hits[0]
    return None, None

def get_required_dependencies(slug, profile):
    """
    Return list of (dep_slug, dep_version_id) for all REQUIRED dependencies only.
    Optional deps are intentionally excluded.
    """
    version = get_best_version(slug, profile)
    if not version:
        return []

    result = []
    for dep in version.get("dependencies", []):
        if dep.get("dependency_type") != "required":
            continue
        project_id = dep.get("project_id")
        version_id = dep.get("version_id")   # may be None (any version)
        if project_id:
            proj = get_project(project_id)
            if proj:
                result.append((proj["slug"], version_id))
    return result

# ══════════════════════════════════════════════════════════════════════════════
#  Install engine
# ══════════════════════════════════════════════════════════════════════════════

def install_mod(name, profile, dest_dir, metadata, parent_slug=None, seen=None):
    """
    Download a mod and all its required dependencies recursively.

    Args:
        name:        mod name or slug to look up
        profile:     dict with mc_version and loader
        dest_dir:    Path to write .jar files
        metadata:    metadata dict (mutated in place)
        parent_slug: slug of the mod that requires this one (None = user request)
        seen:        set of already-processed slugs to prevent cycles

    Returns:
        slug (str) on success, None on failure
    """
    if seen is None:
        seen = set()

    # ── Resolve slug ──────────────────────────────────────────────────────────
    slug, hit = get_slug_from_name(name, profile)
    if not slug:
        err(f"No mod found matching '{name}'")
        return None

    # ── Already handled this install session ─────────────────────────────────
    if slug in seen:
        return slug
    seen.add(slug)

    # ── Print what we're installing ───────────────────────────────────────────
    is_dep = parent_slug is not None
    if is_dep:
        dep_tag(parent_slug)
    step(f"{BWHITE}{slug}{RESET}" + (f"  {dim('(via ' + parent_slug + ')')}" if is_dep else ""))

    # Show resolved title if different from input
    title_from_search = hit.get("title", slug) if hit else slug
    desc_from_search  = hit.get("description", "") if hit else ""
    if slug.lower() != normalize_slug(name):
        print(f"       {TEAL}↳ {title_from_search}{RESET}  {dim(slug)}")

    # ── Get version ───────────────────────────────────────────────────────────
    version = get_best_version(slug, profile)
    if not version:
        err(f"No version available for {profile['mc_version']}/{profile['loader']}: {slug}")
        return None

    file_info = get_primary_file(version)
    if not file_info:
        err(f"No downloadable file found for {slug}")
        return None

    url      = file_info["url"]
    filename = file_info["filename"]
    sha512   = file_info.get("hashes", {}).get("sha512", "")
    dest     = dest_dir / filename

    vnum   = version.get("version_number", "?")
    vtype  = version.get("version_type", "release")
    vcolor = {"release": GREEN, "beta": YELLOW, "alpha": ORANGE}.get(vtype, SLATE)

    print(f"       {CYAN}{filename}{RESET}  {vcolor}v{vnum}{RESET}  {dim('[' + vtype + ']')}")

    # ── Fetch full project metadata ───────────────────────────────────────────
    project = get_project(slug) or {}

    # ── Skip if already downloaded ────────────────────────────────────────────
    if dest.exists():
        skip(f"Already exists — {filename}")
    else:
        success = download_file(url, dest, sha512_expected=sha512 or None)
        if not success:
            return None
        ok(f"{title_from_search}  {dim(filename)}")

    # ── Write metadata ────────────────────────────────────────────────────────
    upsert_mod(metadata, slug,
        title        = project.get("title") or title_from_search,
        description  = project.get("description") or desc_from_search,
        version_id   = version.get("id", ""),
        version      = vnum,
        version_type = vtype,
        file         = filename,
        sha512       = sha512,
        size_bytes   = file_info.get("size", 0),
        project_id   = project.get("id", ""),
        source_url   = project.get("source_url") or project.get("issues_url") or "",
        license      = (project.get("license") or {}).get("id", ""),
        categories   = project.get("categories", []),
        downloads    = project.get("downloads", 0),
        followers    = project.get("followers", 0),
        requested    = not is_dep,
        required_by  = [parent_slug] if parent_slug else [],
        installed_at = _now_iso(),
    )

    # ── Resolve and install dependencies ─────────────────────────────────────
    deps = get_required_dependencies(slug, profile)
    for dep_slug, _dep_version_id in deps:
        # Track this dependency relationship even before downloading
        upsert_mod(metadata, dep_slug, required_by=[slug])

        if dep_slug in seen:
            continue

        print()
        install_mod(dep_slug, profile, dest_dir, metadata,
                    parent_slug=slug, seen=seen)

    return slug


def get_dependents_recursive(slug, mods, seen=None):
    """Return all slugs that (transitively) depend on slug."""
    if seen is None:
        seen = {slug}
    result = []
    for dep in mods.get(slug, {}).get("required_by", []):
        if dep not in seen:
            seen.add(dep)
            result.append(dep)
            result.extend(get_dependents_recursive(dep, mods, seen))
    return result

# ══════════════════════════════════════════════════════════════════════════════
#  Display helpers
# ══════════════════════════════════════════════════════════════════════════════

def print_search_results(results, profile, query=""):
    if not results:
        warn("No results found.")
        return

    header(
        f"Search results  {dim('» ' + query)}",
        f"Minecraft {profile['mc_version']}  ·  {profile['loader'].capitalize()}"
    )

    for i, hit in enumerate(results, 1):
        dl      = fmt_num(hit.get("downloads", 0))
        follows = fmt_num(hit.get("follows", 0))
        cats    = hit.get("categories", [])
        cat_str = "  ".join(f"{PURPLE}#{c}{RESET}" for c in cats[:4])
        desc    = hit.get("description", "")
        if len(desc) > 74:
            desc = desc[:71] + "..."

        idx_col = f"{bg(236)}{BYELLOW} {i:2d} {RESET}"
        title   = f"{BWHITE}{hit['title']}{RESET}"
        slug    = dim(f"({hit['slug']})")
        dl_str  = f"{LIME}↓ {dl}{RESET}"
        fav_str = f"{PINK}♥ {follows}{RESET}"

        print(f"  {idx_col}  {title}  {slug}")
        print(f"       {DIM}{ITALIC}{desc}{RESET}")
        print(f"       {dl_str}    {fav_str}    {cat_str}")
        print()

    divider(c=SLATE)
    print(f"  {dim('get -i <n>')}{SLATE} — install by index{RESET}    "
          f"{dim('show -i <n>')}{SLATE} — view details{RESET}")
    print()

# ══════════════════════════════════════════════════════════════════════════════
#  Commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_set_profile(args):
    mc     = args.mc_version
    loader = args.loader.lower()
    if loader not in KNOWN_LOADERS:
        warn(f"Unknown loader '{loader}'. Common loaders: {', '.join(KNOWN_LOADERS)}")
    save_profile(mc, loader)
    header("Profile updated")
    print(f"  {SLATE}Minecraft  {RESET}{BWHITE}{mc}{RESET}")
    print(f"  {SLATE}Loader     {RESET}{loader_badge(loader)}")
    print()


def cmd_search(args):
    profile = require_profile()
    query   = " ".join(args.query)
    limit   = args.limit or 10
    info(f"Searching {BWHITE}'{query}'{RESET}  "
         f"{dim('[' + profile['mc_version'] + ' / ' + profile['loader'] + ']')}")
    results = search_mods(query, profile, limit=limit)
    save_cache(results, query)
    print_search_results(results, profile, query)


def cmd_get(args):
    profile  = require_profile()
    dest_dir = Path.cwd()
    auto_deps = not getattr(args, "no_deps", False)

    metadata = load_metadata()
    metadata["mc_version"] = profile["mc_version"]
    metadata["loader"]     = profile["loader"]

    # ── By index ──────────────────────────────────────────────────────────────
    if args.i is not None:
        cache = load_cache()
        if not cache:
            err("No search results cached. Run: 3m search <name>")
            sys.exit(1)
        idx = args.i - 1
        if idx < 0 or idx >= len(cache):
            err(f"Index {args.i} out of range (1–{len(cache)})")
            sys.exit(1)
        slug = cache[idx]["slug"]
        header("Installing mod", str(dest_dir))
        print(f"  {SLATE}[1/1]{RESET}  ", end="")
        if auto_deps:
            install_mod(slug, profile, dest_dir, metadata)
        else:
            install_mod(slug, profile, dest_dir, metadata, seen=set())
        save_metadata(metadata)
        print()
        return

    # ── By name(s) ────────────────────────────────────────────────────────────
    if args.names:
        raw  = " ".join(args.names)
        mods = [s.strip() for s in raw.split(",") if s.strip()]

        if not auto_deps:
            print(f"  {dim('Skipping dependencies (--no-deps)')}\n")

        header(f"Installing {len(mods)} mod{'s' if len(mods) != 1 else ''}",
               str(dest_dir))

        seen        = set()
        ok_count    = 0
        fail_list   = []
        install_map = []

        for idx, name in enumerate(mods, 1):
            print(f"  {SLATE}[{idx}/{len(mods)}]{RESET}  ", end="")
            if auto_deps:
                slug = install_mod(name, profile, dest_dir, metadata, seen=seen)
            else:
                # No deps: use a fresh seen set per mod so they don't block each other,
                # but pass parent=None to mark them all as requested
                slug = install_mod(name, profile, dest_dir, metadata,
                                   seen=seen | set(metadata.get("mods", {}).keys()))

            if slug:
                ok_count += 1
                install_map.append((name, slug))
            else:
                fail_list.append(name)
            print()

        save_metadata(metadata)

        # ── Summary ───────────────────────────────────────────────────────────
        divider(c=MINT)
        print(f"  {LIME}✔ {ok_count} succeeded{RESET}", end="")
        if fail_list:
            print(f"    {ROSE}✗ {len(fail_list)} failed:{RESET} {', '.join(fail_list)}", end="")
        print(f"\n  {dim('Directory: ' + str(dest_dir))}\n")

        if len(mods) > 1:
            print(f"  {BYELLOW}Installation map:{RESET}")
            max_len = max(len(m) for m in mods)
            for i, req in enumerate(mods, 1):
                found = next((s for n, s in install_map if n == req), None)
                if found:
                    print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {LIME}{found}{RESET}")
                else:
                    print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {ROSE}(failed){RESET}")
            print()
        return

    err("Missing argument. Usage: get <name>  or  get -i <index>")
    sys.exit(1)


def cmd_show(args):
    profile = require_profile()

    if args.names:
        raw  = " ".join(args.names)
        slug, _ = get_slug_from_name(raw.strip(), profile)
        if not slug:
            err(f"Mod not found: {raw}")
            sys.exit(1)
    elif args.i is not None:
        cache = load_cache()
        if not cache:
            err("No search results cached. Run: 3m search <name>")
            sys.exit(1)
        idx = args.i - 1
        if idx < 0 or idx >= len(cache):
            err(f"Index {args.i} out of range (1–{len(cache)})")
            sys.exit(1)
        slug = cache[idx]["slug"]
    else:
        err("Usage: show <name>  or  show -i <index>")
        sys.exit(1)

    project = get_project(slug)
    if not project:
        err(f"Project not found: {slug}")
        sys.exit(1)

    version = get_best_version(slug, profile)
    f_info  = get_primary_file(version) if version else None

    header(project["title"], project.get("description", ""))

    section("General")
    rows = [
        ("Slug",       f"{CYAN}{project['slug']}{RESET}"),
        ("Project ID", f"{dim(project.get('id', 'N/A'))}"),
        ("Downloads",  f"{LIME}{fmt_num(project.get('downloads', 0))}{RESET}"),
        ("Followers",  f"{PINK}{fmt_num(project.get('followers', 0))}{RESET}"),
        ("License",    f"{SLATE}{(project.get('license') or {}).get('id', 'N/A')}{RESET}"),
        ("Categories", "  ".join(f"{PURPLE}#{c}{RESET}" for c in project.get("categories", []))),
        ("Loaders",    "  ".join(loader_badge(l) for l in project.get("loaders", []))),
        ("Source",     f"{BLUE}{project.get('source_url') or 'N/A'}{RESET}"),
        ("Issues",     f"{BLUE}{project.get('issues_url') or 'N/A'}{RESET}"),
    ]
    for k, v in rows:
        print(f"    {SLATE}{k:<12}{RESET}  {v}")

    section(f"Best version for  {profile['mc_version']} / {profile['loader']}")
    if version and f_info:
        vtype  = version.get("version_type", "?")
        vcolor = {"release": GREEN, "beta": YELLOW, "alpha": ORANGE}.get(vtype, SLATE)
        sha512 = f_info.get("hashes", {}).get("sha512", "")
        rows2 = [
            ("Version",  f"{vcolor}{version['version_number']}{RESET}  {dim('[' + vtype + ']')}"),
            ("File",     f"{CYAN}{f_info['filename']}{RESET}"),
            ("Size",     f"{GOLD}{f_info.get('size', 0) // 1024:,} KB{RESET}"),
            ("SHA-512",  f"{dim(sha512[:24] + '...' if sha512 else 'N/A')}"),
        ]
        for k, v in rows2:
            print(f"    {SLATE}{k:<12}{RESET}  {v}")

        # Show required dependencies
        deps = get_required_dependencies(slug, profile)
        if deps:
            section("Required dependencies")
            for dep_slug, _ in deps:
                dep_proj = get_project(dep_slug)
                dep_title = dep_proj.get("title", dep_slug) if dep_proj else dep_slug
                print(f"    {INDIGO}·{RESET}  {BWHITE}{dep_title}{RESET}  {dim(dep_slug)}")
    else:
        warn("No version matching current profile.")

    section("Supported Minecraft versions")
    all_vers = sorted(project.get("game_versions", []), reverse=True)
    chunks = [all_vers[i:i+8] for i in range(0, min(len(all_vers), 24), 8)]
    for chunk in chunks:
        print("    " + "  ".join(f"{SKY}{v}{RESET}" for v in chunk))

    print(f"\n  {TEAL}🌐  https://modrinth.com/mod/{slug}{RESET}\n")


def cmd_list(args):
    dest_dir = Path.cwd()
    metadata = load_metadata()
    mods     = metadata.get("mods", {})

    header("Installed mods", str(dest_dir))

    if not mods:
        warn("No mods tracked in metadata.")
        jars = sorted(dest_dir.glob("*.jar"))
        if jars:
            info(f"Found {len(jars)} .jar files not tracked by 3m.")
            for j in jars:
                print(f"    {SLATE}{j.name}{RESET}")
        print()
        return

    total_size  = 0
    i           = 1
    req_list    = [(s, m) for s, m in mods.items() if m.get("requested")]
    dep_list    = [(s, m) for s, m in mods.items() if not m.get("requested")]

    sections = [
        ("User-requested mods", req_list, LIME,   "[req]"),
        ("Dependency mods",     dep_list, INDIGO, "[dep]"),
    ]

    for label, items, tag_color, tag_text in sections:
        if not items:
            continue
        print(f"  {BYELLOW}{label}{RESET}\n")
        for slug, entry in items:
            idx_col  = f"{bg(236)}{BYELLOW} {i:2d} {RESET}"
            title    = entry.get("title") or slug
            version  = entry.get("version", "")
            req_tag  = f"{tag_color}{tag_text}{RESET}"
            req_by   = entry.get("required_by", [])
            by_str   = f"  {dim('←')} {ROSE}{', '.join(req_by)}{RESET}" if req_by else ""

            print(f"  {idx_col}  {BWHITE}{title}{RESET}  "
                  f"{dim('v' + version) if version else ''}{req_tag}{by_str}")

            desc = entry.get("description", "")
            if desc:
                short = desc.split("\n")[0][:74]
                if len(desc.split("\n")[0]) > 74:
                    short += "..."
                print(f"       {DIM}{ITALIC}{short}{RESET}")

            file_name = entry.get("file", "")
            if file_name:
                fpath = dest_dir / file_name
                if fpath.exists():
                    size_b = fpath.stat().st_size
                    total_size += size_b
                    size_str = f"{size_b // 1024:,} KB"
                    print(f"       {SLATE}{size_str:>8}  {file_name}{RESET}")
                else:
                    print(f"       {ROSE}file missing: {file_name}{RESET}")

            print()
            i += 1

    divider(c=SLATE)
    total_kb = total_size // 1024
    if total_kb >= 1024:
        size_display = f"{total_kb / 1024:.1f} MB"
    else:
        size_display = f"{total_kb:,} KB"
    print(f"  {dim(str(len(mods)) + ' mod(s) tracked  ·  ' + size_display + ' on disk')}\n")
    print(f"  {dim('Remove by name: 3m remove <name>    Remove by index: 3m remove -i <n>')}\n")


def cmd_remove(args):
    dest_dir = Path.cwd()
    metadata = load_metadata()
    mods     = metadata.get("mods", {})

    if not mods:
        err("No mods in metadata.")
        print()
        sys.exit(1)

    def _do_remove(slug):
        """Remove a single mod: delete file, update metadata."""
        entry    = mods.get(slug, {})
        title    = entry.get("title", slug)
        file_name = entry.get("file", "")
        fpath    = dest_dir / file_name if file_name else None

        metadata_obj = load_metadata()
        remove_mod_from_metadata(metadata_obj, slug)
        save_metadata(metadata_obj)
        # Refresh local reference
        mods.clear()
        mods.update(metadata_obj.get("mods", {}))

        if fpath and fpath.exists():
            fpath.unlink()
            ok(f"Removed: {title}  {dim(file_name)}")
        else:
            ok(f"Removed from metadata: {title}  {dim('(file not found)')}")

    def _confirm_cascade(slug):
        """Check dependents and ask for confirmation if any exist."""
        entry    = mods.get(slug, {})
        title    = entry.get("title", slug)
        req_by   = get_dependents_recursive(slug, mods)

        if req_by:
            print(f"\n  {ROSE}Warning: {BWHITE}{title}{RESET}{ROSE} is required by:{RESET}")
            for r in req_by:
                dep_title = mods.get(r, {}).get("title", r)
                print(f"    {ROSE}·  {dep_title}{RESET}  {dim(r)}")
            print(f"\n  {YELLOW}Also remove these {len(req_by)} dependent mod(s)?{RESET}  {dim('[y/N]')}")
            confirm = input("  > ").strip().lower()
            if confirm != "y":
                print(f"  {dim('Cancelled')}\n")
                return False
            for r in list(req_by):
                _do_remove(r)
        return True

    # ── Remove all ────────────────────────────────────────────────────────────
    if getattr(args, "all", False):
        count = len(mods)
        print(f"\n  {ROSE}Warning: About to remove {count} mod(s)!{RESET}")
        print(f"  {YELLOW}Continue?{RESET}  {dim('[y/N]')}")
        confirm = input("  > ").strip().lower()
        if confirm != "y":
            print(f"  {dim('Cancelled')}\n")
            return
        for slug in list(mods.keys()):
            _do_remove(slug)
        ok(f"Removed all {count} mod(s).")
        print()
        return

    # ── Remove by index ───────────────────────────────────────────────────────
    if args.i is not None:
        req_list = [(s, m) for s, m in mods.items() if m.get("requested")]
        dep_list = [(s, m) for s, m in mods.items() if not m.get("requested")]
        ordered  = req_list + dep_list
        idx      = args.i - 1
        if idx < 0 or idx >= len(ordered):
            err(f"Index {args.i} out of range (1–{len(ordered)})")
            sys.exit(1)
        slug, _ = ordered[idx]
        if not _confirm_cascade(slug):
            return
        _do_remove(slug)
        print()
        return

    # ── Remove by name(s) ─────────────────────────────────────────────────────
    if args.names:
        raw   = " ".join(args.names)
        names = [n.strip() for n in raw.split(",") if n.strip()]
        for name in names:
            # Exact slug match first
            slug = name if name in mods else None
            # Then exact title match
            if not slug:
                slug = next((s for s, m in mods.items()
                             if m.get("title", "").lower() == name.lower()), None)
            # Then fuzzy
            if not slug:
                matched = fuzzy_match(name, list(mods.keys()))
                if matched:
                    slug = matched

            if not slug:
                warn(f"No mod found close to '{name}'")
                continue

            if not _confirm_cascade(slug):
                continue
            _do_remove(slug)

        print()
        return

    err("Usage: remove <name>  or  remove -i <index>  or  remove -a")
    sys.exit(1)


def cmd_profile(args):
    p = load_profile()
    header("Current profile")
    if p:
        print(f"  {SLATE}Minecraft  {RESET}{BWHITE}{p['mc_version']}{RESET}")
        print(f"  {SLATE}Loader     {RESET}{loader_badge(p['loader'])}")
        print(f"  {SLATE}Updated    {RESET}{dim(p.get('updated_at', '?'))}")
        print()
        meta = load_cache_meta()
        if meta and meta.get("query"):
            ts  = meta.get("time", 0)
            ago = f"{int((time.time()-ts)//60)} min ago" if ts else "?"
            print(f"  {SLATE}Last search{RESET}  {dim(repr(meta['query']) + '  (' + ago + ')')}")
        print()
    else:
        warn("No profile set.")
        print(f"  {dim('Example: 3m set-profile 1.21.1 fabric')}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════════

def print_help():
    banner = f"""
{MINT}  ┌──────────────────────────────────────────────────────┐{RESET}
{MINT}  │{RESET}  {BWHITE}3m{RESET}  {SLATE}—{RESET}  {BCYAN}Minecraft Mod Manager{RESET}  {dim('v' + VERSION)}               {MINT}│{RESET}
{MINT}  │{RESET}  {dim('Downloads from Modrinth · Resolves deps · No bloat')}  {MINT}│{RESET}
{MINT}  └──────────────────────────────────────────────────────┘{RESET}
"""
    print(banner)

    divider("═", 62, MINT)
    print(f"  {BWHITE}COMMANDS{RESET}")
    divider("═", 62, MINT)

    commands = [
        (
            f"{BYELLOW}set-profile{RESET} {CYAN}<mc_version> <loader>{RESET}",
            "Set Minecraft version and mod loader.",
            [f"{dim('Loaders:')}  fabric  forge  quilt  neoforge",
             f"{GOLD}3m set-profile 1.21.1 fabric{RESET}"]
        ),
        (
            f"{BYELLOW}search{RESET} {CYAN}<query>{RESET}  {dim('[-n <count>]')}",
            "Search mods. Results are numbered for get/show.",
            [f"{GOLD}3m search sodium{RESET}",
             f"{GOLD}3m search \"performance optimization\" -n 15{RESET}"]
        ),
        (
            f"{BYELLOW}get{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}get{RESET} {CYAN}-i <index>{RESET}",
            "Install mod(s) to current directory. Resolves required deps automatically.",
            [f"{GOLD}3m get sodium{RESET}",
             f"{GOLD}3m get -i 3{RESET}",
             f"{GOLD}3m get --no-deps sodium{RESET}",
             f"{GOLD}3m get sodium, lithium, iris, immediately fast{RESET}"]
        ),
        (
            f"{BYELLOW}show{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}show{RESET} {CYAN}-i <index>{RESET}",
            "Show full mod info: version, size, deps, checksums.",
            [f"{GOLD}3m show sodium{RESET}",
             f"{GOLD}3m show -i 1{RESET}"]
        ),
        (
            f"{BYELLOW}list{RESET}",
            "List all tracked mods with sizes and dependency graph.",
            [f"{GOLD}3m list{RESET}"]
        ),
        (
            f"{BYELLOW}remove{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove{RESET} {CYAN}-i <index>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove -a{RESET}",
            "Remove mod(s). Warns before removing if other mods depend on it.",
            [f"{GOLD}3m remove sodium{RESET}",
             f"{GOLD}3m remove -i 1{RESET}",
             f"{GOLD}3m remove -a{RESET}",
             f"{GOLD}3m remove sodium, lithium{RESET}"]
        ),
        (
            f"{BYELLOW}profile{RESET}",
            "View current profile and cache info.",
            [f"{GOLD}3m profile{RESET}"]
        ),
    ]

    for sig, desc, examples in commands:
        print(f"\n  {sig}")
        print(f"    {desc}")
        for ex in examples:
            print(f"    {SLATE}›{RESET}  {ex}")
    print()

    divider("─", 62, SLATE)
    print(f"  {BWHITE}NOTES{RESET}\n")
    notes = [
        f"Mods always install to the {ITALIC}current directory{RESET} when running {CYAN}get{RESET}.",
        f"Only {LIME}required{RESET} dependencies are auto-installed. Optional deps are skipped.",
        f"Commas separate mods; spaces are part of the name: {GOLD}get immediately fast, sodium{RESET}",
        f"Checksums (SHA-512) are verified after every download.",
        f"Profile stored at {dim('./' + profile_path().name + '  (per mod directory)')}",
        f"Metadata stored at {dim('./' + metadata_path().name + '  (per mod directory)')}",
        f"No login or API key needed. Rate limit: 300 req/min.",
    ]
    for note in notes:
        print(f"  {MINT}▪{RESET}  {note}")
    print()

    divider("─", 62, SLATE)
    print(f"  {BWHITE}QUICK WORKFLOW{RESET}\n")
    steps = [
        ("# First time — set profile",
         ["3m set-profile 1.21.1 fabric"]),
        ("# Install optimization mods",
         ["cd ~/minecraft/mods",
          "3m get sodium, lithium, iris, immediately fast, ferritecore, entityculling"]),
        ("# Search, preview, then install",
         ["3m search \"chunk loading\"",
          "3m show -i 1",
          "3m get -i 1"]),
        ("# Check what's installed",
         ["3m list"]),
        ("# Remove a mod (will warn about dependents)",
         ["3m remove sodium"]),
    ]
    for comment, cmds in steps:
        print(f"  {SLATE}{comment}{RESET}")
        for cmd in cmds:
            print(f"  {GOLD}{cmd}{RESET}")
        print()

    divider("═", 62, MINT)
    print()

# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(prog="3m", add_help=False)
    parser.add_argument("-h", "--help",    action="store_true")
    parser.add_argument("-v", "--version", action="store_true")

    sub = parser.add_subparsers(dest="cmd")

    sp = sub.add_parser("set-profile", add_help=False)
    sp.add_argument("mc_version")
    sp.add_argument("loader")

    sp = sub.add_parser("search", add_help=False)
    sp.add_argument("query", nargs="+")
    sp.add_argument("-n", "--limit", type=int, default=10)

    sp = sub.add_parser("get", add_help=False)
    sp.add_argument("-i", type=int, metavar="INDEX")
    sp.add_argument("--no-deps", action="store_true")
    sp.add_argument("names", nargs="*")

    sp = sub.add_parser("show", add_help=False)
    sp.add_argument("-i", type=int, metavar="INDEX")
    sp.add_argument("names", nargs="*")

    sp = sub.add_parser("remove", add_help=False)
    sp.add_argument("-i", type=int, metavar="INDEX")
    sp.add_argument("-a", "--all", action="store_true")
    sp.add_argument("names", nargs="*")

    sub.add_parser("list",    add_help=False)
    sub.add_parser("profile", add_help=False)

    args = parser.parse_args()

    if args.version:
        print(f"{BWHITE}3m{RESET} version {GOLD}{VERSION}{RESET}")
        return

    if args.help or args.cmd is None:
        print_help()
        return

    dispatch = {
        "set-profile": cmd_set_profile,
        "search":      cmd_search,
        "get":         cmd_get,
        "show":        cmd_show,
        "remove":      cmd_remove,
        "list":        cmd_list,
        "profile":     cmd_profile,
    }

    fn = dispatch.get(args.cmd)
    if fn:
        fn(args)

if __name__ == "__main__":
    main()
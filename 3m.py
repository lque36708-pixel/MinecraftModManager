#!/usr/bin/env python3
"""
3m — Minecraft Mod Manager
Tải mod từ Modrinth nhanh chóng qua CLI.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import argparse
import time
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

VERSION     = "2.0.0"
API_BASE    = "https://api.modrinth.com/v2"
USER_AGENT  = f"3m-cli/{VERSION} (minecraft-mod-manager)"
CACHE_FILE  = Path.home() / ".config" / "3m" / "last_search.json"

def get_local_profile_path():
    return Path.cwd() / ".profile"

# ══════════════════════════════════════════════════════════════════════════════
#  ANSI
# ══════════════════════════════════════════════════════════════════════════════

ESC = "\033["
def _c(*codes): return ESC + ";".join(str(c) for c in codes) + "m"

RESET   = _c(0)
BOLD    = _c(1)
DIM     = _c(2)
ITALIC  = _c(3)

BLACK   = _c(30); RED     = _c(31); GREEN   = _c(32); YELLOW  = _c(33)
BLUE    = _c(34); MAGENTA = _c(35); CYAN    = _c(36); WHITE   = _c(37)

BRED    = _c(1,31); BGREEN  = _c(1,32); BYELLOW = _c(1,33)
BBLUE   = _c(1,34); BMAGENTA= _c(1,35); BCYAN   = _c(1,36); BWHITE  = _c(1,37)

def fg256(n):  return f"\033[38;5;{n}m"
def bg256(n):  return f"\033[48;5;{n}m"

MINT    = fg256(114)
GOLD    = fg256(220)
PURPLE  = fg256(141)
ORANGE  = fg256(208)
PINK    = fg256(213)
SLATE   = fg256(245)
TEAL    = fg256(43)
LIME    = fg256(154)
ROSE    = fg256(196)
SKY     = fg256(117)

def rst(s):    return f"{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"
def italic(s): return f"{ITALIC}{s}{RESET}"

# ══════════════════════════════════════════════════════════════════════════════
#  Print helpers
# ══════════════════════════════════════════════════════════════════════════════

def _print_err(msg):
    print(f"{ROSE}  ✗  {RESET}{RED}{msg}{RESET}", file=sys.stderr)

def _print_ok(msg):
    print(f"{LIME}  ✔  {RESET}{GREEN}{msg}{RESET}")

def _print_info(msg):
    print(f"{SKY}  ›  {RESET}{CYAN}{msg}{RESET}")

def _print_warn(msg):
    print(f"{GOLD}  ⚠  {RESET}{YELLOW}{msg}{RESET}")

def _print_step(msg):
    print(f"{MINT}  ↓  {RESET}{msg}")

def _print_skip(msg):
    print(f"{SLATE}  ⊘  {RESET}{dim(msg)}")

def _divider(char="─", width=60, color=SLATE):
    print(f"{color}{char * width}{RESET}")

def _header(title, subtitle=None):
    print()
    _divider("═", 60, MINT)
    print(f"  {BWHITE}{title}{RESET}")
    if subtitle:
        print(f"  {dim(subtitle)}")
    _divider("═", 60, MINT)
    print()

def _section(title):
    print(f"\n{TEAL}  ▸ {BWHITE}{title}{RESET}")
    print(f"  {SLATE}{'─' * 54}{RESET}")

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
        _print_err(f"API lỗi {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        _print_err(f"Không kết nối được: {e.reason}")
        sys.exit(1)
    except Exception as e:
        _print_err(f"Lỗi mạng: {e}")
        sys.exit(1)

def download_file(url, dest_path):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            t0         = time.time()
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct    = downloaded * 100 // total
                        filled = pct // 4
                        bar    = f"{MINT}{'█' * filled}{SLATE}{'░' * (25 - filled)}{RESET}"
                        speed  = downloaded / max(time.time() - t0, 0.1) / 1024
                        done   = f"{GOLD}{downloaded//1024:,}{RESET}KB"
                        total_ = f"{SLATE}/{total//1024:,}KB{RESET}"
                        spd    = f"{CYAN}{speed:5.0f}KB/s{RESET}"
                        pct_s  = f"{BYELLOW}{pct:3d}%{RESET}"
                        print(f"\r    {bar} {pct_s}  {done}{total_}  {spd} ", end="", flush=True)
        elapsed = time.time() - t0
        size_kb = downloaded // 1024
        print(f"\r    {MINT}{'█'*25}{RESET} {BYELLOW}100%{RESET}  {GOLD}{size_kb:,}KB{RESET}  {dim(f'{elapsed:.1f}s')}         ")
        return True
    except Exception as e:
        print()
        _print_err(f"Tải thất bại: {e}")
        if Path(dest_path).exists():
            Path(dest_path).unlink()
        return False

# ══════════════════════════════════════════════════════════════════════════════
#  Profile / Cache
# ══════════════════════════════════════════════════════════════════════════════

def load_profile():
    p = get_local_profile_path()
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
                if data:
                    return data
        except (json.JSONDecodeError, ValueError):
            pass
    return None

def save_profile(mc_version, loader):
    p = get_local_profile_path()
    with open(p, "w") as f:
        json.dump({"mc_version": mc_version, "loader": loader}, f)

def require_profile():
    p = load_profile()
    if not p:
        _print_err("Chưa có profile. Cần đặt trước:")
        print(f"    {GOLD}VD: 3m set-profile 1.21.1 fabric{RESET}\n")
        sys.exit(1)
    return p

def save_cache(results, query=""):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"query": query, "results": results, "time": time.time()}, f)

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return data.get("results", [])
    return None

def load_cache_meta():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"query": "?", "results": data, "time": 0}
            return data
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  Search & display
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

def normalize_slug(name):
    return name.lower().replace(" ", "-")

def search_mods(query, profile, limit=10):
    facets = json.dumps([
        [f"versions:{profile['mc_version']}"],
        [f"categories:{profile['loader']}"],
        ["project_type:mod"],
    ])
    data = api_get("/search", {
        "query":  query,
        "facets": facets,
        "limit":  limit,
    })
    if data is None:
        return []
    return data.get("hits", [])

def get_slug_from_name(name, profile, limit=5):
    hits = search_mods(name, profile, limit=limit)
    for hit in hits:
        slug = hit.get("slug", "")
        if slug.lower() == normalize_slug(name) or hit.get("title", "").lower() == name.lower():
            return slug
    return hits[0]["slug"] if hits else None

def fmt_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def fuzzy_match(name, choices, threshold=0.6):
    best, best_score = None, 0
    for c in choices:
        score = SequenceMatcher(None, name.lower(), c.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best = c
    return best

def print_results(results, profile, query=""):
    if not results:
        _print_warn("Không tìm thấy kết quả nào.")
        return

    mc  = profile['mc_version']
    ldr = profile['loader']
    _header(
        f"Kết quả tìm kiếm  {dim('» ' + query)}",
        f"Profile: Minecraft {mc}  ·  {ldr.capitalize()}"
    )

    for i, hit in enumerate(results, 1):
        dl      = fmt_num(hit.get("downloads", 0))
        follows = fmt_num(hit.get("follows", 0))
        cats    = hit.get("categories", [])
        cat_str = "  ".join(f"{PURPLE}#{c}{RESET}" for c in cats[:4])
        desc    = hit.get("description", "")
        if len(desc) > 72:
            desc = desc[:69] + "..."

        idx_col = f"{bg256(236)}{BYELLOW} {i:2d} {RESET}"
        title   = f"{BWHITE}{hit['title']}{RESET}"
        slug    = dim(f"({hit['slug']})")
        dl_str  = f"{LIME}↓ {dl}{RESET}"
        fav_str = f"{PINK}♥ {follows}{RESET}"

        print(f"  {idx_col}  {title}  {slug}")
        print(f"       {DIM}{ITALIC}{desc}{RESET}")
        print(f"       {dl_str}    {fav_str}    {cat_str}")
        print()

    _divider(color=SLATE)
    print(f"  {dim('get -i <số>')}{SLATE} — tải theo index{RESET}    "
          f"{dim('show -i <số>')}{SLATE} — xem chi tiết{RESET}")
    print()

# ══════════════════════════════════════════════════════════════════════════════
#  Version / file
# ══════════════════════════════════════════════════════════════════════════════

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
    return data[0]

def get_primary_file(version):
    files = version.get("files", [])
    for f in files:
        if f.get("primary"):
            return f
    return files[0] if files else None

def get_project_info(slug_or_id):
    return api_get(f"/project/{slug_or_id}")

def get_dependencies(slug, profile):
    version = get_best_version(slug, profile)
    if not version:
        return []
    deps = version.get("dependencies", [])
    result = []
    for dep in deps:
        dep_type = dep.get("dependency_type")
        if dep_type in ("required", "optional"):
            project_id = dep.get("project_id")
            if project_id:
                proj = get_project_info(project_id)
                if proj:
                    result.append(proj.get("slug", project_id))
    return result

def resolve_deps_ordered(requests, profile, dest_dir):
    result = []
    seen = set()
    dep_of = {}

    for name in requests:
        req_slug = get_slug_from_name(name, profile)
        if req_slug and req_slug not in seen:
            result.append((name, "req"))
            seen.add(req_slug)

        if req_slug:
            deps = get_dependencies(req_slug, profile)
            for dep_slug in deps:
                if dep_slug not in seen:
                    dep_file = next((d for d in dest_dir.glob(f"{dep_slug}*.jar")), None)
                    if not dep_file:
                        result.append((dep_slug, "dep", name))
                        seen.add(dep_slug)
                        dep_of[dep_slug] = name
                    else:
                        seen.add(dep_slug)

    return result, dep_of

# ══════════════════════════════════════════════════════════════════════════════
#  Download
# ══════════════════════════════════════════════════════════════════════════════

def do_download(name, profile, dest_dir):
    _print_step(f"{BWHITE}{name}{RESET}")

    slug = get_slug_from_name(name, profile)
    if not slug:
        _print_err(f"Không tìm thấy mod khớp với '{name}'")
        return None

    hits = search_mods(name, profile, limit=1)
    title = hits[0]["title"] if hits else name
    if slug.lower() != normalize_slug(name):
        print(f"       {TEAL}↳ {title}{RESET}  {dim(slug)}")

    version = get_best_version(slug, profile)
    if not version:
        _print_err(f"Không có phiên bản {profile['mc_version']}/{profile['loader']} cho {title}")
        return None

    file_info = get_primary_file(version)
    if not file_info:
        _print_err(f"Không tìm thấy file tải về cho {title}")
        return None

    url      = file_info["url"]
    filename = file_info["filename"]
    dest     = dest_dir / filename

    vnum   = version['version_number']
    vtype  = version.get('version_type', '?')
    vcolor = {"release": GREEN, "beta": YELLOW, "alpha": ORANGE}.get(vtype, SLATE)

    print(f"       {CYAN}{filename}{RESET}  "
          f"{vcolor}v{vnum}{RESET}  {dim('[' + vtype + ']')}")

    if dest.exists():
        _print_skip(f"Đã tồn tại, bỏ qua — {filename}")
        return slug

    success = download_file(url, dest)
    if success:
        _print_ok(f"{title}  {dim(filename)}")
        return slug
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  Commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_set_profile(args):
    mc     = args.mc_version
    loader = args.loader.lower()
    known  = ("fabric", "forge", "quilt", "neoforge")
    if loader not in known:
        _print_warn(f"Loader '{loader}' không quen thuộc. Loader phổ biến: {', '.join(known)}")
    save_profile(mc, loader)
    _header("Profile đã cập nhật")
    print(f"  {SLATE}Minecraft  {RESET}{BWHITE}{mc}{RESET}")
    print(f"  {SLATE}Loader     {RESET}{loader_badge(loader)}")
    print()

def cmd_search(args):
    profile = require_profile()
    query   = " ".join(args.query)
    limit   = args.limit if hasattr(args, "limit") and args.limit else 10
    _print_info(f"Đang tìm {BWHITE}'{query}'{RESET}  "
                f"{dim('[' + profile['mc_version'] + ' / ' + profile['loader'] + ']')}")
    results = search_mods(query, profile, limit=limit)
    save_cache(results, query)
    print_results(results, profile, query)

def cmd_get(args):
    profile  = require_profile()
    dest_dir = Path(os.getcwd())
    auto_deps = not args.no_deps if hasattr(args, "no_deps") else True

    if args.names:
        raw   = " ".join(args.names)
        mods  = [s.strip() for s in raw.split(",") if s.strip()]

        if auto_deps:
            _print_info(f"Đang phân tích phụ thuộc...")
            all_items, dep_of = resolve_deps_ordered(mods, profile, dest_dir)
        else:
            print(f"  {dim('Bỏ qua phụ thuộc')}")
            all_items = [(m, "req") for m in mods]
            dep_of = {}
            total = len(all_items)

        total = len(all_items)

        _header(
            f"Cài đặt {total} mod",
            f"→ {dest_dir}"
        )

        installed_map = []
        dep_list = []
        ok_count  = 0
        fail_list = []

        req_count = sum(1 for item in all_items if item[1] == "req")
        idx = 1
        for item in all_items:
            if len(item) == 3:
                name, item_type, parent = item
                tag = f"{PURPLE}[Dep → {parent}]{RESET}"
            else:
                name, item_type = item
                tag = f"{SLATE}[{idx}/{req_count}]{RESET}"
            print(f"  {tag}  ", end="")
            result_slug = do_download(name, profile, dest_dir)
            if result_slug:
                ok_count += 1
                if item_type == "req":
                    installed_map.append((name, result_slug))
                else:
                    dep_list.append(result_slug)
            else:
                if item_type == "req":
                    fail_list.append(name)
            if item_type == "req":
                idx += 1
            print()

        _divider(color=MINT)
        print(f"  {LIME}✔ {ok_count} thành công{RESET}", end="")
        if fail_list:
            print(f"    {ROSE}✗ {len(fail_list)} thất bại:{RESET} "
                  f"{', '.join(fail_list)}", end="")
        print(f"\n  {dim('Thư mục: ' + str(dest_dir))}\n")

        if len(mods) > 1:
            _print_warn("Hãy kiểm tra lại các mod được yêu cầu có được cài đặt chính xác chưa, đôi khi có những mod có tên gần giống nhau")
            print()
            print(f"  {BYELLOW}Kết quả cài đặt:{RESET}")

            max_len = max(len(m) for m in mods) if mods else 0
            idx = 1
            for req in mods:
                found = next((s for n, s in installed_map if n == req), None)
                if found:
                    print(f"    [{idx}] {req:<{max_len}} → {LIME}{found}{RESET}")
                else:
                    print(f"    [{idx}] {req:<{max_len}} → {ROSE}(không cài được){RESET}")
                idx += 1

            if dep_list:
                print()
                print(f"  {PURPLE}Phụ thuộc:{RESET}")
                for d in dep_list:
                    print(f"    {dim('·')} {d}")
            print()
            print(f"  {dim('Gỡ mod bằng: 3m remove <tên> hoặc 3m list → 3m remove -i <index>')}")
            print()
        return

    if args.i is not None:
        cache = load_cache()
        if not cache:
            _print_err("Chưa có kết quả search. Chạy: 3m search <tên>")
            sys.exit(1)
        idx = args.i - 1
        if idx < 0 or idx >= len(cache):
            _print_err(f"Index {args.i} nằm ngoài kết quả (1–{len(cache)})")
            sys.exit(1)
        slug = cache[idx]["slug"]
        _header("Tải mod", f"→ {dest_dir}")
        print(f"  {SLATE}[1/1]{RESET}  ", end="")
        do_download(slug, profile, dest_dir)
        print()
        return

    _print_err("Thiếu đối số. Dùng: get <tên> hoặc get -i <số>")
    sys.exit(1)

def cmd_show(args):
    profile = require_profile()

    if args.names:
        raw  = " ".join(args.names)
        hits = search_mods(raw.strip(), profile, limit=1)
        if not hits:
            _print_err(f"Không tìm thấy mod: {raw}")
            sys.exit(1)
        slug = hits[0]["slug"]
    elif args.i is not None:
        cache = load_cache()
        if not cache:
            _print_err("Chưa có kết quả search. Chạy: 3m search <tên>")
            sys.exit(1)
        idx = args.i - 1
        if idx < 0 or idx >= len(cache):
            _print_err(f"Index {args.i} nằm ngoài kết quả (1–{len(cache)})")
            sys.exit(1)
        slug = cache[idx]["slug"]
    else:
        _print_err("Thiếu đối số. Dùng: show <tên> hoặc show -i <số>")
        sys.exit(1)

    project = api_get(f"/project/{slug}")
    if not project:
        _print_err(f"Không tìm thấy project: {slug}")
        sys.exit(1)

    version = get_best_version(slug, profile)
    f_info  = get_primary_file(version) if version else None

    _header(project["title"], project.get("description", ""))

    _section("Thông tin chung")
    rows = [
        ("Slug",       f"{CYAN}{project['slug']}{RESET}"),
        ("Downloads",  f"{LIME}{fmt_num(project.get('downloads', 0))}{RESET}"),
        ("Followers",  f"{PINK}{fmt_num(project.get('followers', 0))}{RESET}"),
        ("License",    f"{SLATE}{project.get('license', {}).get('id', 'N/A')}{RESET}"),
        ("Categories", "  ".join(f"{PURPLE}#{c}{RESET}" for c in project.get("categories", []))),
        ("Loaders",    "  ".join(loader_badge(l) for l in project.get("loaders", []))),
        ("Source",     f"{BLUE}{project.get('source_url') or 'N/A'}{RESET}"),
    ]
    for k, v in rows:
        print(f"    {SLATE}{k:<12}{RESET}  {v}")

    _section(f"Phiên bản tốt nhất  ({profile['mc_version']} / {profile['loader']})")
    if version and f_info:
        vtype  = version.get("version_type", "?")
        vcolor = {"release": GREEN, "beta": YELLOW, "alpha": ORANGE}.get(vtype, SLATE)
        size_kb = f_info.get("size", 0) // 1024
        rows2 = [
            ("Version",  f"{vcolor}{version['version_number']}{RESET}  {dim('[' + vtype + ']')}"),
            ("File",     f"{CYAN}{f_info['filename']}{RESET}"),
            ("Size",     f"{GOLD}{size_kb:,} KB{RESET}"),
        ]
        for k, v in rows2:
            print(f"    {SLATE}{k:<12}{RESET}  {v}")
    else:
        _print_warn("Không có phiên bản phù hợp với profile hiện tại.")

    _section("Phiên bản Minecraft hỗ trợ")
    all_vers = sorted(project.get("game_versions", []), reverse=True)
    chunks = [all_vers[i:i+6] for i in range(0, min(len(all_vers), 18), 6)]
    for chunk in chunks:
        print("    " + "  ".join(f"{SKY}{v}{RESET}" for v in chunk))

    print(f"\n  {TEAL}🌐  https://modrinth.com/mod/{slug}{RESET}\n")

def cmd_profile(args):
    p = load_profile()
    _header("Profile hiện tại")
    if p:
        print(f"  {SLATE}Minecraft  {RESET}{BWHITE}{p['mc_version']}{RESET}")
        print(f"  {SLATE}Loader     {RESET}{loader_badge(p['loader'])}")
        print()
        meta = load_cache_meta()
        if meta and meta.get("query"):
            ts  = meta.get("time", 0)
            age = f"{int((time.time()-ts)//60)} phút trước" if ts else "?"
            print(f"  {SLATE}Cache cuối {RESET}{dim(repr(meta['query']) + '  (' + age + ')')}")
        print()
    else:
        _print_warn("Chưa có profile.")
        print(f"    {GOLD}VD cách set: 3m set-profile 1.21.1 fabric{RESET}\n")

def cmd_list(args):
    dest_dir = Path(os.getcwd())
    jars = sorted(dest_dir.glob("*.jar"))
    _header("Mod trong thư mục", str(dest_dir))
    if not jars:
        _print_warn("Không có file .jar nào ở đây.")
        print()
        return
    total_size = 0
    for i, j in enumerate(jars, 1):
        size_kb = j.stat().st_size // 1024
        total_size += j.stat().st_size
        mtime = datetime.fromtimestamp(j.stat().st_mtime).strftime("%d/%m/%y %H:%M")
        idx_col = f"{bg256(236)}{BYELLOW} {i:2d} {RESET}"
        print(f"  {idx_col}  {BWHITE}{j.name}{RESET}")
        print(f"       {SLATE}{size_kb:>6,} KB    {mtime}{RESET}")
    _divider(color=SLATE)
    print(f"  {dim(str(len(jars)) + ' file  ·  tổng ' + str(total_size//1024) + ' KB')}\n")
    print(f"  {dim('Dùng index với: 3m remove -i <index>')}\n")

def cmd_remove(args):
    dest_dir = Path(os.getcwd())
    jars = list(sorted(dest_dir.glob("*.jar")))
    if not jars:
        _print_err("Không có mod nào trong thư mục để gỡ.")
        if args.i is not None:
            print(f"  {dim('Bạn đang dùng index trỏ vào danh sách search, không thể thực hiện lệnh xóa.')}")
            print(f"  {dim('Lệnh xóa dành cho danh sách file .jar trên máy (xem bằng 3m list)')}")
        print()
        sys.exit(1)

    if args.all:
        if not args.confirm:
            count = len(jars)
            print(f"  {ROSE}Cảnh báo: Bạn sắp xóa {count} mod!{RESET}")
            print(f"  {dim('Gõ')} {CYAN}3m remove -a --confirm{RESET} {dim('để xác nhận')}")
            print()
            sys.exit(1)
        for j in jars:
            j.unlink()
        _print_ok(f"Đã gỡ {len(jars)} mod")
        print()
        return

    if args.i is not None:
        idx = args.i - 1
        if idx < 0 or idx >= len(jars):
            _print_err(f"Index {args.i} nằm ngoài (1–{len(jars)})")
            sys.exit(1)
        j = jars[idx]
        print(f"  {YELLOW}Xóa: {j.name}?{RESET}  {dim('[y/N]')}")
        confirm = input("  > ").strip().lower()
        if confirm != "y":
            print(f"  {dim('Đã hủy')}")
            print()
            return
        j.unlink()
        _print_ok(f"Đã gỡ: {j.name}")
        print()
        return

    if args.names:
        raw = " ".join(args.names)
        removed = []
        for name in raw.split(","):
            name = name.strip()
            if not name:
                continue
            matched = fuzzy_match(name, [j.stem for j in jars])
            if matched:
                print(f"  {YELLOW}Xóa: {matched}?{RESET}  {dim('[y/N]')}")
                confirm = input("  > ").strip().lower()
                if confirm != "y":
                    print(f"  {dim('Đã hủy')}")
                    continue
                for j in jars:
                    if j.stem == matched:
                        j.unlink()
                        removed.append(matched)
                        break
            else:
                _print_warn(f"Không tìm thấy mod gần với '{name}'")
        if removed:
            print()
            for m in removed:
                _print_ok(f"Đã gỡ: {m}")
        print()
        return

    _print_err("Dùng: remove <tên> hoặc remove -i <index>")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════════

def print_help():
    banner = f"""
{MINT}  ┌─────────────────────────────────────────────────────┐{RESET}
{MINT}  │{RESET}  {BWHITE}3m{RESET}  {SLATE}—{RESET}  {BCYAN}Minecraft Mod Manager{RESET}  {dim('v' + VERSION)}             {MINT}│{RESET}
{MINT}  │{RESET}  {dim('Tải mod từ Modrinth · Nhanh · Nhẹ · Không deps')}    {MINT}│{RESET}
{MINT}  └─────────────────────────────────────────────────────┘{RESET}
"""
    print(banner)

    sections = [
        ("LỆNH", [
            (f"{BYELLOW}set-profile{RESET} {CYAN}<mc_version> <loader>{RESET}",
             "Đặt phiên bản Minecraft và mod loader.",
             [f"{dim('Loader hỗ trợ:')}  fabric  forge  quilt  neoforge",
              f"{GOLD}3m set-profile 1.21.1 fabric{RESET}"]),

            (f"{BYELLOW}search{RESET} {CYAN}<từ khóa>{RESET}  {dim('[-n <số>]')}",
             "Tìm mod. Kết quả được đánh số để dùng với get/show.",
             [f"{GOLD}3m search sodium{RESET}",
              f"{GOLD}3m search \"performance optimization\" -n 15{RESET}"]),

(f"{BYELLOW}get{RESET} {CYAN}<tên>{RESET}  {SLATE}|{RESET}  {BYELLOW}get{RESET} {CYAN}-i <index>{RESET}",
              f"Tải mod về thư mục {ITALIC}hiện tại{RESET}. Tự động cài phụ thuộc. Dùng --no-deps để bỏ qua.",
              [f"{GOLD}3m get sodium{RESET}",
               f"{GOLD}3m get -i 3{RESET}",
               f"{GOLD}3m get --no-deps sodium, lithium{RESET}",
               f"{GOLD}3m get sodium, lithium, iris, immediately fast{RESET}"]),

            (f"{BYELLOW}show{RESET} {CYAN}<tên>{RESET}  {SLATE}|{RESET}  {BYELLOW}show{RESET} {CYAN}-i <index>{RESET}",
             "Xem thông tin chi tiết: downloads, versions, file size...",
             [f"{GOLD}3m show sodium{RESET}",
              f"{GOLD}3m show -i 1{RESET}"]),

            (f"{BYELLOW}list{RESET}",
             "Liệt kê tất cả .jar trong thư mục hiện tại.",
             [f"{GOLD}3m list{RESET}"]),

            (f"{BYELLOW}remove{RESET} {CYAN}<tên>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove{RESET} {CYAN}-i <index>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove -a{RESET}",
             "Gỡ mod. Dùng -a để xóa toàn bộ. Fuzzy match khi gỡ theo tên.",
             [f"{GOLD}3m remove sodium{RESET}",
              f"{GOLD}3m remove -i 1{RESET}",
              f"{GOLD}3m remove -a{RESET}",
              f"{GOLD}3m remove sodium, lithium{RESET}"]),

            (f"{BYELLOW}profile{RESET}",
             "Xem profile và thông tin cache hiện tại.",
             [f"{GOLD}3m profile{RESET}"]),
        ]),
        ("GHI CHÚ", None),
        ("WORKFLOW NHANH", None),
    ]

    # LỆNH
    _divider("═", 60, MINT)
    print(f"  {BWHITE}LỆNH{RESET}")
    _divider("═", 60, MINT)
    for sig, desc, examples in sections[0][1]:
        print(f"\n  {sig}")
        print(f"    {desc}")
        for ex in examples:
            print(f"    {SLATE}›{RESET}  {ex}")
    print()

    # GHI CHÚ
    _divider("─", 60, SLATE)
    print(f"  {BWHITE}GHI CHÚ{RESET}\n")
    notes = [
        f"Mod luôn tải vào {ITALIC}thư mục hiện tại{RESET} khi chạy {CYAN}get{RESET}.",
        f"{CYAN}get <tên>{RESET} tự search rồi lấy hit đầu tiên. Để chắc hơn, dùng {CYAN}search{RESET} → {CYAN}get -i{RESET}.",
        f"Dấu phẩy tách mod, space là phần của tên: {GOLD}get immediately fast, sodium{RESET}",
        f"Profile lưu tại {dim('.profile trong thư mục hiện tại')} · Cache tại {dim('~/.config/3m/last_search.json')}",
        f"Không cần đăng nhập hay API key. Rate limit: 300 req/phút.",
    ]
    for note in notes:
        print(f"  {MINT}▪{RESET}  {note}")
    print()

    # WORKFLOW
    _divider("─", 60, SLATE)
    print(f"  {BWHITE}WORKFLOW NHANH{RESET}\n")
    steps = [
        ("# Lần đầu — đặt profile",
         ["3m set-profile 1.21.1 fabric"]),
        ("# Tải một đống optimization mods",
         ["cd ~/minecraft/mods",
          "3m get sodium, lithium, iris, immediately fast, ferritecore, entityculling"]),
        ("# Tìm rồi xem trước khi tải",
         ["3m search \"chunk loading\"",
          "3m show -i 1",
          "3m get -i 1"]),
        ("# Kiểm tra đã tải gì",
         ["3m list"]),
    ]
    for comment, cmds in steps:
        print(f"  {SLATE}{comment}{RESET}")
        for cmd in cmds:
            print(f"  {GOLD}{cmd}{RESET}")
        print()

    _divider("═", 60, MINT)
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
    sp.add_argument("--confirm", action="store_true")
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
import sys
import time
from pathlib import Path

from mmmcore.core import (
    require_profile, load_profile, save_profile,
    load_metadata, save_metadata, upsert_mod, remove_mod_from_metadata,
    get_dependents_recursive, is_orphaned,
    save_cache, load_cache, load_cache_meta,
    search_mods, get_project, get_best_version, get_primary_file,
    get_slug_from_name, get_required_dependencies, install_mod,
    download_file,
    validate_loader, validate_mc_version, fuzzy_match,
    normalize_slug, fmt_num,
    KNOWN_LOADERS, LOADER_COLORS, API_HINTS,
    ProfileNotFoundError, ModNotFoundError, ValidationError, MMMError,
)
from mmmcore.core.state import _now_iso
from .display import (
    RESET, BOLD, DIM, ITALIC,
    RED, GREEN, YELLOW, BLUE, CYAN, WHITE,
    BRED, BGREEN, BYELLOW, BBLUE, BCYAN, BWHITE,
    MINT, GOLD, PURPLE, ORANGE, PINK, SLATE, TEAL, LIME, ROSE, SKY, INDIGO,
    rst, bold, dim, italic, color, fg, bg,
    err, ok, info, warn, step, skip, dep_tag,
    divider, header, section, loader_badge,
    render_markdown, print_search_results,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_profile():
    try:
        return require_profile()
    except ProfileNotFoundError as e:
        err(str(e))
        print(f"\n  {SKY}💡{RESET}  {BWHITE}This should be your Minecraft mods folder.{RESET}")
        print(f"  {SKY}💡{RESET}  Run:  {GOLD}mmm set-profile <mc_version> <loader>{RESET}")
        print(f"       {dim('Example: mmm set-profile 1.21.1 fabric')}")
        print(f"  {SKY}💡{RESET}  {dim('Or move to your mods folder and set the profile there.')}{RESET}\n")
        sys.exit(1)

def _install_status_callback(event, data):
    if event == "resolving":
        pass
    elif event == "found":
        is_dep = data.get("is_dep", False)
        if is_dep:
            dep_tag(data.get("parent_slug", ""))
        slug = data.get("slug", "")
        title = data.get("title", slug)
        step(f"{BWHITE}{slug}{RESET}" + (f"  {dim('(via ' + data.get('parent_slug', '') + ')')}" if is_dep else ""))
        name = data.get("name", "")
        if slug.lower() != normalize_slug(name) and name:
            print(f"       {TEAL}↳ {title}{RESET}  {dim(slug)}")
    elif event == "downloading":
        pass
    elif event == "download_progress":
        pct = data.get("pct", 0)
        downloaded = data.get("downloaded", 0)
        total = data.get("total", 0)
        speed = data.get("speed", 0)
        if total:
            filled = pct // 4
            bar = f"{MINT}{'█' * filled}{SLATE}{'░' * (25 - filled)}{RESET}"
            done = f"{GOLD}{downloaded//1024:,}{RESET}KB"
            tot_s = f"{SLATE}/{total//1024:,}KB{RESET}"
            spd = f"{CYAN}{speed/1024:5.0f}KB/s{RESET}"
            pct_s = f"{BYELLOW}{pct:3d}%{RESET}"
            print(f"\r    {bar} {pct_s}  {done}{tot_s}  {spd} ", end="", flush=True)
    elif event == "skip_exists":
        title  = data.get("title", data.get("slug", ""))
        fname  = data.get("filename", "")
        is_dep = data.get("is_dependency", False)
        req_by = data.get("required_by", [])
        if is_dep and req_by:
            skip(f"Cannot get {BWHITE}{title}{RESET} — {fname} already exists {dim('(dependency of ' + ', '.join(req_by) + ')')}")
        elif is_dep:
            skip(f"Cannot get {BWHITE}{title}{RESET} — {fname} already exists {dim('(dependency mod)')}")
        else:
            skip(f"Cannot get {BWHITE}{title}{RESET} — {fname} already exists {dim('(requested mod)')}")
    elif event == "download_done":
        ok(f"Installed {BWHITE}{data.get('title', '')}{RESET}  {dim(data.get('filename', ''))}")
    elif event == "dependency":
        pass
    elif event == "already_seen":
        slug   = data.get("slug", "")
        parent = data.get("parent_slug", "")
        if parent:
            skip(f"{BWHITE}{slug}{RESET} — already installed {dim('(dependency of ' + parent + ')')}")
        else:
            skip(f"{BWHITE}{slug}{RESET} — already installed")

def _show_version_line(version, file_info, data_ver):
    vtype  = version.get("version_type", "?")
    vcolor = {"release": GREEN, "beta": YELLOW, "alpha": ORANGE}.get(vtype, SLATE)
    sha512 = file_info.get("hashes", {}).get("sha512", "")
    rows = [
        ("Version",  f"{vcolor}{version['version_number']}{RESET}  {dim('[' + vtype + ']')}"),
        ("File",     f"{CYAN}{file_info['filename']}{RESET}"),
        ("Size",     f"{GOLD}{file_info.get('size', 0) // 1024:,} KB{RESET}"),
        ("SHA-512",  f"{dim(sha512[:24] + '...' if sha512 else 'N/A')}"),
    ]
    for k, v in rows:
        print(f"    {SLATE}{k:<12}{RESET}  {v}")

# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_set_profile(args):
    mc     = args.mc_version
    loader = args.loader.lower()
    try:
        validate_loader(loader)
        validate_mc_version(mc)
    except ValidationError as e:
        err(str(e))
        sys.exit(1)
    except MMMError as e:
        err(str(e))
        sys.exit(1)

    save_profile(mc, loader)
    header("Profile updated")
    print(f"  {SLATE}Minecraft  {RESET}{BWHITE}{mc}{RESET}")
    print(f"  {SLATE}Loader     {RESET}{loader_badge(loader)}")
    if loader in API_HINTS:
        slug, label = API_HINTS[loader]
        print(f"\n  {SKY}💡{RESET}  {dim('Many mods need')} {BWHITE}{label}{RESET}{dim(' but may not declare it as a dependency.')}")
        print(f"       {GOLD}mmm get {slug}{RESET}")
    print()

def cmd_search(args):
    profile = _require_profile()
    query   = " ".join(args.query)
    limit   = args.limit or 10
    no_filter = getattr(args, "no_filter", False)

    mc_version = profile["mc_version"]
    loader     = profile["loader"]

    if getattr(args, "filter_version", None):
        mc_version = args.filter_version
        try:
            validate_mc_version(mc_version)
        except ValidationError as e:
            err(str(e))
            sys.exit(1)
    if getattr(args, "filter_loader", None):
        loader = args.filter_loader.lower()
        try:
            validate_loader(loader)
        except ValidationError as e:
            err(str(e))
            sys.exit(1)

    label = ("No filters" if no_filter
             else f"[{mc_version} / {loader}]" if mc_version and loader
             else f"[{mc_version or 'any version'} / {loader or 'any loader'}]")
    info(f"Searching {BWHITE}'{query}'{RESET}  {dim(label)}")
    try:
        results = search_mods(query, mc_version=mc_version, loader=loader, no_filter=no_filter, limit=limit)
    except MMMError as e:
        err(str(e))
        sys.exit(1)
    save_cache(results, query)
    print_search_results(results, query, mc_version=mc_version, loader=loader, no_filter=no_filter)

def cmd_get(args):
    profile = _require_profile()
    dest_dir = Path.cwd()
    metadata = load_metadata()
    metadata["mc_version"] = profile["mc_version"]
    metadata["loader"]     = profile["loader"]

    if args.i is not None:
        cache = load_cache()
        if not cache:
            err("No search results cached. Run: mmm search <name>")
            sys.exit(1)
        idx = args.i - 1
        if idx < 0 or idx >= len(cache):
            err(f"Index {args.i} out of range (1–{len(cache)})")
            sys.exit(1)
        slug = cache[idx]["slug"]
        header("Installing mod", str(dest_dir))
        print(f"  {SLATE}[1/1]{RESET}  ", end="")
        try:
            install_mod(slug, profile, dest_dir, metadata,
                       status_callback=_install_status_callback)
        except MMMError as e:
            err(str(e))
        save_metadata(metadata)
        print()
        return

    mods = None
    file_label = None
    if getattr(args, "f", None):
        fpath = Path(args.f)
        if not fpath.exists():
            err(f"File not found: {args.f}")
            sys.exit(1)
        raw   = fpath.read_text()
        mods  = [s.strip() for s in raw.replace(",", "\n").split("\n") if s.strip()]
        file_label = fpath.name
    elif args.names:
        raw  = " ".join(args.names)
        mods = [s.strip() for s in raw.split(",") if s.strip()]

    if mods is None:
        err("Usage: get <name>  or  get -i <index>  or  get -f <file>")
        sys.exit(1)

    if file_label:
        header("Installing mods from file", file_label)
    else:
        header(f"Installing {len(mods)} mod{'s' if len(mods) != 1 else ''}",
               str(dest_dir))

    seen        = set()
    installed_list = []
    skipped_list   = []
    fail_list      = []
    install_map    = []

    for idx, name in enumerate(mods, 1):
        print(f"  {SLATE}[{idx}/{len(mods)}]{RESET}  ", end="")
        try:
            result = install_mod(name, profile, dest_dir, metadata, seen=seen,
                                status_callback=_install_status_callback)
            if isinstance(result, tuple):
                slug, action = result
            else:
                slug, action = result, "installed"
            install_map.append((name, slug, action))
            if action == "installed":
                installed_list.append((name, slug))
            elif action in ("skipped", "already_seen"):
                skipped_list.append((name, slug))
            else:
                fail_list.append(name)
        except MMMError as e:
            err(str(e))
            fail_list.append(name)
        print()

    # Ensure user-requested mods are marked as requested=True
    # even if a prior mod already installed them as dependencies
    mods_meta = metadata.get("mods", {})
    for _name, slug, _action in install_map:
        if slug in mods_meta:
            mods_meta[slug]["requested"] = True

    save_metadata(metadata)

    divider(c=MINT)
    parts = []
    if installed_list:
        parts.append(f"{LIME}✔ {len(installed_list)} installed{RESET}")
    if skipped_list:
        parts.append(f"{CYAN}⊘ {len(skipped_list)} already exist{RESET}")
    if fail_list:
        parts.append(f"{ROSE}✗ {len(fail_list)} failed{RESET}")
    if parts:
        print(f"  {'    '.join(parts)}")
    print(f"  {dim('Directory: ' + str(dest_dir))}\n")

    if len(mods) > 1:
        print(f"  {BYELLOW}Installation map:{RESET}")
        max_len = max(len(m) for m in mods)
        for i, req in enumerate(mods, 1):
            found = next(((s, a) for n, s, a in install_map if n == req), None)
            if found:
                slug, action = found
                if action == "installed":
                    print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {LIME}{slug}{RESET}")
                elif action == "skipped":
                    print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {CYAN}{slug}{RESET}  {dim('(already exists)')}")
                else:
                    print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {CYAN}{slug}{RESET}  {dim('(already installed)')}")
            else:
                print(f"    {dim(str(i) + '.')}  {req:<{max_len}}  →  {ROSE}(failed){RESET}")
        print()

def cmd_show(args):
    profile = _require_profile()
    if args.names:
        raw  = " ".join(args.names)
        try:
            slug, _ = get_slug_from_name(raw.strip(), profile)
        except MMMError as e:
            err(str(e))
            sys.exit(1)
        if not slug:
            err(f"Mod not found: {raw}")
            sys.exit(1)
    elif args.i is not None:
        metadata = load_metadata()
        mods = metadata.get("mods", {})
        if mods:
            req_list = [(s, m) for s, m in mods.items() if m.get("requested")]
            dep_list = [(s, m) for s, m in mods.items() if not m.get("requested")]
            ordered  = req_list + dep_list
            idx = args.i - 1
            if idx < 0 or idx >= len(ordered):
                err(f"Index {args.i} out of range (1–{len(ordered)})")
                sys.exit(1)
            slug = ordered[idx][0]
        else:
            cache = load_cache()
            if not cache:
                err("No search results cached. Run: mmm search <name>")
                sys.exit(1)
            idx = args.i - 1
            if idx < 0 or idx >= len(cache):
                err(f"Index {args.i} out of range (1–{len(cache)})")
                sys.exit(1)
            slug = cache[idx]["slug"]
    else:
        err("Usage: show <name>  or  show -i <index>")
        sys.exit(1)

    try:
        project = get_project(slug)
    except MMMError as e:
        err(str(e))
        sys.exit(1)
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
        _show_version_line(version, f_info, None)
        deps = get_required_dependencies(slug, profile)
        if deps:
            section("Required dependencies")
            for dep_slug, _ in deps:
                dep_proj = get_project(dep_slug)
                dep_title = dep_proj.get("title", dep_slug) if dep_proj else dep_slug
                print(f"    {INDIGO}·{RESET}  {BWHITE}{dep_title}{RESET}  {dim(dep_slug)}")
    else:
        warn("No version matching current profile.")

    body = project.get("body", "")
    if body:
        section("Description")
        print()
        rendered = render_markdown(body)
        for line in rendered.split("\n"):
            print(f"  {line}")
        print()

    section("Supported Minecraft versions")
    all_vers = sorted(project.get("game_versions", []), reverse=True)
    chunks = [all_vers[i:i+8] for i in range(0, min(len(all_vers), 24), 8)]
    for chunk in chunks:
        print("    " + "  ".join(f"{SKY}{v}{RESET}" for v in chunk))

    print(f"\n  {TEAL}🌐  https://modrinth.com/mod/{slug}{RESET}\n")

def cmd_list(args):
    profile = _require_profile()
    dest_dir = Path.cwd()
    metadata = load_metadata()
    mods     = metadata.get("mods", {})

    header("Installed mods", str(dest_dir))

    if not mods:
        warn("No mods tracked in metadata.")
        jars = sorted(dest_dir.glob("*.jar"))
        if jars:
            info(f"Found {len(jars)} .jar files not tracked by mmm.")
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

    slug, label = API_HINTS.get(profile["loader"], (None, None))
    if slug and slug not in mods:
        print(f"  {SKY}💡{RESET}  {dim('You have')} {BWHITE}{profile['loader'].capitalize()}{RESET}{dim(' mods but')} {BWHITE}{label}{RESET}{dim(' is missing.')}")
        print(f"       {GOLD}mmm get {slug}{RESET}\n")

    print(f"  {dim('Remove by name: mmm remove <name>    Remove by index: mmm remove -i <n>')}\n")

def cmd_remove(args):
    _require_profile()
    dest_dir = Path.cwd()
    metadata = load_metadata()
    mods     = metadata.get("mods", {})

    if not mods:
        err("No mods in metadata.")
        print()
        sys.exit(1)

    def _do_remove(slug):
        entry    = mods.get(slug, {})
        title    = entry.get("title", slug)
        file_name = entry.get("file", "")
        fpath    = dest_dir / file_name if file_name else None

        remove_mod_from_metadata(metadata, slug)

        if fpath and fpath.exists():
            fpath.unlink()
            ok(f"Removed: {title}  {dim(file_name)}")
        else:
            ok(f"Removed from metadata: {title}  {dim('(file not found)')}")

    def _confirm_cascade(slug):
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
        save_metadata(metadata)
        ok(f"Removed all {count} mod(s).")
        print()
        return

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
        save_metadata(metadata)
        print()
        return

    if args.names:
        raw   = " ".join(args.names)
        names = [n.strip() for n in raw.split(",") if n.strip()]
        for name in names:
            slug = name if name in mods else None
            if not slug:
                slug = next((s for s, m in mods.items()
                             if m.get("title", "").lower() == name.lower()), None)
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
        save_metadata(metadata)
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
        print(f"\n  {SKY}💡{RESET}  {BWHITE}This should be your Minecraft mods folder.{RESET}")
        print(f"  {SKY}💡{RESET}  Run:  {GOLD}mmm set-profile <mc_version> <loader>{RESET}")
        print(f"       {dim('Example: mmm set-profile 1.21.1 fabric')}")
        print(f"  {SKY}💡{RESET}  {dim('Or move to your mods folder and set the profile there.')}{RESET}\n")

def cmd_autoremove(args):
    _require_profile()
    dest_dir = Path.cwd()
    metadata = load_metadata()
    mods = metadata.get("mods", {})

    if not mods:
        warn("No mods in metadata.")
        print()
        return

    orphaned = [s for s in mods if is_orphaned(s, mods)]

    if not orphaned:
        ok("No orphaned dependencies found.")
        print()
        return

    header(f"Removing {len(orphaned)} orphaned dep{'s' if len(orphaned) != 1 else ''}")

    removed = 0
    for slug in orphaned:
        entry = mods.get(slug, {})
        title = entry.get("title", slug)
        fpath = dest_dir / entry["file"] if entry.get("file") else None

        remove_mod_from_metadata(metadata, slug)

        if fpath and fpath.exists():
            fpath.unlink()
            ok(f"{title}  {dim(fpath.name)}")
        else:
            ok(f"{title}  {dim('(no file)')}")
        removed += 1

    save_metadata(metadata)
    print(f"  {dim(f'{removed} orphaned dep(s) removed.')}\n")


def cmd_update(args):
    profile = _require_profile()
    dest_dir = Path.cwd()
    metadata = load_metadata()
    metadata["mc_version"] = profile["mc_version"]
    metadata["loader"] = profile["loader"]
    mods = metadata.get("mods", {})

    if not mods:
        err("No mods in metadata.")
        print()
        return

    if args.names:
        raw = " ".join(args.names)
        names = [s.strip() for s in raw.split(",") if s.strip()]
        slugs = []
        for name in names:
            slug = name if name in mods else None
            if not slug:
                slug = next((s for s, m in mods.items()
                             if m.get("title", "").lower() == name.lower()), None)
            if not slug:
                matched = fuzzy_match(name, list(mods.keys()))
                if matched:
                    slug = matched
            if not slug:
                warn(f"No installed mod found close to '{name}'")
                continue
            slugs.append(slug)
        if not slugs:
            print()
            return
    else:
        slugs = list(mods.keys())

    if not slugs:
        warn("No mods to update.")
        print()
        return

    action = "Would update" if args.dry_run else "Checking updates for"
    header(f"{action} {len(slugs)} mod{'s' if len(slugs) != 1 else ''}", str(dest_dir))

    updated = []
    up_to_date = []
    failed = []
    new_deps = []

    for i, slug in enumerate(slugs, 1):
        entry = mods.get(slug, {})
        current_vid = entry.get("version_id", "")
        current_ver = entry.get("version", "?")
        title = entry.get("title", slug)

        print(f"  {SLATE}[{i}/{len(slugs)}]{RESET}  {BWHITE}{title}{RESET}  "
              f"{dim('v' + current_ver)}", end="", flush=True)

        try:
            version = get_best_version(slug, profile)
            if not version:
                print(f"  {ROSE}no compatible version{RESET}")
                failed.append(slug)
                continue

            latest_vid = version.get("id", "")
            latest_ver = version.get("version_number", "?")

            if latest_vid == current_vid:
                print(f"  {GREEN}✓ up-to-date{RESET}")
                up_to_date.append(slug)
                continue

            print(f"  {YELLOW}v{current_ver} → v{latest_ver}{RESET}")

            if args.dry_run:
                continue

            file_info = get_primary_file(version)
            if not file_info:
                print(f"       {ROSE}no downloadable file{RESET}")
                failed.append(slug)
                continue

            url = file_info["url"]
            filename = file_info["filename"]
            sha512 = file_info.get("hashes", {}).get("sha512", "")

            old_file = entry.get("file", "")
            if old_file and (dest_dir / old_file).exists():
                (dest_dir / old_file).unlink()

            dest = dest_dir / filename

            def _upd_progress(pct, downloaded, total, speed, elapsed):
                if total:
                    filled = pct // 4
                    bar = f"{MINT}{'█' * filled}{SLATE}{'░' * (25 - filled)}{RESET}"
                    done = f"{GOLD}{downloaded//1024:,}{RESET}KB"
                    tot_s = f"{SLATE}/{total//1024:,}KB{RESET}"
                    spd = f"{CYAN}{speed/1024:5.0f}KB/s{RESET}"
                    pct_s = f"{BYELLOW}{pct:3d}%{RESET}"
                    print(f"\r       {bar} {pct_s}  {done}{tot_s}  {spd}  ", end="", flush=True)

            download_file(url, dest, sha512_expected=sha512 or None,
                          progress_callback=_upd_progress)

            project = get_project(slug) or {}
            upsert_mod(metadata, slug,
                title=title,
                description=entry.get("description", ""),
                version_id=latest_vid,
                version=latest_ver,
                version_type=version.get("version_type", "release"),
                file=filename,
                sha512=sha512,
                size_bytes=file_info.get("size", 0),
                project_id=project.get("id", entry.get("project_id", "")),
                source_url=project.get("source_url") or project.get("issues_url") or "",
                license=(project.get("license") or {}).get("id", ""),
                categories=project.get("categories", []),
                downloads=project.get("downloads", 0),
                followers=project.get("followers", 0),
                icon_url=project.get("icon_url", ""),
                gallery=project.get("gallery", []),
                installed_at=_now_iso(),
            )

            print(f"\r       {GREEN}✔{RESET}  {dim(filename)}  ")

            # Re-sync deps from the new version
            deps = get_required_dependencies(slug, profile)
            for dep_slug, _dep_version_id in deps:
                if dep_slug in metadata.get("mods", {}):
                    upsert_mod(metadata, dep_slug, required_by=[slug])
                else:
                    new_deps.append(dep_slug)
                    print(f"       {CYAN}→ new dep:{RESET}  {BWHITE}{dep_slug}{RESET}")
                    seen = set(slugs + [s for s, _, _ in updated])
                    try:
                        install_mod(dep_slug, profile, dest_dir, metadata,
                                    parent_slug=slug, seen=seen,
                                    status_callback=_install_status_callback)
                    except MMMError as e:
                        print(f"       {ROSE}{e}{RESET}")
                    print()

            updated.append((slug, current_ver, latest_ver))

        except MMMError as e:
            print(f"  {ROSE}{e}{RESET}")
            failed.append(slug)

    save_metadata(metadata)

    if updated or up_to_date or failed or new_deps:
        print()
        divider(c=MINT)
        if updated:
            print(f"  {LIME}✔ {len(updated)} updated:{RESET}")
            for slug, old_v, new_v in updated:
                e = metadata.get("mods", {}).get(slug, {})
                print(f"       {BWHITE}{e.get('title', slug)}{RESET}  {dim(f'{old_v} → {new_v}')}")
        if up_to_date:
            print(f"  {CYAN}✓ {len(up_to_date)} up-to-date{RESET}")
        if new_deps:
            print(f"  {TEAL}✦ {len(new_deps)} new dep(s) auto-installed:{RESET}")
            for ds in new_deps:
                e = metadata.get("mods", {}).get(ds, {})
                print(f"       {BWHITE}{e.get('title', ds)}{RESET}  {dim(ds)}")
        if failed:
            print(f"  {ROSE}✗ {len(failed)} failed:{RESET} {', '.join(failed)}")
        print()
        return

    if args.names:
        raw = " ".join(args.names)
        names = [s.strip() for s in raw.split(",") if s.strip()]
        slugs = []
        for name in names:
            slug = name if name in mods else None
            if not slug:
                slug = next((s for s, m in mods.items()
                             if m.get("title", "").lower() == name.lower()), None)
            if not slug:
                matched = fuzzy_match(name, list(mods.keys()))
                if matched:
                    slug = matched
            if not slug:
                warn(f"No installed mod found close to '{name}'")
                continue
            slugs.append(slug)
        if not slugs:
            print()
            return
    elif args.all:
        slugs = list(mods.keys())
    else:
        slugs = [s for s, m in mods.items() if m.get("requested")]

    if not slugs:
        warn("No mods to update.")
        print()
        return

    action = "Would update" if args.dry_run else "Checking updates for"
    header(f"{action} {len(slugs)} mod{'s' if len(slugs) != 1 else ''}", str(dest_dir))

    updated = []
    up_to_date = []
    failed = []

    for i, slug in enumerate(slugs, 1):
        entry = mods.get(slug, {})
        current_vid = entry.get("version_id", "")
        current_ver = entry.get("version", "?")
        title = entry.get("title", slug)

        print(f"  {SLATE}[{i}/{len(slugs)}]{RESET}  {BWHITE}{title}{RESET}  "
              f"{dim('v' + current_ver)}", end="", flush=True)

        try:
            version = get_best_version(slug, profile)
            if not version:
                print(f"  {ROSE}no compatible version{RESET}")
                failed.append(slug)
                continue

            latest_vid = version.get("id", "")
            latest_ver = version.get("version_number", "?")

            if latest_vid == current_vid:
                print(f"  {GREEN}✓ up-to-date{RESET}")
                up_to_date.append(slug)
                continue

            print(f"  {YELLOW}v{current_ver} → v{latest_ver}{RESET}")

            if args.dry_run:
                continue

            file_info = get_primary_file(version)
            if not file_info:
                print(f"       {ROSE}no downloadable file{RESET}")
                failed.append(slug)
                continue

            url = file_info["url"]
            filename = file_info["filename"]
            sha512 = file_info.get("hashes", {}).get("sha512", "")

            old_file = entry.get("file", "")
            if old_file and (dest_dir / old_file).exists():
                (dest_dir / old_file).unlink()

            dest = dest_dir / filename

            def _upd_progress(pct, downloaded, total, speed, elapsed):
                if total:
                    filled = pct // 4
                    bar = f"{MINT}{'█' * filled}{SLATE}{'░' * (25 - filled)}{RESET}"
                    done = f"{GOLD}{downloaded//1024:,}{RESET}KB"
                    tot_s = f"{SLATE}/{total//1024:,}KB{RESET}"
                    spd = f"{CYAN}{speed/1024:5.0f}KB/s{RESET}"
                    pct_s = f"{BYELLOW}{pct:3d}%{RESET}"
                    print(f"\r       {bar} {pct_s}  {done}{tot_s}  {spd}  ", end="", flush=True)

            download_file(url, dest, sha512_expected=sha512 or None,
                          progress_callback=_upd_progress)

            project = get_project(slug) or {}
            upsert_mod(metadata, slug,
                title=title,
                description=entry.get("description", ""),
                version_id=latest_vid,
                version=latest_ver,
                version_type=version.get("version_type", "release"),
                file=filename,
                sha512=sha512,
                size_bytes=file_info.get("size", 0),
                project_id=project.get("id", entry.get("project_id", "")),
                source_url=project.get("source_url") or project.get("issues_url") or "",
                license=(project.get("license") or {}).get("id", ""),
                categories=project.get("categories", []),
                downloads=project.get("downloads", 0),
                followers=project.get("followers", 0),
                icon_url=project.get("icon_url", ""),
                gallery=project.get("gallery", []),
                installed_at=_now_iso(),
            )

            print(f"\r       {GREEN}✔{RESET}  {dim(filename)}  ")
            updated.append((slug, current_ver, latest_ver))

        except MMMError as e:
            print(f"  {ROSE}{e}{RESET}")
            failed.append(slug)

    save_metadata(metadata)

    if updated or up_to_date or failed:
        print()
        divider(c=MINT)
        if updated:
            print(f"  {LIME}✔ {len(updated)} updated:{RESET}")
            for slug, old_v, new_v in updated:
                e = mods.get(slug, {})
                print(f"       {BWHITE}{e.get('title', slug)}{RESET}  {dim(f'{old_v} → {new_v}')}")
        if up_to_date:
            print(f"  {CYAN}✓ {len(up_to_date)} up-to-date{RESET}")
        if failed:
            print(f"  {ROSE}✗ {len(failed)} failed:{RESET} {', '.join(failed)}")
        print()

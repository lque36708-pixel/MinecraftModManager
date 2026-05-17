from .exceptions import ModNotFoundError
from .api import (
    get_slug_from_name, get_best_version, get_primary_file,
    get_project, get_required_dependencies, download_file,
)
from .state import upsert_mod, _now_iso

def install_mod(name, profile, dest_dir, metadata, parent_slug=None, seen=None, status_callback=None):
    if seen is None:
        seen = set()

    if status_callback:
        status_callback("resolving", {"name": name})

    slug, hit = get_slug_from_name(name, profile)
    if not slug:
        raise ModNotFoundError(name)

    if slug in seen:
        if status_callback:
            status_callback("already_seen", {"slug": slug, "parent_slug": parent_slug})
        return slug, "already_seen"
    seen.add(slug)

    is_dep = parent_slug is not None
    if status_callback:
        status_callback("found", {
            "slug": slug,
            "title": hit.get("title", slug) if hit else slug,
            "description": hit.get("description", "") if hit else "",
            "is_dep": is_dep,
            "parent_slug": parent_slug,
        })

    version = get_best_version(slug, profile)
    if not version:
        raise ModNotFoundError(
            f"No version available for {profile['mc_version']}/{profile['loader']}: {slug}"
        )

    file_info = get_primary_file(version)
    if not file_info:
        raise ModNotFoundError(f"No downloadable file found for {slug}")

    url      = file_info["url"]
    filename = file_info["filename"]
    sha512   = file_info.get("hashes", {}).get("sha512", "")
    dest     = dest_dir / filename

    vnum  = version.get("version_number", "?")
    vtype = version.get("version_type", "release")

    project = get_project(slug) or {}

    if dest.exists():
        entry = metadata.get("mods", {}).get(slug, {})
        is_dep_entry = not entry.get("requested", True) if entry else is_dep
        if status_callback:
            status_callback("skip_exists", {
                "slug": slug, "filename": filename,
                "is_dependency": is_dep_entry,
                "required_by": entry.get("required_by", []),
                "title": project.get("title") or (hit.get("title", slug) if hit else slug),
            })
        action = "skipped"
    else:
        if status_callback:
            status_callback("downloading", {
                "slug": slug, "filename": filename,
                "url": url, "sha512": sha512,
                "size": file_info.get("size", 0),
            })

        download_file(url, dest, sha512_expected=sha512 or None,
                      progress_callback=_make_progress_callback(slug, status_callback))

        if status_callback:
            title = project.get("title") or (hit.get("title", slug) if hit else slug)
            status_callback("download_done", {
                "slug": slug, "filename": filename, "title": title,
            })
        action = "installed"

    upsert_mod(metadata, slug,
        title        = project.get("title") or (hit.get("title", slug) if hit else slug),
        description  = project.get("description") or (hit.get("description", "") if hit else ""),
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
        icon_url     = project.get("icon_url", ""),
        gallery      = project.get("gallery", []),
        requested    = not is_dep,
        required_by  = [parent_slug] if parent_slug else [],
        installed_at = _now_iso(),
    )

    deps = get_required_dependencies(slug, profile)
    for dep_slug, _dep_version_id in deps:
        upsert_mod(metadata, dep_slug, required_by=[slug])

        if dep_slug in seen:
            continue

        if status_callback:
            status_callback("dependency", {"slug": dep_slug, "parent_slug": slug})

        install_mod(dep_slug, profile, dest_dir, metadata,
                    parent_slug=slug, seen=seen, status_callback=status_callback)

    return slug, action


def _make_progress_callback(slug, outer_cb):
    if outer_cb is None:
        return None
    def inner(pct, downloaded, total, speed, elapsed):
        outer_cb("download_progress", {
            "slug": slug, "pct": pct,
            "downloaded": downloaded, "total": total,
            "speed": speed, "elapsed": elapsed,
        })
    return inner

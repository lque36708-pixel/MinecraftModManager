import sys
import argparse

from mmmcore.core.api import VERSION, KNOWN_LOADERS, API_HINTS, API_BASE
from mmmcore.core.state import profile_path, metadata_path
from mmmcore.core.exceptions import MMMError
from mmmcore.cli.display import (
    RESET, BOLD, DIM, ITALIC,
    RED, GREEN, YELLOW, BLUE, CYAN, WHITE,
    BRED, BGREEN, BYELLOW, BBLUE, BCYAN, BWHITE,
    MINT, GOLD, PURPLE, ORANGE, PINK, SLATE, TEAL, LIME, ROSE, SKY, INDIGO,
    rst, bold, dim, italic, color, fg, bg,
    err, ok, info, warn, step, skip, dep_tag,
    divider, header, section, loader_badge, fmt_num,
    print_search_results, render_markdown,
)
from mmmcore.cli.commands import (
    cmd_set_profile, cmd_search, cmd_get, cmd_show,
    cmd_list, cmd_remove, cmd_profile, cmd_autoremove,
)

def print_help():
    banner = f"""
{MINT}  ┌──────────────────────────────────────────────────────┐{RESET}
{MINT}  │{RESET}  {BWHITE}mmm{RESET}  {SLATE}—{RESET}  {BCYAN}Minecraft Mod Manager{RESET}  {dim('v' + VERSION)}               {MINT}│{RESET}
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
             f"{GOLD}mmm set-profile 1.21.1 fabric{RESET}"]
        ),
        (
            f"{BYELLOW}search{RESET} {CYAN}<query>{RESET}  {dim('[-n <count>] [--no-filter] [--filter-version V] [--filter-loader L]')}",
            "Search mods. Results are numbered for get/show.",
            [f"{GOLD}mmm search sodium{RESET}",
             f"{GOLD}mmm search \"performance\" -n 15{RESET}",
             f"{GOLD}mmm search sodium --no-filter{RESET}",
             f"{GOLD}mmm search sodium --filter-version 1.21.1 --filter-loader fabric{RESET}"]
        ),
        (
            f"{BYELLOW}get{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}get{RESET} {CYAN}-i <index>{RESET}  {SLATE}|{RESET}  {BYELLOW}get{RESET} {CYAN}-f <file>{RESET}",
            "Install mod(s) to current directory. Resolves required deps automatically.",
            [f"{GOLD}mmm get sodium{RESET}",
             f"{GOLD}mmm get -i 3{RESET}",
             f"{GOLD}mmm get -f mods.txt{RESET}",
             f"{GOLD}mmm get sodium, lithium, iris, immediately fast{RESET}"]
        ),
        (
            f"{BYELLOW}show{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}show{RESET} {CYAN}-i <index>{RESET}",
            "Show full mod info: version, size, deps, checksums.",
            [f"{GOLD}mmm show sodium{RESET}",
             f"{GOLD}mmm show -i 1{RESET}"]
        ),
        (
            f"{BYELLOW}list{RESET}",
            "List all tracked mods with sizes and dependency graph.",
            [f"{GOLD}mmm list{RESET}"]
        ),
        (
            f"{BYELLOW}remove{RESET} {CYAN}<name>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove{RESET} {CYAN}-i <index>{RESET}  {SLATE}|{RESET}  {BYELLOW}remove -a{RESET}",
            "Remove mod(s). Warns before removing if other mods depend on it.",
            [f"{GOLD}mmm remove sodium{RESET}",
             f"{GOLD}mmm remove -i 1{RESET}",
             f"{GOLD}mmm remove -a{RESET}",
             f"{GOLD}mmm remove sodium, lithium{RESET}"]
        ),
        (
            f"{BYELLOW}profile{RESET}",
            "View current profile and cache info.",
            [f"{GOLD}mmm profile{RESET}"]
        ),
        (
            f"{BYELLOW}autoremove{RESET}",
            "Remove orphaned dependencies no longer required by any mod.",
            [f"{GOLD}mmm autoremove{RESET}"]
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
        f"Install from file ({GOLD}-f FILE{RESET}): one mod per line, or comma-separated.",
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
         ["mmm set-profile 1.21.1 fabric"]),
        ("# Install optimization mods",
         ["cd ~/minecraft/mods",
          "mmm get sodium, lithium, iris, immediately fast, ferritecore, entityculling"]),
        ("# Search, preview, then install",
         ["mmm search \"chunk loading\"",
          "mmm show -i 1",
          "mmm get -i 1"]),
        ("# Check what's installed",
         ["mmm list"]),
        ("# Remove a mod (will warn about dependents)",
         ["mmm remove sodium"]),
    ]
    for comment, cmds in steps:
        print(f"  {SLATE}{comment}{RESET}")
        for cmd in cmds:
            print(f"    {MINT}❯{RESET}  {BYELLOW}{cmd}{RESET}")
        print()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mmm",
        add_help=False,
    )

    sub = parser.add_subparsers(dest="cmd")

    # set-profile
    p = sub.add_parser("set-profile")
    p.add_argument("mc_version")
    p.add_argument("loader")

    # search
    p = sub.add_parser("search")
    p.add_argument("query", nargs="+")
    p.add_argument("-n", "--limit", type=int, default=10)
    p.add_argument("--no-filter", action="store_true")
    p.add_argument("--filter-version", dest="filter_version")
    p.add_argument("--filter-loader", dest="filter_loader")

    # get / install
    p = sub.add_parser("get", aliases=["install"])
    p.add_argument("names", nargs="*")
    p.add_argument("-i", type=int)
    p.add_argument("-f")

    # show
    p = sub.add_parser("show")
    p.add_argument("names", nargs="*")
    p.add_argument("-i", type=int)

    # list / ls
    p = sub.add_parser("list", aliases=["ls"])

    # remove / rm
    p = sub.add_parser("remove", aliases=["rm"])
    p.add_argument("names", nargs="*")
    p.add_argument("-i", type=int)
    p.add_argument("-a", "--all", action="store_true")

    # profile
    sub.add_parser("profile")

    # autoremove
    sub.add_parser("autoremove")

    return parser


COMMAND_DISPATCH = {
    "set-profile": cmd_set_profile,
    "search":      cmd_search,
    "get":         cmd_get,
    "install":     cmd_get,
    "show":        cmd_show,
    "list":        cmd_list,
    "ls":          cmd_list,
    "remove":      cmd_remove,
    "rm":          cmd_remove,
    "profile":     cmd_profile,
    "autoremove":  cmd_autoremove,
}


def main():
    parser = build_parser()
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        sys.exit(0)
    args = parser.parse_args()

    if not args.cmd:
        print_help()
        sys.exit(1)

    handler = COMMAND_DISPATCH.get(args.cmd)
    if handler:
        try:
            handler(args)
        except MMMError as e:
            err(str(e))
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            err("Interrupted.")
            sys.exit(130)
        except Exception as e:
            err(f"Unexpected error: {e}")
            if "--debug" in sys.argv:
                raise
            sys.exit(1)


if __name__ == "__main__":
    main()

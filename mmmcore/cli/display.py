import sys
import io
from pathlib import Path

from rich.markdown import Markdown as RichMarkdown
from rich.console import Console as RichConsole

from mmmcore.core.api import LOADER_COLORS as CORE_LOADER_COLORS

# ── ANSI colors ────────────────────────────────────────────────────────────────

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

# ── Loader badge colors ────────────────────────────────────────────────────────

LOADER_COLORS = {
    "fabric":   MINT,
    "forge":    ORANGE,
    "quilt":    PURPLE,
    "neoforge": GOLD,
}

def loader_badge(loader):
    c = LOADER_COLORS.get(loader.lower(), CYAN)
    return f"{c}[{loader}]{RESET}"

# ── Print helpers ──────────────────────────────────────────────────────────────

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

# ── Markdown rendering ─────────────────────────────────────────────────────────

def render_markdown(text, width=None):
    if not text or not text.strip():
        return ""
    if width is None:
        try:
            width = int(__import__("shutil").get_terminal_size().columns) - 2
        except Exception:
            width = 78
    width = max(40, min(width, 120))
    buf = io.StringIO()
    console = RichConsole(file=buf, width=width, force_terminal=True,
                          color_system="truecolor")
    console.print(RichMarkdown(text))
    return buf.getvalue().rstrip("\n")

# ── Search results display ─────────────────────────────────────────────────────

def print_search_results(results, query="", mc_version=None, loader=None, no_filter=False):
    if not results:
        warn("No results found.")
        return

    if no_filter:
        subtitle = "No filters"
    elif mc_version and loader:
        subtitle = f"Minecraft {mc_version}  ·  {loader.capitalize()}"
    elif not mc_version and not loader:
        subtitle = "All versions / all loaders"
    elif mc_version:
        subtitle = f"Minecraft {mc_version}  ·  All loaders"
    else:
        subtitle = f"All versions  ·  {loader.capitalize()}"

    header(f"Search results  {dim('» ' + query)}", subtitle)

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


def fmt_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

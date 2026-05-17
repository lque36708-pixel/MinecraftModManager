#!/usr/bin/env python3
"""
mmm — Minecraft Mod Manager
Download mods from Modrinth with automatic dependency resolution.
"""
import sys
from pathlib import Path

# Ensure the package directory is importable
_pkg_dir = Path(__file__).parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

from mmmcore.cli.main import main

if __name__ == "__main__":
    main()

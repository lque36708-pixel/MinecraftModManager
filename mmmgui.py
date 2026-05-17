#!/usr/bin/env python3
"""
mmm — Minecraft Mod Manager (GUI)
Launch the graphical interface for managing Minecraft mods.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mmmcore.gui.app import run

if __name__ == "__main__":
    run()

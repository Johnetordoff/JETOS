"""Startup file for the JETOS Language diagnostic console."""
from __future__ import annotations

import sys

from jetos import dunicode

sys.ps1 = "jetos> "
sys.ps2 = ".....> "
print("JETOS Language diagnostic console. `dunicode` is preloaded.")

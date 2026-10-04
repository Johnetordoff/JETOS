"""Startup file for the first JETOS CPython shell."""
from __future__ import annotations

import sys

from jetos import dunicode

sys.ps1 = "jetos> "
sys.ps2 = ".....> "
print("CPython is JETOS's first shell. \`dunicode\` is preloaded.")

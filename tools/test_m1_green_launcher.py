#!/usr/bin/env python3
"""Contract test for launching arm64 Green Gate from Apple Silicon."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    text = (ROOT / "tools/m1_green.py").read_text(encoding="utf-8")
    assert 'PLATFORM = "linux/arm64"' in text
    assert '"--platform", PLATFORM' in text
    assert '"python3", "tools/m1_green_gate.py"' in text
    assert 'JETOS_BOOTSTRAP_IMAGE' in text
    assert '"--pull"' not in text
    print("JETOS M1 Green launcher contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import sys
from pathlib import Path

_intel_dir = str(Path(__file__).resolve().parent)
if _intel_dir not in sys.path:
    sys.path.insert(0, _intel_dir)

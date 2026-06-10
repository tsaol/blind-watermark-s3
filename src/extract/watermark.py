import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from watermark import embed, extract, compute_psnr  # noqa: F401, E402

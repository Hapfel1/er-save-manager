#!/usr/bin/env python3
"""Run the Elden Ring Save Manager GUI."""

import logging
import sys
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Configure file logging before importing anything
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

_log_file = log_dir / "er_save_manager.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
# Keep console output at WARNING to avoid noise
logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
logging.getLogger().handlers[-1].setLevel(logging.WARNING)

from er_save_manager.ui import main  # noqa: E402

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the Elden Ring Save Manager GUI."""

import sys
from pathlib import Path

from er_save_manager.ui import main

# Add src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    main()

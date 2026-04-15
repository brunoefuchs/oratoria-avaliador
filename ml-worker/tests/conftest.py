"""Shared pytest fixtures for ml-worker tests.

Story 8.1 — Truth Contract: pytest infra setup (T0).
"""

import sys
from pathlib import Path

# Adicionar ml-worker root ao sys.path para que `from contracts...` e `from workers...` funcionem
_ML_WORKER_ROOT = Path(__file__).parent.parent
if str(_ML_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_WORKER_ROOT))

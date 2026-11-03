import sys
from pathlib import Path

# Automatically ensure backend root directory is on sys.path for all tests
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

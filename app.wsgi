import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crawler import app as application

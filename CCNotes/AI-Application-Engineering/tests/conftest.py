"""pytest 配置：把项目根加入 sys.path，让 tests 能 import src.rag.*"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # AI-Application-Engineering/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

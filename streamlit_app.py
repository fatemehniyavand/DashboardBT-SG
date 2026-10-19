"""Streamlit entry point for tick wave."""
from pathlib import Path
import sys
import runpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from bootstrap_data import ensure_data
ensure_data()
runpy.run_path(str(ROOT/'ticktide_observatory/app.py'),run_name='__main__')

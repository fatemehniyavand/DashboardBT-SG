"""tick wave / Ocean Edition. Streamlit entry point; preserves the V1 entry point."""
from pathlib import Path
import runpy
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
if (ROOT/'bootstrap_data.py').is_file():
    from bootstrap_data import ensure_data
    ensure_data()
runpy.run_path(str(ROOT/'ticktide_observatory/app.py'),run_name='__main__',init_globals={'TICK_WAVE_EDITION':'ocean'})

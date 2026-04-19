"""Streamlit Cloud entry-point shim.

This file exists at repo root so Streamlit Cloud's default convention
(`streamlit_app.py` at root) continues to work after the 2026-04
reorganization that moved the dashboard into `程式碼/儀表板/`.

⚠️ Recommended: In share.streamlit.io app settings, set
   **Main file path** = `程式碼/儀表板/app.py`
and this shim will not be used at all.

If Main file path stays at `streamlit_app.py` or repo auto-detects this
file, the shim does a best-effort delegation:
  1. chdir into dashboard directory so `st.Page("pages/...")` resolves correctly
  2. exec() the canonical app.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "程式碼" / "儀表板"
APP_PATH = DASHBOARD / "app.py"

if not APP_PATH.exists():
    import streamlit as st
    st.error(
        f"❌ 無法找到儀表板入口：{APP_PATH}\n\n"
        "請確認 repo 結構是否完整，或直接以 "
        "`streamlit run 程式碼/儀表板/app.py` 啟動。"
    )
    st.stop()

# Make dashboard module path importable BEFORE CWD change
sys.path.insert(0, str(DASHBOARD))

# Change working directory so `st.Page("pages/home.py")` relative paths work
os.chdir(DASHBOARD)

# Override sys.argv[0] so Streamlit's main_script_path resolves to the real app
sys.argv[0] = str(APP_PATH)

# Execute the canonical app — no code duplication
exec(
    compile(APP_PATH.read_text(encoding="utf-8"), str(APP_PATH), "exec"),
    {"__file__": str(APP_PATH), "__name__": "__main__"},
)

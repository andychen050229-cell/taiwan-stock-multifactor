"""Streamlit Cloud backward-compat shim — 2026-04-20

ORIGINAL: dashboard/app.py was the first entry-point before the project
reorganization moved everything into `程式碼/儀表板/`.

This shim keeps the existing Streamlit Cloud deployment (Main file path =
`dashboard/app.py`) working without requiring a Cloud settings change.
It delegates entirely to the canonical `程式碼/儀表板/app.py`.

For local development, prefer:
  streamlit run 程式碼/儀表板/app.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DASHBOARD = ROOT / "程式碼" / "儀表板"
APP_PATH = DASHBOARD / "app.py"

if not APP_PATH.exists():
    import streamlit as st
    st.error(
        f"❌ 無法找到儀表板入口：{APP_PATH}\n\n"
        "請確認 repo 結構完整。"
    )
    st.stop()

# Make the dashboard folder importable for `utils` etc.
sys.path.insert(0, str(DASHBOARD))

# Change CWD so `st.Page("pages/...")` relative-path resolution works
os.chdir(DASHBOARD)

# Tell Streamlit's main_script_path to point to the canonical app
sys.argv[0] = str(APP_PATH)

# Execute the canonical app (single source of truth, no code duplication)
exec(
    compile(APP_PATH.read_text(encoding="utf-8"), str(APP_PATH), "exec"),
    {"__file__": str(APP_PATH), "__name__": "__main__"},
)

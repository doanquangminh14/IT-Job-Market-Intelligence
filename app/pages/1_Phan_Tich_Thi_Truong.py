import os
import sys
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.components.market_insights import render_market_insights

st.set_page_config(
    page_title="Phân Tích Thị Trường Tuyển Dụng IT",
    layout="wide"
)

render_market_insights()


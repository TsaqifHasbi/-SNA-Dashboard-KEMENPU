import os
import sys
from pathlib import Path
import streamlit as st

# Set path to include root directory
current_dir = Path(__file__).resolve().parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from src.legal_pages import render_privacy_policy

_logo_icon = os.path.join(current_dir, "static", "logo.svg")

st.set_page_config(
    page_title="Privacy Policy | Public Policy Intelligence Platform",
    page_icon=_logo_icon if os.path.exists(_logo_icon) else None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom light styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    .stApp {
        background-color: #F8FAFC;
    }
</style>
""", unsafe_allow_html=True)

render_privacy_policy()

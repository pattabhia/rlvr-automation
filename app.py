"""
Enhanced Streamlit App Launcher

This is a convenience launcher that runs the enhanced Streamlit app
located in src/adapters/input/streamlit/app_enhanced.py

Usage:
    streamlit run app_enhanced.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the actual app
from src.adapters.input.streamlit.app_enhanced import main

if __name__ == "__main__":
    main()

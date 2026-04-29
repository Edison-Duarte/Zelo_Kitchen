import os
import subprocess
import sys

# Comando para forçar a instalação da biblioteca se ela não existir
try:
    import streamlit_gsheets
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-gsheets"])

import streamlit as st
from streamlit_gsheets import GSheetsConnection
# ... (restante do código igual)

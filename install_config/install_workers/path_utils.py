# install_config/ install workers/ path_utils.py
import sys
import os

def get_bdr_path(file_name: str):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, file_name)

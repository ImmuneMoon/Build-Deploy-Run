# install_config/install_workers/minimize_window.py
import ctypes, time

def minimize_window_by_title(window_title, timeout=5):
    user32 = ctypes.windll.user32

    # Wait a bit for the window to appear
    end_time = time.time() + timeout
    while time.time() < end_time:
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            user32.ShowWindow(hwnd, 6)  # 6 = minimize
            return True
        time.sleep(0.5)
    return False
# oven_state.py
import threading

lock = threading.RLock()
is_running: bool = False
cook_session_id: int = 0  # optional (handy for epochs if you ever need it)

def set_running(value: bool) -> bool:
    """Set running state under lock. Returns the new value."""
    global is_running, cook_session_id
    with lock:
        changed = (is_running != value)
        is_running = value
        if changed:
            cook_session_id += 1
        return is_running

def get_running() -> bool:
    """Read running state under lock."""
    with lock:
        return is_running

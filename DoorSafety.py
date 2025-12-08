# DoorSafety.py, Singleton and a Model
import threading
from typing import Callable, List, Optional

# DoorListener: a callable (function) that takes a bool argument and returns None.
DoorListener = Callable[[bool], None]  # (is_open)


class DoorSafety:
    """Thread-safe door model with subscribe/unsubscribe.
    Fail-safe default is OPEN until the controller reports otherwise.
    UI notifications are always marshaled onto the Tk/CTk UI thread via tk_root.after(...).
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # --- state ---
                cls._instance._door_open = False  # True fail-safe default
                cls._instance._state_lock = threading.Lock()
                # --- observers + UI root ---
                cls._instance._listeners = []  # type: List[DoorListener]
                cls._instance._listeners_lock = threading.Lock()
                cls._instance.tk_root = None  # type: Optional[object]

            return cls._instance

    @classmethod
    def Instance(cls) -> "DoorSafety":
        return cls()

    # -------- wiring --------
    def set_ui_root(self, tk_root: object) -> None:
        """Call once during app init (e.g., in MultiPageController.__init__)."""
        if not tk_root or not hasattr(tk_root, "after"):
            raise ValueError("tk_root must be a Tk/CTk root with .after(...)")
        self.tk_root = tk_root

    # -------- model state --------
    def set_open(self, open_: bool) -> None:
        changed = False
        with self._state_lock:
            new_val = bool(open_)
            if new_val != self._door_open:
                self._door_open = new_val
                changed = True
                current = self._door_open
            else:
                current = self._door_open

        if changed:
            # unified, UI-thread-safe notifier
            self._notify_listeners(current)

    def is_open(self) -> bool:
        with self._state_lock:
            return self._door_open

    # -------- observers --------
    def add_listener(self, fn: DoorListener, fire_immediately: bool = True) -> None:
        with self._listeners_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

        if fire_immediately:
            is_open_now = self.is_open()
            # marshal immediate fire to UI thread too
            if not self.tk_root or not hasattr(self.tk_root, "after"):
                raise RuntimeError(
                    "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
                )
            self.tk_root.after(0, fn, is_open_now)

    def remove_listener(self, fn: DoorListener) -> None:
        with self._listeners_lock:
            self._listeners = [f for f in self._listeners if f is not fn]

    # -------- unified notifier (UI-thread only) --------
    def _notify_listeners(self, is_open: bool) -> None:
        if not self.tk_root or not hasattr(self.tk_root, "after"):
            raise RuntimeError(
                "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
            )

        with self._listeners_lock:
            listeners = list(self._listeners)

        # schedule a single UI-thread batch that calls all listeners
        def _run():
            for fn in listeners:
                try:
                    fn(is_open)
                except Exception:
                    # swallow to avoid breaking other listeners
                    pass

        self.tk_root.after(0, _run)

    # -------- optional: parse helper --------
    def parse_controller_line(self, line: str) -> bool:
        """Accepts 'D=1'/'D=0' or 'DOOR=OPEN'/'DOOR=CLOSED'. Returns True if handled."""
        s = line.strip().upper()
        if s.startswith("D=") and len(s) >= 3:
            self.set_open(s[2:3] == "1")
            return True
        if s.startswith("DOOR="):
            val = s.split("=", 1)[1].strip()
            self.set_open(val in ("OPEN", "O", "1", "TRUE"))
            return True
        return False

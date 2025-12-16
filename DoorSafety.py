# DoorSafety.py, Singleton and a Model
import threading
from typing import Callable, List, Optional

# DoorListener: a callable (function) that takes a bool argument and returns None.
DoorListener = Callable[[bool], None]  # (is_open)

# WdtListener: a callable that takes a bool argument and returns None.
WdtListener = Callable[[bool], None]  # (is_timed_out)


class DoorSafety:
    """Thread-safe door model with subscribe/unsubscribe.
    Fail-safe default is OPEN until the controller reports otherwise.
    UI notifications are always marshaled onto the Tk/CTk UI thread via tk_root.after(...).

    Extended:
      - WDT timeout state is tracked independently of door open state
      - separate listener set + notifications for WDT timeout changes
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)

                # --- door state ---
                cls._instance._door_open = (
                    False  # True fail-safe default (comment kept)
                )
                cls._instance._state_lock = threading.Lock()

                # --- door observers + UI root ---
                cls._instance._listeners = []  # type: List[DoorListener]
                cls._instance._listeners_lock = threading.Lock()

                # --- WDT timeout state (independent) ---
                cls._instance._wdt_timed_out = False
                cls._instance._wdt_lock = threading.Lock()

                # --- WDT observers ---
                cls._instance._wdt_listeners = []  # type: List[WdtListener]
                cls._instance._wdt_listeners_lock = threading.Lock()

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

    # ===================== DOOR MODEL =======================================

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
            self._notify_listeners(current)

    def is_open(self) -> bool:
        with self._state_lock:
            return self._door_open

    def add_listener(self, fn: DoorListener, fire_immediately: bool = True) -> None:
        with self._listeners_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

        if fire_immediately:
            is_open_now = self.is_open()
            if not self.tk_root or not hasattr(self.tk_root, "after"):
                raise RuntimeError(
                    "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
                )
            self.tk_root.after(0, fn, is_open_now)

    def remove_listener(self, fn: DoorListener) -> None:
        with self._listeners_lock:
            self._listeners = [f for f in self._listeners if f is not fn]

    def _notify_listeners(self, is_open: bool) -> None:
        if not self.tk_root or not hasattr(self.tk_root, "after"):
            raise RuntimeError(
                "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
            )

        with self._listeners_lock:
            listeners = list(self._listeners)

        def _run():
            for fn in listeners:
                try:
                    fn(is_open)
                except Exception:
                    pass

        self.tk_root.after(0, _run)

    # ===================== WDT TIMEOUT MODEL =================================

    def set_wdt_timed_out(self, timed_out: bool) -> None:
        """Publish communication watchdog timeout state (independent of door open)."""
        changed = False
        with self._wdt_lock:
            new_val = bool(timed_out)
            if new_val != self._wdt_timed_out:
                self._wdt_timed_out = new_val
                changed = True
                current = self._wdt_timed_out
            else:
                current = self._wdt_timed_out

        if changed:
            self._notify_wdt_listeners(current)

    def is_wdt_timed_out(self) -> bool:
        with self._wdt_lock:
            return self._wdt_timed_out

    def add_wdt_listener(self, fn: WdtListener, fire_immediately: bool = True) -> None:
        with self._wdt_listeners_lock:
            if fn not in self._wdt_listeners:
                self._wdt_listeners.append(fn)

        if fire_immediately:
            state_now = self.is_wdt_timed_out()
            if not self.tk_root or not hasattr(self.tk_root, "after"):
                raise RuntimeError(
                    "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
                )
            self.tk_root.after(0, fn, state_now)

    def remove_wdt_listener(self, fn: WdtListener) -> None:
        with self._wdt_listeners_lock:
            self._wdt_listeners = [f for f in self._wdt_listeners if f is not fn]

    def _notify_wdt_listeners(self, is_timed_out: bool) -> None:
        if not self.tk_root or not hasattr(self.tk_root, "after"):
            raise RuntimeError(
                "DoorSafety must be given a tk_root (call set_ui_root) for UI-safe callbacks"
            )

        with self._wdt_listeners_lock:
            listeners = list(self._wdt_listeners)

        def _run():
            for fn in listeners:
                try:
                    fn(is_timed_out)
                except Exception:
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

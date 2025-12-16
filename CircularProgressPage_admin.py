from __future__ import annotations  # if you're on Python 3.8/3.9
from typing import Optional, TYPE_CHECKING

from TimePowerPage import TimePowerPage  # only for typing; no runtime import

import time
from typing import Optional
import customtkinter as ctk
from PIL import Image

from DoorSafety import DoorSafety
from hmi_consts import ASSETS_DIR, HMIColors
from hmi_consts import SETTINGS_DIR  # NEW
import os, json  # NEW

# Reuse your existing widget
from CircularProgress_admin import CircularProgress_admin
from SerialService import SerialService  # uses your CTkCanvas-based class
from MessageBoxPage import showerror
import oven_state
import logging

logger = logging.getLogger(__name__)

PERIODIC_THERMISTOR = True
PERIODIC_INTRERVAL_MS = 1000
WDT_TIMEOUT_MS = 5000
WDT_STARTUP_DELAY_MS = 2000


class CircularProgressPage_admin(ctk.CTkFrame):
    """
    A MultiPageController-friendly page that shows a full-screen circular
    countdown with a single STOP button.
    """

    def __init__(self, controller, shared_data=None, **kwargs):
        super().__init__(controller, fg_color=HMIColors.color_fg, **kwargs)
        self.controller = controller
        self.shared_data = shared_data

        self._time_power_page: Optional["TimePowerPage"] = None

        # Internal state
        self.total_time = 0.0
        self.remaining_time = 0.0
        self._start_epoch = None
        self._running = False
        self._on_stop = None

        # Cached alarm level (loaded on_show)
        self._alarm_level: int = 1500  # default/fallback
        self._alarm_hysteresis: int = 400  # default/fallback
        self._inAlarmState: bool | None = False
        self._prevAlarmState: bool | None = None

        self._isManualCookMode: bool = False
        self._powerLevel: int | None = None
        self._over_temp_power: float = 0.75  # fraction 0..1 used for throttling

        # --- NEW: completely independent 1-second periodic timer ------------
        self._periodic_callback = None
        self._periodic_after_id = None
        if PERIODIC_THERMISTOR:
            self._start_periodic_timer()
        self.bind("<Destroy>", lambda e: self._cancel_periodic_timer())

        # Layout for 800x480
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.progress = CircularProgress_admin(self, size=360, thickness=22)
        self.progress.grid(row=0, column=0, pady=(24, 0))

        self.stop_button = ctk.CTkButton(
            self,
            text="STOP",
            width=220,
            height=56,
            corner_radius=18,
            font=ctk.CTkFont(size=24, weight="bold"),
            command=self.stop,
        )
        self.stop_button.grid(row=1, column=0, pady=(18, 24))

        self.progress.update_progress(0, 1)

        # --- Over-temp icon in upper right ---------------------------------
        try:
            overtemp_size = (96, 96)
            img = Image.open(f"{ASSETS_DIR}/over_temp.png")
            img = img.resize(overtemp_size, Image.Resampling.LANCZOS)
            self._overtemp_icon = ctk.CTkImage(
                light_image=img, dark_image=img, size=overtemp_size
            )
            self._overtemp_lbl = ctk.CTkLabel(self, image=self._overtemp_icon, text="")
            # Note: not placed here; controlled by set_overtemp_visible()
        except Exception as e:
            print(f"Failed to load over_temp.png: {e}")
            self._overtemp_lbl = None

        # --- Power/Scale label (ALWAYS visible, under where the icon goes) ---
        self._power_var = ctk.StringVar(value="Power: N/A")
        self._power_lbl = ctk.CTkLabel(
            self,
            textvariable=self._power_var,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=HMIColors.TEXT_COLOR,
        )
        # Place in upper-right corner a bit below where the icon will sit
        self._power_lbl.place(relx=1.0, rely=0.0, anchor="ne", x=-25, y=130)

        # --- lower-right status label for last serial line ------------------
        self._last_line_var = ctk.StringVar(value="")
        self._last_line_lbl = ctk.CTkLabel(
            self,
            textvariable=self._last_line_var,
            font=ctk.CTkFont(size=24),
            text_color=HMIColors.TEXT_COLOR,
        )
        self._last_line_lbl.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-22)

        # --- lower-right T1..T4 labels -------------------------------------
        self._t1_var = ctk.StringVar(value="T1 = N/A        ")
        self._t1_lbl = ctk.CTkLabel(
            self,
            textvariable=self._t1_var,
            font=ctk.CTkFont(size=24),
            text_color=HMIColors.TEXT_COLOR,
        )

        _yStart = -180
        _LINE_HEIGHT = 40

        self._t1_lbl.place(
            relx=1.0, rely=1.0, anchor="se", x=-10, y=_yStart + 0 * _LINE_HEIGHT
        )

        self._t2_var = ctk.StringVar(value="T2 = N/A        ")
        self._t2_lbl = ctk.CTkLabel(
            self,
            textvariable=self._t2_var,
            font=ctk.CTkFont(size=24),
            text_color=HMIColors.TEXT_COLOR,
        )
        self._t2_lbl.place(
            relx=1.0, rely=1.0, anchor="se", x=-10, y=_yStart + 1 * _LINE_HEIGHT
        )

        self._t3_var = ctk.StringVar(value="T3 = N/A        ")
        self._t3_lbl = ctk.CTkLabel(
            self,
            textvariable=self._t3_var,
            font=ctk.CTkFont(size=24),
            text_color=HMIColors.TEXT_COLOR,
        )
        self._t3_lbl.place(
            relx=1.0, rely=1.0, anchor="se", x=-10, y=_yStart + 2 * _LINE_HEIGHT
        )

        self._t4_var = ctk.StringVar(value="T4 = N/A        ")
        self._t4_lbl = ctk.CTkLabel(
            self,
            textvariable=self._t4_var,
            font=ctk.CTkFont(size=24),
            text_color=HMIColors.TEXT_COLOR,
        )
        self._t4_lbl.place(
            relx=1.0, rely=1.0, anchor="se", x=-10, y=_yStart + 3 * _LINE_HEIGHT
        )

        # Serial
        self.serial: Optional["SerialService"] = getattr(
            self.controller, "serial", None
        )
        if self.serial:
            self.serial.add_listener(self._on_serial_line)
            print("have serial")

        # Periodic thermistor poll
        self.set_periodic_callback(self.on_read_controller_thermistors)

        # --- Watchdog Timer -------------------------------------------------
        self._wdt_after_id = None
        self._wdt_timeout_ms = WDT_TIMEOUT_MS
        if PERIODIC_THERMISTOR:
            self.after(WDT_STARTUP_DELAY_MS, self._kick_watchdog)

    # ---- Public API -----------------------------------------------------

    def on_show(
        self,
        isManualCookMode: bool | None = None,
        time_power_page: TimePowerPage | None = None,
        powerLevel: int | None = None,
    ):
        # Store passed state
        self._isManualCookMode = bool(isManualCookMode)
        self._time_power_page = time_power_page
        self._powerLevel = powerLevel

        # Reset previous alarm state
        self._prevAlarmState = None
        self._inAlarmState = None
        # Load & cache alarm level (only when page is shown)
        self._alarm_level, self._alarm_hysteresis = (
            self._load_alarm_levels_from_settings()
        )
        self._over_temp_power = self._load_over_temp_power_from_settings(default=0.75)

        # Make sure the over temp icon is initially hidden
        self.set_overtemp_visible(False)

        # Initialize the label for the current mode
        if self._isManualCookMode:
            self.set_power_display(int(self._powerLevel) if self._powerLevel else None)
        else:
            # Program mode shows global scale
            self.set_power_display(100)

    def set_power_display(self, value: int | None):
        """
        Update the label:
          - Manual Cook: 'NN% Power'
          - Program Run: 'Scale: NN%'
        """
        try:
            if value is None:
                self._power_var.set(
                    "Power: N/A" if self._isManualCookMode else "Scale: N/A"
                )
            else:
                if self._isManualCookMode:
                    self._power_var.set(f"{value}% Power")
                else:
                    self._power_var.set(f"Scale: {value}%")
        except Exception:
            self._power_var.set(
                "Power: N/A" if self._isManualCookMode else "Scale: N/A"
            )

    # ---------------------- Helper: load alarm level once -------------------
    def _load_alarm_levels_from_settings(
        self, defaultAlarmLevel: int = 1500, defaultHysteresis: int = 400
    ) -> tuple[int, int]:
        """Read alarm_level from settings.alt (same key DiagnosticsPage uses)."""
        path = os.path.join(SETTINGS_DIR, "settings.alt")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    return int(data.get("alarm_level", defaultAlarmLevel)), int(
                        data.get("alarm_hysteresis", defaultHysteresis)
                    )
        except Exception:
            pass
        return defaultAlarmLevel, defaultHysteresis

    def _load_over_temp_power_from_settings(self, default: float = 0.75) -> float:
        path = os.path.join(SETTINGS_DIR, "settings.alt")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    return float(data.get("over_temp_power", default))
        except Exception:
            pass
        return default

    def set_overtemp_visible(self, show: bool):
        """Show or hide the over-temp icon dynamically. Power/Scale label stays visible."""
        if self._overtemp_lbl:
            if show:
                self._overtemp_lbl.place(relx=1.0, rely=0.0, anchor="ne", x=-25, y=25)
            else:
                self._overtemp_lbl.place_forget()

    def start(self, start_seconds: float, on_stop=None):
        self.total_time = max(0.0, float(start_seconds))
        self.remaining_time = self.total_time
        self._on_stop = on_stop

        self._running = True
        self._start_epoch = time.time()
        self._tick()

    def stop(self):
        was_running = self._running
        self._running = False
        if self.remaining_time <= 0.001:
            self.progress.update_progress(0, self.total_time)

        self._stop_manager()

        if self._on_stop:
            cb, self._on_stop = self._on_stop, None
            try:
                cb()
            except Exception as e:
                print(f"[CircularProgressPage] on_stop callback failed: {e}")
        else:
            try:
                self.controller.serial_all_zones_off()
            except Exception:
                pass

        try:
            self.controller.show_HomePage()
        except Exception as e:
            print(f"[CircularProgressPage] Failed to navigate HomePage: {e}")

    # ---- Internal -------------------------------------------------------

    def _stop_manager(self):
        try:
            mgr = (self.shared_data or {}).get("sequence_manager")
            if mgr:
                if hasattr(mgr, "stop_all"):
                    mgr.stop_all()
                elif hasattr(mgr, "request_stop"):
                    mgr.request_stop()
        except Exception as e:
            print(f"[CircularProgressPage] stop manager failed: {e}")

    def _tick(self):
        if not self._running:
            return

        elapsed = time.time() - self._start_epoch
        self.remaining_time = max(0.0, self.total_time - elapsed)

        self.progress.update_progress(self.remaining_time, self.total_time)

        if self.remaining_time > 0.0:
            self.after(50, self._tick)
        else:
            self._running = False
            self.progress.update_progress(0, self.total_time)
            self._stop_manager()

            if self._on_stop:
                cb, self._on_stop = self._on_stop, None
                try:
                    cb()
                except Exception as e:
                    print(f"[CircularProgressPage] on_stop callback failed: {e}")

            try:
                self.controller.show_FoodReadyPage(
                    auto_return_to=TimePowerPage, after_ms=10000
                )
            except Exception:
                pass

    # ===================== Periodic controller poll =========================

    def set_periodic_callback(self, callback):
        self._periodic_callback = callback

    def _start_periodic_timer(self):
        self._periodic_tick()

    def _periodic_tick(self):
        if self._periodic_callback is not None:
            try:
                self._periodic_callback()
            except Exception as e:
                print(f"[CircularProgressPage] periodic callback failed: {e}")
        try:
            self._periodic_after_id = self.after(
                PERIODIC_INTRERVAL_MS, self._periodic_tick
            )
        except Exception:
            self._periodic_after_id = None

    def _cancel_periodic_timer(self):
        if self._periodic_after_id is not None:
            try:
                self.after_cancel(self._periodic_after_id)
            except Exception:
                pass
            self._periodic_after_id = None

    from StopWatch import Stopwatch

    _sw = Stopwatch()
    _sw1 = Stopwatch()

    def on_read_controller_thermistors(self):
        try:
            self._sw.stop()
            if self._sw.elapsed_ms() > (PERIODIC_INTRERVAL_MS * 1.25):
                s = f"[on_read_controller_thermistors] = {self._sw.elapsed_ms():.3f}"
                logger.info(s)
                print(s)
            self._sw.reset()
            self._sw.start()

            self.controller.serial_get_thermistor()
            for sendorId in range(1, 5):
                self.controller.serial_get_IR_temp(sendorId)
        except Exception:
            pass

    # ===================== Watchdog Timer ===================================

    def _kick_watchdog(self):
        """Reset the watchdog countdown."""
        if self._wdt_after_id is not None:
            try:
                self.after_cancel(self._wdt_after_id)
            except Exception:
                pass
        self._wdt_after_id = self.after(self._wdt_timeout_ms, self._wdt_expired)

    def _wdt_expired(self):
        """Called if no kick in WDT_TIMEOUT_MS."""
        print("[CircularProgressPage] Watchdog expired: no serial data")
        try:
            logger.info("Lost communication with the controller!")
            # publish timeout independent of door-open model
            DoorSafety.Instance().set_wdt_timed_out(True)

            self.stop()
            if (
                self.controller.is_admin
            ):  # we only show the modal error message in admin mode so we don't hang the app with a hidden modal messagebox
                showerror(
                    self.controller, "Error", "Lost communication with the controller!"
                )
        except Exception as e:
            print(f"[CircularProgressPage] Failed to show error: {e}")

    def _set_power_if_running(self, pct: float) -> None:
        """
        Runs on the UI thread. Atomically checks the oven running state and
        calls TimePowerPage only if still running.
        """
        with oven_state.lock:
            if (
                oven_state.is_running
                and getattr(self, "_time_power_page", None) is not None
            ):
                self._time_power_page.set_power_to_percent_of_set_value(pct)

    def _set_program_scale(self, scale: float) -> None:
        """
        Program-run throttle: scale all active zones via the sequence manager.
        """
        try:
            mgr = (self.shared_data or {}).get("sequence_manager")
            if mgr and hasattr(mgr, "set_power_scale"):
                mgr.set_power_scale(max(0.0, min(1.0, float(scale))))
        except Exception as e:
            print(f"[CircularProgressPage] set_program_scale failed: {e}")

    def _on_serial_line(self, line: str) -> None:
        try:
            if line.startswith("T0"):
                return

            if line.startswith("D=") and (len(line) == 3):
                doorOpen: bool = line[2:3] == "1"
                DoorSafety.Instance().set_open(doorOpen)

            if line.startswith("R="):
                if PERIODIC_THERMISTOR:
                    self._kick_watchdog()

                self._sw1.stop()
                if self._sw1.elapsed_ms() > (PERIODIC_INTRERVAL_MS * 1.25):
                    s = f"[_on_serial_line] = {self._sw1.elapsed_ms():.3f}"
                    logger.info(s)
                    print(s)
                self._sw1.reset()
                self._sw1.start()

                self._last_line_var.set(line)

                # only do oven temperature control if we are in admin mode
                if not self.controller.is_admin:
                    return

                # --- Over-temp handling for BOTH modes ---------------------
                try:
                    if oven_state.get_running():
                        # Parse "R=num1,num2"
                        r1_str, r2_str = line[2:].split(",", 1)
                        r1, r2 = int(r1_str), int(r2_str)

                        L = self._alarm_level
                        H = self._alarm_hysteresis

                        # first time -> initialize display
                        if self._inAlarmState is None:
                            if self._isManualCookMode:
                                self.set_power_display(
                                    int(self._powerLevel) if self._powerLevel else None
                                )
                            else:
                                self.set_power_display(100)

                        prev = bool(self._inAlarmState)  # treat None as False

                        if prev:
                            # In alarm: remain in alarm unless BOTH are > L+H
                            in_alarm = not (r1 > L + H and r2 > L + H)
                        else:
                            # Not in alarm: enter if ANY is < L
                            in_alarm = (r1 < L) or (r2 < L)

                        if in_alarm != prev:
                            # State changed -> update UI/actions once
                            self.set_overtemp_visible(in_alarm)

                            if in_alarm:
                                # Entering alarm: throttle
                                throttle: float = self._over_temp_power
                                if self._isManualCookMode:
                                    self._set_power_if_running(throttle)
                                    if self._powerLevel is not None:
                                        self.set_power_display(
                                            int(throttle * self._powerLevel)
                                        )
                                    else:
                                        self.set_power_display(int(throttle * 100))
                                else:
                                    # Program mode -> scale all zones
                                    self._set_program_scale(throttle)
                                    self.set_power_display(int(throttle * 100))
                            else:
                                # Leaving alarm: restore to 100%
                                if self._isManualCookMode:
                                    self._set_power_if_running(1)
                                    if self._powerLevel is not None:
                                        self.set_power_display(int(self._powerLevel))
                                    else:
                                        self.set_power_display(100)
                                else:
                                    self._set_program_scale(1.0)
                                    self.set_power_display(100)

                        # Commit new state
                        self._inAlarmState = in_alarm

                except ValueError:
                    pass

            if line.startswith("T1"):
                self._t1_var.set(line)
            if line.startswith("T2"):
                self._t2_var.set(line)
            if line.startswith("T3"):
                self._t3_var.set(line)
            if line.startswith("T4"):
                self._t4_var.set(line)

            if oven_state.get_running() and line.startswith(("T1", "T2", "T3", "T4")):
                logger.info(line)

        except Exception:
            pass


# --- Example usage ------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = ctk.CTk()
    app.geometry("800x480")

    page = CircularProgressPage_admin(app)
    page.pack(fill="both", expand=True)
    page.start(10, on_stop=lambda: print("Timer stopped"))

    app.mainloop()

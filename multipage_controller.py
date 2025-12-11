# multipage_controller.py

import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import logging

from typing import Optional

from image_hotspot_view import ImageHotspotView
from homepage import HomePage
from select_meal_page import SelectMealPage
from prepare_for_cooking1 import PrepareForCookingPage1
from prepare_for_cooking2 import PrepareForCookingPage2
from start_cooking_confirmation import StartCookingConfirmation
from cooking_page import CookingPage
from cooking_finished_page import CookingFinishedPage
from cooking_paused_page import CookingPausedPage
from SerialService import SerialService
from DoorSafety import DoorSafety
from hmi_consts import ASSETS_DIR, SETTINGS_DIR, PROGRAMS_DIR, HMISizePos, __version__
from helpers import restore_saved_fan_delay_settings
from hmi_logger import setup_logging
import oven_state

# NEW: program / sequence helpers
from SelectProgramPage import load_program_into_sequence_collection
from SequenceStructure import SequenceCollection
from CookingSequenceRunner import CookingSequenceManager

logger = logging.getLogger("MultiPageController")


class MultiPageController:
    """
    MultiPageController
    -------------------
    Central controller that:
      - Owns the CTk root window
      - Owns the singleton ImageHotspotView
      - Creates and manages page models (HomePage, etc.)
      - Exposes show_* methods for navigation (called by page callbacks)
      - Owns the CookingSequenceManager lifecycle for cook cycles
    """

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._suppress_finished_page = False  # flag for hard-cancel

        # Create the singleton hotspot view inside the root
        self.view = ImageHotspotView.get_instance(root)
        self.view.pack(fill="both", expand=True)

        # --- create/start shared serial service (pages access via controller.serial) ---
        self.serial = SerialService(
            tk_root=root
        )  # optionally: port_hint="COM5" or "ACM"
        try:
            self.serial.start()
        except Exception as e:
            print("Serial start failed:", e)

        # need to pass CTk root to make the DoorSafety model UI thread safe
        DoorSafety.Instance().set_ui_root(root)

        self.is_admin = False  # <--- global admin flag lives here

        # Shared data (controller owns defaults)
        self.shared_data = {
            "name": ctk.StringVar(),
            "age": ctk.StringVar(),
            "time_page": {
                "minute": ctk.IntVar(value=1),
                "second": ctk.IntVar(value=1),
            },
            "time_power_page": {
                "minute": ctk.IntVar(value=0),
                "second": ctk.IntVar(value=10),
                "power": ctk.IntVar(value=50),
            },
            # reheat cook time
            "reheat_seconds": 0,
        }

        restore_saved_fan_delay_settings(self.shared_data)

        # --- track pending fan-off timer ---
        self._fan_off_timer = None

        # --- currently active CookingSequenceManager (if any) ---
        self.sequence_manager: Optional[CookingSequenceManager] = None
        self.shared_data["sequence_manager"] = None

        # Cache icons for SequenceProgramPage (still used elsewhere)
        self.zone_icons = []
        for i in range(8):
            icon = Image.open(f"{ASSETS_DIR}/Zone{i+1}.png").resize((24, 24))
            self.zone_icons.append(
                ctk.CTkImage(light_image=icon, dark_image=icon, size=(24, 24))
            )

        # --- Create pages and give them a reference to this controller ---
        self.home_page = HomePage(controller=self)
        self.select_meal_page = SelectMealPage(controller=self)
        self.prepare_for_cooking_page1 = PrepareForCookingPage1(controller=self)
        self.prepare_for_cooking_page2 = PrepareForCookingPage2(controller=self)
        self.start_cooking_confirm_page = StartCookingConfirmation(controller=self)
        self.cooking_page = CookingPage(controller=self)
        self.cooking_finished_page = CookingFinishedPage(controller=self)
        self.cooking_paused_page = CookingPausedPage(controller=self)

        self._current_page = None

        # after self.serial.start(), give the controller COM time to be ready to talk to
        self.after(2000, self.serial_get_door_switch)

        setup_logging("hmi")
        logger.info(f"HMI Started {[__version__]}")

    # ------------------------------------------------------------------
    # Convenience proxies to root.after / after_cancel
    # ------------------------------------------------------------------
    def after(self, delay_ms: int, callback, *args):
        """
        Proxy to the Tk root's .after(), so pages and controller
        can call controller.after(...) like a widget.
        """
        return self.root.after(delay_ms, callback, *args)

    def after_cancel(self, after_id):
        """
        Proxy to the Tk root's .after_cancel() for cancelling timers.
        """
        return self.root.after_cancel(after_id)

    # ------------------------------------------------------------------
    # Core navigation helpers
    # ------------------------------------------------------------------
    def show_page(self, page_obj) -> None:
        """
        Generic page switch with lifecycle hooks:
        - Calls on_hide() on the previous page (if it exists)
        - Calls on_show() on the new page (if it exists)
        - Updates the ImageHotspotView
        """
        # 1. Call on_hide on the current page (if available)
        if self._current_page and hasattr(self._current_page, "on_hide"):
            try:
                self._current_page.on_hide()
            except Exception as e:
                print(f"WARNING: on_hide() failed on {self._current_page}: {e}")

        # 2. Call on_show on the new page (if available)
        if hasattr(page_obj, "on_show"):
            try:
                page_obj.on_show()
            except TypeError:
                # Some pages (like StartCookingConfirmation) expect parameters
                # They will call on_show manually before show_page()
                pass

        # 3. Switch pages visually
        self._current_page = page_obj
        self.view.set_page(page_obj)

    def show_HomePage(self) -> None:
        self.show_page(self.home_page)

    def show_SelectMealPage(self) -> None:
        self.show_page(self.select_meal_page)

    def show_PrepareForCookingPage1(self) -> None:
        self.show_page(self.prepare_for_cooking_page1)

    def show_PrepareForCookingPage2(self) -> None:
        self.show_page(self.prepare_for_cooking_page2)

    def show_StartCookingConfirmation(self) -> None:
        self.start_cooking_confirm_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.start_cooking_confirm_page)

    def show_CookingPage(self) -> None:
        # Pass the currently selected meal index into CookingPage
        self.cooking_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.cooking_page)

    def show_CookingFinishedPage(self) -> None:
        self.show_page(self.cooking_finished_page)

    def show_CookingPausedPage(self) -> None:
        # Pass the currently selected meal index into CookingPage
        self.cooking_paused_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.cooking_paused_page)

    # ------------------------------------------------------------------
    # Serial commands + fan off logic
    # ------------------------------------------------------------------

    # --- helpers for fan-off timer ---
    def _cancel_fan_off_timer(self):
        """Cancel any scheduled fan-off so it won't trip while cooking resumes."""
        t = getattr(self, "_fan_off_timer", None)
        if t and t.is_alive():
            try:
                t.cancel()
            except Exception:
                pass
        self._fan_off_timer = None

    def _schedule_fan_off_after_delay(self):
        """
        Schedule fan off based on TimePage delay (minute/second) stored in shared_data.
        Cancels any previous schedule and sets a fresh one.
        """
        self._cancel_fan_off_timer()

        tp = self.shared_data.get("time_page", {})
        minute = int(tp.get("minute").get() if "minute" in tp else 0)
        second = int(tp.get("second").get() if "second" in tp else 0)
        delay_seconds = max(0, minute * 60 + second)

        if delay_seconds == 0:
            try:
                self.serial_fan(False)
            except Exception as e:
                print(f"[MultiPageController] immediate fan off failed: {e}")
            return

        def delayed_fan_off():
            try:
                self.serial_fan(False)
            except Exception as e:
                print(f"[MultiPageController] delayed fan off failed: {e}")

        self._fan_off_timer = threading.Timer(delay_seconds, delayed_fan_off)
        self._fan_off_timer.start()

    # zone: 1 - 8, power: 0 - 100
    def serial_zone(self, zone: int, power: int):
        """
        Send Znn=xxx. If any element is energized (power > 0),
        cancel pending fan-off countdown to avoid shutting the fan off mid-run.
        """
        oven_state.set_running(True)
        try:
            if power > 0:
                self._cancel_fan_off_timer()

            cmd = f"Z{zone:02d}={power:03d}"
            self.serial.send(cmd)
        except Exception:
            raise
        finally:
            logger.info(f"Zone{zone} Power = {power}")

    def serial_all_zones(self, power: int):
        """
        Set all zones to given power. If energizing (power > 0), cancel the fan-off timer.
        """
        if power > 0:
            self._cancel_fan_off_timer()

        for zone in range(1, 9):
            try:
                self.serial_zone(zone, power)
            except Exception as e:
                print(f"Error in serial_all_zones {zone}: {e}")

    def serial_all_zones_off(self):
        """
        Turn everything off and schedule the fan shutdown delay.
        """
        if oven_state.get_running():
            oven_state.set_running(False)
            logger.info("Cook Cycle Ended")
        try:
            print("In serial_all_zones_off()")
            # Controller convention: broadcast Z00=000 to turn everything off
            self.serial.send("Z00=000")
            # Schedule fan off after delay (or immediately if delay=0)
            self._schedule_fan_off_after_delay()
        except Exception:
            pass

    # request the thermistor resistances
    def serial_get_thermistor(self):
        cmd = "R"
        self.serial.send(cmd)

    def serial_get_versions(self):
        cmd = "I"
        self.serial.send(cmd)

    def serial_get_IR_temp(self, sensor: int):
        cmd = f"T{sensor}"
        self.serial.send(cmd)

    def serial_get_door_switch(self):
        cmd = "D"
        self.serial.send(cmd)

    def serial_get_door_lock(self):
        cmd = "L"
        self.serial.send(cmd)

    def serial_door_lock(self, on: bool):
        cmd = "L=" + ("1" if on else "0")
        self.serial.send(cmd)

    def serial_get_fan(self):
        cmd = "F"
        self.serial.send(cmd)

    def serial_fan(self, on: bool):
        cmd = "F=" + ("1" if on else "0")
        self.serial.send(cmd)

    # ------------------------------------------------------------------
    # Cooking sequence lifecycle (BEST DESIGN)
    # ------------------------------------------------------------------
    def _on_all_zones_complete(self):
        """
        Called once when all zone runners complete.
        Runs in a worker thread (CookingSequenceRunner's done_callback).
        """
        try:
            self.serial_all_zones_off()
        except Exception as e:
            print(
                f"[MultiPageController] serial_all_zones_off in _on_all_zones_complete failed: {e}"
            )

        try:
            oven_state.set_running(False)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(False) failed: {e}")

        # If this was a HARD STOP, don't navigate to CookingFinishedPage
        if getattr(self, "_suppress_finished_page", False):
            print("[MultiPageController] Hard stop: suppressing CookingFinishedPage")
            self._suppress_finished_page = False  # reset for next run
            return

        # When cooking is truly finished, show the CookingFinishedPage
        try:
            # Must switch pages on the Tk UI thread
            self.after(0, self.show_CookingFinishedPage)
        except Exception as e:
            print(
                f"[MultiPageController] show_CookingFinishedPage in _on_all_zones_complete failed: {e}"
            )

    def start_meal_program(self, meal_index: int) -> float:
        """
        BEST DESIGN:
        Build and start CookingSequenceManager for the selected meal program.

        - Loads program{31+meal_index}.alt into SequenceCollection
        - Builds per-zone sequences from SequenceCollection
        - Creates CookingSequenceManager and wires it to serial_zone
        - Ensures a dummy Zone8 sequence exists
        - Starts all runners
        - Marks oven_state running
        - Returns total cook time in seconds (max across zones)
        """
        if meal_index is None:
            print("[MultiPageController] start_meal_program: meal_index is None")
            return 0.0

        program_number = meal_index + 31
        print(f"[MultiPageController] Starting meal program {program_number}")

        # 1) Load the program into SequenceCollection
        try:
            load_program_into_sequence_collection(program_number)
        except Exception as e:
            print(
                f"[MultiPageController] load_program_into_sequence_collection({program_number}) failed: {e}"
            )
            return 0.0

        sc = SequenceCollection.Instance()
        zone_sequences: list[tuple[str, list[tuple[float, float]]]] = []

        # 2) Gather non-empty zone sequences (Zone1..Zone8)
        for zone_idx in range(8):
            zone = sc.get_zone_sequence_by_index(zone_idx)
            if not zone:
                continue

            steps: list[tuple[float, float]] = []
            for step in zone.steps:
                try:
                    d = float(step.duration)
                    p = float(step.power)
                except Exception:
                    continue
                if d <= 0:
                    continue
                steps.append((d, p))

            if steps:
                zone_name = f"Zone{zone_idx+1}"
                zone_sequences.append((zone_name, steps))

        if not zone_sequences:
            print("[MultiPageController] No non-empty zone sequences; aborting")
            return 0.0

        # 3) Construct the manager
        mgr = CookingSequenceManager()

        # callback to send to hardware
        def set_zone_output(zone_name, value, duration):
            try:
                zone_id = int(zone_name.replace("Zone", ""))
            except Exception:
                print(f"[HW] Bad zone name: {zone_name}")
                return
            try:
                self.serial_zone(zone_id, int(value))
            except Exception as e:
                print(f"[HW] serial_zone({zone_id}, {value}) failed: {e}")

        # 3b) Add DAC/Zones
        zone8_flag = False
        for zone_name, steps in zone_sequences:
            mgr.add_dac(zone_name, steps, set_zone_output)
            if zone_name == "Zone8":
                zone8_flag = True

        # If there is no Zone8 configured, add a dummy Zone8 [(0s, 0%)]
        if not zone8_flag:
            mgr.add_dac("Zone8", [(0.0, 0)], set_zone_output)

        # 4) Ensure we power-down when all zones complete.
        mgr.set_on_all_complete(self._on_all_zones_complete)

        # 5) Cache manager
        self.sequence_manager = mgr
        self.shared_data["sequence_manager"] = mgr

        # 6) Determine overall program length (max across zones)
        def zone_total(steps):
            return sum(d for (d, _p) in steps)

        total_seconds = max(zone_total(steps) for _name, steps in zone_sequences)
        print(f"[MultiPageController] Meal program total time = {total_seconds:.1f}s")

        # 7) Mark oven running and start
        try:
            oven_state.set_running(True)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(True) failed: {e}")

        try:
            mgr.start_all()
        except Exception as e:
            print(f"[MultiPageController] sequence_manager.start_all() failed: {e}")
            return 0.0

        return float(total_seconds)

    def stop_current_cook(self) -> None:
        """
        Stop any active CookingSequenceManager and power down zones.
        Safe to call even if nothing is running.
        """
        mgr = self.sequence_manager or self.shared_data.get("sequence_manager")
        if mgr:
            try:
                if hasattr(mgr, "stop_all"):
                    print("[MultiPageController] sequence_manager.stop_all()")
                    mgr.stop_all()
            except Exception as e:
                print(f"[MultiPageController] sequence_manager.stop_all failed: {e}")

        try:
            self.serial_all_zones_off()
        except Exception as e:
            print(
                f"[MultiPageController] serial_all_zones_off in stop_current_cook failed: {e}"
            )

        try:
            oven_state.set_running(False)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(False) failed: {e}")

    def pause_current_cook(self, cut_output: bool = True) -> None:
        """
        Optional: pause all zones while keeping the cook session alive.
        Not currently used by CookingPage, but ready for future Pause UI.
        """
        mgr = self.sequence_manager or self.shared_data.get("sequence_manager")
        if mgr and hasattr(mgr, "pause_all"):
            try:
                mgr.pause_all(cut_output)
            except Exception as e:
                print(f"[MultiPageController] pause_current_cook failed: {e}")

    def resume_current_cook(self) -> None:
        """
        Optional: resume all zones after a pause.
        """
        mgr = self.sequence_manager or self.shared_data.get("sequence_manager")
        if mgr and hasattr(mgr, "resume_all"):
            try:
                mgr.resume_all()
            except Exception as e:
                print(f"[MultiPageController] resume_current_cook failed: {e}")

    def start_reheat_cycle(self) -> float:
        """
        Simple reheat: all zones at 80% for shared_data['reheat_seconds'] seconds.
        Returns the total time in seconds for the UI countdown.
        """
        try:
            secs = float(self.shared_data.get("reheat_seconds", 0) or 0)
        except (TypeError, ValueError):
            secs = 0.0

        if secs <= 0:
            print("[MultiPageController] start_reheat_cycle: no reheat_seconds set")
            return 0.0

        power = 80
        print(f"[MultiPageController] Reheat cycle: {secs:.1f}s at {power}%")

        try:
            # mark oven running and energize all zones
            oven_state.set_running(True)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(True) failed: {e}")

        try:
            self.serial_all_zones(power)
        except Exception as e:
            print(f"[MultiPageController] serial_all_zones({power}) failed: {e}")

        # Reheat is “timer-only” – no sequence manager here.
        # CookingPage will later decide when it’s done and can call serial_all_zones_off().
        return secs

    # ------------------------------------------------------------------
    # Application-level actions
    # ------------------------------------------------------------------
    def exit_app(self) -> None:
        """Cleanly shut down the application."""
        self.root.destroy()


# ----------------------------------------------------------------------
# Self-test / harness
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1280x800")

    # root.overrideredirect(True) # remove the titlebar

    controller = MultiPageController(root)
    controller.show_HomePage()

    root.mainloop()

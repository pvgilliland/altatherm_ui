import customtkinter as ctk
from PIL import Image, ImageTk
import threading

from typing import Optional

# --- NEW: shared serial service ---
# from DoorSafety import DoorSafety
from SerialService import SerialService


# Pages import; these expect ui_bits.py to be in the same folder.
from SequenceProgramPage import SequenceProgramPage
from pages.beta_homePage import HomePage
from pages.prepare_cooking_page import PreparePage
from pages.help_page import HelpPage
from pages.select_meal import SelectMealPage
from pages.confirmation_page import ConfirmationPage
from pages.TimePowerPage import TimePowerPage
from pages.reheat_page import ReheatPage
from PhaseTimePowerPage import PhaseTimePowerPage
from SelectProgramPage import SelectProgramPage
from AboutPage import AboutPage
from TimePage import TimePage
from AutoMealsPage import AutoMealsPage
from pages.CircularProgressPage import CircularProgressPage
from CircularProgressPage_admin import CircularProgressPage_admin
from FoodReadyPage_admin import FoodReadyPage_admin
from FoodReadyPage import FoodReadyPage
from DiagnosticsPage import DiagnosticsPage
from HomePage import HomePage_admin
from pages.session_ended_page import SessionEndedPage  # <-- added
from hmi_logger import setup_logging
import oven_state

from utilities import load_use_sound_from_settings

from play_sound import load_sounds

###

import logging

logger = logging.getLogger("MultiPageController")

from hmi_consts import ASSETS_DIR, SETTINGS_DIR, PROGRAMS_DIR, HMISizePos, __version__


class zMultiPageController(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Hide window during construction to avoid seeing intermediate pages ---
        self.withdraw()

        self.title("CustomTkinter Multi-Page App (Controller Design)")
        self.geometry(HMISizePos.SCREEN_RES)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # need to pass CTk root to make the DoorSafety model UI thread safe
        DoorSafety.Instance().set_ui_root(self)

        self.is_admin = False  # <--- global admin flag lives here

        # --- window chrome & drag bar ---
        self.overrideredirect(True)
        self._drag_bar = ctk.CTkFrame(self, height=11, fg_color="#ACC6FF")
        self._drag_bar.place(x=0, y=0, relwidth=1)
        self._drag_bar.lift()
        self._offsetx = 0
        self._offsety = 0
        self._drag_bar.bind("<ButtonPress-1>", self._start_move)
        self._drag_bar.bind("<B1-Motion>", self._do_move)
        self._drag_bar.bind("<ButtonRelease-1>", self._stop_move)

        # --- clean close handlers ---
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        self.bind("<Escape>", lambda e: self._on_app_close())

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
        }

        # --- NEW: track pending fan-off timer ---
        self._fan_off_timer = None

        # --- NEW: create/start shared serial service (pages access via controller.serial) ---
        self.serial = SerialService(
            tk_root=self
        )  # optionally: port_hint="COM5" or "ACM"
        try:
            self.serial.start()
        except Exception as e:
            print("Serial start failed:", e)

        # Cache icons for SequenceProgramPage
        self.zone_icons = []
        for i in range(8):
            icon = Image.open(f"{ASSETS_DIR}/Zone{i+1}.png").resize((24, 24))
            self.zone_icons.append(
                ctk.CTkImage(light_image=icon, dark_image=icon, size=(24, 24))
            )

        # Instantiate all pages once (SessionEndedPage is created on demand)
        self.pages = {}
        for PageClass in (
            HomePage,
            PreparePage,
            TimePowerPage,
            HelpPage,
            SelectMealPage,
            ConfirmationPage,
            SequenceProgramPage,
            PhaseTimePowerPage,
            SelectProgramPage,
            ReheatPage,
            AboutPage,
            TimePage,
            AutoMealsPage,
            CircularProgressPage,
            FoodReadyPage,
            DiagnosticsPage,
            HomePage_admin,
            CircularProgressPage_admin,
            FoodReadyPage_admin,
        ):
            page = PageClass(controller=self, shared_data=self.shared_data)
            self.pages[PageClass] = page
            page.place(x=0, y=0, relwidth=1, relheight=1)

        # Track current page for lifecycle callbacks
        self.current_page = None

        # after self.serial.start()
        self.after(150, self.serial_get_door_switch)

        setup_logging("hmi")
        logger.info(f"HMI Started {[__version__]}")

        # load all the predefined sounds
        use_sound = load_use_sound_from_settings(default=True)
        self.shared_data["use_sound"] = use_sound
        self.set_use_sound(use_sound)

        # Start on HomePage after everything is built, then show the window
        self.after(0, self._show_initial_homepage)

    def _show_initial_homepage(self):
        """
        Show the correct HomePage (admin or normal) and then unhide
        the main window so the user never sees intermediate pages.
        """
        try:
            self.show_HomePage()
        finally:
            # Now that the correct page is visible, show the window
            self.deiconify()
            # Make sure the drag bar stays on top
            if hasattr(self, "_drag_bar"):
                try:
                    self._drag_bar.lift()
                except Exception:
                    pass

    # --- app close: cancel timer, stop serial cleanly, then destroy ---
    def _on_app_close(self):
        try:
            self._cancel_fan_off_timer()
        except Exception:
            pass
        try:
            if hasattr(self, "serial") and self.serial:
                self.serial.stop()
        except Exception:
            pass
        self.destroy()

    # drag handlers
    def _start_move(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def _do_move(self, event):
        x = self.winfo_pointerx() - self._offsetx
        y = self.winfo_pointery() - self._offsety
        self.geometry(f"+{x}+{y}")

    def _stop_move(self, event):
        self._offsetx = 0
        self._offsety = 0

    # ---------------- Navigation helpers (centralized) ----------------
    def show_page(self, page_class):
        """
        Centralized page show:
          - Call on_hide() on the currently visible page (if any).
          - Raise the requested page.
          - Call on_show() on the new page if it accepts no extra arguments.
        """
        if self.current_page and hasattr(self.current_page, "on_hide"):
            try:
                self.current_page.on_hide()
            except Exception as e:
                print(f"[MultiPageController] on_hide failed: {e}")

        target = self.pages[page_class]
        target.tkraise()
        self.current_page = target

        if hasattr(self, "_drag_bar"):
            try:
                self._drag_bar.lift()
            except Exception:
                pass

        if hasattr(target, "on_show"):
            try:
                # if CircularProgressPage_admin, don't call on_show, it messes up
                # the isManualMode setting
                if type(target) != CircularProgressPage_admin:
                    target.on_show()
            except TypeError:
                pass
            except Exception as e:
                print(f"[MultiPageController] on_show failed: {e}")

    def show_AutoMealsPage(self):
        self.show_page(AutoMealsPage)

    def show_HomePage(self):
        if self.is_admin:
            self.show_page(HomePage_admin)
        else:
            self.show_page(HomePage)

    def show_PreparePage(self):
        self.show_page(PreparePage)

    def show_HelpPage(self):
        self.show_page(HelpPage)

    def show_ConfirmationPage(self, item, on_confirm=None):
        page = self.pages[ConfirmationPage]
        print(item)
        page.set_item(item)
        if on_confirm:
            page.set_on_confirm(on_confirm)
        self.show_page(ConfirmationPage)

    def show_SelectMealPage(self, meals=None, on_select=None, on_leave_blank=None):
        self.show_page(SelectMealPage)

    def show_TimePowerPage(self):
        self.show_page(TimePowerPage)

    def show_AboutPage(self):
        self.show_page(AboutPage)

    def show_SequenceProgramPage(self, programNumber: int):
        page = self.pages[SequenceProgramPage]
        if hasattr(page, "on_show"):
            try:
                page.on_show(programNumber)
            except Exception as e:
                print(f"[MultiPageController] SequenceProgramPage.on_show failed: {e}")
        self.show_page(SequenceProgramPage)

    def show_ReheatPage(self):
        page = self.pages[ReheatPage]
        if hasattr(page, "on_show"):
            try:
                page.on_show()
            except Exception as e:
                print(f"[MultiPageController] ReheatPage.on_show failed: {e}")
        self.show_page(ReheatPage)

    def back_to_SequenceProgramPage(self):
        self.show_page(SequenceProgramPage)

    def show_PhaseTimePowerPage(self, title):
        page = self.pages[PhaseTimePowerPage]
        if hasattr(page, "set_title"):
            try:
                page.set_title(title)
            except Exception as e:
                print(f"[MultiPageController] PhaseTimePowerPage.set_title failed: {e}")
        self.show_page(PhaseTimePowerPage)

    def show_SelectProgramPage(self):
        page = self.pages[SelectProgramPage]
        if hasattr(page, "on_show"):
            try:
                page.on_show()
            except Exception as e:
                print(f"[MultiPageController] SelectProgramPage.on_show failed: {e}")
        self.show_page(SelectProgramPage)

    def show_TimePage(self):
        page = self.pages[TimePage]
        if hasattr(page, "on_show"):
            try:
                page.on_show()
            except Exception as e:
                print(f"[MultiPageController] TimePage.on_show failed: {e}")
        self.show_page(TimePage)

    def show_FoodReadyPage(self, auto_return_to=None, after_ms=3000):
        # Delay 2 seconds before showing the FoodReadyPage to give door lock
        # time to unlock
        def _show_page_after_delay():
            if not self.is_admin:
                page = self.pages[FoodReadyPage]
                self.show_page(FoodReadyPage)
                if hasattr(page, "on_show"):
                    try:
                        page.on_show()
                    except Exception as e:
                        print(
                            f"[MultiPageController] FoodReadyPage.on_show failed: {e}"
                        )
            else:
                page = self.pages[FoodReadyPage_admin]
                self.show_page(FoodReadyPage_admin)
                if hasattr(page, "on_show"):
                    try:
                        page.on_show()
                    except Exception as e:
                        print(
                            f"[MultiPageController] FoodReadyPage.on_show failed: {e}"
                        )

        # 2000 ms = 2 second delay
        self.after(2000, _show_page_after_delay)

    def show_DiagnosticsPage(self):
        page = self.pages[DiagnosticsPage]
        if hasattr(page, "on_show"):
            try:
                page.on_show()
            except Exception as e:
                print(f"[MultiPageController] DiagnosticsPage.on_show failed: {e}")
        self.show_page(DiagnosticsPage)

    def show_CircularProgressPage(
        self,
        seconds: int,
        on_stop=None,
        isManualCookMode: bool | None = None,
        time_power_page: Optional["TimePowerPage"] = None,
        powerLevel: int | None = None,
        reheat_mode: bool = False,
    ):
        if not self.is_admin:
            page = self.pages[CircularProgressPage]
            if hasattr(page, "on_show"):
                try:
                    page.on_show(
                        isManualCookMode,
                        time_power_page,
                        powerLevel,
                        reheat_mode=reheat_mode,
                    )
                except Exception as e:
                    print(
                        f"[MultiPageController] CircularProgressPage.on_show failed: {e}"
                    )

            self.show_page(CircularProgressPage)
            try:
                page.start(seconds, on_stop=on_stop)
            except Exception as e:
                print(f"[MultiPageController] CircularProgressPage.start failed: {e}")

        else:
            page = self.pages[CircularProgressPage_admin]
            if hasattr(page, "on_show"):
                try:
                    page.on_show(isManualCookMode, time_power_page, powerLevel)
                except Exception as e:
                    print(
                        f"[MultiPageController] CircularProgressPage_admin.on_show failed: {e}"
                    )
            self.show_page(CircularProgressPage_admin)
            try:
                page.start(seconds, on_stop=on_stop)
            except Exception as e:
                print(
                    f"[MultiPageController] CircularProgressPage_admin.start failed: {e}"
                )

    def show_SessionEndedPage(self, on_continue=None, on_unlock=None):
        """Create on demand and show the SessionEndedPage; allow resume callback injection."""
        page = self.pages.get(SessionEndedPage)
        if page is None:
            page = SessionEndedPage(controller=self, shared_data=self.shared_data)
            self.pages[SessionEndedPage] = page
            page.place(x=0, y=0, relwidth=1, relheight=1)

        # update callbacks
        page.on_continue = on_continue
        if on_unlock is not None:
            page.on_unlock = on_unlock

        self.show_page(SessionEndedPage)

    # legacy helpers
    def get_value(self, key):
        return self.shared_data[key].get()

    def set_value(self, key, value):
        self.shared_data[key].set(value)

    # ---------------- Serial Commands & Fan-Delay Logic ----------------

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
        except:
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
        if oven_state.get_running():
            oven_state.set_running(False)
            logger.info(f"Cook Cycle Ended")
        try:
            print("In serial_all_zones_off()")
            # Controller convention: broadcast Z00=000 to turn everything off
            self.serial.send("Z00=000")
            # Schedule fan off after delay (or immediately if delay=0)
            self._schedule_fan_off_after_delay()

        except Exception:
            pass

    # request the thermistor resisitances.
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

    def set_use_sound(self, use_sound: bool):
        load_sounds(use_sound)


if __name__ == "__main__":
    # HMISizePos.set_resolution("800x480")
    # HMISizePos.set_resolution("1024x600")
    HMISizePos.set_resolution("1280x800")
    app = MultiPageController()
    app.geometry(HMISizePos.SCREEN_RES)
    app.mainloop()

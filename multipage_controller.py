# multipage_controller.py

import customtkinter as ctk
from PIL import Image
import threading
import logging
import inspect
import time

from typing import Optional, Dict, Any, Callable

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
from hmi_consts import (
    ASSETS_DIR,
    SETTINGS_DIR,
    PROGRAMS_DIR,
    HMISizePos,
    HMIColors,
    __version__,
)
from helpers import restore_saved_fan_delay_settings
from hmi_logger import setup_logging
import oven_state

# program / sequence helpers
from SelectProgramPage import load_program_into_sequence_collection
from SequenceStructure import SequenceCollection
from CookingSequenceRunner import CookingSequenceManager

# ----------------------------
# ADMIN PAGES (ProjectA)
# ----------------------------
from HomePage_admin import HomePage_admin
from CircularProgressPage_admin import CircularProgressPage_admin
from FoodReadyPage_admin import FoodReadyPage_admin
from SequenceProgramPage import SequenceProgramPage
from PhaseTimePowerPage import PhaseTimePowerPage

# Optional admin pages (may not exist in ProjectB yet)
from TimePowerPage import TimePowerPage
from TimePage import TimePage
from SelectProgramPage import SelectProgramPage
from DiagnosticsPage import DiagnosticsPage

logger = logging.getLogger("MultiPageController")


class _AdminMasterProxy:
    """
    A proxy that is BOTH:
      - a valid Tk 'master' (has .tk / ._w / .children)
      - a controller (delegates show_* methods etc. to the real controller)

    This solves ProjectA pages that do:
      - super().__init__(controller, ...)     # treating controller as Tk master
      - controller.show_HomePage()            # treating same object as controller
    """

    def __init__(
        self, master_widget: ctk.CTkBaseClass, controller: "MultiPageController"
    ):
        self._master = master_widget
        self._controller = controller

        # Tkinter/CustomTkinter expects these
        self.tk = master_widget.tk
        self._w = master_widget._w
        self.children = master_widget.children

    def __getattr__(self, name: str):
        # Prefer controller methods/attrs first
        if hasattr(self._controller, name):
            return getattr(self._controller, name)
        # Fall back to widget attrs
        return getattr(self._master, name)


class _AdminPlaceholderPage(ctk.CTkFrame):
    """Simple placeholder so admin buttons don't crash if a page isn't copied in yet."""

    def __init__(self, parent, controller: "MultiPageController", title: str):
        super().__init__(parent, fg_color="black")
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=42, weight="bold"))
        lbl.grid(row=0, column=0, pady=(60, 20))

        sub = ctk.CTkLabel(
            self,
            text="(Placeholder page — wire real admin page when ready)",
            font=ctk.CTkFont(size=20),
        )
        sub.grid(row=1, column=0, pady=(0, 30))

        btn = ctk.CTkButton(
            self,
            text="Back",
            width=260,
            height=80,
            command=self.controller.show_HomePage,
        )
        btn.grid(row=2, column=0, pady=(0, 40))


class MultiPageController:
    """
    ProjectB Controller (ImageHotspotView) + Admin Overlay
    -----------------------------------------------------
    - Normal mode: ProjectB page *models* displayed via ImageHotspotView.set_page()
    - Admin mode: ProjectA CTkFrames displayed inside admin_container
    """

    _ADMIN_CLICKS_REQUIRED = 5
    _ADMIN_CLICKS_WINDOW_S = 3.0

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._suppress_finished_page = False  # flag for hard-cancel

        # Root grid must expand so overlay fills the window
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ----------------------------
        # ProjectB base UI: hotspot view
        # ----------------------------
        self.view = ImageHotspotView.get_instance(root)
        self.view.grid(row=0, column=0, sticky="nsew")

        # ----------------------------
        # Serial + DoorSafety
        # ----------------------------
        self.serial = SerialService(tk_root=root)
        try:
            self.serial.start()
        except Exception as e:
            print("Serial start failed:", e)

        DoorSafety.Instance().set_ui_root(root)

        # ----------------------------
        # Admin mode flag + logo click tracking
        # ----------------------------
        self.is_admin: bool = False
        self._logo_click_times: list[float] = []

        # ----------------------------
        # Shared data
        # ----------------------------
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
            "reheat_seconds": 0,
        }

        restore_saved_fan_delay_settings(self.shared_data)

        self._fan_off_timer: Optional[threading.Timer] = None

        # active CookingSequenceManager
        self.sequence_manager: Optional[CookingSequenceManager] = None
        self.shared_data["sequence_manager"] = None

        # Cache icons (still used elsewhere)
        self.zone_icons = []
        for i in range(8):
            icon = Image.open(f"{ASSETS_DIR}/Zone{i+1}.png").resize((24, 24))
            self.zone_icons.append(
                ctk.CTkImage(light_image=icon, dark_image=icon, size=(24, 24))
            )

        # ----------------------------
        # ProjectB pages (models)
        # ----------------------------
        self.home_page = HomePage(controller=self)
        self.select_meal_page = SelectMealPage(controller=self)
        self.prepare_for_cooking_page1 = PrepareForCookingPage1(controller=self)
        self.prepare_for_cooking_page2 = PrepareForCookingPage2(controller=self)
        self.start_cooking_confirm_page = StartCookingConfirmation(controller=self)
        self.cooking_page = CookingPage(controller=self)
        self.cooking_finished_page = CookingFinishedPage(controller=self)
        self.cooking_paused_page = CookingPausedPage(controller=self)

        self._current_page: Optional[Any] = None

        # after serial starts, give COM time to be ready
        self.after(2000, self.serial_get_door_switch)

        setup_logging("hmi")
        logger.info(f"HMI Started {[__version__]}")

        # ----------------------------
        # Admin overlay container + pages
        # ----------------------------
        self.admin_container = ctk.CTkFrame(self.root, fg_color=HMIColors.color_fg)
        self.admin_container.grid(row=0, column=0, sticky="nsew")
        self.admin_container.grid_rowconfigure(0, weight=1)
        self.admin_container.grid_columnconfigure(0, weight=1)
        self.admin_container.lower()  # hidden by default

        # Proxy that is a valid Tk master AND a controller
        self._admin_master_proxy = _AdminMasterProxy(self.admin_container, self)

        self._admin_current: Optional[ctk.CTkFrame] = None
        self.admin_pages: Dict[Any, ctk.CTkFrame] = {}

        # --- Admin navigation debounce / lock ---
        self._admin_nav_busy = False
        self._admin_nav_pending = None

        # Build admin pages (real or placeholders)
        self._build_admin_pages()

    # ------------------------------------------------------------------
    # Convenience proxies to root.after / after_cancel
    # ------------------------------------------------------------------
    def after(self, delay_ms: int, callback: Callable, *args):
        return self.root.after(delay_ms, callback, *args)

    def after_cancel(self, after_id):
        return self.root.after_cancel(after_id)

    # ------------------------------------------------------------------
    # ProjectB navigation (ImageHotspotView)
    # ------------------------------------------------------------------
    def show_page(self, page_obj) -> None:
        if self._current_page and hasattr(self._current_page, "on_hide"):
            try:
                self._current_page.on_hide()
            except Exception as e:
                print(f"WARNING: on_hide() failed on {self._current_page}: {e}")

        if hasattr(page_obj, "on_show"):
            try:
                page_obj.on_show()
            except TypeError:
                pass
            except Exception as e:
                print(f"WARNING: on_show() failed on {page_obj}: {e}")

        self._current_page = page_obj
        self.view.set_page(page_obj)

    # ------------------------------------------------------------------
    # Admin UI plumbing
    # ------------------------------------------------------------------
    def _safe_admin_construct(self, PageClass):
        """
        Robustly build ProjectA admin frames regardless of whether they expect:
          - (parent, controller, shared_data)
          - (controller, shared_data) where controller is ALSO used as Tk master
          - (parent, controller)
          - (parent)
        """

        # Pages that expect (controller, shared_data) where controller is also used as Tk master
        if PageClass.__name__ in (
            "SelectProgramPage",
            "TimePowerPage",
            "TimePage",
            "DiagnosticsPage",
            "SequenceProgramPage",
            "PhaseTimePowerPage",
        ):
            return PageClass(self._admin_master_proxy, self.shared_data)

        # Try to infer signature
        try:
            sig = inspect.signature(PageClass.__init__)
            params = list(sig.parameters.values())[1:]  # skip 'self'
            names = [p.name for p in params]
        except Exception:
            names = []

        # Case 1: explicit parent/master parameter exists
        if "parent" in names or "master" in names:
            parent_key = "parent" if "parent" in names else "master"
            kwargs = {parent_key: self.admin_container}
            if "controller" in names:
                kwargs["controller"] = self
            if "shared_data" in names:
                kwargs["shared_data"] = self.shared_data

            try:
                return PageClass(**kwargs)
            except Exception:
                try:
                    return PageClass(self.admin_container, self, self.shared_data)
                except TypeError:
                    try:
                        return PageClass(self.admin_container, self)
                    except TypeError:
                        return PageClass(self.admin_container)

        # Case 2: "controller" is first arg AND page explicitly expects controller-as-master
        if (
            len(names) >= 1
            and names[0] == "controller"
            and PageClass.__name__
            in ("CircularProgressPage_admin", "FoodReadyPage_admin")
        ):
            try:
                if "shared_data" in names:
                    return PageClass(self._admin_master_proxy, self.shared_data)
                return PageClass(self._admin_master_proxy)
            except Exception:
                pass

        # Case 3: common positional fallbacks
        try:
            return PageClass(self.admin_container, self, self.shared_data)
        except TypeError:
            pass
        try:
            return PageClass(self.admin_container, self)
        except TypeError:
            pass

        return PageClass(self.admin_container)

    def _register_admin_page(self, key: Any, frame: ctk.CTkFrame) -> None:
        self.admin_pages[key] = frame
        # Grid ONCE — never remove again
        frame.grid(row=0, column=0, sticky="nsew")
        frame.lower()

    def _build_admin_pages(self) -> None:
        self.admin_pages = {}

        # Required admin pages (always class-keyed)
        for PageClass in (
            HomePage_admin,
            CircularProgressPage_admin,
            FoodReadyPage_admin,
        ):
            frame = self._safe_admin_construct(PageClass)
            self._register_admin_page(PageClass, frame)

        # Optional admin pages (class-keyed; placeholder is registered under the class too)
        for OptionalClass, placeholder_title in (
            (TimePowerPage, "Time + Power (TODO)"),
            (TimePage, "Fan Delay (TODO)"),
            (DiagnosticsPage, "Diagnostics (TODO)"),
            (SelectProgramPage, "Select Program (TODO)"),
        ):
            try:
                frame = self._safe_admin_construct(OptionalClass)
            except Exception as e:
                print(f"[Admin] {OptionalClass.__name__} construct failed: {e}")
                frame = _AdminPlaceholderPage(
                    self.admin_container, self, placeholder_title
                )
            self._register_admin_page(OptionalClass, frame)

        # Sequence Program Editor (class-keyed)
        try:
            frame = self._safe_admin_construct(SequenceProgramPage)
        except Exception:
            frame = _AdminPlaceholderPage(
                self.admin_container, self, "Sequence Program (TODO)"
            )
        self._register_admin_page(SequenceProgramPage, frame)

        # Phase Time/Power Editor (class-keyed)
        try:
            frame = self._safe_admin_construct(PhaseTimePowerPage)
        except Exception as e:
            print(f"[Admin] PhaseTimePowerPage construct failed: {e}")
            frame = _AdminPlaceholderPage(
                self.admin_container, self, "Phase Time + Power (TODO)"
            )
        self._register_admin_page(PhaseTimePowerPage, frame)

        # Backward-compat convenience (some pages do controller.pages.get(<Class>))
        self.pages = self.admin_pages

    def _show_admin_page(self, key: Any) -> None:
        # If we're already switching pages, remember the *latest* request and return.
        if getattr(self, "_admin_nav_busy", False):
            self._admin_nav_pending = key
            return

        frame = self.admin_pages.get(key)
        if frame is None:
            print(f"[MultiPageController] Unknown admin page key: {key}")
            return

        if self._admin_current is frame:
            self._admin_nav_busy = False
            self._admin_nav_pending = None
            return

        # Acquire lock for this navigation
        self._admin_nav_busy = True
        self._admin_nav_pending = None

        # lifecycle: hide prior
        if self._admin_current and hasattr(self._admin_current, "on_hide"):
            try:
                self._admin_current.on_hide()
            except Exception:
                pass

        # Raise immediately (fast visual response)
        frame.tkraise()
        self._admin_current = frame

        # Run on_show *after* this click handler returns to the event loop
        def _finish_switch():
            try:
                if hasattr(frame, "on_show") and (
                    key is not CircularProgressPage_admin
                ):
                    try:
                        frame.on_show()
                    except TypeError:
                        frame.on_show()
            except Exception:
                pass
            finally:
                # release lock shortly after, so rapid double-clicks don’t wedge the UI
                def _release():
                    self._admin_nav_busy = False
                    pending = self._admin_nav_pending
                    self._admin_nav_pending = None
                    if pending is not None and pending != key:
                        self._show_admin_page(pending)

                self.after(120, _release)  # tweak 80–200ms if you want

        self.after(0, _finish_switch)

    def enter_admin_mode(self) -> None:
        if self.is_admin:
            return

        self.is_admin = True

        # Reset admin nav debounce state (prevents "stuck" page on re-enter)
        self._admin_nav_busy = False
        self._admin_nav_pending = None

        # DO NOT grid_remove the view
        # DO NOT grid() the admin_container here

        # Bring the admin layer to the front
        try:
            self.admin_container.tkraise()
        except Exception:
            pass

        # Always start at Admin Home
        self._show_admin_page(HomePage_admin)

    def exit_admin_mode(self) -> None:
        if not self.is_admin:
            return

        self.is_admin = False

        # Reset admin nav debounce state
        self._admin_nav_busy = False
        self._admin_nav_pending = None

        # DO NOT grid_remove/grid anything here — just raise the normal layer
        try:
            self.view.tkraise()
        except Exception:
            pass

    # ----- optional: 5-click easter egg -----
    def register_logo_click(self) -> None:
        now = time.monotonic()
        self._logo_click_times.append(now)
        cutoff = now - self._ADMIN_CLICKS_WINDOW_S
        self._logo_click_times = [t for t in self._logo_click_times if t >= cutoff]

        if len(self._logo_click_times) >= self._ADMIN_CLICKS_REQUIRED:
            self._logo_click_times.clear()
            self.enter_admin_mode()

    def on_logo_easter_egg(self) -> None:
        self.enter_admin_mode()

    # ------------------------------------------------------------------
    # show_* methods (ProjectB preserved + admin routing)
    # ------------------------------------------------------------------
    def show_HomePage(self) -> None:
        if self.is_admin:
            self._show_admin_page(HomePage_admin)
        else:
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
        self.cooking_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.cooking_page)

    def show_CookingFinishedPage(self) -> None:
        self.show_page(self.cooking_finished_page)

    def show_CookingPausedPage(self) -> None:
        self.cooking_paused_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.cooking_paused_page)

    # ---- Admin pages called by HomePage_admin ----
    def show_TimePowerPage(self) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_TimePowerPage called in normal mode; ignoring."
            )
            return
        self._show_admin_page(TimePowerPage)

    def show_TimePage(self) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_TimePage called in normal mode; ignoring."
            )
            return
        self._show_admin_page(TimePage)

    def show_DiagnosticsPage(self) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_DiagnosticsPage called in normal mode; ignoring."
            )
            return
        self._show_admin_page(DiagnosticsPage)

    def show_SelectProgramPage(self) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_SelectProgramPage called in normal mode; ignoring."
            )
            return
        self._show_admin_page(SelectProgramPage)

    # Admin-enabled versions
    def show_CircularProgressPage(
        self,
        seconds: int,
        on_stop=None,
        isManualCookMode: bool | None = None,
        time_power_page: Optional[Any] = None,
        powerLevel: int | None = None,
        reheat_mode: bool = False,
    ) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_CircularProgressPage ignored in normal mode (ProjectB)"
            )
            return

        page = self.admin_pages.get(CircularProgressPage_admin)
        if page is None:
            print("[MultiPageController] CircularProgressPage_admin not constructed")
            return

        # IMPORTANT: tell the page the manual mode + power BEFORE starting
        try:
            if hasattr(page, "on_show"):
                page.on_show(isManualCookMode, time_power_page, powerLevel)
        except Exception as e:
            print(
                f"[MultiPageController] CircularProgressPage_admin.on_show failed: {e}"
            )

        self._show_admin_page(CircularProgressPage_admin)

        try:
            page.start(seconds, on_stop=on_stop)
        except Exception as e:
            print(f"[MultiPageController] CircularProgressPage_admin.start failed: {e}")

    def show_FoodReadyPage(self, auto_return_to=None, after_ms=3000) -> None:
        if not self.is_admin:
            self.show_CookingFinishedPage()
            return

        def _show():
            self._show_admin_page(FoodReadyPage_admin)

        self.after(2000, _show)

    def show_SequenceProgramPage(self, program_number: int) -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_SequenceProgramPage called in normal mode; ignoring."
            )
            return

        page = self.admin_pages.get(SequenceProgramPage)
        if page is None:
            print("[MultiPageController] SequenceProgramPage not constructed")
            return

        self._show_admin_page(SequenceProgramPage)

        # Call on_show(programNumber) if present
        try:
            if hasattr(page, "on_show"):
                page.on_show(program_number)
        except Exception as e:
            print(f"[MultiPageController] SequenceProgramPage.on_show failed: {e}")

    def back_to_SequenceProgramPage(self) -> None:
        if not self.is_admin:
            return
        self._show_admin_page(SequenceProgramPage)

    def show_PhaseTimePowerPage(self, title: str = "") -> None:
        if not self.is_admin:
            print(
                "[MultiPageController] show_PhaseTimePowerPage called in normal mode; ignoring."
            )
            return

        page = self.admin_pages.get(PhaseTimePowerPage)
        if page is None:
            print("[MultiPageController] PhaseTimePowerPage not constructed")
            return

        self._show_admin_page(PhaseTimePowerPage)

        # Update title + load current selection into the numeric inputs
        try:
            if hasattr(page, "set_title"):
                page.set_title(title)
            elif hasattr(page, "on_show"):
                try:
                    page.on_show(title)
                except TypeError:
                    page.on_show()
        except Exception as e:
            print(f"[MultiPageController] PhaseTimePowerPage title/show failed: {e}")

    # ------------------------------------------------------------------
    # Serial commands + fan off logic (unchanged from ProjectB)
    # ------------------------------------------------------------------
    def _cancel_fan_off_timer(self):
        t = getattr(self, "_fan_off_timer", None)
        if t and t.is_alive():
            try:
                t.cancel()
            except Exception:
                pass
        self._fan_off_timer = None

    def _schedule_fan_off_after_delay(self):
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

    def serial_zone(self, zone: int, power: int):
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
            logger.info("Cook Cycle Ended")
        try:
            print("In serial_all_zones_off()")
            self.serial.send("Z00=000")
            self._schedule_fan_off_after_delay()
        except Exception:
            pass

    def serial_get_thermistor(self):
        self.serial.send("R")

    def serial_get_versions(self):
        self.serial.send("I")

    def serial_get_IR_temp(self, sensor: int):
        self.serial.send(f"T{sensor}")

    def serial_get_door_switch(self):
        self.serial.send("D")

    def serial_get_door_lock(self):
        self.serial.send("L")

    def serial_door_lock(self, on: bool):
        self.serial.send("L=" + ("1" if on else "0"))

    def serial_get_fan(self):
        self.serial.send("F")

    def serial_fan(self, on: bool):
        self.serial.send("F=" + ("1" if on else "0"))

    # ask the controller for the power supply zone voltages
    # returns "V=nn.n,nn.n,nn.n,nn.n,nn.n,nn.n,nn.n,nn.n\r" for the 8 zones
    def serial_power_supply_diagnostics(self):
        self.serial.send("V")  # Get power supply zone voltages
        self.serial.send("P")  # Get Fan current

    # ------------------------------------------------------------------
    # Cooking sequence lifecycle (unchanged from ProjectB)
    # ------------------------------------------------------------------
    def _on_all_zones_complete(self):
        try:
            self.serial_all_zones_off()
        except Exception as e:
            print(f"[MultiPageController] serial_all_zones_off failed: {e}")

        try:
            oven_state.set_running(False)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(False) failed: {e}")

        if getattr(self, "_suppress_finished_page", False):
            print("[MultiPageController] Hard stop: suppressing CookingFinishedPage")
            self._suppress_finished_page = False
            return

        try:
            self.after(0, self.show_CookingFinishedPage)
        except Exception as e:
            print(f"[MultiPageController] show_CookingFinishedPage failed: {e}")

    def start_meal_program(self, meal_index: int) -> float:
        self._suppress_finished_page = False
        if meal_index is None:
            print("[MultiPageController] start_meal_program: meal_index is None")
            return 0.0

        program_number = meal_index + 31
        print(f"[MultiPageController] Starting meal program {program_number}")

        try:
            load_program_into_sequence_collection(program_number)
        except Exception as e:
            print(
                f"[MultiPageController] load_program_into_sequence_collection({program_number}) failed: {e}"
            )
            return 0.0

        sc = SequenceCollection.Instance()
        zone_sequences: list[tuple[str, list[tuple[float, float]]]] = []

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

        mgr = CookingSequenceManager()

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

        zone8_flag = False
        for zone_name, steps in zone_sequences:
            mgr.add_dac(zone_name, steps, set_zone_output)
            if zone_name == "Zone8":
                zone8_flag = True

        if not zone8_flag:
            mgr.add_dac("Zone8", [(0.0, 0)], set_zone_output)

        mgr.set_on_all_complete(self._on_all_zones_complete)

        self.sequence_manager = mgr
        self.shared_data["sequence_manager"] = mgr

        def zone_total(steps):
            return sum(d for (d, _p) in steps)

        total_seconds = max(zone_total(steps) for _name, steps in zone_sequences)
        print(f"[MultiPageController] Meal program total time = {total_seconds:.1f}s")

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
            print(f"[MultiPageController] serial_all_zones_off failed: {e}")

        try:
            oven_state.set_running(False)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(False) failed: {e}")

    def pause_current_cook(self, cut_output: bool = True) -> None:
        mgr = self.sequence_manager or self.shared_data.get("sequence_manager")
        if mgr and hasattr(mgr, "pause_all"):
            try:
                mgr.pause_all(cut_output)
            except Exception as e:
                print(f"[MultiPageController] pause_current_cook failed: {e}")

    def resume_current_cook(self) -> None:
        mgr = self.sequence_manager or self.shared_data.get("sequence_manager")
        if mgr and hasattr(mgr, "resume_all"):
            try:
                mgr.resume_all()
            except Exception as e:
                print(f"[MultiPageController] resume_current_cook failed: {e}")

    def start_reheat_cycle(self) -> float:
        self._suppress_finished_page = False
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
            oven_state.set_running(True)
        except Exception as e:
            print(f"[MultiPageController] oven_state.set_running(True) failed: {e}")

        try:
            self.serial_all_zones(power)
        except Exception as e:
            print(f"[MultiPageController] serial_all_zones({power}) failed: {e}")

        return secs

    def get(self, key, default=None):
        """Compatibility shim for ProjectA admin pages that treat controller like a dict."""
        try:
            return self.shared_data.get(key, default)
        except Exception:
            return default

    def exit_app(self) -> None:
        self.root.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1280x800")
    # root.overrideredirect(True)
    HMISizePos.set_resolution("1280x800")

    # REQUIRED: give DoorSafety the UI root
    DoorSafety.Instance().set_ui_root(root)

    controller = MultiPageController(root)
    controller.show_HomePage()

    root.mainloop()

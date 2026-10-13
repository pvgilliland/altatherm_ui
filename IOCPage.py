"""IOC (AltaTherm Cure Station) admin page.

Reuses SequenceProgramPage's actual sequence editor, model synchronization,
Run/Save, duplication, and phase editing. Hardware pulse wiring is deliberately
not invented: provide controller.set_ioc_pulse_enabled(bool) when supported.
"""
import logging
import queue
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from PIL import Image

from SequenceProgramPage import SequenceProgramPage
from hmi_consts import ASSETS_DIR, HMIColors, HMISizePos, LightOnly

log = logging.getLogger(__name__)


class IOCPage(SequenceProgramPage):
    """IOC controls above the existing sequence editor."""

    def _build_ui(self):
        # Build and preserve the original sequence editor and its functionality.
        super()._build_ui()

        self._header.grid_configure(row=1)
        self._table.grid_configure(row=2)
        self._footer.grid_configure(row=3)
        # Reserve actual vertical space for IOC controls. The inherited eight-row
        # editor otherwise consumes it and clips the radio buttons/thermistors.
        self.grid_rowconfigure(0, weight=0, minsize=190)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)

        # Allow all six rows to grow and occupy the entire available table area.
        self.DESIRED_ROW_H = 72
        self.MIN_ROW_H = 34
        self.DESIRED_PILL_H = 40
        self.MIN_PILL_H = 26

        # IOC uses six physical heater zones, not the eight-zone editor.
        # Keep inherited widgets internally for compatibility, but do not
        # display or allow the final two zones in an IOC program.
        for row in self.step_widgets[6:]:
            row.grid_remove()
        for index in (6, 7, 8):
            self._table.grid_rowconfigure(index, minsize=0, weight=0)
        for index in range(6):
            self._table.grid_rowconfigure(index, weight=1)

        background = LightOnly.FG
        blue = HMIColors.color_blue
        foreground = LightOnly.ROW_TEXT
        self._ioc_top = ctk.CTkFrame(self, fg_color=background, corner_radius=0)
        self._ioc_top.grid(row=0, column=0, sticky="nsew",
                           padx=20, pady=(8, 4))
        self._ioc_top.grid_columnconfigure(0, weight=1)
        self._ioc_top.grid_rowconfigure(0, weight=1)

        # Three independent columns prevent the heading from covering controls.
        # Left: IOC switches/readouts; middle: page heading; right: zone map.
        content = ctk.CTkFrame(self._ioc_top, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)
        content.grid_columnconfigure(2, weight=0)

        self.ioc_title = ctk.CTkLabel(
            content,
            text="IOC Cure Station",
            font=ctk.CTkFont(
                family="Arial", size=HMISizePos.s(23),
                weight="bold", underline=True,
            ),
            text_color=foreground,
            fg_color="transparent",
        )
        self.ioc_title.grid(row=0, column=1, sticky="n", padx=(6, 6), pady=(0, 0))

        controls = ctk.CTkFrame(content, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="nw", padx=(0, HMISizePos.sx(8)))
        controls.grid_columnconfigure(0, weight=0)
        controls.grid_columnconfigure(1, weight=0)

        heading_font = ctk.CTkFont(family="Arial", size=HMISizePos.s(18), weight="bold")
        value_font = ctk.CTkFont(family="Arial", size=HMISizePos.s(15))
        # Radio groups share one Tk variable per function so each selection
        # is mutually exclusive.  The callbacks also update the hardware.
        self.pulse_enabled = False
        self.fan_enabled = False
        self.pulse_choice = tk.IntVar(master=self, value=0)
        self.fan_choice = tk.IntVar(master=self, value=0)
        radio_style = dict(
            font=value_font, text_color=foreground,
            fg_color=blue, hover_color=blue,
            border_color=foreground, radiobutton_width=HMISizePos.s(21),
            radiobutton_height=HMISizePos.s(21),
        )

        ctk.CTkLabel(controls, text="PULSE ACTION:", font=heading_font, text_color=foreground).grid(
            row=0, column=0, rowspan=2, sticky="e", padx=(0, HMISizePos.sx(14)))
        self.pulse_on_radio = ctk.CTkRadioButton(
            controls, text="ENABLED", variable=self.pulse_choice, value=1,
            command=lambda: self._set_pulse(True), **radio_style)
        self.pulse_off_radio = ctk.CTkRadioButton(
            controls, text="DISABLED", variable=self.pulse_choice, value=0,
            command=lambda: self._set_pulse(False), **radio_style)
        self.pulse_on_radio.grid(row=0, column=1, sticky="w", pady=2)
        self.pulse_off_radio.grid(row=1, column=1, sticky="w", pady=2)

        ctk.CTkLabel(controls, text="COOLING FANS:", font=heading_font, text_color=foreground).grid(
            row=2, column=0, rowspan=2, sticky="e", padx=(0, HMISizePos.sx(14)), pady=(6, 0))
        self.fan_on_radio = ctk.CTkRadioButton(
            controls, text="ON", variable=self.fan_choice, value=1,
            command=lambda: self._set_fan(True), **radio_style)
        self.fan_off_radio = ctk.CTkRadioButton(
            controls, text="OFF", variable=self.fan_choice, value=0,
            command=lambda: self._set_fan(False), **radio_style)
        self.fan_on_radio.grid(row=2, column=1, sticky="w", pady=(6, 2))
        self.fan_off_radio.grid(row=3, column=1, sticky="w", pady=2)

        ctk.CTkLabel(controls, text="THERMISTORS:", font=heading_font, text_color=foreground).grid(
            row=4, column=0, rowspan=2, sticky="e", padx=(0, HMISizePos.sx(14)), pady=(6, 0))
        self.thermistor_1_var = tk.StringVar(master=self, value="T1=XXXXX")
        self.thermistor_2_var = tk.StringVar(master=self, value="T2=XXXXX")
        self.t1_label = ctk.CTkLabel(controls, textvariable=self.thermistor_1_var,
                                     font=value_font, text_color=foreground, anchor="w")
        self.t2_label = ctk.CTkLabel(controls, textvariable=self.thermistor_2_var,
                                     font=value_font, text_color=foreground, anchor="w")
        self.t1_label.grid(row=4, column=1, sticky="w", pady=(6, 0))
        self.t2_label.grid(row=5, column=1, sticky="w")

        # Right-aligned station graphic, loaded from the project assets folder.
        # Keep a reference to CTkImage so Tk does not discard it.
        zone_image_path = Path(ASSETS_DIR) / "IOC_Zones.png"
        with Image.open(zone_image_path) as source_image:
            zone_image = source_image.convert("RGB")

        # Preserve the original image aspect ratio inside the top panel.
        max_width = HMISizePos.sx(285)
        max_height = HMISizePos.sy(150)
        image_scale = min(max_width / zone_image.width,
                          max_height / zone_image.height)
        image_size = (max(1, round(zone_image.width * image_scale)),
                      max(1, round(zone_image.height * image_scale)))
        self.ioc_zones_image = ctk.CTkImage(
            light_image=zone_image,
            dark_image=zone_image,
            size=image_size,
        )
        self.ioc_zones_label = ctk.CTkLabel(
            content, image=self.ioc_zones_image, text="",
            fg_color="transparent", width=image_size[0], height=image_size[1],
        )
        self.ioc_zones_label.grid(
            row=0, column=2, sticky="ne", padx=(HMISizePos.sx(8), 0)
        )

        # Received lines can originate on a serial worker thread; drain on Tk's
        # event loop rather than touching StringVars/widgets from that worker.
        self.oven_ctrl_serial = getattr(self.controller, "oven_ctrl_serial", None)
        self._serial_lines = queue.Queue(maxsize=100)
        self._serial_listening = False
        self._serial_poll_job = None
        self._serial_ui_job = None
        self._ioc_visible = False

        # Start disabled: IOC Run depends on Pulse Action only.
        self._update_run_button_state()

        # Radio buttons reflect their IntVar; no manual color refresh needed.

    def _set_pulse(self, enabled: bool):
        # No documented pulse serial command in supplied controller: UI state only
        # until an appropriate controller API is provided.
        setter = getattr(self.controller, "set_ioc_pulse_enabled", None)
        if callable(setter):
            try:
                setter(enabled)
            except Exception:
                log.exception("Could not set IOC pulse")
                self.pulse_choice.set(int(self.pulse_enabled))
                return
        else:
            log.info("IOC pulse selection changed; hardware pulse command not configured")
        self.pulse_enabled = enabled
        self.pulse_choice.set(int(enabled))
        self._update_run_button_state()

    def on_door_change(self, is_open: bool):
        """Ignore door status on the IOC page; Run depends only on Pulse Action."""
        pass

    def _update_run_button_state(self):
        """Enable Run when Pulse Action is enabled, regardless of door status."""
        if not hasattr(self, "run_button") or self.run_button is None:
            return

        allowed = bool(getattr(self, "pulse_enabled", False))
        self.run_button_font.configure(overstrike=not allowed)
        self.run_button.configure(
            state="normal" if allowed else "disabled",
            border_color=(
                HMIColors.color_blue if allowed
                else HMIColors.DISABLED_BORDER_COLOR
            ),
            text="Run" if allowed else "Run\n(Pulse Disabled)",
        )

    def on_run(self):
        """Prevent starting an IOC program unless Pulse Action is enabled."""
        if not getattr(self, "pulse_enabled", False):
            self._update_run_button_state()
            log.warning("IOC Run blocked: pulse disabled")
            return
        # Tell the shared cook/progress logic that the IOC cooling fans are
        # manually controlled. Its fan-delay expiry handler must not switch
        # the fan off for this run.
        self.shared_data["ioc_keep_fan_on"] = True
        # Prevent a previous cook's pending delayed fan-off from firing during IOC.
        cancel_timer = getattr(self.controller, "_cancel_fan_off_timer", None)
        if callable(cancel_timer):
            cancel_timer()
        super().on_run()

    def _set_fan(self, enabled: bool):
        try:
            self.controller.serial_fan(enabled)
        except Exception:
            log.exception("Could not set IOC cooling fan")
            self.fan_choice.set(int(self.fan_enabled))
            return
        self.fan_enabled = enabled
        self.fan_choice.set(int(enabled))

    def update_thermistors(self, t1, t2):
        """Feed this from the existing thermistor serial response parser."""
        self.thermistor_1_var.set(f"T1={t1}")
        self.thermistor_2_var.set(f"T2={t2}")

    def _on_serial_line(self, line: str) -> None:
        """SerialService callback; do not access Tk widgets from this callback."""
        if not self._ioc_visible:
            return
        line = str(line).strip()
        if not (line.startswith("R=") or line.startswith("F=")):
            return
        try:
            self._serial_lines.put_nowait(line)
        except queue.Full:
            log.warning("IOC serial receive queue full; dropping response: %s", line)

    def _process_serial_lines(self):
        """Handle queued serial responses on the Tk main thread."""
        self._serial_ui_job = None
        if not self._ioc_visible:
            return
        for _ in range(100):
            try:
                line = self._serial_lines.get_nowait()
            except queue.Empty:
                break
            if line.startswith("R="):
                readings = [part.strip() for part in line[2:].split(",")]
                if len(readings) >= 2 and readings[0] and readings[1]:
                    self.update_thermistors(readings[0], readings[1])
                else:
                    log.warning("Unexpected IOC thermistor response: %s", line)
            elif line.startswith("F="):
                status = line[2:].strip()
                if status in ("0", "1"):
                    self.fan_enabled = status == "1"
                    self.fan_choice.set(int(self.fan_enabled))
        self._serial_ui_job = self.after(100, self._process_serial_lines)

    def _poll_thermistors(self):
        """Request updated readings once a second while IOC is visible."""
        self._serial_poll_job = None
        if not self._ioc_visible:
            return
        try:
            self.controller.serial_get_thermistor()  # sends "R"
        except Exception:
            log.exception("IOC thermistor request failed")
        self._serial_poll_job = self.after(1000, self._poll_thermistors)

    def on_show(self, programNumber=None):
        if programNumber is None:
            programNumber = self.shared_data.get("ioc_program_number", 1)
        self.shared_data["ioc_program_number"] = int(programNumber)
        # Returning from PhaseTimePowerPage must not reload the saved program:
        # it would overwrite edits that have not yet been saved to disk.
        skip_refresh = self.shared_data.pop("ioc_skip_program_refresh_once", False)
        if skip_refresh:
            self.programNumber = int(programNumber)
            self.program_label.configure(text=f"Program {programNumber}")
        else:
            super().on_show(int(programNumber))

        if self._ioc_visible:
            return  # do not register duplicate listeners / timers
        self._ioc_visible = True
        if self.oven_ctrl_serial is not None:
            try:
                self.oven_ctrl_serial.add_listener(self._on_serial_line)
                self._serial_listening = True
            except Exception:
                log.exception("IOC failed to attach oven serial listener")
        self._process_serial_lines()
        # Read actual fan state rather than assuming it is OFF.
        try:
            self.controller.serial_get_fan()  # sends "F"
        except Exception:
            log.exception("IOC fan status request failed")
        self._poll_thermistors()

    def on_hide(self):
        """Stop polling and detach the listener when navigating away."""
        self._ioc_visible = False
        for job_name in ("_serial_poll_job", "_serial_ui_job"):
            job = getattr(self, job_name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except (tk.TclError, ValueError):
                    pass
                setattr(self, job_name, None)
        if self._serial_listening and self.oven_ctrl_serial is not None:
            try:
                self.oven_ctrl_serial.remove_listener(self._on_serial_line)
                self._serial_listening = False
            except Exception:
                log.exception("IOC failed to detach oven serial listener")
        while True:
            try:
                self._serial_lines.get_nowait()
            except queue.Empty:
                break

    def _on_row_selected(self, row_1based, col_index_or_none):
        if col_index_or_none is not None:
            # Synchronize the current IOC widget values before phase editing.
            self.sync_to_model()
            self.shared_data["phase_return_page"] = "IOC"
        super()._on_row_selected(row_1based, col_index_or_none)

    def _set_selected_row(self, row_1based: int):
        # In IOC mode there is no seventh destination for Duplicate.
        if not 1 <= row_1based <= 6:
            return
        super()._set_selected_row(row_1based)
        if row_1based == 6:
            self.duplicate_btn.grid_forget()

    def _resize_rows(self):
        """Expand six sequence rows to fill the table above the footer.

        The original SequenceProgramPage caps row height at 44/45 pixels and
        reserves a weighted filler row (index 8). Both cause the large empty
        area visible below row 6 on the IOC page.
        """
        if not getattr(self, "_table", None) or not hasattr(self, "step_widgets"):
            return
        if not hasattr(self, "_ioc_top"):
            return  # Superclass schedules a resize before IOC setup is complete.

        table_height = self._table.winfo_height()
        if table_height <= 1:
            return

        # One pixel above and below each row; distribute remaining height.
        gap = 1
        usable_height = max(0, table_height - 6 * 2 * gap)
        row_height = max(self.MIN_ROW_H, usable_height // 6)
        pill_height = max(
            self.MIN_PILL_H,
            min(self.DESIRED_PILL_H, int(row_height * 0.66)),
        )

        for i, row in enumerate(self.step_widgets[:6]):
            row.set_row_height(row_height, pill_height)
            row.grid_configure(sticky="nsew", pady=(gap, gap))
            self._table.grid_rowconfigure(i, minsize=row_height + 2 * gap, weight=1)

        # The inherited editor's row 8 is a weighted blank filler: remove it.
        for i in (6, 7, 8):
            self._table.grid_rowconfigure(i, minsize=0, weight=0)

    def sync_to_model(self):
        # Run and Save call this method. Explicitly clear hidden zones 7/8
        # so a previously loaded eight-zone program cannot energize them.
        super().sync_to_model()
        from SequenceStructure import SequenceCollection
        collection = SequenceCollection.Instance()
        for index in (6, 7):
            zone = collection.get_zone_sequence_by_index(index)
            if zone:
                for step in zone.steps:
                    step.power = 0
                    step.duration = 0.0

# SelectProgramPage.py
import customtkinter as ctk
from dataclasses import dataclass
from typing import Any, Dict, List
from hmi_consts import HMIColors, HMISizePos, ASSETS_DIR, PROGRAMS_DIR
from PIL import Image
import os, json
from SequenceStructure import SequenceCollection  # uses to_dict/from_dict/load/save


########## Helper functions, not part of any class ##########
PROGRAM_COUNT = 36
os.makedirs(PROGRAMS_DIR, exist_ok=True)


def _program_path(idx: int) -> str:
    return os.path.join(PROGRAMS_DIR, f"program{idx}.alt")


def _format_total_time(seconds_total: float) -> str:
    total = max(0, int(round(seconds_total)))
    if total >= 3600:
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h}:{m:02d}"
    else:
        m = total // 60
        s = total % 60
        return f"{m:02d}:{s:02d}"


def _compute_total_time_from_zone_sequences(
    zone_sequences: List[Dict[str, Any]],
) -> str:
    # zones run in parallel → overall = max(zone_total_seconds)
    zone_totals = []
    for z in zone_sequences or []:
        steps = z.get("steps", [])
        z_total = 0.0
        for st in steps:
            try:
                z_total += float(st.get("duration", 0.0))
            except Exception:
                pass
        zone_totals.append(z_total)
    overall = max(zone_totals) if zone_totals else 0.0
    return _format_total_time(overall)


def _new_default_program_dict(idx: int) -> Dict[str, Any]:
    """
    Create a default file payload using SequenceCollection's zeroed init:
      - description
      - zone_sequences from SequenceCollection.to_dict()
      - total_time computed from zone data (00:00)
    """
    sc = SequenceCollection.Instance()  # already initialized with zeros
    d = sc.to_dict()  # {"zone_sequences": [...]}
    zone_sequences = d.get("zone_sequences", [])
    total_time = _compute_total_time_from_zone_sequences(zone_sequences)
    return {
        "description": f"Program {idx}",
        "zone_sequences": zone_sequences,
        "total_time": total_time,
    }


def save_program_from_sequence_collection(idx: int, description: str = None) -> None:
    """
    Persist the CURRENT SequenceCollection singleton to program{idx}.alt.
    Optionally update description.
    """
    path = _program_path(idx)
    sc = SequenceCollection.Instance()
    data = sc.to_dict()  # {"zone_sequences": [...]}
    zone_sequences = data.get("zone_sequences", [])
    payload = {
        "description": description if description is not None else f"Program {idx}",
        "zone_sequences": zone_sequences,
        "total_time": _compute_total_time_from_zone_sequences(zone_sequences),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def load_program_into_sequence_collection(idx: int) -> Dict[str, Any]:
    """
    Load program{idx}.alt. If missing/corrupt, create default.
    Hydrates the SequenceCollection singleton from the file's zone_sequences.
    Returns the loaded payload dict.
    """
    path = _program_path(idx)
    payload = None
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                payload = json.load(f)
            if not isinstance(payload, dict) or "zone_sequences" not in payload:
                raise ValueError("Invalid payload")
        except Exception:
            payload = None

    if payload is None:
        # Create default and save
        payload = _new_default_program_dict(idx)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    # Hydrate SequenceCollection
    SequenceCollection.from_dict({"zone_sequences": payload.get("zone_sequences", [])})

    # Recompute & persist total_time in case steps changed externally
    recomputed = _compute_total_time_from_zone_sequences(
        payload.get("zone_sequences", [])
    )
    if recomputed != payload.get("total_time"):
        payload["total_time"] = recomputed
        try:
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    return payload


#############################################################
# ---------- Data model ----------
@dataclass
class Program:
    index: int
    description: str
    total_time: str  # "MM:SS" or "H:MM"


# ---------- Row widget ----------
class ProgramRow(ctk.CTkFrame):
    def __init__(
        self, master, program: Program, on_edit=None, fg_color="transparent", **kwargs
    ):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.program = program
        self.on_edit = on_edit

        # Grid layout: # | Description | spacer | Time pill | Edit button
        self.grid_columnconfigure(1, weight=1)  # description grows

        # Number column
        num_lbl = ctk.CTkLabel(
            self,
            text=f"{program.index}",
            width=HMISizePos.sx(30),
            anchor="w",
            font=ctk.CTkFont(size=HMISizePos.s(14), weight="bold"),
        )
        num_lbl.grid(
            row=0,
            column=0,
            padx=(HMISizePos.sx(6), HMISizePos.sx(10)),
            pady=HMISizePos.sy(8),
            sticky="w",
        )

        # Description
        desc_lbl = ctk.CTkLabel(
            self,
            text=program.description,
            anchor="w",
            font=ctk.CTkFont(size=HMISizePos.s(16)),
        )
        desc_lbl.grid(
            row=0,
            column=1,
            padx=(0, HMISizePos.sx(10)),
            pady=HMISizePos.sy(8),
            sticky="we",
        )

        # "pill" for time (rounded label look)
        time_pill = ctk.CTkLabel(
            self,
            text=program.total_time,
            corner_radius=HMISizePos.s(18),
            fg_color=("#EBEEF5", "#2A2E36"),
            text_color=("black", "white"),
            width=HMISizePos.sx(90),
            padx=HMISizePos.sx(16),
            pady=HMISizePos.sy(4),
            font=ctk.CTkFont(size=HMISizePos.s(14), weight="bold"),
        )
        PADX_LEFT_TOTAL_TIME_PILL = HMISizePos.sx(375)
        time_pill.grid(
            row=0,
            column=2,
            padx=(PADX_LEFT_TOTAL_TIME_PILL, HMISizePos.sx(10)),
            pady=HMISizePos.sy(6),
            sticky="e",
        )

        icon = Image.open(f"{ASSETS_DIR}/pencil48.png")
        my_image = ctk.CTkImage(
            light_image=icon, dark_image=icon, size=(HMISizePos.s(24), HMISizePos.s(24))
        )

        # Edit button
        edit_btn = ctk.CTkButton(
            self,
            text="",
            image=my_image,
            width=HMISizePos.sx(44),
            height=HMISizePos.sy(36),
            corner_radius=HMISizePos.s(8),
            command=self._handle_edit,
        )
        edit_btn.grid(
            row=0,
            column=3,
            padx=(0, HMISizePos.sx(8)),
            pady=HMISizePos.sy(6),
            sticky="e",
        )

        # bottom divider line (optional)
        divider = ctk.CTkFrame(
            self, height=HMISizePos.sy(1), fg_color=("#D7DCE5", "#3A3F4A")
        )
        divider.grid(row=1, column=0, columnspan=4, sticky="we", padx=HMISizePos.sx(6))

    def _handle_edit(self):
        if callable(self.on_edit):
            self.on_edit(self.program)


# ---------- Main page ----------
class SelectProgramPage(ctk.CTkFrame):
    def __init__(self, controller, shared_data, per_page: int = 6, **kwargs):
        super().__init__(controller, fg_color=HMIColors.color_fg, **kwargs)
        self.controller = controller
        self.programs = SelectProgramPage.loadPrograms()
        self.shared_data = shared_data
        self.per_page = per_page
        self.total_pages = max(1, (len(self.programs) + per_page - 1) // per_page)
        self.page_index = 0  # zero-based

        # ---- Layout skeleton (all grid, no pack) ----
        self.grid_rowconfigure(2, weight=1)  # table area expands
        self.grid_columnconfigure(0, weight=1)  # content column
        self.grid_columnconfigure(1, weight=0)  # right rail (fixed width)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="we",
            padx=HMISizePos.PADDING,
            pady=(HMISizePos.PADDING, HMISizePos.sy(8)),
        )
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Select Program",
            font=ctk.CTkFont(size=HMISizePos.s(22), weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self.page_label = ctk.CTkLabel(
            header, text="Page 1 of X", font=ctk.CTkFont(size=HMISizePos.s(14))
        )
        self.page_label.grid(row=0, column=1, sticky="e")

        # Column headers
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.grid(row=1, column=0, columnspan=2, sticky="we", padx=HMISizePos.PADDING)
        cols.grid_columnconfigure(1, weight=1)

        boldFont = ctk.CTkFont(size=HMISizePos.s(16), weight="bold")
        col_num = ctk.CTkLabel(
            cols, text="#", width=HMISizePos.sx(30), anchor="w", font=boldFont
        )
        col_num.grid(
            row=0,
            column=0,
            padx=(HMISizePos.sx(6), HMISizePos.sx(5)),
            pady=(0, HMISizePos.sy(4)),
            sticky="w",
        )

        col_desc = ctk.CTkLabel(cols, text="Description", anchor="w", font=boldFont)
        col_desc.grid(
            row=0,
            column=1,
            padx=(0, HMISizePos.sx(10)),
            pady=(0, HMISizePos.sy(4)),
            sticky="w",
        )

        PADX_RIGHT_TOTAL_TIME = HMISizePos.sx(195)
        col_time = ctk.CTkLabel(cols, text="Total Time", anchor="e", font=boldFont)
        col_time.grid(
            row=0,
            column=2,
            padx=(0, PADX_RIGHT_TOTAL_TIME),
            pady=(0, HMISizePos.sy(4)),
            sticky="e",
        )

        # underline under headers
        header_underline = ctk.CTkFrame(
            cols, height=HMISizePos.sy(2), fg_color="#888888"
        )
        header_underline.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="we",
            pady=(0, HMISizePos.sy(10)),
            padx=(0, HMISizePos.sx(120)),
        )

        # Table area (left)
        self.table = ctk.CTkFrame(self, fg_color="transparent")
        self.table.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(HMISizePos.PADDING, HMISizePos.sx(8)),
            pady=(0, HMISizePos.sy(8)),
        )

        # Right rail with page-up / page-down (grid only)
        rail = ctk.CTkFrame(self, width=HMISizePos.sx(72), fg_color="transparent")
        rail.grid(
            row=2,
            column=1,
            sticky="ns",
            padx=(0, HMISizePos.PADDING),
            pady=(0, HMISizePos.sy(8)),
        )
        rail.grid_rowconfigure(0, weight=0)
        rail.grid_rowconfigure(1, weight=1)  # flexible space for vertical centering
        rail.grid_rowconfigure(2, weight=0)
        rail.grid_columnconfigure(0, weight=1)

        self.btn_up = ctk.CTkButton(
            rail,
            text="▲",
            width=HMISizePos.sx(56),
            height=HMISizePos.sy(56),
            command=self.page_up,
        )
        self.btn_up.grid(row=0, column=0, pady=(0, HMISizePos.sy(8)), sticky="n")

        self.dash_frame = ctk.CTkFrame(rail, fg_color="transparent")
        self.dash_frame.grid(row=1, column=0, sticky="ns")  # occupies the stretch row

        self.btn_down = ctk.CTkButton(
            rail,
            text="▼",
            width=HMISizePos.sx(56),
            height=HMISizePos.sy(56),
            command=self.page_down,
        )
        self.btn_down.grid(row=2, column=0, pady=(HMISizePos.sy(8), 0), sticky="s")

        # Footer with Back button
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="we",
            padx=HMISizePos.PADDING,
            pady=(0, HMISizePos.PADDING),
        )
        footer.grid_columnconfigure(0, weight=1)

        back_btn = ctk.CTkButton(
            footer,
            text="← Back",
            width=HMISizePos.sx(90),
            height=HMISizePos.sy(50),
            command=self.on_back,
        )
        back_btn.grid(row=0, column=0, sticky="w", padx=HMISizePos.sx(10))

        self._render_page()

    @classmethod
    def loadPrograms(cls) -> List[Program]:
        programs: List[Program] = []
        for idx in range(1, PROGRAM_COUNT + 1):
            payload = load_program_into_sequence_collection(idx)
            desc = payload.get("description", f"Program {idx}")
            total_time = payload.get("total_time", "00:00")
            programs.append(Program(index=idx, description=desc, total_time=total_time))
        return programs

    # Public callbacks
    def on_back(self):
        self.controller.show_HomePage()

    def on_edit_program(self, program: Program):
        print(f"Edit pressed: {program.index} - {program.description}")
        self.controller.show_SequenceProgramPage(program.index)

    # Pagination
    def page_up(self):
        if self.page_index > 0:
            self.page_index -= 1
            self._render_page()

    def page_down(self):
        if self.page_index < self.total_pages - 1:
            self.page_index += 1
            self._render_page()

    def _render_page(self):
        # Clear existing rows
        for child in self.table.winfo_children():
            child.destroy()

        start = self.page_index * self.per_page
        end = min(len(self.programs), start + self.per_page)
        page_items = self.programs[start:end]

        # Define alternating colors (light mode, dark mode)
        row_colors = [
            ("#E1F7FF", "#2B2F38"),  # even rows
            ("#FFFFFF", "#23262E"),  # odd rows
        ]

        # Build rows
        for r, prog in enumerate(page_items):
            bg_color = row_colors[r % 2]
            row = ProgramRow(
                self.table, prog, on_edit=self.on_edit_program, fg_color=bg_color
            )
            row.grid(row=r, column=0, sticky="we")
            self.table.grid_rowconfigure(r, weight=0)

        # Fill remaining space so rows stay grouped at top
        self.table.grid_rowconfigure(len(page_items), weight=1)

        # Update header page label
        self.page_label.configure(
            text=f"Page {self.page_index + 1} of {self.total_pages}"
        )

        # Draw dash marks for page indicator (grid-only; single column, vertically centered)
        for child in self.dash_frame.winfo_children():
            child.destroy()

        # Create a single-column grid in dash_frame
        self.dash_frame.grid_columnconfigure(0, weight=1)
        # Make room to center vertically a bit (optional)
        for i in range(self.total_pages):
            self.dash_frame.grid_rowconfigure(i, weight=0)
        self.dash_frame.grid_rowconfigure(self.total_pages, weight=1)

        for i in range(self.total_pages):
            mark = "—" if i == self.page_index else "·"
            lbl = ctk.CTkLabel(
                self.dash_frame, text=mark, font=ctk.CTkFont(size=HMISizePos.s(20))
            )
            lbl.grid(
                row=i,
                column=0,
                padx=HMISizePos.sx(2),
                pady=HMISizePos.sy(2),
                sticky="n",
            )

        # Enable/disable rail buttons
        self.btn_up.configure(state="normal" if self.page_index > 0 else "disabled")
        self.btn_down.configure(
            state="normal" if self.page_index < self.total_pages - 1 else "disabled"
        )

    def on_show(self):
        # Re-read programs from disk (creates missing files and recomputes total_time)
        self.programs = SelectProgramPage.loadPrograms()
        # Recompute pagination in case anything changed
        self.total_pages = max(
            1, (len(self.programs) + self.per_page - 1) // self.per_page
        )
        # Keep current page in range
        self.page_index = min(self.page_index, self.total_pages - 1)
        # Re-render the visible page
        self._render_page()


# ---------- Demo app (grid only) ----------
def demo_app():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Select Program")
    root.geometry(HMISizePos.SCREEN_RES)

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    page = SelectProgramPage(root, shared_data=None, per_page=6)
    page.grid(row=0, column=0, sticky="nsew")

    root.mainloop()


if __name__ == "__main__":
    # If you run this file directly, make sure a resolution is chosen before creating UI
    try:
        from hmi_consts import HMISizePos as _Sz

        _Sz.set_resolution("800x480")  # or "1024x600"
    except Exception:
        pass
    demo_app()

# SelectProgramPage.py
import customtkinter as ctk
from dataclasses import dataclass
from typing import Any, Dict, List
from hmi_consts import HMIColors, HMISizePos, ASSETS_DIR, PROGRAMS_DIR, LightOnly
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
    sc = SequenceCollection.Instance()
    d = sc.to_dict()
    zone_sequences = d.get("zone_sequences", [])
    total_time = _compute_total_time_from_zone_sequences(zone_sequences)
    return {
        "description": f"Program {idx}",
        "zone_sequences": zone_sequences,
        "total_time": total_time,
    }


def save_program_from_sequence_collection(idx: int, description: str = None) -> None:
    path = _program_path(idx)
    sc = SequenceCollection.Instance()
    data = sc.to_dict()
    zone_sequences = data.get("zone_sequences", [])
    payload = {
        "description": description if description is not None else f"Program {idx}",
        "zone_sequences": zone_sequences,
        "total_time": _compute_total_time_from_zone_sequences(zone_sequences),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def load_program_into_sequence_collection(idx: int) -> Dict[str, Any]:
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
        payload = _new_default_program_dict(idx)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    SequenceCollection.from_dict({"zone_sequences": payload.get("zone_sequences", [])})

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

        self.grid_columnconfigure(1, weight=1)

        num_lbl = ctk.CTkLabel(
            self,
            text=f"{program.index}",
            width=HMISizePos.sx(30),
            anchor="w",
            font=ctk.CTkFont(size=HMISizePos.s(14), weight="bold"),
            text_color=LightOnly.ROW_TEXT,
        )
        num_lbl.grid(
            row=0,
            column=0,
            padx=(HMISizePos.sx(6), HMISizePos.sx(10)),
            pady=HMISizePos.sy(8),
            sticky="w",
        )

        desc_lbl = ctk.CTkLabel(
            self,
            text=program.description,
            anchor="w",
            font=ctk.CTkFont(size=HMISizePos.s(16)),
            text_color=LightOnly.ROW_TEXT,
        )
        desc_lbl.grid(
            row=0,
            column=1,
            padx=(0, HMISizePos.sx(10)),
            pady=HMISizePos.sy(8),
            sticky="we",
        )

        time_pill = ctk.CTkLabel(
            self,
            text=program.total_time,
            corner_radius=HMISizePos.s(18),
            fg_color=LightOnly.PILL_BG,
            text_color=LightOnly.PILL_TEXT,
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

        edit_btn = ctk.CTkButton(
            self,
            text="",
            image=my_image,
            width=HMISizePos.sx(44),
            height=HMISizePos.sy(36),
            corner_radius=HMISizePos.s(8),
            fg_color=LightOnly.ACCENT,
            hover_color=LightOnly.ACCENT,
            command=self._handle_edit,
        )
        edit_btn.grid(
            row=0,
            column=3,
            padx=(0, HMISizePos.sx(8)),
            pady=HMISizePos.sy(6),
            sticky="e",
        )

        divider = ctk.CTkFrame(
            self, height=HMISizePos.sy(1), fg_color=LightOnly.DIVIDER
        )
        divider.grid(row=1, column=0, columnspan=4, sticky="we", padx=HMISizePos.sx(6))

    def _handle_edit(self):
        if callable(self.on_edit):
            self.on_edit(self.program)


# ---------- Main page ----------
class SelectProgramPage(ctk.CTkFrame):
    def __init__(self, controller, shared_data, per_page: int = 6, **kwargs):
        super().__init__(controller, fg_color=LightOnly.FG, **kwargs)
        self.controller = controller
        self.programs = SelectProgramPage.loadPrograms()
        self.shared_data = shared_data
        self.per_page = per_page
        self.total_pages = max(1, (len(self.programs) + per_page - 1) // per_page)
        self.page_index = 0  # zero-based

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

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
            text_color=LightOnly.ROW_TEXT,
        )
        title.grid(row=0, column=0, sticky="w")

        self.page_label = ctk.CTkLabel(
            header,
            text="Page 1 of X",
            font=ctk.CTkFont(size=HMISizePos.s(14)),
            text_color=LightOnly.ROW_TEXT,
        )
        self.page_label.grid(row=0, column=1, sticky="e")

        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.grid(row=1, column=0, columnspan=2, sticky="we", padx=HMISizePos.PADDING)
        cols.grid_columnconfigure(1, weight=1)

        boldFont = ctk.CTkFont(size=HMISizePos.s(16), weight="bold")
        col_num = ctk.CTkLabel(
            cols,
            text="#",
            width=HMISizePos.sx(30),
            anchor="w",
            font=boldFont,
            text_color=LightOnly.ROW_TEXT,
        )
        col_num.grid(
            row=0,
            column=0,
            padx=(HMISizePos.sx(6), HMISizePos.sx(5)),
            pady=(0, HMISizePos.sy(4)),
            sticky="w",
        )

        col_desc = ctk.CTkLabel(
            cols,
            text="Description",
            anchor="w",
            font=boldFont,
            text_color=LightOnly.ROW_TEXT,
        )
        col_desc.grid(
            row=0,
            column=1,
            padx=(0, HMISizePos.sx(10)),
            pady=(0, HMISizePos.sy(4)),
            sticky="w",
        )

        PADX_RIGHT_TOTAL_TIME = HMISizePos.sx(195)
        col_time = ctk.CTkLabel(
            cols,
            text="Total Time",
            anchor="e",
            font=boldFont,
            text_color=LightOnly.ROW_TEXT,
        )
        col_time.grid(
            row=0,
            column=2,
            padx=(0, PADX_RIGHT_TOTAL_TIME),
            pady=(0, HMISizePos.sy(4)),
            sticky="e",
        )

        header_underline = ctk.CTkFrame(
            cols, height=HMISizePos.sy(2), fg_color=LightOnly.DIVIDER
        )
        header_underline.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="we",
            pady=(0, HMISizePos.sy(10)),
            padx=(0, HMISizePos.sx(120)),
        )

        self.table = ctk.CTkFrame(self, fg_color="transparent")
        self.table.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(HMISizePos.PADDING, HMISizePos.sx(8)),
            pady=(0, HMISizePos.sy(8)),
        )

        rail = ctk.CTkFrame(self, width=HMISizePos.sx(72), fg_color="transparent")
        rail.grid(
            row=2,
            column=1,
            sticky="ns",
            padx=(0, HMISizePos.PADDING),
            pady=(0, HMISizePos.sy(8)),
        )
        rail.grid_rowconfigure(0, weight=0)
        rail.grid_rowconfigure(1, weight=1)
        rail.grid_rowconfigure(2, weight=0)
        rail.grid_columnconfigure(0, weight=1)

        self.btn_up = ctk.CTkButton(
            rail,
            text="▲",
            width=HMISizePos.sx(56),
            height=HMISizePos.sy(56),
            fg_color=LightOnly.ACCENT,
            hover_color=LightOnly.ACCENT,
            command=self.page_up,
        )
        self.btn_up.grid(row=0, column=0, pady=(0, HMISizePos.sy(8)), sticky="n")

        self.dash_frame = ctk.CTkFrame(rail, fg_color="transparent")
        self.dash_frame.grid(row=1, column=0, sticky="ns")

        self.btn_down = ctk.CTkButton(
            rail,
            text="▼",
            width=HMISizePos.sx(56),
            height=HMISizePos.sy(56),
            fg_color=LightOnly.ACCENT,
            hover_color=LightOnly.ACCENT,
            command=self.page_down,
        )
        self.btn_down.grid(row=2, column=0, pady=(HMISizePos.sy(8), 0), sticky="s")

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
            fg_color=LightOnly.ACCENT,
            hover_color=LightOnly.ACCENT,
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

    def on_back(self):
        self.controller.show_HomePage()

    def on_edit_program(self, program: Program):
        print(f"Edit pressed: {program.index} - {program.description}")
        self.controller.show_SequenceProgramPage(program.index)

    def page_up(self):
        if self.page_index > 0:
            self.page_index -= 1
            self._render_page()

    def page_down(self):
        if self.page_index < self.total_pages - 1:
            self.page_index += 1
            self._render_page()

    def _render_page(self):
        for child in self.table.winfo_children():
            child.destroy()

        start = self.page_index * self.per_page
        end = min(len(self.programs), start + self.per_page)
        page_items = self.programs[start:end]

        row_colors = [LightOnly.ROW_EVEN, LightOnly.ROW_ODD]

        for r, prog in enumerate(page_items):
            bg_color = row_colors[r % 2]
            row = ProgramRow(
                self.table, prog, on_edit=self.on_edit_program, fg_color=bg_color
            )
            row.grid(row=r, column=0, sticky="we")
            self.table.grid_rowconfigure(r, weight=0)

        self.table.grid_rowconfigure(len(page_items), weight=1)

        self.page_label.configure(
            text=f"Page {self.page_index + 1} of {self.total_pages}"
        )

        for child in self.dash_frame.winfo_children():
            child.destroy()

        self.dash_frame.grid_columnconfigure(0, weight=1)
        for i in range(self.total_pages):
            self.dash_frame.grid_rowconfigure(i, weight=0)
        self.dash_frame.grid_rowconfigure(self.total_pages, weight=1)

        for i in range(self.total_pages):
            mark = "—" if i == self.page_index else "·"
            lbl = ctk.CTkLabel(
                self.dash_frame,
                text=mark,
                font=ctk.CTkFont(size=HMISizePos.s(20)),
                text_color=LightOnly.ROW_TEXT,
            )
            lbl.grid(
                row=i,
                column=0,
                padx=HMISizePos.sx(2),
                pady=HMISizePos.sy(2),
                sticky="n",
            )

        self.btn_up.configure(state="normal" if self.page_index > 0 else "disabled")
        self.btn_down.configure(
            state="normal" if self.page_index < self.total_pages - 1 else "disabled"
        )

    def on_show(self):
        self.programs = SelectProgramPage.loadPrograms()
        self.total_pages = max(
            1, (len(self.programs) + self.per_page - 1) // self.per_page
        )
        self.page_index = min(self.page_index, self.total_pages - 1)
        self._render_page()

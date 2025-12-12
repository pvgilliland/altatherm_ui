# MessageBoxPage.py
from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from typing import Optional, Tuple
from hmi_consts import HMIColors

# ---- Optional palette (swap to your ui_bits/HMIColors if desired) ----
COLOR_BG_LIGHT = "white"
COLOR_BG_DARK = "#1E1E1E"
COLOR_ACCENT = "#3776C3"
COLOR_TEXT_LIGHT = "#111111"
COLOR_TEXT_DARK = "#EAEAEA"
# OVERLAY_DIM_LIGHT = "gray85"
OVERLAY_DIM_LIGHT = HMIColors.color_fg
OVERLAY_DIM_DARK = "gray10"

""" Your showinfo(...) call on AutoMealsPage is created as a modal overlay. 
When you press OK, the overlay tears itself down (releases the grab, place_forget(),
destroy()), revealing the page that was already underneath—AutoMealsPage—so it looks
like a “navigate back,” but it’s just the overlay going away. 
If you do want OK to navigate somewhere, pass the controller and an index for the target page"""


class MessageBoxPage(ctk.CTkFrame):
    """
    A modal overlay that mimics tkinter.messagebox using CustomTkinter widgets.
    - No bind_all (CTk blocks it). Uses grab_set() for modality after waiting for visibility.
    - Works inside a multi-page controller window.
    - Returns: 'ok', 'cancel', 'yes', 'no', or 'retry'

    Styles: 'ok', 'okcancel', 'yesno', 'retrycancel'
    Icons:  'info', 'warning', 'error', 'question'

    Extra:
    - If controller (list-based pages) is provided AND ok_page_index is an int,
      clicking OK will navigate to controller.pages[ok_page_index].
    """

    def __init__(
        self,
        master: tk.Misc,
        controller: Optional[object] = None,  # your multipage controller
        ok_page_index: Optional[int] = None,  # e.g., 1 to go to page[1] on OK
        *,
        width: int = 520,
        height: int = 220,
        corner_radius: int = 16,
        **kwargs,
    ):
        # Semi-opaque overlay background; dialog is a centered card
        super().__init__(
            master, fg_color=(OVERLAY_DIM_LIGHT, OVERLAY_DIM_DARK), **kwargs
        )
        self._result_var = tk.StringVar(value="")
        self._dialog: Optional[ctk.CTkFrame] = None
        self._dialog_size = (max(280, width), max(150, height))
        self._corner_radius = corner_radius

        # Controller / navigation
        self.controller = controller
        self.ok_page_index = ok_page_index

        # Keep track of widgets to optionally tweak
        self._primary_button: Optional[ctk.CTkButton] = None

        # Track parent <Configure> bind so we can unbind on teardown
        self._conf_bind_id: Optional[str] = None
        toplevel = self.winfo_toplevel()
        self._conf_bind_id = toplevel.bind(
            "<Configure>", self._on_parent_configure, add="+"
        )

    # ---------- Public API ----------
    def show(
        self, title: str, message: str, style: str = "ok", icon: str = "info"
    ) -> str:
        """
        Display the overlay and block until a button is pressed.
        Returns one of: 'ok', 'cancel', 'yes', 'no', 'retry'
        """
        # Cover entire window and raise
        self.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        self.lift()

        # Build and center dialog
        self._build_dialog(title, message, style, icon)
        self._center_dialog()

        # Ensure the overlay/dialog are actually viewable before grabbing
        self.update_idletasks()
        try:
            self.wait_visibility(self)
        except Exception:
            pass
        if self._dialog is not None:
            try:
                self.wait_visibility(self._dialog)
            except Exception:
                pass

        # Try immediate grab; if WM isn't ready yet, schedule it
        try:
            self.grab_set()
        except tk.TclError:
            self.after(0, self._safe_grab)

        # Focus default (primary) button for Enter/Space activation
        if self._primary_button is not None:
            self.after(10, self._primary_button.focus_set)

        # Block until result is set
        self.wait_variable(self._result_var)

        # Teardown
        result = self._result_var.get()

        # Unbind parent <Configure> safely
        try:
            if self._conf_bind_id:
                self.winfo_toplevel().unbind("<Configure>", self._conf_bind_id)
        except Exception:
            pass
        finally:
            self._conf_bind_id = None

        # Release grab, forget, and destroy
        try:
            self.grab_release()
        except Exception:
            pass

        # Clear dialog ref to avoid using a destroyed widget
        self._dialog = None

        try:
            self.place_forget()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

        return result

    def _safe_grab(self):
        # Attempt grab again when the widget is certainly viewable
        try:
            self.grab_set()
        except Exception:
            # If still failing, let it go; wait_variable still provides modal-ish flow
            pass

    # ---------- Layout / Build ----------
    def _build_dialog(self, title: str, message: str, style: str, icon: str):
        dlg_w, dlg_h = self._dialog_size
        self._dialog = ctk.CTkFrame(
            self,
            corner_radius=self._corner_radius,
            fg_color=(COLOR_BG_LIGHT, COLOR_BG_DARK),
            width=dlg_w,
            height=dlg_h,
        )
        # NOTE: width/height passed to constructor (not place) to avoid CTk errors
        self._dialog.place(relx=0.5, rely=0.5, anchor="center")

        # grid: header / body / buttons
        self._dialog.grid_rowconfigure(0, weight=0)
        self._dialog.grid_rowconfigure(1, weight=1)
        self._dialog.grid_rowconfigure(2, weight=0)
        self._dialog.grid_columnconfigure(0, weight=1)

        # ESC to cancel (when logical)
        self._dialog.bind("<Escape>", self._on_escape)
        # Enter to "activate" primary button
        self._dialog.bind("<Return>", self._on_return)
        self._dialog.bind("<KP_Enter>", self._on_return)

        # Header
        header = ctk.CTkFrame(self._dialog, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(
            header,
            text=self._icon_char(icon),
            font=ctk.CTkFont(size=22),
        )
        icon_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=(COLOR_ACCENT, COLOR_ACCENT),
        )
        title_label.grid(row=0, column=1, sticky="w")

        # Body
        body = ctk.CTkFrame(self._dialog, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(2, 6))

        wrap = max(200, self._dialog_size[0] - 40)
        message_label = ctk.CTkLabel(
            body,
            text=message,
            font=ctk.CTkFont(size=15),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            justify="left",
            wraplength=wrap,
        )
        message_label.pack(anchor="w")

        # Buttons
        btn_row = self._make_button_row(self._dialog, style)
        btn_row.grid(row=2, column=0, sticky="e", padx=14, pady=(4, 12))

    def _make_button_row(self, parent: tk.Misc, style: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        for col in (0, 1, 2):
            row.grid_columnconfigure(col, weight=1)

        def add_btn(
            col: int, text: str, value: str, primary: bool = False
        ) -> ctk.CTkButton:
            btn = ctk.CTkButton(
                row,
                text=text,
                width=110,
                height=36,
                corner_radius=12,
                fg_color=(COLOR_ACCENT if primary else None),
                command=lambda v=value: self._set_result(v),
            )
            btn.grid(row=0, column=col, padx=6, pady=(4, 2), sticky="e")
            if primary:
                self._primary_button = btn
            return btn

        # Build set matching style
        if style == "ok":
            add_btn(2, "OK", "ok", True)
        elif style == "okcancel":
            add_btn(1, "Cancel", "cancel", False)
            add_btn(2, "OK", "ok", True)
        elif style == "yesno":
            add_btn(1, "No", "no", False)
            add_btn(2, "Yes", "yes", True)
        elif style == "retrycancel":
            add_btn(1, "Cancel", "cancel", False)
            add_btn(2, "Retry", "retry", True)
        else:
            # Fallback
            add_btn(2, "OK", "ok", True)

        return row

    # ---------- Event handlers ----------
    def _set_result(self, value: str):
        # Set the result and unblock .show()
        if self._result_var.get() == "":
            self._result_var.set(value)

            # Extra: navigate on OK if requested
            if (
                value == "ok"
                and self.controller is not None
                and isinstance(self.ok_page_index, int)
            ):
                self._navigate_to_index(self.ok_page_index)

    def _navigate_to_index(self, index: int):
        """
        Robust navigation for list-of-pages controllers.
        Tries common methods; falls back to pages[index].tkraise()/lift().
        """
        c = self.controller
        try:
            if hasattr(c, "show_page"):
                c.show_page(index)
                return
            if hasattr(c, "show_frame"):
                c.show_frame(index)
                return
            if hasattr(c, "raise_page"):
                c.raise_page(index)
                return

            # Fallbacks using pages list
            if hasattr(c, "pages"):
                pages = c.pages
                page = pages[index] if isinstance(pages, (list, tuple)) else None
                if page is not None:
                    if hasattr(page, "tkraise"):
                        page.tkraise()
                        return
                    if hasattr(page, "lift"):
                        page.lift()
                        return
        except Exception as e:
            print(f"Navigation to page[{index}] failed:", e)

    def _on_escape(self, *_):
        if self._result_var.get():
            return
        # Esc acts as cancel if cancel exists
        self._result_var.set("cancel")

    def _on_return(self, *_):
        if self._primary_button is not None:
            self._primary_button.invoke()

    def _on_parent_configure(self, *_):
        # Ignore after teardown or if dialog no longer exists
        if not self.winfo_exists():
            return
        if self._dialog is None:
            return
        try:
            # _dialog might be a Python object after Tk widget is gone; check existence
            if (
                getattr(self._dialog, "winfo_exists", None)
                and not self._dialog.winfo_exists()
            ):
                return
        except Exception:
            return
        self._center_dialog()

    # ---------- Helpers ----------
    def _center_dialog(self):
        if not self._dialog:
            return
        try:
            self._dialog.place_configure(relx=0.5, rely=0.5, anchor="center")
        except tk.TclError:
            # Dialog already destroyed; ignore
            pass

    @staticmethod
    def _icon_char(icon: str) -> str:
        return {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "⛔",
            "question": "❓",
        }.get(icon, "ℹ️")


# --------- Convenience functions mirroring tkinter.messagebox ----------
def showinfo(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> str:
    return MessageBoxPage(
        master, controller=controller, ok_page_index=ok_page_index
    ).show(title, message, style="ok", icon="info")


def showwarning(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> str:
    return MessageBoxPage(
        master, controller=controller, ok_page_index=ok_page_index
    ).show(title, message, style="ok", icon="warning")


def showerror(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> str:
    return MessageBoxPage(
        master, controller=controller, ok_page_index=ok_page_index
    ).show(title, message, style="ok", icon="error")


def askokcancel(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> bool:
    return (
        MessageBoxPage(master, controller=controller, ok_page_index=ok_page_index).show(
            title, message, style="okcancel", icon="question"
        )
        == "ok"
    )


def askyesno(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> bool:
    return (
        MessageBoxPage(master, controller=controller, ok_page_index=ok_page_index).show(
            title, message, style="yesno", icon="question"
        )
        == "yes"
    )


def askretrycancel(
    master: tk.Misc,
    title: str,
    message: str,
    controller: object = None,
    ok_page_index: Optional[int] = None,
) -> Tuple[bool, str]:
    res = MessageBoxPage(
        master, controller=controller, ok_page_index=ok_page_index
    ).show(title, message, style="retrycancel", icon="warning")
    return (res == "retry", res)


# ---------- Demo ----------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")  # or "dark"
    app = ctk.CTk()
    app.title("MessageBoxPage Demo")
    app.geometry("800x480")

    app.overrideredirect(True)

    def do_info():
        # No controller in this standalone demo; just returns 'ok'
        r = showinfo(
            app,
            "Information",
            "This is a custom message box overlay.\nLooks native enough?",
        )
        print("Result:", r)

    def do_yesno():
        if askyesno(
            app, "Confirm", "Do you want to enable the elements for 10 minutes?"
        ):
            showinfo(app, "OK", "Enabled.")
        else:
            showwarning(app, "Cancelled", "No changes applied.")

    def do_retrycancel():
        retry, raw = askretrycancel(
            app, "Connection Lost", "Could not reach controller.\nTry again?"
        )
        print("Retry:", retry, "Raw:", raw)

    btn1 = ctk.CTkButton(app, text="Show Info", command=do_info)
    btn2 = ctk.CTkButton(app, text="Ask Yes/No", command=do_yesno)
    btn3 = ctk.CTkButton(app, text="Ask Retry/Cancel", command=do_retrycancel)

    btn1.pack(pady=16)
    btn2.pack(pady=16)
    btn3.pack(pady=16)

    app.mainloop()

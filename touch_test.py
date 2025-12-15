import tkinter as tk

root = tk.Tk()
root.geometry("1280x800")
root.configure(bg="black")


def log(e):
    print(
        "EVENT",
        e.type,
        "num",
        getattr(e, "num", None),
        "x",
        getattr(e, "x", None),
        "y",
        getattr(e, "y", None),
        "x_root",
        getattr(e, "x_root", None),
        "y_root",
        getattr(e, "y_root", None),
    )


# bind on the TOPLEVEL window (no bind_all)
root.bind("<ButtonPress-1>", log)
root.bind("<ButtonRelease-1>", log)
root.bind("<Motion>", lambda e: None)  # just ensures Tk is alive

# force focus
root.after(200, lambda: (root.lift(), root.focus_force()))
print("Tk windowing system:", root.tk.call("tk", "windowingsystem"))

root.mainloop()

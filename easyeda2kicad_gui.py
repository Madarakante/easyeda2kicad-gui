#!/usr/bin/env python3
"""
Simple GUI for easyeda2kicad — convert LCSC / EasyEDA parts to KiCad libraries.

Requires:
    pip install easyeda2kicad

Run:
    python easyeda2kicad_gui.py
"""

import os
import sys
import queue
import logging
import threading
import subprocess
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import kicad_register

APP_TITLE = "EasyEDA2KiCad — LCSC Part Importer"


def _base_dir():
    """Folder to store config next to the app (works as script or frozen exe)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(_base_dir(), ".e2k_gui.json")


class _QueueWriter:
    """File-like object that forwards writes to the GUI log queue."""

    def __init__(self, log_queue):
        self._q = log_queue

    def write(self, text):
        if text:
            self._q.put(("line", text))
        return len(text)

    def flush(self):
        pass


class _QueueLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self._q = log_queue

    def emit(self, record):
        try:
            self._q.put(("line", self.format(record) + "\n"))
        except Exception:  # noqa: BLE001
            pass


def run_easyeda2kicad(argv, log_queue):
    """Run easyeda2kicad in-process, streaming its output to log_queue.

    Returns the integer exit code (0 = success)."""
    import easyeda2kicad.__main__ as e2k

    # Attach our handler to the root logger so easyeda2kicad's logging reaches us.
    root = logging.getLogger()
    handler = _QueueLogHandler(log_queue)
    handler.setFormatter(logging.Formatter(fmt="[{levelname}] {message}", style="{"))
    root.addHandler(handler)
    prev_level = root.level

    old_out, old_err = sys.stdout, sys.stderr
    writer = _QueueWriter(log_queue)
    sys.stdout = sys.stderr = writer
    try:
        rc = e2k.main(argv)
        return int(rc) if rc is not None else 0
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        root.removeHandler(handler)
        root.setLevel(prev_level)


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("760x620")
        root.minsize(640, 520)
        self._set_icon()

        self.running = False
        self.log_queue = queue.Queue()

        self._build_ui()
        self._load_config()
        self.root.after(100, self._drain_log)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        # Icon files sit next to the script, or in the PyInstaller temp dir when frozen.
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            if os.name == "nt":
                ico = os.path.join(base, "app.ico")
                if os.path.exists(ico):
                    self.root.iconbitmap(ico)
            else:
                # iconbitmap(.ico) is unreliable on Linux/macOS; use a PNG.
                png = os.path.join(base, "app.png")
                if os.path.exists(png):
                    self._icon_img = tk.PhotoImage(file=png)  # keep a ref
                    self.root.iconphoto(True, self._icon_img)
        except tk.TclError:
            pass

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)

        # --- LCSC IDs ---
        idf = ttk.LabelFrame(main, text="LCSC Part ID(s)", padding=8)
        idf.grid(row=0, column=0, sticky="ew", **pad)
        idf.columnconfigure(0, weight=1)
        self.ids_var = tk.StringVar()
        ent = ttk.Entry(idf, textvariable=self.ids_var, font=("Consolas", 11))
        ent.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ent.bind("<Return>", lambda e: self.run())
        ttk.Label(
            idf,
            text="One or more IDs separated by spaces or commas, e.g.  C1591  C25804, C7442",
            foreground="#666",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        # --- What to fetch ---
        wf = ttk.LabelFrame(main, text="What to import", padding=8)
        wf.grid(row=1, column=0, sticky="ew", **pad)
        self.symbol = tk.BooleanVar(value=True)
        self.footprint = tk.BooleanVar(value=True)
        self.model3d = tk.BooleanVar(value=True)
        ttk.Checkbutton(wf, text="Symbol", variable=self.symbol).grid(row=0, column=0, sticky="w", padx=6)
        ttk.Checkbutton(wf, text="Footprint", variable=self.footprint).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Checkbutton(wf, text="3D model", variable=self.model3d).grid(row=0, column=2, sticky="w", padx=6)
        ttk.Button(wf, text="Select all", command=self._select_all).grid(row=0, column=3, padx=12)

        # --- Options ---
        optf = ttk.LabelFrame(main, text="Options", padding=8)
        optf.grid(row=2, column=0, sticky="ew", **pad)
        self.overwrite = tk.BooleanVar(value=True)
        self.project_relative = tk.BooleanVar(value=False)
        self.use_cache = tk.BooleanVar(value=True)
        self.debug = tk.BooleanVar(value=False)
        self.auto_register = tk.BooleanVar(value=False)
        ttk.Checkbutton(optf, text="Overwrite existing", variable=self.overwrite).grid(row=0, column=0, sticky="w", padx=6)
        ttk.Checkbutton(optf, text="3D path project-relative", variable=self.project_relative).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Checkbutton(optf, text="Cache API responses", variable=self.use_cache).grid(row=0, column=2, sticky="w", padx=6)
        ttk.Checkbutton(optf, text="Debug logging", variable=self.debug).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Checkbutton(optf, text="Auto-register with KiCad after import", variable=self.auto_register).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 0))

        # --- Output ---
        of = ttk.LabelFrame(main, text="Output library (.kicad_sym) — leave blank for easyeda2kicad default", padding=8)
        of.grid(row=3, column=0, sticky="ew", **pad)
        of.columnconfigure(0, weight=1)
        self.output_var = tk.StringVar()
        ttk.Entry(of, textvariable=self.output_var).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(of, text="Browse…", command=self._browse_output).grid(row=0, column=1)

        # --- Buttons ---
        bf = ttk.Frame(main)
        bf.grid(row=4, column=0, sticky="ew", **pad)
        self.run_btn = ttk.Button(bf, text="▶  Import", command=self.run)
        self.run_btn.pack(side="left")
        self.reg_btn = ttk.Button(bf, text="Register with KiCad", command=self.register_kicad)
        self.reg_btn.pack(side="left", padx=6)
        ttk.Button(bf, text="Open output folder", command=self._open_output_folder).pack(side="left")
        ttk.Button(bf, text="Clear log", command=self._clear_log).pack(side="left", padx=6)
        self.status = ttk.Label(bf, text="Ready", foreground="#0a7")
        self.status.pack(side="right")

        # --- Log ---
        lf = ttk.LabelFrame(main, text="Log", padding=6)
        lf.grid(row=5, column=0, sticky="nsew", **pad)
        main.rowconfigure(5, weight=1)
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.log = tk.Text(lf, wrap="word", height=12, bg="#1e1e1e", fg="#d4d4d4",
                           insertbackground="#d4d4d4", font=("Consolas", 10))
        self.log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log["yscrollcommand"] = sb.set
        self.log.tag_config("err", foreground="#f48771")
        self.log.tag_config("ok", foreground="#89d185")
        self.log.configure(state="disabled")

    # ------------- actions -------------
    def _select_all(self):
        self.symbol.set(True)
        self.footprint.set(True)
        self.model3d.set(True)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Output KiCad symbol library",
            defaultextension=".kicad_sym",
            filetypes=[("KiCad symbol library", "*.kicad_sym"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _parse_ids(self):
        raw = self.ids_var.get().replace(",", " ").split()
        ids = []
        for tok in raw:
            tok = tok.strip().upper()
            if not tok:
                continue
            if not tok.startswith("C"):
                tok = "C" + tok
            ids.append(tok)
        return ids

    def _build_argv(self, ids):
        argv = ["--lcsc_id", *ids]
        if self.symbol.get() and self.footprint.get() and self.model3d.get():
            argv.append("--full")
        else:
            if self.symbol.get():
                argv.append("--symbol")
            if self.footprint.get():
                argv.append("--footprint")
            if self.model3d.get():
                argv.append("--3d")
        out = self.output_var.get().strip()
        if out:
            argv += ["--output", out]
        if self.overwrite.get():
            argv.append("--overwrite")
        if self.project_relative.get():
            argv.append("--project-relative")
        if self.use_cache.get():
            argv.append("--use-cache")
        if self.debug.get():
            argv.append("--debug")
        return argv

    def run(self):
        if self.running:
            messagebox.showinfo(APP_TITLE, "An import is already running.")
            return
        ids = self._parse_ids()
        if not ids:
            messagebox.showwarning(APP_TITLE, "Enter at least one LCSC part ID (e.g. C1591).")
            return
        if not (self.symbol.get() or self.footprint.get() or self.model3d.get()):
            messagebox.showwarning(APP_TITLE, "Select at least one of Symbol / Footprint / 3D model.")
            return

        argv = self._build_argv(ids)
        self._save_config()
        self._clear_log()
        self._append("easyeda2kicad " + " ".join(argv) + "\n\n")
        self.run_btn.configure(state="disabled")
        self.running = True
        self.status.configure(text="Running…", foreground="#e0a800")

        t = threading.Thread(target=self._worker, args=(argv,), daemon=True)
        t.start()

    def _worker(self, argv):
        try:
            rc = run_easyeda2kicad(argv, self.log_queue)
            self.log_queue.put(("done", rc))
        except Exception as e:  # noqa: BLE001
            self.log_queue.put(("line", f"ERROR: {e}\n"))
            self.log_queue.put(("done", -1))
        finally:
            self.running = False

    def register_kicad(self):
        if self.running:
            messagebox.showinfo(APP_TITLE, "Wait for the current job to finish.")
            return
        self.running = True
        self.run_btn.configure(state="disabled")
        self.reg_btn.configure(state="disabled")
        self.status.configure(text="Registering…", foreground="#e0a800")
        self._append("\n=== Registering easyeda2kicad library with KiCad ===\n")
        out = self.output_var.get()
        threading.Thread(target=self._reg_worker, args=(out,), daemon=True).start()

    def _reg_worker(self, out):
        try:
            ok = kicad_register.register(out, log=lambda m: self.log_queue.put(("line", m + "\n")))
            self.log_queue.put(("regdone", ok))
        except Exception as e:  # noqa: BLE001
            self.log_queue.put(("line", f"ERROR: {e}\n"))
            self.log_queue.put(("regdone", False))
        finally:
            self.running = False

    def _open_output_folder(self):
        base, _ = kicad_register.resolve_output(self.output_var.get())
        if not os.path.isdir(base):
            messagebox.showinfo(APP_TITLE, f"Folder doesn't exist yet:\n{base}")
            return
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(base)])
            elif os.name == "nt":
                os.startfile(str(base))  # noqa: SIM115  (Windows only)
            else:
                subprocess.run(["xdg-open", str(base)])
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(e))

    def _drain_log(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "line":
                    low = payload.lower()
                    tag = "err" if ("error" in low or "traceback" in low or "failed" in low) else None
                    if tag is None and ("success" in low or "written" in low or "created" in low):
                        tag = "ok"
                    self._append(payload, tag)
                elif kind == "done":
                    rc = payload
                    self.run_btn.configure(state="normal")
                    if rc == 0:
                        self.status.configure(text="Done ✓", foreground="#0a7")
                        self._append("\n--- Finished successfully ---\n", "ok")
                        if self.auto_register.get():
                            self.register_kicad()
                    else:
                        self.status.configure(text=f"Failed (exit {rc})", foreground="#c0392b")
                        self._append(f"\n--- Finished with exit code {rc} ---\n", "err")
                elif kind == "regdone":
                    self.run_btn.configure(state="normal")
                    self.reg_btn.configure(state="normal")
                    if payload:
                        self.status.configure(text="Registered ✓", foreground="#0a7")
                    else:
                        self.status.configure(text="Register incomplete", foreground="#c0392b")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    def _append(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ------------- config persistence -------------
    def _save_config(self):
        data = {
            "output": self.output_var.get(),
            "symbol": self.symbol.get(),
            "footprint": self.footprint.get(),
            "model3d": self.model3d.get(),
            "overwrite": self.overwrite.get(),
            "project_relative": self.project_relative.get(),
            "use_cache": self.use_cache.get(),
            "debug": self.debug.get(),
            "auto_register": self.auto_register.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        self.output_var.set(data.get("output", ""))
        self.symbol.set(data.get("symbol", True))
        self.footprint.set(data.get("footprint", True))
        self.model3d.set(data.get("model3d", True))
        self.overwrite.set(data.get("overwrite", True))
        self.project_relative.set(data.get("project_relative", False))
        self.use_cache.set(data.get("use_cache", True))
        self.debug.set(data.get("debug", False))
        self.auto_register.set(data.get("auto_register", False))

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno(APP_TITLE, "An import is running. Quit anyway?"):
                return
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

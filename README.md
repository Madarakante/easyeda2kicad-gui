# EasyEDA2KiCad GUI

A simple Windows desktop GUI for importing **LCSC / EasyEDA parts into KiCad**.

It is a graphical front-end for the excellent command-line tool
[**easyeda2kicad**](https://github.com/uPesy/easyeda2kicad.py) by *uPesy* — you
type an LCSC part number, tick what you want (symbol / footprint / 3D model),
and it downloads and converts the part into a KiCad library. It can also
**register that library with KiCad for you** so the parts show up automatically.

> **Transparency note:** This tool does two things that touch your system —
> it **writes library files** to your Documents folder, and (only when you click
> *Register with KiCad*) it **edits KiCad's configuration files**. Exactly what
> it writes and where is documented below. It makes a backup of every KiCad
> config file before changing it. This project was built as a personal helper
> tool with AI assistance; read the source — it's short and plain Python.

---

## What it does

- Downloads any LCSC part by ID (e.g. `C1591`) via easyeda2kicad and converts it
  to KiCad format.
- Lets you choose **Symbol**, **Footprint**, and/or **3D model**.
- Streams the tool's live output into a log panel.
- Remembers your settings between runs.
- **One-click "Register with KiCad"** — makes KiCad aware of the generated
  library (symbols, footprints, and the `EASYEDA2KICAD` path variable for 3D
  models), across every installed KiCad version it detects.
- Optional **auto-register after each import**.
- "Open output folder" and an app icon / desktop shortcut for convenience.

---

## Where your files are saved

When the **Output** box is left blank, easyeda2kicad writes everything under:

```
C:\Users\<you>\Documents\Kicad\easyeda2kicad\
├── easyeda2kicad.kicad_sym       ← symbols
├── easyeda2kicad.pretty\         ← footprints (*.kicad_mod)
└── easyeda2kicad.3dshapes\       ← 3D models (*.wrl, *.step)
```

If you set a custom path in the **Output** box, it uses that name/location
instead.

---

## What "Register with KiCad" changes (and how it's kept safe)

KiCad does **not** scan folders for libraries — it reads config files. So to make
your imported parts appear, this tool edits, **per installed KiCad version**
(found under `%APPDATA%\kicad\<version>\`):

| File | Change |
| --- | --- |
| `sym-lib-table` | adds/updates an `easyeda2kicad` symbol-library entry |
| `fp-lib-table` | adds/updates an `easyeda2kicad` footprint-library entry |
| `kicad_common.json` | sets the `EASYEDA2KICAD` environment variable to the library folder (so 3D-model paths resolve) |

Safety measures:

- **A backup is made** of every file before it's modified: `<file>.e2k-bak`.
- The operation is **idempotent** — running it again updates the existing entry
  instead of adding duplicates.
- **Close KiCad before registering.** KiCad rewrites these files when it exits,
  so it would discard the changes. The tool detects a running KiCad and warns you.

You only need to register **once**. After that, every future import lands in the
same library files KiCad already knows about, so new parts appear automatically
(reload libraries or restart KiCad).

To undo a registration, restore the `.e2k-bak` files or remove the
`easyeda2kicad` entries from the two lib-table files.

---

## Requirements

- **Windows** (uses `.ico`, `os.startfile`, and edits `%APPDATA%\kicad`).
- To run **from source**: Python 3.9+ and the `easyeda2kicad` package.
- To run the **prebuilt app**: nothing — Python and easyeda2kicad are bundled
  inside the executable.

---

## How to run

### Option A — Run the prebuilt app (easiest)

1. Build it once (see *Building* below) or grab the `dist\EasyEDA2KiCad` folder.
2. Double-click **`EasyEDA2KiCad.exe`** inside that folder, or use the desktop
   shortcut created by `create_shortcut.bat`.

No Python installation is required for this — everything is bundled.

### Option B — Run from source (Python)

```bash
pip install easyeda2kicad
python easyeda2kicad_gui.py
```

That's it. The GUI uses only the Python standard library (`tkinter`) plus
`easyeda2kicad`.

### Then, in the app

1. Type one or more LCSC IDs (space- or comma-separated). `C1591`, `1591`, and
   `c1591` all work.
2. Tick **Symbol / Footprint / 3D model**.
3. Click **▶ Import**.
4. (Once) close KiCad and click **Register with KiCad** — or tick
   **Auto-register after import**.
5. Open KiCad → the `easyeda2kicad` symbol & footprint libraries are there.

---

## Building the desktop app yourself

Requires [PyInstaller](https://pyinstaller.org/) (and Pillow only if you want to
regenerate the icon).

```bash
pip install pyinstaller pillow easyeda2kicad

# (optional) regenerate the app icon
python make_icon.py

# build the one-folder app  ->  dist\EasyEDA2KiCad\EasyEDA2KiCad.exe
build.bat
#   or:  python -m PyInstaller easyeda2kicad_gui.spec --noconfirm

# (optional) create a Desktop shortcut to the built app
create_shortcut.bat
```

The result is a **one-folder** build: distribute the whole `dist\EasyEDA2KiCad`
folder (the `.exe` needs the `_internal` folder beside it).

---

## Files in this repo

| File | Purpose |
| --- | --- |
| `easyeda2kicad_gui.py` | The GUI (Tkinter). Runs easyeda2kicad in-process and streams its output. |
| `kicad_register.py` | Logic that registers the library into KiCad's config (with backups). |
| `make_icon.py` | Generates `app.ico` (needs Pillow). |
| `easyeda2kicad_gui.spec` | PyInstaller build recipe (one-folder, windowed, icon). |
| `build.bat` | Convenience wrapper to build the app. |
| `create_shortcut.bat` | Creates a Desktop shortcut to the built app. |
| `app.ico` | Application icon. |
| `LICENSE` | GNU AGPL-3.0. |

Build outputs (`build/`, `dist/`), caches, and the generated
`.e2k_gui.json` settings file are git-ignored.

---

## Credits & license

- **Core conversion engine:** [easyeda2kicad.py](https://github.com/uPesy/easyeda2kicad.py)
  by *uPesy* — this GUI would not exist without it. All the hard work of talking
  to the EasyEDA API and producing valid KiCad libraries is theirs.
- This GUI wrapper is a thin convenience layer around that tool.

Because it builds on easyeda2kicad, which is licensed under the **GNU Affero
General Public License v3.0**, this project is released under the **same license**
(AGPL-3.0). See [`LICENSE`](LICENSE).

## Disclaimer

Provided as-is, with no warranty. It modifies KiCad configuration files as
described above; back up your KiCad config if you're cautious, and always close
KiCad before registering. Not affiliated with or endorsed by LCSC, EasyEDA, or
KiCad.

#!/usr/bin/env python3
"""
Register the easyeda2kicad library with KiCad automatically.

KiCad does not scan folders for libraries — it reads three config files per
installed version (under %APPDATA%\\kicad\\<version>\\):

    sym-lib-table      global symbol libraries
    fp-lib-table       global footprint libraries
    kicad_common.json  environment variables (we set EASYEDA2KICAD here)

This module adds/updates an "easyeda2kicad" entry in the symbol and footprint
tables (pointing via the ${EASYEDA2KICAD} variable), and sets that variable to
the library's base folder — matching the 3D-model paths easyeda2kicad writes
into its footprints.

Registration is a ONE-TIME action. After it's done, newly imported parts land
in the same .kicad_sym / .pretty files KiCad already knows about, so they show
up automatically (reload libraries or restart KiCad).
"""

from __future__ import annotations

import os
import re
import sys
import json
import shutil
from pathlib import Path

LIB_NICKNAME = "easyeda2kicad"
ENV_VAR = "EASYEDA2KICAD"


def default_base_folder() -> Path:
    return Path.home() / "Documents" / "Kicad" / "easyeda2kicad"


def resolve_output(output_setting: str):
    """Mirror easyeda2kicad's own logic: return (base_folder, lib_name)."""
    out = (output_setting or "").strip()
    if out:
        p = Path(out)
        if p.is_dir():
            return p, "easyeda2kicad"
        return p.parent, (p.stem or "easyeda2kicad")
    return default_base_folder(), "easyeda2kicad"


def find_kicad_config_dirs():
    """Return list of (version, dir) for every KiCad config dir that has a
    sym-lib-table, newest version last."""
    root = kicad_config_root()
    found = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "sym-lib-table").exists():
                found.append((d.name, d))
    return found


def kicad_config_root() -> Path:
    """Platform-specific base folder that holds KiCad's per-version config dirs.

    Windows: %APPDATA%\\kicad
    macOS:   ~/Library/Preferences/kicad
    Linux:   $XDG_CONFIG_HOME/kicad  (default ~/.config/kicad)
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Preferences" / "kicad"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "kicad"
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "kicad"


def kicad_is_running() -> bool:
    """Best-effort check for a running KiCad process, on any OS."""
    import subprocess

    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            ).stdout.lower()
            return "kicad" in out
        # macOS / Linux: list process command names
        out = subprocess.run(
            ["ps", "-A", "-o", "comm"],
            capture_output=True,
            text=True,
        ).stdout.lower()
        return "kicad" in out
    except Exception:  # noqa: BLE001
        return False


def _backup(path: Path):
    bak = path.with_suffix(path.suffix + ".e2k-bak")
    if not bak.exists() and path.exists():
        shutil.copy2(path, bak)


def _lib_entry(uri: str) -> str:
    return (
        f'\t(lib (name "{LIB_NICKNAME}") (type "KiCad") '
        f'(uri "{uri}") (options "") (descr "LCSC parts via easyeda2kicad"))'
    )


def _upsert_lib_table(path: Path, uri: str, log):
    """Add or replace the easyeda2kicad entry in a *-lib-table file."""
    text = path.read_text(encoding="utf-8")
    new_line = _lib_entry(uri)

    # Match an existing entry for our nickname (whole line).
    pat = re.compile(
        r'^[ \t]*\(lib \(name "' + re.escape(LIB_NICKNAME) + r'"\).*\)[ \t]*$',
        re.MULTILINE,
    )
    if pat.search(text):
        text = pat.sub(new_line, text)
        log(f"    updated existing entry in {path.name}")
    else:
        # Insert before the final closing paren of the table.
        idx = text.rstrip().rfind(")")
        if idx == -1:
            raise ValueError(f"Unexpected format: {path}")
        text = text[:idx] + new_line + "\n" + text[idx:]
        log(f"    added entry to {path.name}")
    _backup(path)
    path.write_text(text, encoding="utf-8")


def _set_env_var(path: Path, base_folder_posix: str, log):
    """Set EASYEDA2KICAD in kicad_common.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log(f"    ! could not read {path.name}, skipping env var")
        return
    env = data.get("environment")
    if not isinstance(env, dict):
        env = {}
        data["environment"] = env
    vars_ = env.get("vars")
    if not isinstance(vars_, dict):
        vars_ = {}
        env["vars"] = vars_
    if vars_.get(ENV_VAR) == base_folder_posix:
        log(f"    {ENV_VAR} already set in {path.name}")
        return
    vars_[ENV_VAR] = base_folder_posix
    _backup(path)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log(f"    set {ENV_VAR}={base_folder_posix} in {path.name}")


def register(output_setting: str, log=print) -> bool:
    """Register the library into every detected KiCad version.

    Returns True on success. `log` is a callable taking one string."""
    base_folder, lib_name = resolve_output(output_setting)
    base_posix = base_folder.as_posix()

    sym_file = base_folder / f"{lib_name}.kicad_sym"
    fp_dir = base_folder / f"{lib_name}.pretty"

    log(f"Library base folder: {base_posix}")
    if not sym_file.exists() and not fp_dir.exists():
        log("! Nothing to register yet — import at least one part first.")
        return False

    sym_uri = "${%s}/%s.kicad_sym" % (ENV_VAR, lib_name)
    fp_uri = "${%s}/%s.pretty" % (ENV_VAR, lib_name)

    dirs = find_kicad_config_dirs()
    if not dirs:
        log("! No KiCad config folders found under %APPDATA%\\kicad.")
        return False

    if kicad_is_running():
        log("! WARNING: KiCad appears to be running. Close it first — KiCad")
        log("  rewrites these files on exit and will discard these changes.")

    ok = True
    for version, d in dirs:
        log(f"KiCad {version}:")
        try:
            _upsert_lib_table(d / "sym-lib-table", sym_uri, log)
            _upsert_lib_table(d / "fp-lib-table", fp_uri, log)
            common = d / "kicad_common.json"
            if common.exists():
                _set_env_var(common, base_posix, log)
        except Exception as e:  # noqa: BLE001
            log(f"    ERROR: {e}")
            ok = False

    if ok:
        log("")
        log("Done. Restart KiCad (or Preferences > Manage Libraries) to see")
        log(f'the "{LIB_NICKNAME}" symbol & footprint libraries.')
        log("You only need to register ONCE — future imports appear automatically.")
    return ok


if __name__ == "__main__":
    import sys

    register(sys.argv[1] if len(sys.argv) > 1 else "")

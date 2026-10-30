"""Relink a DLL from a saved link command with /MAP and output paths redirected.

Usage:
  pixi run -e dev python tools/link_with_map.py LINK_CMD.txt OUT_DIR [--cwd DIR] [--linker PATH]

LINK_CMD.txt holds a command line containing link.exe and its arguments. Text after
" && " is ignored. /OUT, /IMPLIB and /PDB are redirected into OUT_DIR, and a
CvGameCoreDLL-style map is written there as <name>.map (name taken from /OUT).
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LINKER = ROOT / "toolchain" / "Vc7" / "bin" / "link.exe"
DEFAULT_CWD = ROOT / "build" / "final-release-vc7"


def parse_args_from_command(text):
    idx = text.index("link.exe") + len("link.exe")
    end = text.find(" && ", idx)
    return text[idx:end if end != -1 else None].split()


def rewrite(args, out_dir):
    out_name = "out.dll"
    rewritten = []
    for a in args:
        low = a.lower()
        if low.startswith(("/out:", "/implib:", "/pdb:")):
            opt, _, value = a.partition(":")
            name = Path(value.strip('"')).name
            if opt.lower() == "/out":
                out_name = name
            rewritten.append(f"{opt}:{out_dir / name}")
        else:
            rewritten.append(a)
    map_name = Path(out_name).with_suffix(".map")
    rewritten.append(f"/MAP:{out_dir / map_name}")
    return rewritten


def main(argv=None):
    p = argparse.ArgumentParser(description="Relink a DLL with a map file.")
    p.add_argument("command_file", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--cwd", type=Path, default=DEFAULT_CWD, help="working directory for link.exe")
    p.add_argument("--linker", type=Path, default=DEFAULT_LINKER, help="path to link.exe")
    args = p.parse_args(argv)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    text = args.command_file.read_text().strip()
    link_args = rewrite(parse_args_from_command(text), out_dir)
    result = subprocess.run([str(args.linker), *link_args], cwd=args.cwd)
    print("link exit", result.returncode)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

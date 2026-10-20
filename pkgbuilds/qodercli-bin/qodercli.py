#!/usr/bin/python3
"""Keep pacman's update policy and caller hooks in one native settings input."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile


VENDOR = "/opt/qodercli/qodercli"
POLICY = "/usr/share/qodercli/pacman-settings.json"


def settings(value):
    text = value if value.lstrip().startswith(("{", "[")) else Path(value).read_text()
    # Native settings accept comments; quoted URLs and escape sequences stay intact.
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else " ", text)
    text = re.sub(r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])',
                  lambda m: m[0] if m[0].startswith('"') else "", text)
    document = json.loads(text)
    if not isinstance(document, dict):
        raise ValueError("settings must be a JSON object")
    return document


def arguments(args):
    forwarded = []
    selected = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            forwarded.extend(args[index:])
            break
        if arg == "--settings" or arg.startswith("--settings="):
            if selected is not None:
                raise ValueError("use one --settings input; repeated inputs are ambiguous")
            if arg == "--settings":
                index += 1
                if index == len(args) or args[index].startswith("--"):
                    raise ValueError("--settings requires a file or inline JSON object")
                selected = args[index]
            else:
                selected = arg.partition("=")[2]
            if not selected:
                raise ValueError("--settings requires a file or inline JSON object")
        else:
            forwarded.append(arg)
        index += 1
    return forwarded, settings(selected) if selected is not None else {}


def main():
    args = sys.argv[1:]
    if args[:1] == ["update"]:
        print("Qoder CLI is managed by pacman. Update the qodercli-bin package "
              "through your package manager.", file=sys.stderr)
        return 1
    try:
        forwarded, document = arguments(args)
        general = document.setdefault("general", {})
        if not isinstance(general, dict):
            raise ValueError("settings.general must be a JSON object")
        general.update(json.loads(Path(POLICY).read_text())["general"])
        # Exec preserves the native PID and signals. The unlinked, private file
        # avoids exposing caller settings in argv or leaving a config on disk.
        with tempfile.TemporaryFile() as snapshot:
            snapshot.write(json.dumps(document, allow_nan=False).encode())
            snapshot.flush()
            os.set_inheritable(snapshot.fileno(), True)
            os.execv(VENDOR, [VENDOR, "--settings", "/proc/self/fd/" + str(snapshot.fileno()),
                              *forwarded])
    except (OSError, ValueError) as error:
        print("qodercli: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

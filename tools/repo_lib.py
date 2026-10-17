"""Small, dependency-free helpers. Reading SRCINFO never executes a recipe."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[a-z0-9][a-z0-9@._+-]*\Z")


def recipe_dir(name, root=ROOT):
    if not NAME.fullmatch(name):
        raise ValueError("invalid package directory: " + name)
    directory = root / "pkgbuilds" / name
    if (not directory.is_dir() or directory.is_symlink()
            or not directory.resolve().is_relative_to(root.resolve())):
        raise ValueError("missing package directory: " + name)
    return directory


def package_input(directory, target):
    """Resolve an existing recipe input without allowing traversal or escaping links."""
    relative = Path(target)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("unsafe package input: " + str(target))
    path = directory / relative
    if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("missing or escaping package input: " + str(target))
    return path


def source_target(source):
    """Return an origin; a makepkg download alias must be a plain filename."""
    alias, separator, target = source.partition("::")
    # A literal IPv6 URL contains :: too, but has no makepkg alias prefix.
    if separator and "://" not in alias:
        if not alias or Path(alias).name != alias or alias in {".", ".."}:
            raise ValueError("unsafe source alias: " + alias)
        return target
    return source


def read_srcinfo(path):
    path = package_input(path.parent, path.name)
    return read_srcinfo_text(path.read_text(), str(path))


def read_srcinfo_text(text, path=".SRCINFO"):
    fields = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(" = ")
        if not separator or not key or not value:
            raise ValueError("{}:{}: invalid SRCINFO assignment".format(path, number))
        fields.setdefault(key, []).append(value)
    for key in ("pkgbase", "pkgname", "pkgver", "pkgrel", "arch", "license"):
        if not fields.get(key):
            raise ValueError("{}: missing {}".format(path, key))
    for key in ("pkgbase", "pkgname", "pkgver", "pkgrel"):
        if len(fields[key]) != 1:
            raise ValueError("{}: expected one {} (split packages are not supported here)".format(path, key))
    return fields


def srcinfo_matches(first, second):
    """Ignore field-key formatting/order, while preserving package scope and value order."""
    def sections(text):
        read_srcinfo_text(text)
        result, scope = {}, None
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition(" = ")
            if key in {"pkgbase", "pkgname"}:
                scope = (key, value)
                result[scope] = {}
            else:
                if scope is None:
                    raise ValueError("SRCINFO field precedes pkgbase")
                result[scope].setdefault(key, []).append(value)
        return result
    return sections(first) == sections(second)


def local_sources(fields, directory):
    """Return only declared local inputs, refusing links outside the package."""
    files = set()
    for key, sources in fields.items():
        if key != "source" and not key.startswith("source_"):
            continue
        for source in sources:
            target = source_target(source)
            if "://" in target:
                continue
            package_input(directory, target)
            files.add(target)
    for key in ("install", "changelog"):
        for target in fields.get(key, []):
            package_input(directory, target)
            files.add(target)
    return sorted(files)


def generated_srcinfo(directory):
    return subprocess.check_output(["makepkg", "--printsrcinfo"], cwd=directory, text=True)


def load_catalog(root=ROOT):
    return json.loads((root / "catalog.json").read_text())


def nested(data, path):
    for component in path.split("."):
        data = data[component]
    return data

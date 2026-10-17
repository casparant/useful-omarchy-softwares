"""Dependency-free checks for the public plugin catalog and standalone exports."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
FOLDER = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
ENTRY_POINTS = {
    "bar": "bar", "bar-widget": "barWidget", "menu": "menu",
    "overlay": "overlay", "panel": "panel", "service": "service",
}
CACHE_DIRS = {".git", "__pycache__", ".pytest_cache"}


def safe_relative(value):
    """Accept canonical POSIX paths, without traversal or platform ambiguity."""
    if (not isinstance(value, str) or not value or ".." in value
            or any(character in value for character in "\0\n\r\\")):
        raise ValueError("unsafe plugin path: " + repr(value))
    relative = PurePosixPath(value)
    if relative.is_absolute() or relative.as_posix() != value or value == ".":
        raise ValueError("unsafe plugin path: " + repr(value))
    return relative


def regular_input(directory, name):
    relative = safe_relative(name)
    path = directory
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("plugin symlinks are not allowed: " + str(path))
    if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("missing or escaping plugin file: " + name)
    return path


def valid_id(value):
    return (isinstance(value, str) and PLUGIN_ID.fullmatch(value)
            and ".." not in value and not value.startswith("omarchy."))


def load_catalog(root=ROOT):
    catalog = json.loads(regular_input(root, "plugins/catalog.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or type(catalog.get("schema_version")) is not int or catalog["schema_version"] != 1:
        raise ValueError("unsupported plugin catalog schema_version")
    entries = catalog.get("plugins")
    if not isinstance(entries, list):
        raise ValueError("plugin catalog must contain a plugins array")
    ids, paths = set(), set()
    for entry in entries:
        if not isinstance(entry, dict) or not valid_id(entry.get("id")):
            raise ValueError("invalid or reserved plugin catalog id")
        if entry["id"] in ids:
            raise ValueError("duplicate plugin catalog id: " + entry["id"])
        ids.add(entry["id"])
        path = safe_relative(entry.get("path"))
        if (len(path.parts) != 2 or path.parts[0] != "plugins"
                or not FOLDER.fullmatch(path.parts[1])):
            raise ValueError("plugin path must be plugins/<folder-name>")
        if str(path) in paths:
            raise ValueError("duplicate plugin catalog path: " + str(path))
        paths.add(str(path))
        for field in ("status", "license"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("plugin catalog requires " + field)
        architectures = entry.get("architectures")
        if (not isinstance(architectures, list) or not architectures
                or any(not isinstance(arch, str) or arch not in {"x86_64", "aarch64", "any"} for arch in architectures)
                or len(set(architectures)) != len(architectures)
                or ("any" in architectures and len(architectures) != 1)):
            raise ValueError("invalid plugin catalog architectures")
        dependencies = entry.get("runtime_dependencies")
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) or not dep.strip() for dep in dependencies):
            raise ValueError("plugin runtime_dependencies must be a string array")
        documentation = safe_relative(entry.get("documentation"))
        if documentation.parts[:2] != path.parts:
            raise ValueError("plugin documentation must be inside its source folder")
        files = entry.get("files")
        if not isinstance(files, list) or not files or any(not isinstance(name, str) for name in files):
            raise ValueError("plugin catalog requires an explicit files allowlist")
        if len(set(files)) != len(files):
            raise ValueError("duplicate plugin files allowlist entry")
        for name in files:
            relative = safe_relative(name)
            if relative.parts[0] in CACHE_DIRS or relative.parts[0] == "tests":
                raise ValueError("development files cannot be plugin export inputs: " + name)
        document_name = documentation.relative_to(path).as_posix()
        if not {"manifest.json", "LICENSE", document_name}.issubset(set(files)):
            raise ValueError("plugin export must include manifest.json, LICENSE and documentation")
    return entries


def select_plugin(name, root=ROOT):
    if not isinstance(name, str) or not FOLDER.fullmatch(name) or ".." in name:
        raise ValueError("invalid plugin folder name: " + repr(name))
    entries = [entry for entry in load_catalog(root) if entry["path"] == "plugins/" + name]
    if len(entries) != 1:
        raise ValueError("plugin is not in the public catalog: " + name)
    directory = root / "plugins" / name
    if (not directory.is_dir() or (root / "plugins").is_symlink()
            or directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve())):
        raise ValueError("missing or escaping plugin directory: " + name)
    return directory, entries[0]


def check(directory, entry, require_omarchy=False):
    """Check source without running plugin code; defer official schema checks when available."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("plugin directory must be a regular directory")
    for parent, subdirectories, names in os.walk(directory, followlinks=False):
        # Git internals are not plugin inputs and official validation skips them too.
        for name in subdirectories + names:
            if name == ".git":
                continue
            path = Path(parent) / name
            if path.is_symlink():
                raise ValueError("plugin symlinks are not allowed: " + str(path))
        subdirectories[:] = [name for name in subdirectories if name != ".git"]
        for name in names:
            if name == ".git" or name == ".DS_Store" or name.endswith(".pyc"):
                continue
            path = Path(parent) / name
            relative = path.relative_to(directory).as_posix()
            if any(part in CACHE_DIRS for part in path.relative_to(directory).parts):
                continue
            if relative not in entry["files"] and relative.split("/", 1)[0] != "tests" and relative != ".gitignore":
                raise ValueError("undeclared plugin source file: " + relative)
            if not path.is_file():
                raise ValueError("plugin inputs must be regular files: " + relative)
            if path.suffix == ".py":
                compile(path.read_bytes(), str(path), "exec")
    for name in entry["files"]:
        regular_input(directory, name)
    manifest = json.loads(regular_input(directory, "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or type(manifest.get("schemaVersion")) is not int or manifest["schemaVersion"] != 1:
        raise ValueError("unsupported plugin manifest schemaVersion")
    if not valid_id(manifest.get("id")) or manifest["id"] != entry["id"]:
        raise ValueError("invalid, reserved or mismatching plugin manifest id")
    for field in ("name", "version"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError("plugin manifest requires " + field)
    kinds = manifest.get("kinds")
    if (not isinstance(kinds, list) or not kinds
            or any(not isinstance(kind, str) or kind not in ENTRY_POINTS for kind in kinds)
            or len(set(kinds)) != len(kinds)):
        raise ValueError("plugin kinds must be a non-empty array of supported kinds")
    points = manifest.get("entryPoints")
    if not isinstance(points, dict):
        raise ValueError("plugin entryPoints must be an object")
    for name in points.values():
        regular_input(directory, name)
        if name not in entry["files"]:
            raise ValueError("plugin entry point is missing from export files: " + name)
    for kind in kinds:
        if ENTRY_POINTS[kind] not in points:
            raise ValueError("plugin kind requires entryPoints." + ENTRY_POINTS[kind])
    bar = manifest.get("barWidget", {})
    if not isinstance(bar, dict) or ("defaultSection" in bar and (not isinstance(bar["defaultSection"], str)
            or bar["defaultSection"] not in {"left", "centerBegin", "center", "centerEnd", "tray", "right"})):
        raise ValueError("invalid plugin barWidget.defaultSection")
    binary = shutil.which("omarchy")
    if binary:
        subprocess.run([binary, "plugin", "validate", str(directory)], check=True)
        return "static checks and omarchy plugin validate passed"
    if require_omarchy:
        raise ValueError("omarchy required for this check; run on Omarchy Linux")
    return "static checks only; omarchy unavailable"


def export(directory, entry, destination):
    """Copy only reviewed public catalog inputs into a NEW standalone plugin root."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("destination already exists: " + str(destination))
    if destination.resolve().is_relative_to(directory.resolve()):
        raise ValueError("destination cannot be inside the plugin source directory")
    check(directory, entry)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for name in entry["files"]:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(regular_input(directory, name), target)
    except Exception:
        shutil.rmtree(destination)
        raise
    return len(entry["files"])

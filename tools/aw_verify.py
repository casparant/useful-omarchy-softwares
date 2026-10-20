"""Verify installed AW receipts and offline behavior without starting services."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile


COMPONENTS = {"aw-core", "aw-provider-tokenless", "aw-provider-sec-core"}


def verify_receipts(prefix):
    """Check the exact installed bytes/modes, including RTK provenance inputs."""
    receipts = {}
    owned = set()
    for path in (prefix / ".aw-packages").glob("*.json"):
        value = json.loads(path.read_text())
        component = value["component"]
        if component not in COMPONENTS or path.stem != component or component in receipts:
            raise ValueError("invalid component receipt")
        receipts[component] = value
        for name, metadata in value["files"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or name in owned:
                raise ValueError("invalid or duplicate receipt path")
            owned.add(name)
            target = prefix / relative
            if target.is_symlink() or not target.is_file():
                raise ValueError("missing or linked payload: " + name)
            if not target.resolve().is_relative_to(prefix.resolve()):
                raise ValueError("escaping payload: " + name)
            if stat.S_IMODE(target.stat().st_mode) != metadata["mode"]:
                raise ValueError("payload mode mismatch: " + name)
            if hashlib.sha256(target.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError("payload digest mismatch: " + name)
    if set(receipts) != COMPONENTS:
        raise ValueError("missing component receipt")
    core = receipts["aw-core"]
    for component, value in receipts.items():
        for field in ("source_commit", "version", "arch", "os"):
            if value[field] != core[field]:
                raise ValueError("component provenance mismatch")
        if component != "aw-core" and value["requires"] != {"aw-core": core["version"]}:
            raise ValueError("component dependency mismatch")
    return receipts


def smoke(prefix):
    """Exercise real configure/validate/inspect and missing-backend diagnostics."""
    verify_receipts(prefix)
    launcher = Path("/usr/lib/aw-preview/aw-launch")
    desktop = Path("/usr/share/applications/aw-preview.desktop")
    if Path("/usr/bin/aw-launch").resolve() != launcher:
        raise ValueError("public Panel launcher must resolve to the packaged entry")
    source = launcher.read_text()
    compile(source, str(launcher), "exec")
    if '@PREFIX@' in source or str(prefix) not in source:
        raise ValueError("desktop launcher does not reference the installed prefix")
    if stat.S_IMODE(launcher.stat().st_mode) != 0o755:
        raise ValueError("desktop launcher must be executable")
    if "Exec=/usr/lib/aw-preview/aw-launch\n" not in desktop.read_text() or "Terminal=true\n" not in desktop.read_text():
        raise ValueError("desktop entry must open the AW launcher in a terminal")
    aw = prefix / "bin/aw"
    package = prefix / "bin/aw-package"
    security = prefix / "libexec/aw/providers/sec-core"
    tokenless = prefix / "libexec/aw/providers/tokenless"
    with tempfile.TemporaryDirectory(prefix="aw-smoke-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        environment = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / "config"),
                           TOKENLESS_DATA_DIR=str(root / "tokenless"))

        def run(*args):
            return subprocess.check_output([str(arg) for arg in args], text=True,
                                           env=environment, cwd=root, timeout=15)

        run(aw, "--help")
        if "0.49.0" not in run(tokenless / "rtk", "--version"):
            raise ValueError("unexpected bundled RTK version")
        config = root / "aw.yaml"
        state = root / "state"
        run(package, "configure", "--prefix", prefix, "--config", config,
            "--state-dir", state, "--provider", "sec-core+tokenless",
            "--socket", root / "missing.sock", "--qoder", "/usr/bin/true")
        run(aw, "validate", "--config", config)
        document = json.loads(run(package, "config", "show", "--config", config))
        events = document["spec"]["events"]
        if [step["id"] for step in events["tool.before"]["steps"]] != ["scan-code", "rewrite-command"]:
            raise ValueError("security must precede Tokenless retry advice")
        if events["tool.before"]["steps"][0]["on_error"] != "block":
            raise ValueError("security failures must block in the generated policy")
        if [step["id"] for step in events["tool.after"]["steps"]] != ["observe-completion", "compress-result"]:
            raise ValueError("completion observation must precede result compression")
        before = config.read_bytes()
        snapshot = json.loads(run(aw, "inspect", "--config", config, "--json"))
        if snapshot["service"]["state"] != "offline" or state.exists():
            raise ValueError("inspection started or created daemon state")
        view = next(item for item in snapshot["providers"] if item["implementation"] == "tokenless")
        if view["admission"] != "unknown" or view["views"]["metrics.summary"]["status"] not in ("ok", "no_data"):
            raise ValueError("unexpected offline Tokenless view")
        if config.read_bytes() != before or (root / "tokenless").exists():
            raise ValueError("inspection modified configuration or compression storage")
        health = json.loads(run(security / "aw-provider-sec-core", "--health", "--helper",
                                security / "agent-sec-daemon-health", "--socket", root / "missing.sock"))
        if (health["backend"], health["admission"], health["check_result"]) != ("unavailable", "unknown", "unknown"):
            raise ValueError("missing backend reported ready")
    verify_receipts(prefix)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path)
    smoke(parser.parse_args().prefix)
    print("AW receipts/configure/validate/offline inspect/RTK/missing-backend: passed")

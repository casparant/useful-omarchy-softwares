"""Explicit VM acceptance: disconnect owned Foot clients, never stop the agent/server.

Run inside the target desktop user account: python3 tests/live_herdr.py ID OUTPUT
Requires a pre-existing managed Qoder session; does not send model prompts or approve tools.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('live_workspace', ROOT / 'workspace.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
key, output = sys.argv[1:]
identity_fields = ('id', 'pane', 'pid', 'conversation', 'revision', 'generation')


def observed():
    row = next(s for s in w.snapshot()['sessions'] if s['id'] == key)
    assert row['policy'] == 'bound', row
    assert all(row.get(k) for k in identity_fields), row
    return {k: row[k] for k in identity_fields}


environment = os.environ.copy()
desktop = subprocess.check_output(['systemctl', '--user', 'show-environment'], text=True)
for line in desktop.splitlines():
    k, _, v = line.partition('=')
    if k in ('WAYLAND_DISPLAY', 'DISPLAY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS'):
        environment[k] = v


def client(action, *args):
    p = subprocess.Popen(['/usr/bin/foot', '--app-id=anolisa-cosh-test', '--title=cosh live acceptance',
                          '-e', sys.executable, str(ROOT / 'workspace.py'), action, *args],
                         cwd=str(Path.home()), env=environment, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(1)
    assert p.poll() is None, 'Foot client exited during startup'
    pending = [p.pid]
    connected = False
    while pending:
        pid = pending.pop()
        try:
            command = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
            if command and Path(os.fsdecode(command[0])).name == 'herdr':
                connected = True
            children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
            pending.extend(int(child) for child in children)
        except FileNotFoundError:
            pass
    assert connected, 'No live herdr client; an error prompt is not a successful attachment'
    return p


def close(p):
    # Only the exact client this test created. Herdr server/PTY/agent are independent.
    p.terminate()
    p.wait(timeout=5)


before = observed()
first = client('open')
home = w.live()
assert next(x for x in home['workspaces'] if x['workspace_id'] == home['focused_workspace_id'])['label'] == 'cosh · AI Shell'
close(first)
after_close = observed()
assert before == after_close
second = client('open')
after_reopen = observed()
assert before == after_reopen
close(second)
third = client('attach', key)
after_attach = observed()
assert before == after_attach
Path(output).parent.mkdir(parents=True, exist_ok=True)
Path(output).write_text(json.dumps({'before': before, 'after_close': after_close,
                                  'after_reopen': after_reopen, 'after_attach': after_attach,
                                  'client_pid': third.pid, 'default_view': 'cosh AI Shell',
                                  'vm_reboot_tested': False}, indent=2))
print('PASS: Foot close/reopen/direct return kept the same Qoder process, conversation and AW binding')

"""Manual Omarchy acceptance: overlays stay visible while the cosh terminal is focused.

Run as the target desktop user with an existing anolisa-cosh window:
python3 tests/live_panel.py OUTPUT_DIRECTORY
No agent launch, model request, tool approval or terminal input is performed.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

output = Path(sys.argv[1]).resolve()
output.mkdir(parents=True, exist_ok=True, mode=0o700)
for line in subprocess.check_output(['systemctl', '--user', 'show-environment'], text=True).splitlines():
    key, _, value = line.partition('=')
    if key in {'WAYLAND_DISPLAY', 'DISPLAY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS',
               'HYPRLAND_INSTANCE_SIGNATURE', 'OMARCHY_PATH'}:
        os.environ[key] = value


def summon(payload):
    subprocess.run(['omarchy-shell', 'shell', 'summon', 'anolisa.agent-entry', json.dumps(payload)],
                   check=True, stdout=subprocess.DEVNULL)


def surface(name):
    result = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers'], text=True))
    for monitor in result.values():
        for level, rows in monitor['levels'].items():
            for row in rows:
                if row.get('namespace') == name:
                    return {key: row[key] for key in ('namespace', 'x', 'y', 'w', 'h')} | {'level': level}
    return None


def observed(name):
    for _ in range(40):
        value = surface(name)
        if value:
            assert value['level'] == '3', 'Expected overlay above pinned application windows'
            return value
        time.sleep(.1)
    raise AssertionError('Panel surface unavailable: ' + name)


results = {}
for label, payload, name in [('compact', {}, 'anolisa-control-plane'),
                             ('workbench', {'view': 'details'}, 'anolisa-workbench')]:
    summon(payload)
    before = observed(name)
    subprocess.run(['omarchy', 'hyprland', 'focus', 'app', '^anolisa-cosh$'], check=True)
    time.sleep(.6)  # Allow focus notifications and a rendered status frame.
    after = surface(name)
    assert before == after, 'Panel disappeared or moved after focusing the terminal'
    subprocess.run(['grim', str(output / (label + '.png'))], check=True)
    results[label] = {'before_terminal_focus': before, 'after_terminal_focus': after}
summon({})
(output / 'overlays.json').write_text(json.dumps(results, indent=2))
print('PASS: compact and workbench overlays persist above windows after terminal focus')

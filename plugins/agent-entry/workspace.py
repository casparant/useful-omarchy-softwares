#!/usr/bin/env python3
"""cosh/herdr live-session bridge. Runtime receipts contain no credentials or tool text."""
# Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent
NAME = 'anolisa-cosh'
spec = importlib.util.spec_from_file_location('workspace_aw', ROOT / 'aw_status.py')
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)


def profile():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'anolisa/cosh-herdr.toml'


def runtime():
    base = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
    if not base.is_absolute() or base.stat().st_uid != os.getuid():
        raise ValueError('A user-owned XDG_RUNTIME_DIR is required')
    return base / 'anolisa-cosh'


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Private user-owned directory required')


def write_json(path, value):
    private_dir(path.parent)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def session_dir(key):
    if not re.fullmatch(r'[a-f0-9]{32}', key):
        raise ValueError('Invalid managed session ID')
    return runtime() / key


def herdr_env():
    value = os.environ.copy()
    # Never accidentally target an inherited, unrelated Herdr server.
    for key in ('HERDR_SOCKET_PATH', 'HERDR_SESSION', 'HERDR_SESSION_NAME'):
        value.pop(key, None)
    value['HERDR_CONFIG_PATH'] = str(profile())
    return value


def herdr(*args):
    binary = aw.trusted_file(Path(shutil.which('herdr') or '/usr/bin/herdr'))
    return [str(binary), '--session', NAME, *args]


def api(*args):
    # query() intentionally never starts a server, reads a terminal, or prints stderr.
    aw.trusted_file(profile())
    return aw.query(herdr(*args), env=herdr_env(), timeout=3)['result']


def live():
    return api('api', 'snapshot')['snapshot']


def setup():
    shell = aw.trusted_file(ROOT / 'cosh-shell')
    aw.trusted_file(Path(shutil.which('cosh') or '/usr/bin/cosh'))
    herdr('--version')
    config = profile()
    config.parent.mkdir(parents=True, exist_ok=True)
    if not config.exists():
        text = ('onboarding = false\n[terminal]\ndefault_shell = ' + json.dumps(str(shell))
                + '\n[update]\nversion_check = false\nmanifest_check = false\n'
                  '[session]\nresume_agents_on_restore = false\n')
        with config.open('x') as handle:
            handle.write(text)
        config.chmod(0o600)
    aw.trusted_file(config)


def focus_shell(directory=None):
    setup()
    try:
        data = live()
    except (ValueError, OSError, subprocess.SubprocessError):
        # Only an explicit user launch may start the dedicated server.
        subprocess.Popen(herdr('server'), env=herdr_env(), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
        for _ in range(30):
            try:
                data = live()
                break
            except (ValueError, OSError, subprocess.SubprocessError):
                time.sleep(.1)
        else:
            raise ValueError('herdr did not start; check herdr status server')
    home = next((w for w in data['workspaces'] if w.get('label') == 'cosh · AI Shell'), None)
    if home is None:
        home = api('workspace', 'create', '--cwd', str(directory or Path.cwd()),
                   '--label', 'cosh · AI Shell', '--no-focus')['workspace']
    api('workspace', 'focus', home['workspace_id'])


def open_shell():
    focus_shell()
    os.execve(herdr()[0], herdr(), herdr_env())


def aw_command(argv):
    """Cosh's local Bash adapter; all execution still uses the native AW binary."""
    options, native_args = {}, []
    head, separator, tail = argv, [], []
    if '--' in argv:
        split = argv.index('--')
        head, separator, tail = argv[:split], ['--'], argv[split + 1:]
    if head[:1] != ['run']:
        os.execv(str(aw.AW), [str(aw.AW), *argv])
        return
    # The pinned native CLI accepts key/value options before its -- delimiter.
    for index in range(1, len(head), 2):
        name = head[index]
        if index + 1 == len(head) or name in options:
            raise ValueError('AW run requires distinct key/value options; see aw --help')
        options[name] = head[index + 1]
        if name not in ('--config', '--agent'):
            native_args.extend(head[index:index + 2])
    if options.get('--agent') != 'qoder':
        os.execv(str(aw.AW), [str(aw.AW), *argv])
        return
    if set(options) - {'--config', '--agent', '--native-settings', '--native-profile', '--native-state-dir'}:
        raise ValueError('Unknown AW run option; see aw --help')
    start(options.get('--config'), native_args + separator + tail)


def start(config=None, native_args=()):
    if os.environ.get('HERDR_ENV') != '1':
        raise ValueError('Open cosh first, then run: aw run --agent qoder')
    # Match the actual calling pane against the dedicated session, never focused state.
    data = live()
    if os.environ.get('HERDR_PANE_ID') not in {p['pane_id'] for p in data['panes']}:
        raise ValueError('This cosh pane does not belong to the managed session')
    if not aw.AW.exists() or not shutil.which('qodercli'):
        raise ValueError('Install AW and Qoder with omarchy-tools aw first')
    source = (Path(config).expanduser() if config is not None else
              Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'aw/preview.yaml').resolve()
    aw.trusted_file(source)
    key = uuid.uuid4().hex
    write_json(session_dir(key) / 'intent.json', {'id': key, 'project': str(Path.cwd()),
                                               'config': str(source), 'native_args': list(native_args)})
    result = api('workspace', 'create', '--cwd', str(Path.cwd()), '--label', 'Qoder · ' + Path.cwd().name,
                 '--env', 'ANOLISA_AW_SESSION=' + key, '--focus')
    print('herdr 已创建终端；AW 启动与 Qoder 登录状态请在该终端确认。')
    print(json.dumps({'id': key, 'pane': result['root_pane']['pane_id']}))


def proc_identity(pid):
    # starttime disambiguates PID reuse. comm may itself contain parentheses.
    values = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()
    return values[19]


def qoder_process(parent):
    parents, commands = {}, {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            pid = int(path.parent.name)
            parents[pid] = int(fields[1])
            commands[pid] = (path.parent / 'cmdline').read_bytes().decode().split('\0')[:-1]
        except (OSError, ValueError, UnicodeError):
            pass
    for pid, argv in commands.items():
        ancestor = pid
        for _ in range(32):
            if ancestor == parent:
                if argv and Path(argv[0]).name in ('qodercli', 'qoderclicn'):
                    return pid, argv
                break
            ancestor = parents.get(ancestor, 0)
            if not ancestor:
                break
    return None, []


def native_settings(pid, argv):
    path = argv[argv.index('--settings') + 1]
    if not re.fullmatch(r'/proc/self/fd/[0-9]+', path):
        raise ValueError('Native AW settings descriptor required')
    path = Path(f'/proc/{pid}/fd') / Path(path).name
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Native settings limit')
    return json.loads(path.read_text())


def consume_intent(directory, key):
    """Saved Herdr environment must never recreate an agent after server restart."""
    path = directory / 'intent.json'
    aw.trusted_file(path)
    intent = json.loads(path.read_text())
    if (not isinstance(intent, dict) or set(intent) != {'id', 'project', 'config', 'native_args'}
            or intent['id'] != key or intent['project'] != str(Path.cwd())
            or not isinstance(intent['config'], str) or not Path(intent['config']).is_absolute()
            or not isinstance(intent['native_args'], list)
            or not all(isinstance(a, str) and '\0' not in a for a in intent['native_args'])):
        raise ValueError('Launch intent does not match this terminal')
    # Only one consumer can remove this private intent successfully.
    path.unlink()
    return intent


def hooks_bound(pid, argv, config, revision, generation):
    """Verify both native hook phases against this immutable policy path."""
    try:
        if not revision or not generation:
            return False
        settings = native_settings(pid, argv)
        document = json.loads(config.read_text())
        found = False
        for phase, event in [('PreToolUse', 'tool.before'), ('PostToolUse', 'tool.after')]:
            expected = document['spec']['events'].get(event, {})
            expected = [(s['id'], s['on_error']) for s in expected.get('steps', [])
                        if expected.get('enabled') and s.get('enabled', True)]
            observed = []
            for group in settings.get('hooks', {}).get(phase, []):
                for hook in group.get('hooks', []):
                    if Path(hook.get('command', '')).resolve() != aw.AW.resolve():
                        continue
                    args = hook.get('args', [])
                    if args[:1] != ['hook'] or args[args.index('--event') + 1] != event:
                        return False
                    binding_path = Path(args[args.index('--binding') + 1])
                    aw.trusted_file(binding_path)
                    if (not binding_path.resolve().is_relative_to(config.parent / 'aw')
                            or binding_path.stat().st_size > 65536):
                        return False
                    binding = json.loads(binding_path.read_text())
                    if (binding['adapter'] != 'qoder' or binding['binding']['target'] != 'qoder'
                            or binding['binding']['identity'] != {'generation': generation, 'config_revision': revision}
                            or binding['socket'] != str(config.parent / 'aw/aw.sock')):
                        return False
                    observed.append((args[args.index('--step') + 1], args[args.index('--on-error') + 1]))
                    found = True
            if observed != expected:
                return False
        return found
    except (OSError, ValueError, IndexError, TypeError, KeyError):
        return False


def run_agent():
    key = os.environ.get('ANOLISA_AW_SESSION', '')
    directory = session_dir(key)
    try:
        intent = consume_intent(directory, key)
    except FileNotFoundError:
        print('此终端没有新的启动请求；进入 cosh，不自动恢复或新建 Qoder。', flush=True)
        os.environ.pop('ANOLISA_AW_SESSION', None)
        os.execv(str(ROOT / 'cosh-shell'), [str(ROOT / 'cosh-shell')])
    private_dir(directory)
    record = {'id': key, 'pane': os.environ['HERDR_PANE_ID'], 'project': str(Path.cwd()),
              'supervisor': os.getpid(), 'starttime': proc_identity(os.getpid()),
              'started': int(time.time()), 'state': 'starting'}
    receipt = directory / 'receipt.json'
    write_json(receipt, record)
    def terminate(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGHUP, terminate)
    process = None
    config = directory / 'policy.json'
    try:
        executable = aw.trusted_file(aw.AW)
        source = Path(intent['config'])
        aw.trusted_file(source)
        package = aw.trusted_file(executable.parent / 'aw-package')
        document = aw.query([package, 'config', 'show', '--config', source])
        # Preserve all selected providers, conditions, external hooks and native permissions.
        document['spec']['daemon']['state_dir'] = str(directory / 'aw')
        document['spec']['daemon']['endpoint'] = str(directory / 'aw/aw.sock')
        write_json(config, document)
        subprocess.run([str(executable), 'validate', '--config', str(config)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        security_id, socket = aw.security_transport(document, executable.parent.parent)
        if socket and aw.health(executable.parent.parent, socket) != 'authenticated_reachable':
            raise ValueError('sec-core unavailable; launch blocked by the selected policy')
        record['digest'] = hashlib.sha256(config.read_bytes()).hexdigest()
        write_json(receipt, record)
        print('AW 策略已固定。登录与权限确认保留在 Qoder；关闭窗口保留会话。', flush=True)
        environment = os.environ.copy()
        # The entry adapter belongs to the AI Shell, never to Qoder's tools.
        for name in ('BASH_FUNC_aw%%', 'ANOLISA_COSH_WORKSPACE'):
            environment.pop(name, None)
        process = subprocess.Popen([str(executable), 'run', '--config', str(config), '--agent', 'qoder',
                                    *intent['native_args']], env=environment)
        record.update(state='running', aw_pid=process.pid)
        write_json(receipt, record)
        code = process.wait()
        record.update(state='exited', exit_code=code)
    except KeyboardInterrupt:
        record.update(state='exited', exit_code=130)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        record['state'] = 'failed'
        print('AW 启动未完成：请检查 AW 配置与安全后台。未跳过策略或原生权限。', file=sys.stderr)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if config.exists() and process is not None:
            try:
                subprocess.run([str(aw.AW), 'stop', '--config', str(config)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
        write_json(receipt, record)
    if record['state'] == 'failed':
        input('按 Enter 返回 cosh。')


def project_record(record, directory, data):
    item = {key: record[key] for key in ('id', 'pane', 'project', 'started')}
    item.update(agent='Qoder', state='exited', policy='unverified', revision=None,
                conversation=None, pid=None, status_source='herdr_screen', tokenless=None, security=None)
    try:
        alive = proc_identity(record['supervisor']) == record['starttime']
    except FileNotFoundError:
        alive = False
    if record['state'] in ('exited', 'failed') or not alive:
        item['state'] = record['state'] if record['state'] in ('exited', 'failed') else 'exited'
        return item
    pane = next((p for p in data['panes'] if p['pane_id'] == record['pane']), None)
    if pane is None:
        return item
    item['state'] = pane.get('agent_status', 'unknown')
    agents = [a for a in data['agents'] if a.get('pane_id') == record['pane']]
    if agents:
        agent = agents[0]
        # Herdr's public projection varies by release; absent identity stays unknown.
        ref = agent.get('agent_session') or {}
        candidate = ref.get('value') if ref.get('kind') == 'id' else None
        if isinstance(candidate, str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', candidate):
            item['conversation'] = candidate
    pid, argv = qoder_process(record['supervisor'])
    item['pid'] = pid
    config = directory / 'policy.json'
    aw.trusted_file(config)
    if not pid or hashlib.sha256(config.read_bytes()).hexdigest() != record.get('digest'):
        return item
    report = aw.snapshot(config)
    item.update(aw_state=report['state'], tokenless=report['tokenless'], security=report['security'],
                activities=report['activities'], generation=report.get('generation'),
                revision=report.get('revision'), hook_plan=report['hook_plan'])
    if report['state'] == 'online' and hooks_bound(pid, argv, config, report.get('revision'), report.get('generation')):
        item['policy'] = 'bound'
    return item


def snapshot():
    result = {'state': 'unavailable', 'sessions': [], 'updated': time.strftime('%H:%M:%S')}
    try:
        data = live()
        result['state'] = 'online'
        directory = runtime()
        if not directory.exists():
            return result
        aw.trusted_file(profile())
        paths = sorted(directory.glob('*/receipt.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
        deadline = time.monotonic() + 8
        for path in paths:
            try:
                if time.monotonic() > deadline:
                    raise ValueError('session_query_budget')
                aw.trusted_file(path)
                if path.stat().st_size > 16384:
                    continue
                record = json.loads(path.read_text())
                if session_dir(record['id']) != path.parent:
                    continue
                result['sessions'].append(project_record(record, path.parent, data))
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                # Never retain a green receipt when a live query fails.
                result['sessions'].append({'id': path.parent.name, 'agent': 'Qoder', 'state': 'unknown',
                                           'policy': 'unverified', 'project': '', 'pane': '', 'revision': None})
        managed = {s['pane'] for s in result['sessions']}
        for agent in data['agents'][:20]:
            if agent.get('pane_id') not in managed:
                result['sessions'].append({'agent': str(agent.get('agent', 'Agent'))[:40],
                                           'state': agent.get('state', 'unknown'), 'policy': 'unmanaged',
                                           'project': '', 'id': '', 'pane': agent.get('pane_id', '')})
        # Other Qoder terminals are visible as unmanaged, never inferred AW adoption.
        managed_pids = {s.get('pid') for s in result['sessions']}
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                if path.stat().st_uid != os.getuid() or int(path.parent.name) in managed_pids:
                    continue
                args = path.read_bytes().split(b'\0')
                if args and Path(os.fsdecode(args[0])).name in ('qodercli', 'qoderclicn'):
                    result['sessions'].append({'agent': 'Qoder', 'state': 'unknown', 'policy': 'unmanaged',
                                               'project': str((path.parent / 'cwd').resolve()), 'id': '', 'pane': '',
                                               'pid': int(path.parent.name)})
            except (OSError, ValueError):
                pass
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        result.update(state='unavailable', sessions=[])
    return result


def attach(key):
    item = next((s for s in snapshot()['sessions'] if s['id'] == key), None)
    if not item or not item.get('pid'):
        raise ValueError('Session is no longer live; no new Qoder was started')
    args = herdr('agent', 'attach', item['pane'])
    subprocess.run(args, env=herdr_env(), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'open', 'start', 'run', 'list', 'attach', 'aw'))
    parser.add_argument('id', nargs='?')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if os.geteuid() == 0:
            raise ValueError('Use the desktop user account, not sudo')
        if args.action == 'setup':
            setup()
            subprocess.run(herdr('integration', 'install', 'qodercli'), env=herdr_env(), check=True)
        elif args.action == 'open':
            open_shell()
        elif args.action == 'start':
            start()
        elif args.action == 'aw':
            aw_command(([args.id] if args.id else []) + args.native_args)
        elif args.action == 'run':
            run_agent()
        elif args.action == 'attach':
            attach(args.id or '')
        else:
            print(json.dumps(snapshot(), ensure_ascii=False))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('cosh: ' + str(error), file=sys.stderr)
        if args.action == 'attach' and sys.stdin.isatty():
            input('未新建 Qoder。请检查已有会话窗口或托管后台；按 Enter 关闭。')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Bounded, read-only AW workbench queries; never expose config or tool payloads."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

AW = Path('/usr/bin/aw')
VIEW_STATES = {'ok', 'no_data', 'unavailable', 'unsupported', 'stale', 'disabled', 'partial'}


def trusted_file(path):
    """Only query files whose names and contents other users cannot replace."""
    resolved = path.resolve(strict=True)
    for candidate in (path, resolved):
        info = candidate.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('invalid_file')
        for entry in (candidate, *candidate.parents):
            info = entry.stat()
            sticky = entry != candidate and info.st_uid == 0 and info.st_mode & stat.S_ISVTX
            if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not sticky):
                raise ValueError('untrusted_file')
    return resolved


def query(argv, timeout=6, limit=2 * 1024 * 1024):
    """Cap time and output, suppress private stderr, and reap owned queries."""
    deadline = time.monotonic() + timeout
    with subprocess.Popen([str(arg) for arg in argv], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          start_new_session=True) as process:
        try:
            output = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline - time.monotonic())):
                        raise ValueError('query_timeout')
                    chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > limit:
                        raise ValueError('output_limit')
                else:
                    raise ValueError('query_timeout')
            if process.wait(timeout=max(0, deadline - time.monotonic())):
                raise ValueError('query_failed')
            return json.loads(output)
        finally:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()


def empty(state):
    return {'state': state, 'audit': None, 'updated': time.strftime('%H:%M:%S'),
            'tokenless': {'configured': None, 'enabled': None, 'status': 'unavailable'},
            'security': {'configured': None, 'enabled': None, 'backend': 'not_checked'},
            'activity_status': 'unavailable', 'activities': [],
            'hook_plan': {'status': 'unavailable', 'phases': []}}


def hook_plan(document, security_id, tokenless_id):
    """Describe configured order, never infer runtime attachment or adoption."""
    events = document['spec']['events']
    phases = []
    for event in ('tool.before', 'tool.after'):
        value = events.get(event)
        if value is None:
            phases.append({'event': event, 'enabled': False, 'steps': []})
            continue
        enabled = value['enabled']
        steps = value['steps']
        if type(enabled) is not bool or not isinstance(steps, list) or len(steps) > 128:
            raise ValueError('hook_plan_contract')
        projected = []
        for step in steps:
            role = 'custom'
            if security_id is not None and step.get('provider') == security_id:
                role = {'scan_code': 'security', 'observe_tool': 'observation'}.get(step.get('operation'), role)
            elif tokenless_id is not None and step.get('provider') == tokenless_id:
                role = {'pre_tool': 'optimization', 'post_tool': 'compression'}.get(step.get('operation'), role)
            action = step['on_error']
            step_enabled = step.get('enabled', True)
            if action not in ('block', 'report', 'withhold_result') or type(step_enabled) is not bool:
                raise ValueError('hook_error_action')
            # No argv, guards, user-defined names, config values or input payloads.
            projected.append({'role': role, 'on_error': action,
                              'enabled': step_enabled})
        phases.append({'event': event, 'enabled': enabled, 'steps': projected,
                       'conditional': 'guard' in value or 'match' in value})
    return {'status': 'configured', 'phases': phases}


def flags(provider):
    if any(type(provider[key]) is not bool for key in ('configured', 'enabled')):
        raise ValueError('provider_flags')
    if provider['admission'] != 'unknown' or provider['native_readiness'] != 'unknown':
        raise ValueError('provider_contract')
    return {key: provider[key] for key in ('configured', 'enabled')}


def project(data, security_id=None):
    """Project known aggregates, preserving unknown evidence and scope limits."""
    if data['api_version'] != 'aw-panel/v1alpha1':
        raise ValueError('unsupported_contract')
    service = data['service']
    if service['state'] not in ('online', 'offline', 'unavailable') or service['adoption'] != 'unverified':
        raise ValueError('service_contract')
    if service['audit_healthy'] is not None and type(service['audit_healthy']) is not bool:
        raise ValueError('audit_contract')
    result = empty(service['state'])
    result['audit'] = service['audit_healthy']
    for component in ('tokenless', 'security'):
        result[component].update(configured=False, enabled=False)
    providers = data['providers']
    if not isinstance(providers, list):
        raise ValueError('providers')
    tokenless = [p for p in providers if p.get('implementation') == 'tokenless']
    security = [p for p in providers if security_id is not None and p['id'] == security_id]
    if len(tokenless) > 1 or len(security) > 1:
        raise ValueError('ambiguous_provider')
    if security:
        result['security'].update(flags(security[0]))
    tokenless_id = None
    if tokenless:
        provider = tokenless[0]
        tokenless_id = provider['id']
        report = result['tokenless']
        report.update(flags(provider))
        view = provider['views']['metrics.summary']
        if view['status'] not in VIEW_STATES:
            raise ValueError('view_contract')
        report['status'] = view['status']
        if view['status'] == 'ok':
            metrics = view['data']
            if (metrics['scope'] != 'component_store_recent_records' or metrics['requested_limit'] != 200
                    or metrics['recording_state'] != 'unknown' or metrics['adoption'] != 'unverified'):
                raise ValueError('metrics_scope')
            for target, source in [('records', 'records'), ('before', 'before_tokens_estimated'),
                                   ('after', 'after_tokens_estimated'), ('saved', 'saved_tokens_estimated'),
                                   ('percent', 'saved_percent')]:
                value = metrics[source]
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or not 0 <= value <= 9007199254740991
                        or (target != 'percent' and type(value) is not int)
                        or (target == 'records' and value > 200) or (target == 'percent' and value > 100)):
                    raise ValueError('invalid_metric')
                report[target] = value
    recent = data['recent_execution']
    if recent['status'] not in VIEW_STATES:
        raise ValueError('activity_contract')
    result['activity_status'] = recent['status']
    if recent['status'] == 'ok':
        recent = recent['data']
        if recent['scope'] != 'service_generation' or recent['limit'] != 20 or not isinstance(recent['items'], list) or len(recent['items']) > 20:
            raise ValueError('activity_scope')
        for item in recent['items']:
            if (item['status'] not in ('ok', 'error') or type(item['policy_block']) is not bool
                    or item['failure_action'] not in (None, 'block', 'report')
                    or type(item['elapsed_ms']) is not int or not 0 <= item['elapsed_ms'] <= 9007199254740991):
                raise ValueError('activity_fields')
            kind, tone = 'step_completed', 'neutral'
            if item['status'] == 'error':
                kind = 'error_block' if item['failure_action'] == 'block' else 'step_error'
                tone = 'danger'
            elif item['policy_block']:
                if item['provider'] == tokenless_id and item['step_id'] == 'rewrite-command':
                    kind, tone = 'optimization_retry', 'notice'
                elif item['provider'] == security_id:
                    kind, tone = 'security_block', 'danger'
                else:
                    kind, tone = 'policy_block', 'notice'
            elif item['provider'] == security_id:
                kind = {'scan-code': 'security_checked', 'observe-completion': 'completion_observed'}.get(item['step_id'], kind)
            elif item['provider'] == tokenless_id:
                kind = {'compress-result': 'compression_completed', 'rewrite-command': 'optimization_checked'}.get(item['step_id'], kind)
            result['activities'].append({'kind': kind, 'tone': tone, 'elapsed_ms': item['elapsed_ms']})
    return result


def security_transport(document, prefix):
    provider = prefix / 'libexec/aw/providers/sec-core/aw-provider-sec-core'
    matches = [(key, value.get('transport', {}).get('argv', []))
               for key, value in document['spec']['providers'].items()
               if value.get('transport', {}).get('argv', [None])[0:1] == [str(provider)]]
    if not matches:
        return None, None
    if len(matches) != 1:
        raise ValueError('ambiguous_security_provider')
    key, argv = matches[0]
    if (len(argv) != 5 or argv[1] != '--cli' or argv[2] != str(provider.parent / 'agent-sec-cli')
            or argv[3] != '--socket' or not isinstance(argv[4], str) or not Path(argv[4]).is_absolute()):
        raise ValueError('security_transport')
    return key, argv[4]


def health(prefix, socket):
    directory = prefix / 'libexec/aw/providers/sec-core'
    receipt = json.loads(trusted_file(prefix / '.aw-packages/aw-provider-sec-core.json').read_text())
    for name in ('aw-provider-sec-core', 'agent-sec-daemon-health'):
        path = trusted_file(directory / name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if receipt['files'][str(path.relative_to(prefix))]['sha256'] != digest or not os.access(path, os.X_OK):
            raise ValueError('receipt_mismatch')
    value = query([directory / 'aw-provider-sec-core', '--health', '--helper',
                   directory / 'agent-sec-daemon-health', '--socket', socket], timeout=4, limit=65536)
    if (value['api_version'] != 'aw-sec-core-health/v1alpha1' or type(value['helper_installed']) is not bool
            or value['socket_configured'] is not True or value['admission'] != 'unknown'
            or value['check_result'] != 'unknown' or value['backend'] not in ('authenticated_reachable', 'unavailable')
            or value['code'] not in (None, 'component_missing', 'probe_failed', 'deadline_exceeded', 'probe_transport_error')):
        raise ValueError('health_contract')
    if (value['backend'] == 'authenticated_reachable') != (value['code'] is None and value['helper_installed']):
        raise ValueError('health_evidence')
    return value['backend']


def snapshot():
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'aw/preview.yaml'
    if not AW.exists():
        return empty('not_installed')
    if not config.exists() and not config.is_symlink():
        return empty('unconfigured')
    try:
        executable = trusted_file(AW)
        trusted_file(config)
        prefix = executable.parent.parent
        package = trusted_file(prefix / 'bin/aw-package')
        document = query([package, 'config', 'show', '--config', config])
        security_id, socket = security_transport(document, prefix)
        data = query([executable, 'inspect', '--config', config, '--json'])
        result = project(data, security_id)
        tokenless_id = next((p['id'] for p in data['providers']
                             if p.get('implementation') == 'tokenless'), None)
        try:
            result['hook_plan'] = hook_plan(document, security_id, tokenless_id)
        except (KeyError, TypeError, ValueError, AttributeError):
            # A plan projection error must not erase independent health or metrics.
            pass
        if socket is not None:
            try:
                result['security']['backend'] = health(prefix, socket)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, subprocess.SubprocessError):
                result['security']['backend'] = 'query_failed'
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, subprocess.SubprocessError):
        # Neither configuration, raw stderr nor command arguments belong on the desktop.
        return empty('query_failed')

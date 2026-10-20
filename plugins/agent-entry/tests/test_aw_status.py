"""Read-only workbench boundaries and upstream aw-panel/v1alpha1 fixtures."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workbench', ROOT / 'aw_status.py')
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)


def fixture(name='ok'):
    return json.loads((ROOT / 'tests/fixtures' / ('panel-' + name + '.json')).read_text())


class ProjectionTest(unittest.TestCase):
    def test_upstream_online_and_offline_metrics_have_the_same_stored_scope(self):
        for name, state in [('ok', 'online'), ('offline', 'offline')]:
            result = aw.project(fixture(name), 'security')
            self.assertEqual(result['state'], state)
            self.assertEqual(result['tokenless']['saved'], 3500)
            self.assertEqual(result['tokenless']['records'], 12)
            self.assertNotIn('session', result)
            self.assertEqual(result['security']['backend'], 'not_checked')

    def test_unavailable_metrics_do_not_become_zero_or_reuse_old_numbers(self):
        for name in ['no-data', 'partial', 'component-missing']:
            result = aw.project(fixture(name), 'security')
            self.assertNotIn('saved', result['tokenless'])
            self.assertNotIn('percent', result['tokenless'])

    def test_unknown_evidence_and_invalid_numbers_are_rejected(self):
        for key, value in [('adoption', 'verified'), ('scope', 'session'), ('records', True),
                           ('records', 201), ('saved_percent', float('nan')),
                           ('saved_percent', 101), ('before_tokens_estimated', -1)]:
            data = fixture()
            data['providers'][0]['views']['metrics.summary']['data'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                aw.project(data)

    def test_stale_runtime_does_not_invalidate_independent_store_metrics(self):
        result = aw.project(fixture('stale'))
        self.assertEqual(result['state'], 'unavailable')
        self.assertEqual(result['tokenless']['saved'], 3500)
        self.assertEqual(result['activities'], [])

    def test_stale_response_with_numbers_hides_them(self):
        data = fixture()
        data['providers'][0]['views']['metrics.summary']['status'] = 'stale'
        self.assertNotIn('saved', aw.project(data)['tokenless'])

    def test_duplicate_provider_and_unknown_version_are_rejected(self):
        data = fixture()
        data['providers'].append(copy.deepcopy(data['providers'][0]))
        with self.assertRaises(ValueError):
            aw.project(data)
        data = fixture()
        data['api_version'] = 'aw-panel/future'
        with self.assertRaises(ValueError):
            aw.project(data)

    def test_events_distinguish_retry_rejection_and_fail_closed(self):
        data = fixture()
        base = {'elapsed_ms': 10, 'status': 'ok', 'policy_block': False, 'failure_action': None}
        rows = [
            dict(base, provider='tokenless-main', step_id='rewrite-command', policy_block=True),
            dict(base, provider='security', step_id='scan-code', policy_block=True),
            dict(base, provider='security', step_id='scan-code', status='error', failure_action='block'),
            dict(base, provider='security', step_id='scan-code', status='error', failure_action='report'),
            dict(base, provider='security', step_id='scan-code'),
            dict(base, provider='security', step_id='observe-completion'),
            dict(base, provider='tokenless-main', step_id='compress-result'),
        ]
        for row in rows:
            row.update(command='PRIVATE_COMMAND', token='PRIVATE_TOKEN', failure='PRIVATE_ERROR')
        data['recent_execution'] = {'status': 'ok', 'data': {'scope': 'service_generation', 'limit': 20, 'items': rows}}
        result = aw.project(data, 'security')
        self.assertEqual([r['kind'] for r in result['activities']],
                         ['optimization_retry', 'security_block', 'error_block', 'step_error',
                          'security_checked', 'completion_observed', 'compression_completed'])
        self.assertNotIn('PRIVATE_', json.dumps(result))

    def test_failed_query_has_no_false_disabled_or_success_values(self):
        result = aw.empty('query_failed')
        self.assertIsNone(result['security']['enabled'])
        self.assertIsNone(result['tokenless']['configured'])
        self.assertEqual(result['activities'], [])


class QueryTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_output_and_timeout_limits_reap_the_owned_process(self):
        for mode in ['output', 'timeout']:
            pid = self.root / (mode + '.pid')
            code = ('import os,time; from pathlib import Path; '
                    f'Path({str(pid)!r}).write_text(str(os.getpid())); '
                    + ('print("x"*4096, flush=True); ' if mode == 'output' else '')
                    + 'time.sleep(30)')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                aw.query([sys.executable, '-c', code], timeout=.3, limit=1024)
            if sys.platform == 'linux':
                self.assertFalse(Path('/proc/' + pid.read_text()).exists())

    def test_json_query_is_bounded_and_hides_stderr(self):
        result = aw.query([sys.executable, '-c', 'print("{\\"ok\\": true}")'])
        self.assertEqual(result, {'ok': True})
        with self.assertRaisesRegex(ValueError, '^query_failed$'):
            aw.query([sys.executable, '-c', 'import sys; print("SECRET", file=sys.stderr); sys.exit(1)'])

    def test_untrusted_file_and_parent_are_rejected(self):
        p = self.root / 'binary'
        p.write_text('test')
        p.chmod(0o666)
        with self.assertRaises(ValueError):
            aw.trusted_file(p)
        p.chmod(0o600)
        self.root.chmod(0o777)
        with self.assertRaises(ValueError):
            aw.trusted_file(p)
        self.root.chmod(0o700)
        self.assertEqual(aw.trusted_file(p), p)

    def test_missing_configuration_does_not_spawn_or_initialize(self):
        executable = self.root / 'aw'
        executable.touch()
        with patch.object(aw, 'AW', executable), patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root)}), patch.object(aw, 'query') as query:
            self.assertEqual(aw.snapshot()['state'], 'unconfigured')
            query.assert_not_called()
            self.assertFalse((self.root / 'aw/preview.yaml').exists())

    def test_transport_never_executes_configuration_supplied_programs(self):
        prefix = Path('/opt/aw')
        provider = str(prefix / 'libexec/aw/providers/sec-core/aw-provider-sec-core')
        doc = {'spec': {'providers': {'security': {'transport': {'argv': ['/tmp/arbitrary', '--socket', '/tmp/s']}}}}}
        self.assertEqual(aw.security_transport(doc, prefix), (None, None))
        doc['spec']['providers']['security']['transport']['argv'] = [provider, '--cli', '/tmp/arbitrary', '--socket', '/tmp/s']
        with self.assertRaises(ValueError):
            aw.security_transport(doc, prefix)

    def test_poll_uses_only_existing_read_only_interfaces(self):
        prefix = self.root / 'prefix'
        (prefix / 'bin').mkdir(parents=True)
        executable = prefix / 'bin/aw'
        executable.touch()
        (prefix / 'bin/aw-package').touch()
        config = self.root / 'config/aw/preview.yaml'
        config.parent.mkdir(parents=True)
        config.write_text('PRIVATE CONFIG')
        for file in [executable, prefix/'bin/aw-package', config]:
            file.chmod(0o600)
        for directory in [prefix, prefix/'bin', config.parent, config.parent.parent]:
            directory.chmod(0o700)
        directory = prefix / 'libexec/aw/providers/sec-core'
        doc = {'spec': {'providers': {'security': {'transport': {'argv': [str(directory/'aw-provider-sec-core'), '--cli', str(directory/'agent-sec-cli'), '--socket', '/run/sec.sock']}}}}}
        before = config.read_bytes()
        with patch.object(aw, 'AW', executable), patch.dict(os.environ, {'XDG_CONFIG_HOME': str(config.parent.parent)}), patch.object(aw, 'query', side_effect=[doc, fixture('partial')]) as query, patch.object(aw, 'health', return_value='authenticated_reachable') as health:
            result = aw.snapshot()
            self.assertEqual([c.args[0][1] for c in query.call_args_list], ['config', 'inspect'])
            self.assertEqual(query.call_args_list[0].args[0][2], 'show')
            health.assert_called_once_with(prefix, '/run/sec.sock')
            self.assertEqual(result['security']['backend'], 'authenticated_reachable')
            self.assertNotIn('PRIVATE', json.dumps(result))
            self.assertEqual(before, config.read_bytes())

    def test_health_checks_receipts_and_preserves_unknown_evidence(self):
        prefix = self.root / 'health'
        directory = prefix / 'libexec/aw/providers/sec-core'
        directory.mkdir(parents=True)
        receipt = prefix / '.aw-packages/aw-provider-sec-core.json'
        receipt.parent.mkdir()
        files = {}
        for name in ('aw-provider-sec-core', 'agent-sec-daemon-health'):
            path = directory / name
            path.write_bytes(b'fixture executable')
            path.chmod(0o700)
            files[str(path.relative_to(prefix))] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        receipt.write_text(json.dumps({'files': files}))
        receipt.chmod(0o600)
        for path in prefix.rglob('*'):
            if path.is_dir():
                path.chmod(0o700)
        prefix.chmod(0o700)
        value = {'api_version': 'aw-sec-core-health/v1alpha1', 'helper_installed': True,
                 'socket_configured': True, 'admission': 'unknown', 'check_result': 'unknown',
                 'backend': 'authenticated_reachable', 'code': None}
        with patch.object(aw, 'query', return_value=value) as query:
            self.assertEqual(aw.health(prefix, '/run/test.sock'), 'authenticated_reachable')
            self.assertEqual(query.call_args.kwargs, {'timeout': 4, 'limit': 65536})
            for key, invalid in [('admission', 'accepted'), ('check_result', 'safe'),
                                 ('helper_installed', False), ('code', 'probe_failed')]:
                with self.subTest(key=key), patch.dict(value, {key: invalid}), self.assertRaises(ValueError):
                    aw.health(prefix, '/run/test.sock')
            query.reset_mock()
            (directory / 'agent-sec-daemon-health').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'receipt_mismatch'):
                aw.health(prefix, '/run/test.sock')
            query.assert_not_called()

    def test_health_failure_does_not_discard_tokenless_metrics(self):
        # Health and statistics are independent evidence, never inferred from one another.
        with patch.object(aw, 'trusted_file', side_effect=lambda p: p), patch.object(aw.Path, 'exists', return_value=True), patch.object(aw, 'security_transport', return_value=('security', '/run/sec.sock')), patch.object(aw, 'query', side_effect=[{}, fixture()]), patch.object(aw, 'health', side_effect=ValueError('PRIVATE_ERROR')):
            result = aw.snapshot()
            self.assertEqual(result['security']['backend'], 'query_failed')
            self.assertEqual(result['tokenless']['saved'], 3500)
            self.assertNotIn('PRIVATE_ERROR', json.dumps(result))


if __name__ == '__main__':
    unittest.main()

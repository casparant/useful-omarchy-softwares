"""Live binding truth, frozen policy, lifecycle and read-only discovery boundaries."""
import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('test_workspace_module', ROOT / 'workspace.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.config = self.root / 'policy.json'
        self.document = {'spec': {'events': {
            'tool.before': {'enabled': True, 'steps': [{'id': 'scan', 'on_error': 'block'}]},
            'tool.after': {'enabled': True, 'steps': [{'id': 'compress', 'on_error': 'report'}]},
        }}}
        self.config.write_text(json.dumps(self.document))
        self.config.chmod(0o600)
        directory = self.root / 'aw/launch-1'
        directory.parent.mkdir(mode=0o700)
        directory.mkdir(mode=0o700)
        self.binding = directory / 'binding.json'
        self.identity = {'generation': 'gen1', 'config_revision': 'rev1'}
        self.value = {'adapter': 'qoder', 'socket': str(self.root / 'aw/aw.sock'),
                      'binding': {'target': 'qoder', 'identity': self.identity, 'audit_key': 'PRIVATE_KEY'}}
        self.binding.write_text(json.dumps(self.value))
        self.binding.chmod(0o600)
        self.settings = {'hooks': {}}
        for phase, event, step, action in [('PreToolUse', 'tool.before', 'scan', 'block'),
                                          ('PostToolUse', 'tool.after', 'compress', 'report')]:
            self.settings['hooks'][phase] = [{'hooks': [{'command': str(w.aw.AW),
                'args': ['hook', '--binding', str(self.binding), '--event', event,
                         '--step', step, '--on-error', action]}]}]

    def bound(self):
        with patch.object(w, 'native_settings', return_value=self.settings):
            return w.hooks_bound(1, [], self.config, 'rev1', 'gen1')

    def test_recreated_ai_shell_uses_requested_project_instead_of_helper_cwd(self):
        with patch.object(w, 'setup'), patch.object(w, 'live', return_value={'workspaces': []}), patch.object(w, 'api', return_value={'workspace': {'workspace_id': 'w8'}}) as api:
            w.focus_shell(self.root)
            api.assert_any_call('workspace', 'create', '--cwd', str(self.root),
                                '--label', 'cosh · AI Shell', '--no-focus')
            api.assert_any_call('workspace', 'focus', 'w8')

    def test_native_identity_binds_both_hook_phases_without_exposing_audit_key(self):
        self.assertTrue(self.bound())
        self.assertNotIn('PRIVATE_KEY', str(self.bound()))
        self.settings['hooks']['PostToolUse'] = []
        self.assertFalse(self.bound())

    def test_other_generation_revision_target_or_socket_is_not_bound(self):
        for field, replacement in [('identity', {'generation': 'old', 'config_revision': 'rev1'}),
                                   ('identity', {'generation': 'gen1', 'config_revision': 'other'}),
                                   ('target', 'other')]:
            value = copy.deepcopy(self.value)
            value['binding'][field] = replacement
            self.binding.write_text(json.dumps(value))
            self.assertFalse(self.bound())
        value = copy.deepcopy(self.value)
        value['socket'] = '/run/another/aw.sock'
        self.binding.write_text(json.dumps(value))
        self.assertFalse(self.bound())

    def test_removed_disabled_reordered_or_weakened_native_hook_is_not_bound(self):
        hook = self.settings['hooks']['PreToolUse'][0]['hooks'][0]
        hook['args'][-1] = 'report'
        self.assertFalse(self.bound())
        hook['args'][-1] = 'block'
        self.document['spec']['events']['tool.before']['steps'][0]['enabled'] = False
        self.config.write_text(json.dumps(self.document))
        self.assertFalse(self.bound())

    def test_missing_runtime_identity_stays_unverified(self):
        with patch.object(w, 'native_settings') as settings:
            self.assertFalse(w.hooks_bound(1, [], self.config, None, None))
            settings.assert_not_called()

    def test_session_id_cannot_escape_private_runtime(self):
        for key in ['../secret', '', 'G' * 32, 'a' * 33]:
            with self.assertRaises(ValueError):
                w.session_dir(key)

    def test_private_receipts_are_atomic_and_no_world_read_permission(self):
        directory = self.root / 'receipts'
        w.write_json(directory / 'receipt.json', {'state': 'starting'})
        self.assertEqual((directory.stat().st_mode & 0o777), 0o700)
        self.assertEqual(((directory / 'receipt.json').stat().st_mode & 0o777), 0o600)
        self.assertEqual(len(list(directory.iterdir())), 1)

    def test_launch_intent_is_consumed_once_and_cannot_restore_a_new_agent(self):
        key = 'a' * 32
        intent = {'id': key, 'project': str(Path.cwd()), 'config': str(self.config),
                  'native_args': ['--', '--resume', 'conversation-id']}
        w.write_json(self.root / 'intent.json', intent)
        self.assertEqual(w.consume_intent(self.root, key), intent)
        with self.assertRaises(FileNotFoundError):
            w.consume_intent(self.root, key)

    def test_saved_environment_without_fresh_intent_only_returns_to_cosh(self):
        with patch.dict(os.environ, {'ANOLISA_AW_SESSION': 'a' * 32}), patch.object(w, 'session_dir', return_value=self.root), patch.object(w.os, 'execv', side_effect=SystemExit) as execute, patch.object(w.subprocess, 'Popen') as spawn:
            with self.assertRaises(SystemExit):
                w.run_agent()
            execute.assert_called_once_with(str(ROOT / 'cosh-shell'), [str(ROOT / 'cosh-shell')])
            spawn.assert_not_called()

    def test_symlink_private_directory_is_rejected(self):
        path = self.root / 'link'
        path.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            w.private_dir(path)

    def test_readonly_discovery_without_profile_never_starts_a_process(self):
        with patch.object(w, 'profile', return_value=self.root / 'missing'), patch.object(w.subprocess, 'Popen') as spawn:
            self.assertEqual(w.snapshot()['sessions'], [])
            spawn.assert_not_called()
            self.assertFalse((self.root / 'missing').exists())

    def test_query_failure_clears_previous_bound_sessions(self):
        with patch.object(w, 'live', side_effect=ValueError('offline')):
            value = w.snapshot()
        self.assertEqual(value['state'], 'unavailable')
        self.assertEqual(value['sessions'], [])

    def test_exited_or_reused_pid_never_reads_policy_or_becomes_bound(self):
        record = {'id': 'a' * 32, 'pane': 'w1:p1', 'project': '/project', 'started': 1,
                  'state': 'running', 'supervisor': 123, 'starttime': 'old'}
        for outcome in ['new', FileNotFoundError()]:
            with patch.object(w, 'proc_identity', side_effect=outcome if isinstance(outcome, Exception) else None,
                              return_value=outcome), patch.object(w.aw, 'snapshot') as inspect:
                item = w.project_record(record, self.root, {'panes': [], 'agents': []})
                self.assertEqual(item['state'], 'exited')
                self.assertEqual(item['policy'], 'unverified')
                inspect.assert_not_called()

    def test_changed_frozen_policy_cannot_inherit_previous_green_state(self):
        record = {'id': 'a' * 32, 'pane': 'w1:p1', 'project': '/project', 'started': 1,
                  'state': 'running', 'supervisor': 123, 'starttime': 'old', 'digest': 'different'}
        data = {'panes': [{'pane_id': 'w1:p1', 'agent_status': 'idle'}], 'agents': []}
        with patch.object(w, 'proc_identity', return_value='old'), patch.object(w, 'qoder_process', return_value=(124, [])), patch.object(w.aw, 'snapshot') as inspect:
            self.assertEqual(w.project_record(record, self.root, data)['policy'], 'unverified')
            inspect.assert_not_called()

    def test_session_isolates_explicit_and_auto_endpoints_with_the_state_directory(self):
        for endpoint in ['/previous/aw.sock', 'auto']:
            with self.subTest(endpoint=endpoint):
                document = copy.deepcopy(self.document)
                document['spec']['daemon'] = {'startup': 'on_demand',
                                              'state_dir': '/previous', 'endpoint': endpoint}
                intent = {'config': str(self.config), 'native_args': []}
                with patch.dict(os.environ, {'ANOLISA_AW_SESSION': 'a' * 32,
                                             'HERDR_PANE_ID': 'w1:p1'}), \
                        patch.object(w, 'session_dir', return_value=self.root), \
                        patch.object(w, 'consume_intent', return_value=intent), \
                        patch.object(w, 'proc_identity', return_value='1'), \
                        patch.object(w.aw, 'trusted_file', side_effect=Path), \
                        patch.object(w.aw, 'query', return_value=copy.deepcopy(document)), \
                        patch.object(w.aw, 'security_transport', return_value=(None, None)), \
                        patch.object(w.signal, 'signal'), patch.object(w.subprocess, 'run'), \
                        patch.object(w.subprocess, 'Popen') as spawn:
                    spawn.return_value.pid = 123
                    spawn.return_value.wait.return_value = 0
                    spawn.return_value.poll.return_value = 0
                    w.run_agent()
                    spawn.assert_called_once()
                selected = json.loads(self.config.read_text())
                daemon = selected['spec']['daemon']
                self.assertEqual(daemon['state_dir'], str(self.root / 'aw'))
                self.assertEqual(daemon['endpoint'], str(Path(daemon['state_dir']) / 'aw.sock'))
                document['spec']['daemon'] = daemon
                self.assertEqual(selected, document)

    def test_start_requires_cosh_context_and_never_implicitly_launches_a_server(self):
        with patch.dict(os.environ, {'HERDR_ENV': '0'}), patch.object(w, 'api') as api:
            with self.assertRaises(ValueError):
                w.start()
            api.assert_not_called()

    def test_bash_adapter_exports_to_backend_without_changing_path(self):
        result = subprocess.run(['/bin/bash', '-c',
            "source \"$1\"; /bin/bash -c 'type -t aw; printf \"%s\\n\" \"$ANOLISA_COSH_WORKSPACE\"'",
            'test', str(ROOT / 'cosh-aw.bash')], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.splitlines(), ['function', str(ROOT / 'workspace.py')])

    def test_cosh_aw_run_defaults_and_preserves_explicit_config_and_native_arguments(self):
        with patch.object(w, 'start') as start:
            w.aw_command(['run', '--agent', 'qoder'])
            start.assert_called_once_with(None, [])
        with patch.object(w, 'start') as start:
            args = ['run', '--config', 'policy with spaces.yaml', '--agent', 'qoder',
                    '--native-settings', 'native.json', '--', '--resume', 'same-id', '$(literal)']
            w.aw_command(args)
            start.assert_called_once_with('policy with spaces.yaml',
                ['--native-settings', 'native.json', '--', '--resume', 'same-id', '$(literal)'])

    def test_other_aw_targets_and_commands_keep_native_argv(self):
        for args in [['inspect', '--config', '/tmp/config.json', '--json'],
                     ['run', '--agent', 'openclaw', '--config', '/tmp/config.json']]:
            with patch.object(w.os, 'execv') as execute, patch.object(w, 'start') as start:
                w.aw_command(args)
                execute.assert_called_once_with(str(w.aw.AW), [str(w.aw.AW), *args])
                start.assert_not_called()

    def test_invalid_managed_run_cannot_silently_fall_back_to_unmanaged(self):
        for args in [['run', '--agent', 'qoder', '--config'],
                     ['run', '--agent', 'qoder', '--agent', 'qoder'],
                     ['run', '--agent', 'qoder', '--unknown', 'value']]:
            with patch.object(w.os, 'execv') as execute, patch.object(w, 'start') as start:
                with self.assertRaises(ValueError):
                    w.aw_command(args)
                execute.assert_not_called()
                start.assert_not_called()

    def test_native_aw_child_has_original_arguments_without_cosh_adapter(self):
        intent = {'config': str(self.config), 'native_args': ['--native-settings', 'native.json',
                                                          '--', '--resume', 'same-id']}
        document = {'spec': {'daemon': {'state_dir': '/previous'}}}
        with patch.dict(os.environ, {'ANOLISA_AW_SESSION': 'a' * 32, 'HERDR_PANE_ID': 'w1:p1',
                                    'BASH_FUNC_aw%%': 'adapter', 'ANOLISA_COSH_WORKSPACE': '/adapter'}), \
                patch.object(w, 'session_dir', return_value=self.root), \
                patch.object(w, 'consume_intent', return_value=intent), \
                patch.object(w, 'proc_identity', return_value='1'), \
                patch.object(w.aw, 'trusted_file', side_effect=Path), \
                patch.object(w.aw, 'query', return_value=document), \
                patch.object(w.aw, 'security_transport', return_value=(None, None)), \
                patch.object(w.signal, 'signal'), patch.object(w.subprocess, 'run'), patch.object(w.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 123
            spawn.return_value.wait.return_value = 0
            spawn.return_value.poll.return_value = 0
            w.run_agent()
            argv = spawn.call_args.args[0]
            self.assertEqual(argv, [str(w.aw.AW), 'run', '--config', str(self.root / 'policy.json'),
                                    '--agent', 'qoder', *intent['native_args']])
            environment = spawn.call_args.kwargs['env']
            self.assertNotIn('BASH_FUNC_aw%%', environment)
            self.assertNotIn('ANOLISA_COSH_WORKSPACE', environment)

    def test_expired_return_does_not_start_a_replacement_qoder(self):
        with patch.object(w, 'snapshot', return_value={'sessions': []}), patch.object(w.os, 'execve') as execute:
            with self.assertRaises(ValueError):
                w.attach('a' * 32)
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()

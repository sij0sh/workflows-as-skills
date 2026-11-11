"""Mechanical contracts and representative workflow trials; no model-quality claims."""
import contextlib
from copy import deepcopy
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts/skillflow.py'
spec = importlib.util.spec_from_file_location('skillflow', SCRIPT)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


def candidate(mode='none', phases=('format',)):
    c = deepcopy(flow.CANDIDATE)
    c['frame'].update(name='test-skill', description='Format a local example on explicit request.')
    c['workflow']['phases'] = [{**flow.PHASE, 'id': p} for p in phases]
    c['workflow']['engine']['mode'] = mode
    return c


def review(c):
    r = deepcopy(flow.PASS)
    r['subtract'] = [{**flow.CHECK, 'choice': choice} for choice in flow.choices(c)]
    return r


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.s = flow.new(self.root, 'Create a small explicitly invoked formatting skill.')
        flow.save(self.root, self.s)

    def cli(self, *args, data=None, ok=True):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--root', str(self.root), *args],
                                input=json.dumps(data) if data is not None else '',
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stdout + result.stderr)
        return result

    def stored(self):
        return flow.decode((self.root / flow.STATE).read_bytes())

    def stage(self, c=None):
        c = c or candidate()
        path = self.root / self.s['stage']
        path.mkdir(parents=True, exist_ok=True)
        (path / 'SKILL.md').write_text(
            f'---\nname: {c["frame"]["name"]}\ndescription: {c["frame"]["description"]}\n'
            'disable-model-invocation: true\n---\n# Formatting\n\nFormat the supplied text.\n')
        if c['workflow']['engine']['mode'] == 'single-file':
            (path / 'scripts').mkdir(exist_ok=True)
            (path / 'scripts/convert.py').write_text('def convert(text):\n    return text.upper()\n')
            (path / 'tests').mkdir(exist_ok=True)
            (path / 'tests/test_convert.py').write_text(
                'import importlib.util\nfrom pathlib import Path\nimport unittest\n'
                'spec = importlib.util.spec_from_file_location("convert", '\
                'Path(__file__).resolve().parents[1] / "scripts/convert.py")\n'
                'module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n'
                'class ConvertTest(unittest.TestCase):\n'
                '    def test_upper(self):\n        self.assertEqual(module.convert("hello"), "HELLO")\n')
        return path

    def advance(self, value, run_tests=False):
        with contextlib.redirect_stdout(io.StringIO()):
            flow.advance(self.root, self.s, value, tests_authorized=run_tests)

    def draft(self, c=None):
        c = c or candidate()
        self.stage(c)
        self.advance(c)
        return c

    def test_show_discloses_references_by_phase(self):
        c = candidate()
        self.stage(c)
        draft = self.cli()
        self.assertIn('boundaries.md', draft.stdout)
        self.assertNotIn('authoring.md', draft.stdout)
        self.cli('done', self.s['ticket'], data=c)
        self.s = self.stored()
        review_out = self.cli()
        self.assertIn('boundaries.md', review_out.stdout)
        self.assertIn('authoring.md', review_out.stdout)
        resolve_out = self.cli('done', self.s['ticket'], data=flow.NEED)
        self.assertNotIn('boundaries.md', resolve_out.stdout)
        self.assertNotIn('authoring.md', resolve_out.stdout)

    def test_bare_resume_without_state_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), '--root', directory], capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_prose_full_cli_and_replay(self):
        c = candidate()
        self.stage(c)
        old = self.s['ticket']
        self.cli('done', old, data=c)
        self.s = self.stored()
        self.assertEqual(self.s['phase'], 'review')
        self.cli('done', old, data=c, ok=False)
        final = self.s['ticket']
        result = self.cli('done', final, data=review(c))
        self.assertIn('COMPLETE:', result.stdout)
        self.s = self.stored()
        self.assertIsNone(self.s['candidate'])
        self.assertTrue((self.root / '.agents/skills/test-skill/SKILL.md').is_file())
        record = self.root / self.s['record']
        self.assertIn('"status": "pass"', record.read_text())
        self.cli('done', final)
        self.cli()
        self.assertEqual(record.read_bytes(), (self.root / self.s['record']).read_bytes())

    def test_nonempty_target_refused_before_review(self):
        c = candidate()
        self.stage(c)
        dest = self.root / '.agents/skills/test-skill'
        dest.mkdir(parents=True)
        (dest / 'foreign').write_text('do not touch')
        self.cli('done', self.s['ticket'], data=c, ok=False)
        self.assertEqual(self.stored()['phase'], 'draft')
        self.assertEqual((dest / 'foreign').read_text(), 'do not touch')

    def test_empty_existing_target_is_supported(self):
        dest = self.root / '.agents/skills/test-skill'
        dest.mkdir(parents=True)
        c = self.draft()
        self.advance(review(c))
        self.assertTrue((dest / 'SKILL.md').is_file())

    def test_single_file_linear_trial_without_loop(self):
        c = candidate('single-file', ('scan', 'convert'))
        c['workflow']['boundaries'] = [{'id': 'B1', 'how': 'Source hash captured before conversion.',
            'where': 'scan hands source/hash to convert; discard exploratory logs.',
            'why': 'Merging permits a changed source to use stale evidence.', 'rewind': 'scan'}]
        path = self.stage(c)
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests'],
                                cwd=path, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        r = review(c)
        r['tests'] = 'observed: python3 -B -m unittest discover -s tests; Ran 1 test; OK'
        # These are schema fixtures, not a claim that this toy has a state guard.
        self.advance(c)
        self.advance(r, run_tests=True)
        self.assertEqual(self.s['phase'], 'complete')
        self.assertIn('"test_run": {', (self.root / self.s['record']).read_text())
        self.assertIn('engine', flow.choices(c))
        self.assertEqual(c['workflow']['loops'], [])

    def test_judgment_loop_and_high_consequence_shapes(self):
        for phases in (('propose', 'attack'), ('inspect', 'approve', 'apply', 'verify')):
            c = candidate('single-file', phases)
            if phases[0] == 'propose':
                c['workflow']['loops'] = [{**flow.LOOP, 'entry': 'attack', 'rewind': 'propose'}]
            flow.candidate(c)
            flow.review(review(c), c)
        self.assertIn('loop:0', flow.choices(candidate_with_loop()))

    def test_extra_or_missing_result_keys_fail(self):
        c = candidate()
        self.stage(c)
        for bad in ({**c, 'next': 'publish'}, {k: v for k, v in c.items() if k != 'workflow'}, []):
            self.cli('done', self.s['ticket'], data=bad, ok=False)
            self.assertEqual(self.stored()['phase'], 'draft')

    def test_phase_names_are_dynamic_and_zero_boundaries_valid(self):
        c = candidate(phases=('extract',))
        flow.candidate(c)
        self.assertFalse(c['workflow']['boundaries'])
        c['workflow']['phases'].append(deepcopy(c['workflow']['phases'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            flow.candidate(c)

    def test_loop_references_and_budgets(self):
        c = candidate_with_loop()
        flow.candidate(c)
        for value in (0, True, 21, '3'):
            c['workflow']['loops'][0]['budget'] = value
            with self.assertRaises(ValueError):
                flow.candidate(c)
        c = candidate_with_loop()
        c['workflow']['loops'][0]['rewind'] = 'made-up'
        with self.assertRaises(ValueError):
            flow.candidate(c)

    def test_decision_basis_labeled_and_revisit_required(self):
        c = candidate()
        c['workflow']['decisions'] = [{**flow.DECISION, 'basis': 'assumed: stable intent'}]
        flow.candidate(c)
        for bad in ('certain', 'assumed:', ''):
            c['workflow']['decisions'][0]['basis'] = bad
            with self.assertRaises(ValueError):
                flow.candidate(c)
        c['workflow']['decisions'][0].update(basis='assumed: stable', revisit='')
        with self.assertRaises(ValueError):
            flow.candidate(c)

    def test_missing_subtraction_or_lens_rejected(self):
        c = self.draft(candidate(phases=('extract', 'format')))
        for kind in ('subtract', 'coverage_checks'):
            r = review(c)
            if kind == 'subtract':
                r[kind].pop()
            else:
                r[kind].pop(flow.LENSES[0])
            self.cli('done', self.s['ticket'], data=r, ok=False)
            self.assertEqual(self.stored()['phase'], 'review')

    def test_unknown_review_status_and_fake_independence_rejected(self):
        c = self.draft()
        for r in ({**review(c), 'status': 'publish'}, {**review(c), 'basis': 'independent proof'}):
            self.cli('done', self.s['ticket'], data=r, ok=False)

    def test_engine_requires_test_evidence(self):
        c = candidate('single-file')
        for key in ('tests', 'negative_control'):
            r = review(c)
            r[key] = 'n/a: skipped'
            with self.assertRaises(ValueError):
                flow.review(r, c)

    def test_mutation_before_pass_forces_fresh_review_and_ticket(self):
        c = self.draft()
        old_ticket = self.s['ticket']
        skill = self.root / self.s['stage'] / 'SKILL.md'
        skill.write_text(skill.read_text() + '\nUse a second example.\n')
        self.advance(review(c))
        self.assertEqual(self.s['phase'], 'review')
        self.assertNotEqual(self.s['ticket'], old_ticket)
        self.assertIsNone(self.s['review'])
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())
        self.advance(review(c))
        self.assertEqual(self.s['phase'], 'complete')

    def test_revise_rotates_stage_retains_old_and_counts_only_revise(self):
        c = self.draft()
        old = self.root / self.s['stage']
        for turn in range(3):
            self.advance({'status': 'revise', 'gaps': [{**flow.GAP, 'rewind': 'format'}]})
            self.assertEqual(self.s['attempts'], turn + 1)
            if turn < 2:
                self.assertEqual(self.s['phase'], 'draft')
                self.assertTrue(old.exists())
                self.draft(c)
        self.assertEqual(self.s['phase'], 'incomplete')
        self.assertIn('INCOMPLETE', (self.root / self.s['record']).read_text())
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())
        self.cli('done', self.s['ticket'])

    def test_invalid_rewind_does_not_change_state(self):
        self.draft()
        self.cli('done', self.s['ticket'], data={'status': 'revise', 'gaps': [flow.GAP]}, ok=False)
        self.assertEqual(self.stored()['attempts'], 0)

    def test_resolve_blocked_and_rebuild_without_budget_cost(self):
        self.draft()
        self.advance(flow.NEED)
        self.assertEqual(self.s['phase'], 'resolve')
        self.advance({'status': 'blocked', 'question': 'Which scope?', 'needs': 'user answer'})
        self.assertEqual(self.s['phase'], 'blocked')
        self.advance({'status': 'resolved', 'answer': 'Local files only.', 'basis': 'documented: user answer'})
        self.assertEqual(self.s['phase'], 'draft')
        self.assertEqual(self.s['attempts'], 0)
        self.assertIsNone(self.s['candidate'])
        self.assertTrue(self.s['resolutions'])

    def test_publication_crash_after_rename_resumes(self):
        c = self.draft()
        with patch.object(flow, 'finish', side_effect=OSError('simulated crash')):
            with self.assertRaises(OSError):
                self.advance(review(c))
        self.s = self.stored()
        self.assertEqual(self.s['phase'], 'publishing')
        self.assertTrue(Path(self.s['target']).is_dir())
        self.cli()
        self.assertEqual(self.stored()['phase'], 'complete')

    def test_publication_crash_after_record_resumes(self):
        c = self.draft()
        original_save = flow.save
        def crash(root, s):
            if s['phase'] == 'complete':
                raise OSError('crash after record')
            original_save(root, s)
        with patch.object(flow, 'save', side_effect=crash):
            with self.assertRaises(OSError):
                self.advance(review(c))
        self.s = self.stored()
        record = self.root / f'.agents/artifacts/skill-design-{self.s["ticket"]}.md'
        before = record.read_bytes()
        self.cli()
        self.assertEqual(before, record.read_bytes())

    def test_target_or_record_mismatch_during_recovery_refused(self):
        c = self.draft()
        with patch.object(flow, 'finish', side_effect=OSError('crash')):
            with self.assertRaises(OSError):
                self.advance(review(c))
        self.s = self.stored()
        dest = Path(self.s['target']) / 'SKILL.md'
        original = dest.read_text()
        dest.write_text('foreign content')
        self.cli(ok=False)
        self.assertEqual(dest.read_text(), 'foreign content')
        dest.write_text(original)
        record = self.root / f'.agents/artifacts/skill-design-{self.s["ticket"]}.md'
        record.write_text('foreign record')
        self.cli(ok=False)
        self.assertEqual(record.read_text(), 'foreign record')

    def test_snapshot_change_cannot_publish(self):
        c = self.draft()
        original_copy = flow.shutil.copytree
        def mutate(source, dest, **kwargs):
            file = source / 'SKILL.md'
            file.write_text(file.read_text() + '\nChanged during copy.\n')
            return original_copy(source, dest, **kwargs)
        with patch.object(flow.shutil, 'copytree', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                self.advance(review(c))
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())
        self.cli()
        self.assertEqual(self.stored()['phase'], 'review')

    def test_completed_record_tampering_detected(self):
        c = self.draft()
        self.advance(review(c))
        (self.root / self.s['record']).write_text('tampered')
        self.cli(ok=False)

    def test_corrupt_legacy_and_inconsistent_state_fail_closed(self):
        original = self.stored()
        for bad in ('{', '[]', json.dumps({**original, 'version': 0}),
                    json.dumps({**original, 'version': True}),
                    json.dumps({**original, 'phase': 'review'}),
                    json.dumps({**original, 'phase': 'complete'}),
                    json.dumps({**original, 'unknown': 1})):
            (self.root / flow.STATE).write_text(bad)
            self.cli(ok=False)
            self.assertEqual((self.root / flow.STATE).read_text(), bad)

    def test_duplicate_json_nan_and_bounded_ingress(self):
        for raw in ('{"status":"candidate","status":"pass"}', '{"v":NaN}'):
            with self.assertRaises(ValueError):
                flow.decode(raw)
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
                                 'done', self.s['ticket']], input=' ' * (flow.LIMIT + 1),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('64 KiB', result.stderr)

    def test_different_active_request_refused_and_finished_allows_new(self):
        self.cli('--request', 'Other request', ok=False)
        self.cli('--request', self.s['request'])
        c = self.draft()
        self.advance(review(c))
        self.cli('--request', 'Other request')
        self.assertEqual(self.stored()['request'], 'Other request')
        self.assertEqual(self.stored()['phase'], 'draft')

    def test_project_local_target_and_reserved_paths(self):
        for selected in ('/tmp/outside-skill', str(self.root), str(self.root / '.agents/artifacts/new'),
                         str(self.root / '.agents/skills')):
            s = flow.new(self.root, 'Create skill', selected)
            with self.assertRaises(ValueError):
                flow.validate(self.root, s)
        self.s['target'] = str(self.root / 'skills/custom')
        flow.save(self.root, self.s)
        c = self.draft()
        self.advance(review(c))
        self.assertTrue((self.root / 'skills/custom/SKILL.md').is_file())

    def test_symlink_state_stage_and_target_refused(self):
        path = self.root / flow.STATE
        content = path.read_text()
        path.unlink()
        source = self.root / 'state-copy'
        source.write_text(content)
        path.symlink_to(source)
        self.cli(ok=False)
        path.unlink()
        path.write_text(content)
        stage = self.stage()
        (stage / 'link').symlink_to(source)
        with self.assertRaises(ValueError):
            flow.tree(stage)
        (stage / 'link').unlink()
        (self.root / 'skills').symlink_to(self.root / '.agents')
        self.s['target'] = str(self.root / 'skills/foreign')
        with self.assertRaises(ValueError):
            flow.validate(self.root, self.s)

    def test_word_frontmatter_placeholder_and_engine_limits(self):
        c = candidate()
        path = self.stage(c)
        file = path / 'SKILL.md'
        original = file.read_text()
        variants = [original + ' word' * 101,
                    original.replace('disable-model-invocation: true', 'disable-model-invocation: false'),
                    original.replace('name: test-skill', 'name: test-skill\nname: test-skill'),
                    original + '\nTODO\n']
        for content in variants:
            file.write_text(content)
            with self.assertRaises(ValueError):
                flow.skill_tree(path, c)
        file.write_text(original)
        (path / 'references').mkdir()
        reference = path / 'references/policy.md'
        reference.write_text('word ' * 351)
        with self.assertRaises(ValueError):
            flow.skill_tree(path, c)
        reference.write_text('Use the local convention.')
        flow.skill_tree(path, c)
        (path / 'scripts').mkdir()
        (path / 'scripts/extra.py').write_text('pass\n')
        with self.assertRaises(ValueError):
            flow.skill_tree(path, c)

    def test_no_dependency_or_python_syntax_errors(self):
        c = candidate('single-file')
        path = self.stage(c)
        file = path / 'scripts/convert.py'
        for source in ('import requests\n', 'def broken(:\n'):
            file.write_text(source)
            with self.assertRaises((ValueError, SyntaxError)):
                flow.skill_tree(path, c)

    def test_generated_code_not_executed_by_validation(self):
        c = candidate('single-file')
        path = self.stage(c)
        (path / 'scripts/convert.py').write_text('raise RuntimeError("must not execute")\n')
        self.advance(c)
        self.assertEqual(self.s['phase'], 'review')
        self.cli('done', self.s['ticket'], data=review(c), ok=False)
        self.assertEqual(self.stored()['phase'], 'review')

    def test_rewind_retains_candidate_and_orders_earliest_gap(self):
        c = self.draft(candidate(phases=('inspect', 'convert', 'verify')))
        old_stage = self.s['stage']
        self.advance({'status': 'revise', 'gaps': [
            {**flow.GAP, 'rewind': 'verify'}, {**flow.GAP, 'rewind': 'inspect'}]})
        self.assertEqual(self.s['previous'], {'candidate': c, 'stage': old_stage})
        self.assertEqual(self.s['feedback'][0]['rewind'], 'inspect')
        self.cli()  # Saved context must remain resumable.
        c2 = self.draft(c)
        self.advance(review(c2))
        self.assertIsNone(self.s['previous'])
        self.assertIn(old_stage, (self.root / self.s['record']).read_text())

    def test_record_conflict_prevents_any_target_copy(self):
        c = self.draft()
        path = self.root / f'.agents/artifacts/skill-design-{self.s["ticket"]}.md'
        path.write_text('foreign record')
        self.cli('done', self.s['ticket'], data=review(c), ok=False)
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())
        self.assertEqual(path.read_text(), 'foreign record')
        self.assertEqual(self.stored()['phase'], 'publishing')

    def test_foreign_temporary_sibling_is_not_deleted(self):
        c = self.draft()
        sibling = self.root / f'.agents/skills/.test-skill.skillflow-{self.s["ticket"]}'
        sibling.mkdir(parents=True)
        (sibling / 'foreign').write_text('preserve')
        self.advance(review(c))
        self.assertEqual((sibling / 'foreign').read_text(), 'preserve')

    def test_large_state_is_not_written_unreadably(self):
        original = (self.root / flow.STATE).read_bytes()
        self.s['resolutions'] = [dict(type='fact', question='q' * 4000,
            answer='a' * 4000, basis='b' * 4000) for _ in range(32)]
        with self.assertRaisesRegex(ValueError, '256 KiB'):
            flow.save(self.root, self.s)
        self.assertEqual((self.root / flow.STATE).read_bytes(), original)

    def test_subtraction_contract_covers_more_than_sixteen_phases(self):
        c = candidate(phases=tuple(f'task{i}' for i in range(20)))
        flow.candidate(c)
        flow.review(review(c), c)
        self.assertEqual(len(flow.choices(c)), 39)

    def test_ambiguous_yaml_and_quoted_boolean_are_rejected(self):
        c = candidate()
        path = self.stage(c)
        file = path / 'SKILL.md'
        original = file.read_text()
        for bad in ('"true"', "'true'"):
            file.write_text(original.replace('disable-model-invocation: true',
                                             'disable-model-invocation: ' + bad))
            with self.assertRaises(ValueError):
                flow.skill_tree(path, c)
        c['frame']['description'] = 'Format text: do not execute effects. # quoted'
        file.write_text(original.replace('description: Format a local example on explicit request.',
                                         'description: ' + c['frame']['description']))
        with self.assertRaises(ValueError):
            flow.skill_tree(path, c)
        file.write_text(original.replace('description: Format a local example on explicit request.',
                                         'description: ' + json.dumps(c['frame']['description'])))
        flow.skill_tree(path, c)

    def test_assets_cannot_hide_python_engine(self):
        c = candidate()
        path = self.stage(c)
        (path / 'assets').mkdir()
        (path / 'assets/run.py').write_text('pass\n')
        with self.assertRaises(ValueError):
            flow.skill_tree(path, c)

    def test_resolution_after_topology_revision_has_no_stale_rewind(self):
        self.draft(candidate(phases=('inspect', 'convert')))
        self.advance({'status': 'revise', 'gaps': [{**flow.GAP, 'rewind': 'inspect'}]})
        self.draft(candidate(phases=('answer',)))
        self.advance(flow.NEED)
        self.assertEqual(self.s['phase'], 'resolve')
        self.assertEqual(self.s['previous']['candidate']['workflow']['phases'][0]['id'], 'answer')
        self.cli()

    def test_single_file_pass_runs_exact_snapshot_tests_with_explicit_opt_in(self):
        c = self.draft(candidate('single-file'))
        self.cli('done', self.s['ticket'], data=review(c), ok=False)
        result = self.cli('--run-tests', 'done', self.s['ticket'], data=review(c))
        self.assertIn('COMPLETE:', result.stdout)
        s = self.stored()
        report = (self.root / s['record']).read_text()
        self.assertIn('"test_run": {', report)
        self.assertIn('Ran 1 test', report)

    def test_failing_or_empty_tests_never_publish(self):
        c = candidate('single-file')
        path = self.stage(c)
        (path / 'tests/test_convert.py').write_text(
            'import unittest\nclass Failure(unittest.TestCase):\n'
            '    def test_bad(self):\n        self.fail("deliberate")\n')
        self.advance(c)
        self.cli('--run-tests', 'done', self.s['ticket'], data=review(c), ok=False)
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())
        # No automatic edit/reset: changed source must return to review first.
        (path / 'tests/test_convert.py').write_text('import unittest\n')
        self.cli()
        self.s = self.stored()
        self.assertEqual(self.s['phase'], 'review')
        self.cli('--run-tests', 'done', self.s['ticket'], data=review(c), ok=False)
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())

    def test_manually_copied_tree_cannot_bypass_failed_tests(self):
        import shutil
        c = self.draft(candidate('single-file'))
        with patch.object(flow, 'run_tests', side_effect=ValueError('failed tests')):
            with self.assertRaises(ValueError):
                self.advance(review(c), run_tests=True)
        self.s = self.stored()
        shutil.copytree(self.root / self.s['stage'], Path(self.s['target']))
        result = self.cli(ok=False)
        self.assertIn('without verified tests', result.stderr)
        self.assertEqual(self.stored()['phase'], 'publishing')

    def test_single_file_crash_after_record_keeps_verified_test_result(self):
        c = self.draft(candidate('single-file'))
        original_save = flow.save
        def crash(root, s):
            if s['phase'] == 'complete':
                raise OSError('crash after record')
            original_save(root, s)
        with patch.object(flow, 'save', side_effect=crash):
            with self.assertRaises(OSError):
                self.advance(review(c), run_tests=True)
        self.s = self.stored()
        self.assertIsNotNone(self.s['test_run'])
        with patch.object(flow, 'run_tests', side_effect=AssertionError('must not rerun')):
            with contextlib.redirect_stdout(io.StringIO()):
                flow.publish(self.root, self.s)
        self.assertEqual(self.s['phase'], 'complete')

    def test_test_mutations_do_not_get_published(self):
        c = candidate('single-file')
        path = self.stage(c)
        (path / 'tests/test_convert.py').write_text(
            'from pathlib import Path\nimport unittest\nclass Mutate(unittest.TestCase):\n'
            '    def test_mutate(self):\n'
            '        path = Path(__file__).resolve().parents[1] / "SKILL.md"\n'
            '        path.write_text(path.read_text() + " changed")\n')
        self.advance(c)
        self.cli('--run-tests', 'done', self.s['ticket'], data=review(c), ok=False)
        self.assertFalse((self.root / '.agents/skills/test-skill').exists())

    def test_lock_timeout_is_bounded(self):
        lock = self.root / '.agents/skillflow.lock'
        with lock.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.cli(ok=False)
            self.assertIn('5 seconds', result.stderr)

    def test_atomic_state_failure_preserves_old(self):
        before = (self.root / flow.STATE).read_bytes()
        with patch.object(flow.os, 'replace', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                flow.atomic(self.root / flow.STATE, 'broken')
        self.assertEqual((self.root / flow.STATE).read_bytes(), before)
        self.assertFalse(list((self.root / '.agents').glob('.skillflow.json*')))


class SurfaceTest(unittest.TestCase):
    def test_instruction_budgets(self):
        body = (REPO / 'SKILL.md').read_text().split('---\n', 2)[2]
        self.assertLessEqual(len(body.split()), 60)
        self.assertEqual(len(re.findall(r'[.!?](?=\s+[A-Z]|$)', body)), 2)
        self.assertIn('printed staging directory', body)
        for path in (REPO / 'references').glob('*.md'):
            self.assertLessEqual(len(path.read_text().split()), 220, str(path))
        contracts = {'draft': [flow.CANDIDATE, flow.NEED, {'boundary': flow.BOUNDARY,
                      'loop': flow.LOOP, 'decision': flow.DECISION}],
                     'review': [flow.PASS, {'status': 'revise', 'gaps': [flow.GAP]}, flow.NEED],
                     'resolve': [{'status': 'resolved', 'answer': 'text', 'basis': 'text'},
                                 {'status': 'blocked', 'question': 'text', 'needs': 'text'}]}
        for name, prompt in flow.PROMPTS.items():
            words = len(prompt.split()) + sum(len(json.dumps(x).split()) for x in contracts[name])
            self.assertLessEqual(words, 400, name)
        self.assertLessEqual(len((REPO / 'references/engine-template.py').read_text().splitlines()), 120)
        self.assertIn('disable-model-invocation: true', (REPO / 'SKILL.md').read_text())

    def test_reference_content_covers_design(self):
        boundaries = (REPO / 'references/boundaries.md').read_text()
        for choice in ('One-pass prose', 'Linear phases', 'Persistent engine',
                       'Judgment loop', 'Conditional resolution', 'Approval/effect gate'):
            self.assertIn(choice, boundaries)
        for lens in flow.LENSES:
            self.assertIn(lens, boundaries)
        for condition in ('closure check', 'handoff', 'failure witness', 'earliest rewind',
                          'exit', 'invalidation', 'budget', 'exhaustion'):
            self.assertIn(condition, boundaries)
        authoring = (REPO / 'references/authoring.md').read_text()
        for kind in ('Semantic', 'Evaluative', 'Mechanical'):
            self.assertIn(kind, authoring)
        self.assertIn('not a generic runner', authoring)

    def test_prompt_reference_disclosure_and_ownership(self):
        draft = flow.PROMPTS['draft']
        self.assertIn('boundaries.md', draft)
        self.assertIn('intent/authority', draft)
        self.assertIn('Python reference template', draft)
        for excluded in ('authoring.md', 'Read both references', 'Start one-pass',
                         'five lenses', 'engine none', 'generic runner'):
            self.assertNotIn(excluded, draft)
        review_prompt = flow.PROMPTS['review']
        self.assertIn('boundaries.md', review_prompt)
        self.assertIn('authoring.md', review_prompt)
        self.assertIn('defeat or coverage_checks', review_prompt)
        resolve_prompt = flow.PROMPTS['resolve']
        self.assertNotIn('boundaries.md', resolve_prompt)
        self.assertNotIn('authoring.md', resolve_prompt)

    def test_packaged_skill_passes_its_own_file_contract(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in ('SKILL.md', 'VERSION'):
                shutil.copy2(REPO / name, path / name)
            for name in ('scripts', 'references', 'tests'):
                shutil.copytree(REPO / name, path / name, ignore=shutil.ignore_patterns('__pycache__'))
            c = candidate('single-file')
            c['frame'].update(name='workflows-as-skills', description=(
                'Create and publish an explicitly invoked agent skill from a request. '
                'Synthesize the smallest viable task-specific workflow, with optional phases, persistence, and challenge loops.'))
            flow.skill_tree(path, c)

    def test_template_verifies_count_and_refuses_stale_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input.txt').write_text('one two three')
            script = REPO / 'references/engine-template.py'
            def cli(*args, data=''):
                return subprocess.run([sys.executable, str(script), '--root', directory, *args],
                                      input=data, text=True, capture_output=True)
            self.assertEqual(cli('--source', 'input.txt').returncode, 0)
            s = json.loads((root / '.agents/exampleflow.json').read_text())
            self.assertEqual(cli('--done', s['ticket'], data='{"words":2}').returncode, 1)
            self.assertEqual(cli('--done', 'wrong', data='{"words":3}').returncode, 1)
            (root / 'input.txt').write_text('different source')
            self.assertEqual(cli('--done', s['ticket'], data='{"words":2}').returncode, 1)
            (root / 'input.txt').write_text('one two three')
            self.assertEqual(cli('--done', s['ticket'], data='{"words":3}').returncode, 0)
            self.assertEqual(cli().returncode, 0)

    def test_negative_control_review_coverage_guard(self):
        import inspect
        c = candidate(phases=('inspect', 'convert'))
        incomplete = review(c)
        incomplete['subtract'].pop()
        def invariant(validator):
            with self.assertRaises(ValueError):
                validator(incomplete, c)
        invariant(flow.review)
        source = inspect.getsource(flow.review)
        guard = "require(set(found) == set(choices(c)), 'review must attempt every printed subtraction choice')"
        self.assertIn(guard, source)
        namespace = dict(vars(flow))
        exec(source.replace(guard, 'pass  # removed review coverage guard'), namespace)
        with self.assertRaises(AssertionError):
            invariant(namespace['review'])

    def test_negative_control_ticket_guard(self):
        # This invariant test fails when the stale-ticket guard is removed.
        import inspect
        source = inspect.getsource(flow.main)
        guard = "require(args.ticket == s['ticket'], 'stale or duplicate ticket')"
        self.assertIn(guard, source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s = flow.new(root, 'Create a local skill')
            flow.save(root, s)
            namespace = dict(vars(flow))
            exec(source.replace(guard, 'pass  # negative control'), namespace)
            stream = io.TextIOWrapper(io.BytesIO(json.dumps(flow.NEED).encode()))
            with patch.object(sys, 'stdin', stream), contextlib.redirect_stdout(io.StringIO()):
                code = namespace['main'](['--root', directory, 'done', 'stale-ticket'])
            self.assertEqual(code, 0)
            self.assertEqual(flow.decode((root / flow.STATE).read_bytes())['phase'], 'resolve')
            # Positive control: ordinary stale submission must be rejected.
            result = subprocess.run([sys.executable, str(SCRIPT), '--root', directory,
                                     'done', 'stale-ticket'], input=json.dumps(flow.NEED),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)


def candidate_with_loop():
    c = candidate(phases=('propose', 'attack'))
    c['workflow']['loops'] = [{**flow.LOOP, 'entry': 'attack', 'rewind': 'propose'}]
    return c


if __name__ == '__main__':
    unittest.main()

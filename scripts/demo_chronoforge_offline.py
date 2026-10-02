"""Real ChronoForge execution with scripted maintenance; no LLM or benchmark claim."""
import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from lr_agent.chronoforge import ChronoForge
from lr_agent.config import Settings
from lr_agent.models import ChatResponse


BASE = "def timeout(config):\n    return config.get('timeout_s', 15)\n"
COMPAT = "def timeout(config):\n    return config.get('request_timeout', config.get('timeout_s', 15))\n"
BREAK = "def timeout(config):\n    return config.get('request_timeout', 15)\n"
CHECKS = "from app import timeout\n\ndef test_default():\n    assert timeout({}) == 15\n\ndef test_legacy_config():\n    assert timeout({'timeout_s': 7}) == 7\n"


async def main(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lr-chrono-demo-') as temporary:
        root = Path(temporary)
        settings = Settings(workspace=root/'workspace', database=root/'memory.db',
            knowledge_database=root/'knowledge.db', genome_database=root/'genome.db',
            universe_root=root/'universes', chronoforge_root=root/'chronoforge',
            chronoforge_database=root/'chronoforge.db', enable_planning=False,
            enable_review=False)
        settings.ensure_dirs()
        (settings.workspace/'app.py').write_text(BASE)
        (settings.workspace/'test_app.py').write_text(CHECKS)
        (settings.workspace/'pyproject.toml').write_text('[tool.pytest.ini_options]\naddopts="-q"\n')
        baseline = subprocess.run([sys.executable, '-m', 'pytest'], cwd=settings.workspace,
            capture_output=True, text=True)
        print('BASELINE: actual pytest exit', baseline.returncode, flush=True)
        print(baseline.stdout, flush=True)
        if baseline.returncode:
            raise RuntimeError('Baseline failed; do not publish a success claim.')

        async def scripted_maintainer(child, prompt):
            app = child.workspace/'app.py'
            previous = app.read_text()
            app.write_text(COMPAT if previous == BASE else BREAK)
            print('MAINTENANCE:', 'add compatible key' if previous == BASE else 'remove legacy fallback', flush=True)
            return ChatResponse(session_id='offline-script', run_id='scripted-maintenance',
                status='completed', answer='Scripted file change; no LLM inference.', steps=[])

        engine = ChronoForge(settings, agent_runner=scripted_maintainer)

        async def scenarios(**kwargs):
            return [dict(category='config_contract', name='scripted configuration transition',
                instruction='Apply the declared offline configuration transition.',
                weight=1.0, source='scripted-offline-fixture')]

        engine._generate_scenarios = scenarios
        report = await engine.run(task='Preserve timeout_s compatibility', generations=2, trajectories=1)
        steps = report['trajectory_results'][0]['generations']
        evidence = []
        for step in steps:
            workspace = Path(step['workspace'])
            evidence.append(dict(generation=step['generation'], survived=step['survived'],
                app= (workspace/'app.py').read_text(), tests=(workspace/'test_app.py').read_text(),
                verification=step['seed_verification']))
            print('GENERATION', step['generation'], 'survived=', step['survived'], flush=True)
            print(json.dumps(step['seed_verification'], ensure_ascii=False, indent=2), flush=True)
        expected = [True, False]
        if [s['survived'] for s in steps] != expected:
            raise RuntimeError('Unexpected result; inspect evidence before publishing.')
        if any(e['tests'] != CHECKS for e in evidence):
            raise RuntimeError('Original tests changed.')
        bundle = dict(mode='scripted-offline-real-engine', llm_used=False,
            python=platform.python_version(), baseline_exit=baseline.returncode,
            baseline_stdout=baseline.stdout, original_tests_sha256=hashlib.sha256(CHECKS.encode()).hexdigest(),
            survival_curve=report['survival_curve'], generations=evidence,
            limits='Scripted fixture verifies orchestration and real test replay, not model intelligence or predictive accuracy.')
        # Paths in the raw report refer to temporary workspaces; preserve code and outputs separately.
        (output/'evidence.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2)+'\n')
        (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print('SURVIVAL CURVE:', json.dumps(report['survival_curve']), flush=True)
        print('EVIDENCE:', output/'evidence.json', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/chronoforge-offline'))
    asyncio.run(main(parser.parse_args().output))

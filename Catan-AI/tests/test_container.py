"""Setup failures must be actionable and preserve existing environments."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def fixture_repo(tmp_path):
    (tmp_path / '.devcontainer').mkdir()
    (tmp_path / 'Catan-AI').mkdir()
    shutil.copyfile(ROOT / '.devcontainer/setup.sh', tmp_path / '.devcontainer/setup.sh')
    return tmp_path / '.devcontainer/setup.sh'


def interpreter(tmp_path, body):
    executable = tmp_path / 'python-test'
    executable.write_text('#!/usr/bin/env bash\n' + body)
    executable.chmod(0o755)
    return str(executable)


def run_setup(script, executable):
    return subprocess.run(['bash', str(script)], env={**os.environ, 'CATAN_PYTHON': executable},
                          capture_output=True, text=True)


def test_unsupported_python_does_not_create_environment(tmp_path):
    script = fixture_repo(tmp_path)
    result = run_setup(script, interpreter(tmp_path, 'exit 1\n'))
    assert result.returncode != 0
    assert 'CATAN_PYTHON' in result.stderr
    assert not (tmp_path / 'Catan-AI/.venv-container').exists()


def test_broken_environment_is_preserved(tmp_path):
    script = fixture_repo(tmp_path)
    env = tmp_path / 'Catan-AI/.venv-container'
    env.mkdir()
    sentinel = env / 'keep-me'
    sentinel.write_text('existing data')
    result = run_setup(script, interpreter(tmp_path, "printf '(3, 12)\\n'\n"))
    assert result.returncode != 0
    assert 'Move' in result.stderr
    assert sentinel.read_text() == 'existing data'


def test_failed_install_never_reports_ready(tmp_path):
    script = fixture_repo(tmp_path)
    env = tmp_path / 'Catan-AI/.venv-container/bin'
    env.mkdir(parents=True)
    executable = interpreter(tmp_path, "if [[ $1 == -c ]]; then printf '(3, 12)\\n'; else exit 42; fi\n")
    shutil.copyfile(executable, env / 'python')
    (env / 'python').chmod(0o755)
    result = run_setup(script, executable)
    assert result.returncode == 42
    assert 'ready' not in result.stdout

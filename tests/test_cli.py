import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMD = [sys.executable, "-m", "resolver"]


def run_cli(payload, tmp_path: Path):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        CMD + [str(request_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )


def test_cli_outputs_json_selection(tmp_path):
    payload = {
        "packages": {"a": {"1": {}, "2": {}}},
        "root": {"a": [1, 2]},
        "installed": {},
    }
    result = run_cli(payload, tmp_path)
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"a": 2}


def test_cli_outputs_unresolvable_sentinel(tmp_path):
    payload = {
        "packages": {"a": {"1": {"dependencies": {"a": [2, 2]}}, "2": {}}},
        "root": {"a": [1, 1]},
        "installed": {},
    }
    result = run_cli(payload, tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == "UNRESOLVABLE"
    assert result.stderr == ""


def test_cli_rejects_bad_json_with_nonzero_exit(tmp_path):
    request_path = tmp_path / "bad.json"
    request_path.write_text("{not json", encoding="utf-8")
    result = subprocess.run(
        CMD + [str(request_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: ")


def test_cli_rejects_contract_violation_with_exit_code_two(tmp_path):
    # A reversed interval is a contract error, not an unresolvable request:
    # the error goes to stderr and the process exits 2 with no plan on stdout.
    payload = {
        "packages": {"a": {"1": {}}},
        "root": {"a": [2, 1]},
        "installed": {},
    }
    result = run_cli(payload, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: ")


def test_cli_rejects_root_outside_catalog_without_crashing(tmp_path):
    # Previously a lone out-of-catalog root escaped validation and made the
    # solver raise a raw KeyError; the CLI must report it cleanly instead.
    payload = {
        "packages": {"a": {"1": {}}},
        "root": {"missing": [1, 1]},
        "installed": {},
    }
    result = run_cli(payload, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr

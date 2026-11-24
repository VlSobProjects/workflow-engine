import json
import os
import subprocess
import venv
from pathlib import Path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _cli_launcher(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "workflow-engine.exe"
    return venv_dir / "bin" / "workflow-engine"


def test_installed_cli_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    # The smoke environment is created first and builds the wheel with its own pip: the project
    # environment that runs pytest is made by uv, which does not install pip into it.
    smoke_venv = tmp_path / "smoke-venv"
    venv.EnvBuilder(with_pip=True).create(smoke_venv)

    python_exe = _venv_python(smoke_venv)
    launcher = _cli_launcher(smoke_venv)
    assert python_exe.exists()

    subprocess.run(
        [str(python_exe), "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo_root)],
        cwd=repo_root,
        check=True,
    )

    wheels = sorted(wheelhouse.glob("workflow_engine-*.whl"))
    assert wheels, "Expected a built workflow_engine wheel"
    wheel_path = wheels[-1]

    subprocess.run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            str(wheel_path),
        ],
        cwd=tmp_path,
        check=True,
    )
    assert launcher.exists()

    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps(
            {
                "work_dir": tmp_path.as_posix(),
                "external_modules": [],
                "storage": {},
            },
            indent=2,
        )
    )

    result = subprocess.run(
        [
            str(launcher),
            "help-components",
            "--config",
            str(config_path),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["command"] == "help-components"
    assert response["command_status"] == "completed"
    assert isinstance(response["data"]["components"], dict)

    # The report viewer ships as package data: a wheel without it writes no report. See ADR 022 §4.
    viewer = subprocess.run(
        [
            str(python_exe),
            "-c",
            "from importlib.resources import files; viewer = files('workflow_engine.report') / 'viewer'; "
            "print(all((viewer / name).is_file() for name in ('shell.html', 'report.css', 'report.js')))",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert viewer.stdout.strip() == "True"

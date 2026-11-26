"""The documented opt-in should work without duplicating a real secret."""
import io
import json
import os
import shutil
import subprocess

import pytest
from dotenv import dotenv_values


ENV_EXAMPLE = (
    "OPENAI_API_KEY=synthetic-chat-key\n"
    "OPENAI_EMBEDDING_API_KEY=${OPENAI_API_KEY}\n"
)


def test_python_dotenv_expands_explicit_shared_key():
    values = dotenv_values(stream=io.StringIO(ENV_EXAMPLE))
    assert values["OPENAI_EMBEDDING_API_KEY"] == values["OPENAI_API_KEY"] == "synthetic-chat-key"


def test_compose_expands_explicit_shared_key_without_running_services(tmp_path):
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker Compose CLI not installed")
    # Neither the project's .env nor any inherited application credentials enter this render.
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "ProgramFiles",
                                      "ProgramData", "COMSPEC", "PATHEXT") if k in os.environ}
    env["DOCKER_CONFIG"] = str(tmp_path)
    args = {"cwd": tmp_path, "env": env, "capture_output": True, "text": True, "timeout": 30}
    if subprocess.run([docker, "compose", "version"], **args).returncode:
        pytest.skip("Docker Compose plugin not installed")
    dotenv = tmp_path / "synthetic.env"
    dotenv.write_text(ENV_EXAMPLE, encoding="utf-8")
    compose = "services:\n  sync:\n    image: offline-test\n    environment:\n      OPENAI_EMBEDDING_API_KEY: ${OPENAI_EMBEDDING_API_KEY}\n"
    run = subprocess.run([docker, "compose", "-p", "interpolation-test", "--env-file", str(dotenv),
                          "-f", "-", "config", "--format", "json"], input=compose, check=True, **args)
    assert json.loads(run.stdout)["services"]["sync"]["environment"] == {
        "OPENAI_EMBEDDING_API_KEY": "synthetic-chat-key",
    }

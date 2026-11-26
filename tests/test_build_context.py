"""Opt-in BuildKit check using a synthetic context, not the real vault or .env."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(os.getenv("TEST_DOCKER_BUILD_CONTEXT") != "1", reason="Requires local Docker BuildKit")
def test_build_context_only_includes_runtime_inputs(tmp_path):
    context, exported = tmp_path / "context", tmp_path / "export"
    context.mkdir()
    shutil.copyfile(Path(__file__).resolve().parents[1] / ".dockerignore", context / ".dockerignore")
    allowed = {
        "app.py", "sync_documents.py", "requirements.txt", "search/document_index.py",
        "rag/model_config.py", "embed/embedder.py", "scripts/smoke_luna.py",
        "frontend/src/App.tsx", "frontend/src/components/ChatInput.tsx",
        "frontend/src/types/index.ts", "frontend/src/index.css", "frontend/public/favicon.svg",
        "frontend/package-lock.json", "frontend/index.html",
    }
    denied = {
        ".env", ".env.production", "private/notes.md", "backup.rdb", "docs/private.md",
        "data/vault/note.md", "tests/test_example_local.py", "scripts/one_off.py",
        "frontend/node_modules/pkg/index.js", "frontend/public/private.md", "frontend/.env.local",
        "frontend/src/components/.env.local", "rag/personal.txt", "embed/credentials.pem",
    }
    for name in allowed | denied:
        p = context / name
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text("fixture", encoding="utf-8")
    # Scratch and local export need no base image, credentials, or application services.
    subprocess.run(["docker", "build", "--network=none", "-f", "-", "--output",
                    f"type=local,dest={exported}", "."], input="FROM scratch\nCOPY . /\n",
                   cwd=context, text=True, capture_output=True, check=True, timeout=90)
    assert {p.relative_to(exported).as_posix() for p in exported.rglob("*") if p.is_file()} == allowed

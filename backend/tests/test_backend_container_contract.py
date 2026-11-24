from pathlib import Path


def test_backend_image_has_runtime_dependencies_and_excludes_secrets_from_context():
    backend = Path(__file__).resolve().parents[1]
    dockerfile = (backend / "Dockerfile").read_text()
    dockerignore = (backend / ".dockerignore").read_text()

    assert "COPY requirements.txt" in dockerfile
    assert "tesseract-ocr" in dockerfile
    assert 'USER aairo' in dockerfile
    assert '"app.main:app"' in dockerfile
    assert ".env" in dockerignore
    assert "venv/" in dockerignore

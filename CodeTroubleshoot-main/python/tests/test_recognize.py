import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.preprocessing.image_ops import resize_image
from app.utils.files import read_result, write_result


def png_bytes(width=80, height=40):
    image = Image.new("RGB", (width, height), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes():
    image = Image.new("RGB", (80, 40), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_homepage():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Process" in response.text
    assert "Copy text" in response.text
    assert "Download text" in response.text


def test_recognize_png(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    received = {}

    def recognize(image, lang="eng", config=""):
        received["shape"] = image.shape
        return "Hello"

    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        recognize,
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["text"], str)
    assert isinstance(body["processing_ms"], (int, float))
    assert body["filename"] == "note.png"
    assert received["shape"] == (40, 80)
    assert client.get(f"/api/results/{body['id']}/download").text == "Hello"
    assert client.get(f"/api/results/{body['id']}/processed.png").status_code == 200


def test_read_result_preserves_saved_text(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    write_result("a" * 32, "Recognized text")

    assert read_result("a" * 32) == "Recognized text"
    assert read_result("a" * 32) == "Recognized text"


def test_resize_image_preserves_aspect_ratio_and_does_not_enlarge():
    wide_image = np.zeros((300, 1200, 3), dtype=np.uint8)
    small_image = np.zeros((40, 80, 3), dtype=np.uint8)

    resized = resize_image(wide_image)
    unchanged = resize_image(small_image)

    assert resized.shape == (200, 800, 3)
    assert unchanged.shape == small_image.shape


def test_recognize_jpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        lambda image, lang="eng", config="": "Hello",
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("scan.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["text"], str)


def test_missing_file():
    client = TestClient(app)
    response = client.post("/api/recognize")
    assert response.status_code == 422


def test_rejects_pdf():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400


def test_rejects_png_with_wrong_content():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400


def test_rejects_oversized_image():
    client = TestClient(app)
    payload = png_bytes() + b"0" * (5 * 1024 * 1024)
    response = client.post(
        "/api/recognize",
        files={"file": ("large.png", payload, "image/png")},
    )
    assert response.status_code == 400


def test_rejects_path_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("../../secret.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 400

from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from backend import config, database, pipeline
from backend.main import app
from backend.schemas import Detection


class FakeDetector:
    def detect(self, _image):
        return [Detection(label="bottle", confidence=0.9, bbox=(1, 1, 20, 20)),
                Detection(label="cup", confidence=0.9, bbox=(22, 1, 40, 20)),
                Detection(label="book", confidence=0.9, bbox=(1, 22, 20, 40)),
                Detection(label="cell phone", confidence=0.9, bbox=(22, 22, 40, 40))]


def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (60, 60), "white").save(stream, "PNG")
    return stream.getvalue()


def test_full_api_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setattr(config, "ANNOTATED_DIR", tmp_path / "annotated")
    monkeypatch.setattr(pipeline, "get_detector", lambda *_args: FakeDetector())
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/checklists").json()[0]["id"] == "demo_kit"
        response = client.post("/inspect", data={"checklist_id": "demo_kit"},
                               files={"file": ("test.png", png_bytes(), "image/png")})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "Pass"
        assert client.get(payload["annotated_image_url"]).status_code == 200
        assert client.get("/summary").json() == {"inspected": 1, "passed": 1, "needs_review": 0}
        assert "test.png" in client.get("/inspections/export.csv").text
        assert client.get(f"/inspections/{payload['id']}").status_code == 200
        assert client.post("/inspect", data={"checklist_id": "unknown"},
                           files={"file": ("test.png", png_bytes(), "image/png")}).status_code == 404
        assert client.post("/inspect", data={"checklist_id": "demo_kit"},
                           files={"file": ("bad.png", b"not an image", "image/png")}).status_code == 400


def test_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setattr(config, "ANNOTATED_DIR", tmp_path / "annotated")
    monkeypatch.setattr(pipeline, "get_detector", lambda *_args: FakeDetector())
    with TestClient(app) as client:
        response = client.post("/inspect/batch", data={"checklist_id": "demo_kit"},
            files=[("files", ("one.png", png_bytes(), "image/png")),
                   ("files", ("two.png", png_bytes(), "image/png"))])
        assert response.status_code == 200, response.text
        assert len(response.json()) == 2


def test_missing_checklist_model_reports_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PACKING_MODEL_WEIGHTS", str(tmp_path / "missing.pt"))
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["models_by_checklist"]["packing_sample_878"] == (
            "unavailable (checkpoint not installed)"
        )
        response = client.post(
            "/inspect", data={"checklist_id": "packing_sample_878"},
            files={"file": ("test.png", png_bytes(), "image/png")},
        )
        assert response.status_code == 503
        assert "checkpoint is unavailable" in response.json()["detail"]

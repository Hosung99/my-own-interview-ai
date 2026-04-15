import json
import os
import shutil
import uuid
from datetime import datetime

TEMPLATES_DIR = "./data/templates"
METADATA_PATH = "./data/templates/metadata.json"


def _ensure_dir():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)


def _load_metadata() -> dict:
    _ensure_dir()
    if not os.path.exists(METADATA_PATH):
        return {"templates": []}
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"templates": []}


def _save_metadata(data: dict):
    _ensure_dir()
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_template(src_path: str, name: str) -> dict:
    """파일을 템플릿으로 저장하고 메타데이터를 반환한다."""
    _ensure_dir()
    template_id = str(uuid.uuid4())
    original_name = os.path.basename(src_path)
    stored_filename = f"{template_id}_{original_name}"
    dest_path = os.path.join(TEMPLATES_DIR, stored_filename)

    shutil.copy2(src_path, dest_path)

    entry = {
        "id": template_id,
        "name": name.strip() or original_name,
        "filename": stored_filename,
        "original_name": original_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    metadata = _load_metadata()
    metadata["templates"].append(entry)
    _save_metadata(metadata)
    return entry


def list_templates() -> list[dict]:
    """저장된 템플릿 목록을 반환한다."""
    return _load_metadata().get("templates", [])


def get_template_path(template_id: str) -> str | None:
    """템플릿 파일 경로를 반환한다. 존재하지 않으면 None."""
    for t in list_templates():
        if t["id"] == template_id:
            path = os.path.join(TEMPLATES_DIR, t["filename"])
            return path if os.path.exists(path) else None
    return None


def delete_template(template_id: str):
    """템플릿 파일과 메타데이터 항목을 삭제한다."""
    metadata = _load_metadata()
    target = next((t for t in metadata["templates"] if t["id"] == template_id), None)
    if target:
        path = os.path.join(TEMPLATES_DIR, target["filename"])
        if os.path.exists(path):
            os.remove(path)
        metadata["templates"] = [t for t in metadata["templates"] if t["id"] != template_id]
        _save_metadata(metadata)

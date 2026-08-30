import json
from pathlib import Path
from typing import Any

import joblib


def save_model(model: Any, model_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)


def load_model(model_path: Path) -> Any:
    if not model_path.exists():
        raise FileNotFoundError(
            f"모델 파일이 없습니다: {model_path}. 먼저 scripts/train_model.py를 실행하세요."
        )
    return joblib.load(model_path)


def save_metadata(metadata: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

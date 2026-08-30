from pathlib import Path

from src.ml.features import make_supervised_dataset
from src.ml.model_store import save_metadata, save_model
from src.ml.train import build_model_metadata, train_final_model, walk_forward_validate
from src.tools.demo_data import make_demo_market_data
from src.tools.indicators import add_indicators
import src.tools.ml_predictor as predictor


def test_lightgbm_train_save_load_predict(tmp_path: Path, monkeypatch):
    raw = make_demo_market_data(days=1050, seed=21)
    featured = add_indicators(raw)
    dataset = make_supervised_dataset(featured)
    wf = walk_forward_validate(dataset)
    model = train_final_model(dataset)
    metadata = build_model_metadata(dataset, wf)

    model_path = tmp_path / "btc_lgbm.joblib"
    metadata_path = tmp_path / "btc_lgbm_metadata.json"
    save_model(model, model_path)
    save_metadata(metadata, metadata_path)

    monkeypatch.setattr(predictor, "MODEL_PATH", model_path)
    monkeypatch.setattr(predictor, "MODEL_METADATA_PATH", metadata_path)

    result = predictor.predict_latest(featured)
    assert result["available"] is True
    assert 0.0 <= result["up_probability"] <= 100.0
    assert result["metadata"]["sample_count"] > 300

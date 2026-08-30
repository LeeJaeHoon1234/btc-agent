import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import HISTORY_YEARS, MARKET, MODEL_METADATA_PATH, MODEL_PATH
from src.ml.features import make_supervised_dataset
from src.ml.model_store import save_metadata, save_model
from src.ml.train import build_model_metadata, train_final_model, walk_forward_validate
from src.tools.indicators import add_indicators
from src.tools.market_data import get_daily_candles_history


def main():
    print("[1/5] BTC 데이터 수집")
    df = get_daily_candles_history(market=MARKET, years=HISTORY_YEARS)

    print("[2/5] 지표 계산")
    df = add_indicators(df)

    print("[3/5] ML Dataset 생성")
    dataset = make_supervised_dataset(df)

    print("[4/5] Walk-Forward 검증")
    wf = walk_forward_validate(dataset)
    if wf.empty:
        print("검증 가능한 연도가 없습니다.")
    else:
        print(wf.round(4).to_string(index=False))
        print("평균 AUC:", round(float(wf["auc"].mean()), 4))

    print("[5/5] 최종 모델 학습 및 저장")
    model = train_final_model(dataset)
    metadata = build_model_metadata(dataset, wf)

    save_model(model, MODEL_PATH)
    save_metadata(metadata, MODEL_METADATA_PATH)

    print("모델:", MODEL_PATH)
    print("메타데이터:", MODEL_METADATA_PATH)


if __name__ == "__main__":
    main()

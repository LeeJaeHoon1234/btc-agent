import time

import pandas as pd
import requests


BASE_URL = "https://api.upbit.com/v1"


def _normalize_daily_candles(data: list[dict]) -> pd.DataFrame:
    if not data:
        raise ValueError("Upbit에서 캔들 데이터를 받지 못했습니다.")

    df = pd.DataFrame(data)
    df = df[
        [
            "candle_date_time_kst",
            "opening_price",
            "high_price",
            "low_price",
            "trade_price",
            "candle_acc_trade_volume",
        ]
    ]

    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df["date"] = pd.to_datetime(df["date"])

    return (
        df.sort_values("date")
        .drop_duplicates("date")
        .reset_index(drop=True)
    )


def get_daily_candles(market: str = "KRW-BTC", count: int = 200) -> pd.DataFrame:
    url = f"{BASE_URL}/candles/days"
    params = {"market": market, "count": min(count, 200)}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return _normalize_daily_candles(response.json())


def get_daily_candles_history(
    market: str = "KRW-BTC",
    years: int = 8,
) -> pd.DataFrame:
    url = f"{BASE_URL}/candles/days"
    target_count = years * 365

    all_data: list[dict] = []
    to = None

    while len(all_data) < target_count:
        remaining = target_count - len(all_data)
        count = min(200, remaining)

        params = {"market": market, "count": count}
        if to is not None:
            params["to"] = to

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        all_data.extend(data)
        to = data[-1]["candle_date_time_utc"]
        time.sleep(0.15)

    return _normalize_daily_candles(all_data)

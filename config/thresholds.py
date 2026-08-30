# 한 곳에서 Rule threshold를 관리한다.
# 이후 백테스트/실험으로 이 값만 교체할 수 있게 만드는 것이 목적이다.

ENTRY_STRONG = 70
ENTRY_WEAK = 55

EXIT_WARNING = 60
EXIT_STRONG = 75
EXIT_CRITICAL = 88

GATE_FAST_CONFIDENCE = 0.74
GATE_MIN_MODEL_AUC = 0.52

RSI_OVERSOLD = 35
RSI_WEAK = 45
RSI_OVERBOUGHT = 70
RSI_EXTREME = 80

# Decision boundary 근처는 confidence가 높아도 심층 분석으로 보낸다.
ENTRY_DEEP_MARGIN = 5
EXIT_DEEP_MARGIN = 5

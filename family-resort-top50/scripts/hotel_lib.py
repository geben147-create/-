"""hotels.json과 settings.json을 읽고 물놀이 점수를 계산하는 공용 함수."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load():
    hotels = json.loads((DATA / "hotels.json").read_text(encoding="utf-8"))
    settings = json.loads((DATA / "settings.json").read_text(encoding="utf-8"))
    return hotels, settings


def water_score(h, weights):
    """구글시트 G열 수식과 같은 계산 (자체 평가, 100점 만점)."""
    f = h["facilities"]
    yes = lambda k: f[k] == "있음"
    s = 0
    s += weights["waterpark_slide"] if yes("waterpark_slide") else 0
    s += weights["kids_water"] if yes("kids_water") else 0
    s += weights["indoor_heated_pool"] if (yes("indoor_pool") or yes("heated_pool")) else 0
    s += weights["kids_club_play"] if yes("kids_club_play") else 0
    s += weights["near_attractions"] if yes("near_attractions") else 0
    s += h["season_fit_oct_nov"] * weights["season_fit"]
    s += h["info_reliability"] * weights["info_reliability"]
    return math.floor(s + 0.5)  # 구글시트 ROUND와 같은 반올림

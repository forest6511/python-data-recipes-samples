"""Recipe 06: 日本の労働時間は世界何位か.

OECD「平均年間実労働時間 (Average annual hours actually worked per worker)」
から各国の年間労働時間を取得し、最新年の国際ランキングにおける日本の順位と、
日本の長期推移 (1970-2024) を分析する。

データ出典: OECD Data Explorer (SDMX REST API)
  DSD_HW@DF_AVG_ANN_HRS_WKD  WORKER_STATUS=_T (Total)
API キー不要。
"""

import io
import os
import sys

import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe06_working_hours.csv")
IMG_RANK = os.path.join(os.path.dirname(__file__), "images",
                        "recipe06_hours_rank.png")
IMG_TREND = os.path.join(os.path.dirname(__file__), "images",
                         "recipe06_japan_trend.png")

URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.ELS.SAE,DSD_HW@DF_AVG_ANN_HRS_WKD,/all"
    "?format=csvfilewithlabels"
)


def load_data():
    """OECD から年間労働時間 (Total) を取得。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    raw = pd.read_csv(io.BytesIO(requests.get(URL, timeout=90).content))
    cols = ["REF_AREA", "Reference area", "TIME_PERIOD", "OBS_VALUE",
            "WORKER_STATUS"]
    df = raw[cols].copy()
    df = df[df["WORKER_STATUS"] == "_T"]  # Total（雇用者+自営を含む全就業者）
    df = df.drop(columns="WORKER_STATUS")
    df.to_csv(CACHE, index=False)
    return df


df = load_data()
df = df.rename(columns={"Reference area": "country", "TIME_PERIOD": "year",
                        "OBS_VALUE": "hours"})

YEAR = 2024

latest = df[(df["year"] == YEAR) & (df["REF_AREA"] != "OECD")].copy()
latest = latest.sort_values("hours", ascending=False).reset_index(drop=True)
oecd_avg = df[(df["year"] == YEAR) & (df["REF_AREA"] == "OECD")]["hours"].iloc[0]

jp_hours = latest.loc[latest["REF_AREA"] == "JPN", "hours"].iloc[0]
jp_rank = latest.index[latest["REF_AREA"] == "JPN"][0] + 1
n_countries = len(latest)

print(f"=== {YEAR}年 年間労働時間ランキング ===")
print(f"対象国数: {n_countries}")
print(f"日本: {jp_hours:.0f} 時間  第{jp_rank}位（多い順）")
print(f"OECD 平均: {oecd_avg:.0f} 時間")
print(f"最長: {latest.iloc[0]['country']} {latest.iloc[0]['hours']:.0f}h")
print(f"最短: {latest.iloc[-1]['country']} {latest.iloc[-1]['hours']:.0f}h")

jp = df[df["REF_AREA"] == "JPN"].sort_values("year")
reg = stats.linregress(jp["year"], jp["hours"])
h1970 = jp[jp["year"] == 1970]["hours"].iloc[0]
h2024 = jp[jp["year"] == 2024]["hours"].iloc[0]
print(f"\n=== 日本の長期推移 ===")
print(f"1970: {h1970:.0f}h  2024: {h2024:.0f}h  減少: {h1970 - h2024:.0f}h")
print(f"回帰の傾き = {reg.slope:.2f} h/年  p値 = {reg.pvalue:.2g}  r = {reg.rvalue:.3f}")

fig, ax = plt.subplots(figsize=(10, 9))
colors = ["black" if c == "JPN" else "lightgray"
          for c in latest["REF_AREA"]]
ax.barh(latest["country"], latest["hours"], color=colors,
        edgecolor="black", linewidth=0.4)
ax.axvline(oecd_avg, color="black", linestyle="--", linewidth=1.5,
           label=f"OECD平均 {oecd_avg:.0f}h")
ax.invert_yaxis()
ax.set_xlabel("年間労働時間（時間）")
ax.set_title(f"OECD加盟国の年間労働時間（{YEAR}年）　黒＝日本")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(IMG_RANK, dpi=200)

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(jp["year"], jp["hours"], color="black", linewidth=1.0,
        marker="o", markersize=3, label="日本の年間労働時間")
ax.plot(jp["year"], reg.intercept + reg.slope * jp["year"],
        color="black", linestyle="--", linewidth=2, label="回帰直線")
ax.set_xlabel("年")
ax.set_ylabel("年間労働時間（時間）")
ax.set_title("日本の1人あたり年間労働時間の推移（1970-2024）")
ax.legend()
fig.tight_layout()
fig.savefig(IMG_TREND, dpi=200)

print(f"\n保存: {os.path.relpath(IMG_RANK)}")
print(f"保存: {os.path.relpath(IMG_TREND)}")

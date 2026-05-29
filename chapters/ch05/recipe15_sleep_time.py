"""Recipe 15: 日本人の睡眠時間は本当に短いか.

OECD「Time use（生活時間の使い方）」から各国の Personal care
（睡眠・食事・身づくろいを含む「身の回りのこと」）の1日あたり時間を取得し、
日本の国際的な位置づけと男女差を分析する。

注意: OECD の現行 SDMX では睡眠単独の系列がなく、睡眠は Personal care に
含まれる。睡眠単独の比較ではない点に注意する。

データ出典: OECD Data Explorer (SDMX REST API)
  OECD.WISE.INE,DSD_TIME_USE@DF_TIME_USE  MEASURE=PCA (Personal care)
  単位: Minutes per day  /  API キー不要。
"""

import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import requests  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe15_time_use.csv")
IMG_RANK = os.path.join(
    os.path.dirname(__file__), "images", "recipe15_personal_care_rank.png"
)
IMG_SEX = os.path.join(
    os.path.dirname(__file__), "images", "recipe15_japan_sex.png"
)

URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.WISE.INE,DSD_TIME_USE@DF_TIME_USE,/all"
    "?format=csvfilewithlabels"
)


def load_data():
    """OECD Time use を取得。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    raw = pd.read_csv(io.BytesIO(requests.get(URL, timeout=120).content))
    cols = ["REF_AREA", "Reference area", "MEASURE", "Measure", "SEX",
            "OBS_VALUE", "Unit of measure"]
    df = raw[cols].copy()
    df.to_csv(CACHE, index=False)
    return df


df = load_data()

# Personal care（睡眠を含む身の回りのこと）の合計時間
pca = df[df["MEASURE"] == "PCA"].copy()

# 国際ランキング（Total）。分→時間に変換
total = pca[pca["SEX"] == "_T"][["Reference area", "OBS_VALUE"]].copy()
total["hours"] = total["OBS_VALUE"] / 60
total = total.sort_values("OBS_VALUE", ascending=False).reset_index(drop=True)

n = len(total)
jp_min = total.loc[total["Reference area"] == "Japan", "OBS_VALUE"].iloc[0]
jp_rank = total.index[total["Reference area"] == "Japan"][0] + 1
oecd_mean = total["OBS_VALUE"].mean()
longest = total.iloc[0]
shortest = total.iloc[-1]

print("=== Personal care（睡眠含む身の回りのこと, 分/日, Total）===")
print(f"対象国数: {n}")
print(f"日本: {jp_min:.0f}分/日 = {jp_min / 60:.2f}時間  第{jp_rank}位（多い順）")
print(f"対象国平均: {oecd_mean:.0f}分/日 = {oecd_mean / 60:.2f}時間")
print(f"最長: {longest['Reference area']} {longest['OBS_VALUE']:.0f}分")
print(f"最短: {shortest['Reference area']} {shortest['OBS_VALUE']:.0f}分")

# 日本の男女差
jp_sex = pca[pca["Reference area"] == "Japan"].set_index("SEX")["OBS_VALUE"]
jp_f = jp_sex["F"]
jp_m = jp_sex["M"]
print(f"\n=== 日本の男女別 ===")
print(f"女性: {jp_f:.0f}分  男性: {jp_m:.0f}分  差: {jp_f - jp_m:.0f}分（女性が多い）")

# --- 作図1: 国際ランキング（横棒、日本を強調）---
fig, ax = plt.subplots(figsize=(10, 9))
colors = ["black" if c == "Japan" else "lightgray"
          for c in total["Reference area"]]
ax.barh(total["Reference area"], total["OBS_VALUE"], color=colors,
        edgecolor="black", linewidth=0.4)
ax.axvline(oecd_mean, color="black", linestyle="--", linewidth=1.5,
           label=f"対象国平均 {oecd_mean:.0f}分")
ax.invert_yaxis()
ax.set_xlabel("1日あたりの時間（分）")
ax.set_title("OECD各国の Personal care 時間（睡眠含む身の回りのこと）　黒＝日本")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(IMG_RANK, dpi=200)

# --- 作図2: 日本の男女差 ---
fig, ax = plt.subplots(figsize=(8, 5))
labels = ["女性", "男性"]
values = [jp_f, jp_m]
bars = ax.bar(labels, values, color=["dimgray", "lightgray"],
              edgecolor="black", linewidth=0.8, hatch=["//", ""])
for b, v in zip(bars, values):
    ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}分",
            ha="center", va="bottom")
ax.set_ylabel("Personal care 時間（分/日）")
ax.set_title("日本の Personal care 時間の男女差")
ax.set_ylim(0, max(values) * 1.15)
fig.tight_layout()
fig.savefig(IMG_SEX, dpi=200)

print(f"\n保存: {os.path.relpath(IMG_RANK)}")
print(f"保存: {os.path.relpath(IMG_SEX)}")

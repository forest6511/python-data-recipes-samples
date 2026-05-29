"""Recipe 17: コンビニの数と人口の関係.

都道府県別のコンビニエンスストア店舗数（商業動態統計調査）と総人口を結合し、
店舗数が人口でどこまで説明できるか、人口あたり店舗数（コンビニ密度）が
都道府県でどう違うかを分析する。

データ出典: e-Stat
  0003395254  商業動態統計調査 コンビニエンスストア販売 都道府県別（店舗数 tab=150, 2019年）
  0000010101  社会・人口統計体系 A 人口・世帯（総人口 A1101, 2019年）
API キー必要（ESTAT_APP_ID）。
"""

import os
import sys

import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
APP_ID = os.environ["ESTAT_APP_ID"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe17_convenience.csv")
IMG_SCATTER = os.path.join(
    os.path.dirname(__file__), "images", "recipe17_pop_vs_store.png"
)
IMG_DENSITY = os.path.join(
    os.path.dirname(__file__), "images", "recipe17_density_rank.png"
)

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
YEAR_STORE = "2019000000"  # コンビニ店舗数の最新年
YEAR_POP = "2019100000"    # 社会・人口統計体系の年度コード


def _fetch_stores():
    """商業動態統計から都道府県別コンビニ店舗数と都道府県名を取得。"""
    params = {"appId": APP_ID, "statsDataId": "0003395254", "cdTab": "150",
              "cdTime": YEAR_STORE, "metaGetFlg": "Y"}
    j = requests.get(API, params=params, timeout=120).json()
    sdata = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = sdata["DATA_INF"]["VALUE"]
    names = {}
    for c in sdata["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "area":
            for x in c["CLASS"]:
                names[x["@code"]] = x["@name"]
    rows = []
    for v in vals:
        area = v.get("@area")
        if area == "00000":
            continue
        rows.append({"area": area, "pref": names.get(area, area),
                     "stores": float(v.get("$"))})
    return pd.DataFrame(rows)


def _fetch_pop():
    """社会・人口統計体系から都道府県別総人口を取得。"""
    params = {"appId": APP_ID, "statsDataId": "0000010101", "cdCat01": "A1101",
              "cdTime": YEAR_POP, "metaGetFlg": "N"}
    j = requests.get(API, params=params, timeout=120).json()
    vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    rows = []
    for v in vals:
        area = v.get("@area")
        if area == "00000":
            continue
        try:
            rows.append({"area": area, "pop": float(v.get("$"))})
        except (ValueError, TypeError):
            pass
    return pd.DataFrame(rows)


def load_data():
    """店舗数と人口を結合。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area": str})
    df = _fetch_stores().merge(_fetch_pop(), on="area")
    df.to_csv(CACHE, index=False)
    return df


df = load_data()

# 人口1万人あたり店舗数（コンビニ密度）
df["stores_per_10k"] = df["stores"] / df["pop"] * 10000

n = len(df)
total_stores = df["stores"].sum()
print(f"対象都道府県数: {n}")
print(f"全国合計店舗数（47都道府県分）: {total_stores:.0f}店")

# 店舗数と人口の相関・回帰
reg = stats.linregress(df["pop"], df["stores"])
r, p = stats.pearsonr(df["pop"], df["stores"])
print(f"\n=== 店舗数 vs 人口 ===")
print(f"相関 r={r:.3f}  p={p:.3g}  決定係数 R^2={r ** 2:.3f}")
print(f"回帰: 店舗数 = {reg.slope * 100000:.1f}店 / 人口10万人 + {reg.intercept:.0f}")

# 人口1万人あたり店舗数のランキング
df = df.sort_values("stores_per_10k", ascending=False).reset_index(drop=True)
print(f"\n=== 人口1万人あたり店舗数（コンビニ密度）===")
print(f"全国平均: {df['stores_per_10k'].mean():.2f}店/万人")
print(f"最多: {df.iloc[0]['pref']} {df.iloc[0]['stores_per_10k']:.2f}店/万人")
print(f"最少: {df.iloc[-1]['pref']} {df.iloc[-1]['stores_per_10k']:.2f}店/万人")

# --- 作図1: 人口 vs 店舗数 散布図 ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df["pop"] / 10000, df["stores"], color="black", s=30, marker="o")
xs = [df["pop"].min(), df["pop"].max()]
ax.plot([x / 10000 for x in xs],
        [reg.intercept + reg.slope * x for x in xs],
        color="black", linestyle="--", linewidth=1.5,
        label=f"回帰直線（R²={r ** 2:.2f}）")
# 主要な外れ値（東京）に注記
tokyo = df[df["pref"] == "東京都"]
if len(tokyo):
    t = tokyo.iloc[0]
    ax.annotate("東京都", (t["pop"] / 10000, t["stores"]),
                textcoords="offset points", xytext=(-40, 5))
ax.set_xlabel("総人口（万人）")
ax.set_ylabel("コンビニ店舗数（店）")
ax.set_title("都道府県別 人口とコンビニ店舗数（2019年）")
ax.legend()
fig.tight_layout()
fig.savefig(IMG_SCATTER, dpi=200)

# --- 作図2: 人口1万人あたり店舗数ランキング ---
fig, ax = plt.subplots(figsize=(10, 10))
mean_density = df["stores_per_10k"].mean()
colors = ["black" if c == "東京都" else "lightgray" for c in df["pref"]]
ax.barh(df["pref"], df["stores_per_10k"], color=colors,
        edgecolor="black", linewidth=0.4)
ax.axvline(mean_density, color="black", linestyle="--", linewidth=1.5,
           label=f"全国平均 {mean_density:.2f}店/万人")
ax.invert_yaxis()
ax.set_xlabel("人口1万人あたりコンビニ店舗数（店）")
ax.set_title("都道府県別 コンビニ密度（2019年）　黒＝東京都")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(IMG_DENSITY, dpi=200)

print(f"\n保存: {os.path.relpath(IMG_SCATTER)}")
print(f"保存: {os.path.relpath(IMG_DENSITY)}")

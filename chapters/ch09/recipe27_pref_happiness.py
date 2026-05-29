"""Recipe 27: 都道府県幸福度ランキングを自分で作る.

所得・雇用・健康・住まいなど複数の指標を組み合わせて、自分なりの
合成指標（コンポジット・インデックス）を作る。各指標は単位がバラバラ
なので z スコア（標準化）でそろえてから合成する。さらに、指標の重みを
変えると順位が変わることを確かめ、合成指標が作り手の価値観に左右される
主観的なものであることを体験する。

使う5指標（都道府県別, e-Stat 社会生活統計指標）:
  1. 1人当たり県民所得（高いほど良い）  #C01321
  2. 完全失業率（低いほど良い→符号反転） #F01301
  3. 平均余命（0歳・男）（高いほど良い）  #I0520101
  4. 持ち家住宅の延べ面積・1住宅当たり（高いほど良い） #H0210301
  5. 持ち家比率（高いほど良い）           #H01301

データ出典: e-Stat 社会・人口統計体系（社会生活統計指標, 都道府県）
  0000010203 C 経済基盤 / 0000010206 F 労働 / 0000010209 I 健康・医療
  0000010208 H 居住
API キー必要（ESTAT_APP_ID）。この章のディレクトリの .env に設定する。

caveat:
  - この「幸福度」は主観的に選んだ5指標の合成であり、公式の幸福度ではない。
    指標・重みを変えれば順位は変わる（本レシピの主眼）。
  - 各指標は相関であって因果ではない。
  - 指標ごとに最新で全47都道府県がそろう年を採用するため、観測年は指標間で
    必ずしも一致しない。
"""

import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
APP_ID = os.environ["ESTAT_APP_ID"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe27_pref_indicators.csv")
IMG = os.path.join(IMG_DIR, "recipe27_pref_happiness.png")

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

# (表ID, カテゴリコード, 表示名, 高いほど良い?)
INDICATORS = [
    ("0000010203", "#C01321", "1人当たり県民所得", True),
    ("0000010206", "#F01301", "完全失業率", False),
    ("0000010209", "#I0520101", "平均余命(男)", True),
    ("0000010208", "#H0210301", "持ち家の広さ", True),
    ("0000010208", "#H01301", "持ち家比率", True),
]


def _fetch_latest(stats_id, cat, want_names=False):
    """指標の、全47都道府県がそろう最新年の値を返す dict[area]=value。"""
    p = {"appId": APP_ID, "statsDataId": stats_id, "cdCat01": cat,
         "metaGetFlg": "Y" if want_names else "N", "limit": 4000}
    j = requests.get(API, params=p, timeout=120).json()
    sd = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = sd["DATA_INF"]["VALUE"]
    if isinstance(vals, dict):
        vals = [vals]
    by_time = defaultdict(dict)
    for v in vals:
        area = v.get("@area")
        if not area or area == "00000" or len(area) != 5:
            continue
        if not area.endswith("000"):  # 都道府県(NN000)のみ。市区町村を除外
            continue
        try:
            by_time[v.get("@time")][area] = float(v.get("$"))
        except (ValueError, TypeError):
            pass
    chosen, chosen_year = {}, None
    for t in sorted(by_time, reverse=True):
        if len(by_time[t]) >= 47:
            chosen, chosen_year = by_time[t], t
            break
    if not chosen:
        t = max(by_time, key=lambda k: len(by_time[k]))
        chosen, chosen_year = by_time[t], t
    names = {}
    if want_names:
        for c in sd["CLASS_INF"]["CLASS_OBJ"]:
            if c.get("@id") == "area":
                cl = c.get("CLASS", [])
                if isinstance(cl, dict):
                    cl = [cl]
                for x in cl:
                    names[x.get("@code")] = x.get("@name")
    return chosen, chosen_year, names


def load_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area": str})
    series = {}
    area_names = {}
    years = {}
    for i, (sid, cat, label, _good) in enumerate(INDICATORS):
        vals, year, names = _fetch_latest(sid, cat, want_names=(i == 0))
        series[label] = vals
        years[label] = year
        if names:
            area_names = names
    df = pd.DataFrame(series)
    df.index.name = "area"
    df = df.reset_index()
    df["pref"] = df["area"].map(area_names)
    for label, y in years.items():
        print(f"  {label}: 採用年 {y[:4]}")
    df.to_csv(CACHE, index=False)
    return df


df = load_data()
df = df.dropna().reset_index(drop=True)
print(f"\n=== 全指標がそろった都道府県数: {len(df)} ===")

labels = [x[2] for x in INDICATORS]
good = {x[2]: x[3] for x in INDICATORS}


def zscore(s):
    return (s - s.mean()) / s.std(ddof=0)


z = pd.DataFrame({"pref": df["pref"]})
for lab in labels:
    zz = zscore(df[lab])
    z[lab] = zz if good[lab] else -zz  # 悪い指標は符号反転

z["score_equal"] = z[labels].mean(axis=1)
rank_equal = z.sort_values("score_equal", ascending=False).reset_index(drop=True)
rank_equal["rank"] = rank_equal.index + 1

print("\n=== 等重み合成スコア ランキング 上位10 ===")
for _, r in rank_equal.head(10).iterrows():
    print(f"  {r['rank']:>2}位 {r['pref']:<6} スコア {r['score_equal']:+.3f}")
print("  ...")
print("=== 下位5 ===")
for _, r in rank_equal.tail(5).iterrows():
    print(f"  {r['rank']:>2}位 {r['pref']:<6} スコア {r['score_equal']:+.3f}")

W_INCOME = {"1人当たり県民所得": 3.0, "完全失業率": 1.0, "平均余命(男)": 1.0,
            "持ち家の広さ": 1.0, "持ち家比率": 1.0}
wsum = sum(W_INCOME.values())
z["score_income"] = sum(z[lab] * W_INCOME[lab] for lab in labels) / wsum
rank_income = (z.sort_values("score_income", ascending=False)
               .reset_index(drop=True))
rank_income["rank_income"] = rank_income.index + 1

merged = rank_equal[["pref", "rank"]].merge(
    rank_income[["pref", "rank_income"]], on="pref")
merged["diff"] = merged["rank"] - merged["rank_income"]
merged["abs_diff"] = merged["diff"].abs()

print("\n=== 所得重視に変えたとき順位が大きく動いた県 ===")
movers = merged.sort_values("abs_diff", ascending=False).head(6)
for _, r in movers.iterrows():
    arrow = "↑" if r["diff"] > 0 else "↓"
    print(f"  {r['pref']:<6} 等重み{int(r['rank']):>2}位 → 所得重視"
          f"{int(r['rank_income']):>2}位 ({arrow}{int(r['abs_diff'])})")

top_equal = rank_equal.iloc[0]["pref"]
top_income = rank_income.iloc[0]["pref"]
max_move = int(merged["abs_diff"].max())
print(f"\n等重み1位: {top_equal} / 所得重視1位: {top_income}")
print(f"重みを変えたときの最大順位変動: {max_move}位")

print(f"\n=== {top_equal}（等重み1位）の各指標 z スコア ===")
prof = z[z["pref"] == top_equal].iloc[0]
for lab in labels:
    print(f"  {lab:<14} {prof[lab]:+.2f}")

# --- 作図: 等重みランキングの横棒（z スコア合成）---
os.makedirs(IMG_DIR, exist_ok=True)
plot = rank_equal.iloc[::-1]
colors = ["0.2" if s >= 0 else "0.6" for s in plot["score_equal"]]
fig, ax = plt.subplots(figsize=(10, 9))
ax.barh(plot["pref"], plot["score_equal"], color=colors,
        edgecolor="black", linewidth=0.5)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("合成幸福度スコア（5指標の z スコア平均, 等重み）")
ax.set_title("自作・都道府県幸福度ランキング（所得・雇用・健康・住まいの合成）")
ax.tick_params(axis="y", labelsize=8)
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

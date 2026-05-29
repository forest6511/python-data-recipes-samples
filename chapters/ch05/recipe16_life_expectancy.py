"""Recipe 16: 平均寿命と何が相関するか.

都道府県別の平均寿命（平均余命0歳）を軸に、医師数密度・健康寿命・所得など
の都道府県別指標と横断的な相関を取り、「平均寿命は何と相関するか」を探る。

注意: 相関は因果ではない。医師が多い県ほど長寿でも、医師数が寿命を延ばす
とは限らない（豊かな県ほど医師も多く健康意識も高い、等の交絡）。

データ出典: e-Stat 社会・人口統計体系（都道府県データ）
  0000010109  I 健康・医療（平均余命・健康寿命・医師数）
  0000010101  A 人口・世帯（総人口）
API キー必要（ESTAT_APP_ID）。
"""

import os
import sys
from collections import defaultdict

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
CACHE = os.path.join(DATA_DIR, "recipe16_life_expectancy.csv")
IMG_DOCTOR = os.path.join(
    os.path.dirname(__file__), "images", "recipe16_doctor_vs_life.png"
)
IMG_HEALTHY = os.path.join(
    os.path.dirname(__file__), "images", "recipe16_healthy_gap.png"
)

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
# 平均余命(0歳)男女, 健康寿命男女, 医師数  / 別データセットで総人口
LIFE_CATS = "I1101,I1102,I1601,I1602,I6100"
YEAR_LIFE = "2020100000"   # 都道府県別生命表は2020が最新
YEAR_HEALTHY = "2019100000"  # 健康寿命は2019が最新


def _fetch(stats_id, cats, year, want_meta=False):
    """e-Stat から指定カテゴリ・年の都道府県値を取得して dict[area][cat] に。"""
    params = {"appId": APP_ID, "statsDataId": stats_id, "cdCat01": cats,
              "cdTime": year, "metaGetFlg": "Y" if want_meta else "N"}
    j = requests.get(API, params=params, timeout=120).json()
    sdata = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = sdata["DATA_INF"]["VALUE"]
    if isinstance(vals, dict):
        vals = [vals]
    out = defaultdict(dict)
    for v in vals:
        area = v.get("@area")
        if area == "00000":  # 全国は除外（都道府県の横断分析）
            continue
        try:
            out[area][v.get("@cat01")] = float(v.get("$"))
        except (ValueError, TypeError):
            pass
    if want_meta:
        names = {}
        for c in sdata["CLASS_INF"]["CLASS_OBJ"]:
            if c.get("@id") == "area":
                for x in c.get("CLASS", []):
                    names[x.get("@code")] = x.get("@name")
        return out, names
    return out


def load_data():
    """e-Stat から取得して結合。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area": str})

    life, names = _fetch("0000010109", "I1101,I1102,I6100", YEAR_LIFE,
                         want_meta=True)
    healthy = _fetch("0000010109", "I1601,I1602", YEAR_HEALTHY)
    pop = _fetch("0000010101", "A1101", YEAR_LIFE)

    rows = []
    for area in life:
        r = {"area": area, "pref": names.get(area, area)}
        r["life_m"] = life[area].get("I1101")
        r["life_f"] = life[area].get("I1102")
        r["doctors"] = life[area].get("I6100")
        r["healthy_m"] = healthy.get(area, {}).get("I1601")
        r["healthy_f"] = healthy.get(area, {}).get("I1602")
        r["pop"] = pop.get(area, {}).get("A1101")  # 単位:人
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    return df


df = load_data()
df = df.dropna(subset=["life_f", "life_m", "doctors", "pop"]).copy()

# 人口10万人あたり医師数
df["doctors_per_100k"] = df["doctors"] / df["pop"] * 100000
# 健康寿命と平均寿命の差（不健康な期間, 女性）
df["unhealthy_f"] = df["life_f"] - df["healthy_f"]

n = len(df)
imax, imin = df["life_f"].idxmax(), df["life_f"].idxmin()
print(f"対象都道府県数: {n}")
print(f"平均寿命（女性）最長: {df.loc[imax, 'pref']} "
      f"{df.loc[imax, 'life_f']:.2f}年")
print(f"平均寿命（女性）最短: {df.loc[imin, 'pref']} "
      f"{df.loc[imin, 'life_f']:.2f}年")
print(f"全国レンジ（女性）: {df['life_f'].max() - df['life_f'].min():.2f}年")

# 相関: 平均寿命（女性）と各指標
print("\n=== 平均寿命（女性）との相関 ===")
for col, label in [("life_m", "平均寿命（男性）"),
                   ("doctors_per_100k", "人口10万あたり医師数"),
                   ("healthy_f", "健康寿命（女性）")]:
    sub = df.dropna(subset=[col, "life_f"])
    r, p = stats.pearsonr(sub[col], sub["life_f"])
    print(f"  {label}: r={r:.3f}  p={p:.3g}  (n={len(sub)})")

# 医師数との相関（散布図用に確定）
r_doc, p_doc = stats.pearsonr(df["doctors_per_100k"], df["life_f"])

# 不健康な期間
sub_h = df.dropna(subset=["unhealthy_f"])
hmax, hmin = sub_h["unhealthy_f"].idxmax(), sub_h["unhealthy_f"].idxmin()
print(f"\n=== 不健康な期間（平均寿命 - 健康寿命, 女性）===")
print(f"全国平均: {sub_h['unhealthy_f'].mean():.2f}年")
print(f"最長（不健康期間が長い）: {sub_h.loc[hmax, 'pref']} "
      f"{sub_h.loc[hmax, 'unhealthy_f']:.2f}年")
print(f"最短: {sub_h.loc[hmin, 'pref']} "
      f"{sub_h.loc[hmin, 'unhealthy_f']:.2f}年")

# --- 作図1: 医師数 vs 平均寿命 散布図 ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df["doctors_per_100k"], df["life_f"], color="black", s=30,
           marker="o")
reg = stats.linregress(df["doctors_per_100k"], df["life_f"])
xs = [df["doctors_per_100k"].min(), df["doctors_per_100k"].max()]
ax.plot(xs, [reg.intercept + reg.slope * x for x in xs], color="black",
        linestyle="--", linewidth=1.5,
        label=f"回帰直線（r={r_doc:.2f}）")
ax.set_xlabel("人口10万人あたり医師数（人）")
ax.set_ylabel("平均寿命・女性（年）")
ax.set_title("都道府県別 医師数密度と平均寿命（女性, 2020年）")
ax.legend()
fig.tight_layout()
fig.savefig(IMG_DOCTOR, dpi=200)

# --- 作図2: 不健康な期間（平均寿命 - 健康寿命, 女性）上位/下位 ---
sub_h = sub_h.sort_values("unhealthy_f", ascending=False)
top = pd.concat([sub_h.head(8), sub_h.tail(8)])
fig, ax = plt.subplots(figsize=(10, 7))
colors = ["dimgray"] * 8 + ["lightgray"] * 8
ax.barh(range(len(top)), top["unhealthy_f"], color=colors,
        edgecolor="black", linewidth=0.4)
ax.set_yticks(range(len(top)))
ax.set_yticklabels(top["pref"])
ax.invert_yaxis()
ax.set_xlabel("不健康な期間（平均寿命 - 健康寿命, 年）")
ax.set_title("不健康な期間が長い/短い都道府県（女性）　濃＝長い上位")
fig.tight_layout()
fig.savefig(IMG_HEALTHY, dpi=200)

print(f"\n保存: {os.path.relpath(IMG_DOCTOR)}")
print(f"保存: {os.path.relpath(IMG_HEALTHY)}")

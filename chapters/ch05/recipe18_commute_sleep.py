"""Recipe 18: 通勤時間と睡眠時間の関係.

都道府県別の通勤・通学時間と睡眠時間（社会生活基本調査ベース、有業者）を
結合し、「通勤が長い県ほど睡眠が削られているか」を横断的に分析する。

注意: 相関は因果ではない。通勤が長い県で睡眠が短くても、通勤が睡眠を削る
とは限らない（都市部ほど通勤も長く生活リズムも夜型、等の交絡）。

データ出典: e-Stat 社会・人口統計体系（都道府県データ）M 生活時間
  0000010113  通勤・通学時間 M2101x / 睡眠時間 M1101x（有業者・2021年度）
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
CACHE = os.path.join(DATA_DIR, "recipe18_commute_sleep.csv")
IMG_SCATTER = os.path.join(
    os.path.dirname(__file__), "images", "recipe18_commute_vs_sleep.png"
)
IMG_RANK = os.path.join(
    os.path.dirname(__file__), "images", "recipe18_commute_rank.png"
)

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
YEAR = "2021100000"  # 社会生活基本調査の最新（5年ごと）
# 有業者の通勤・通学時間（男 M210101 / 女 M210201）、睡眠時間（男 M110101 / 女 M110201）
CATS = "M210101,M210201,M110101,M110201"


def load_data():
    """e-Stat から通勤・睡眠時間を取得。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area": str})

    params = {"appId": APP_ID, "statsDataId": "0000010113", "cdCat01": CATS,
              "cdTime": YEAR, "metaGetFlg": "Y"}
    j = requests.get(API, params=params, timeout=120).json()
    sdata = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = sdata["DATA_INF"]["VALUE"]
    names = {}
    for c in sdata["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "area":
            for x in c["CLASS"]:
                names[x["@code"]] = x["@name"]

    bycat = defaultdict(dict)
    for v in vals:
        area = v.get("@area")
        if area == "00000":
            continue
        try:
            bycat[area][v.get("@cat01")] = float(v.get("$"))
        except (ValueError, TypeError):
            pass

    rows = []
    for area, c in bycat.items():
        # 男女の単純平均（有業者の通勤・睡眠時間, 分/日）
        commute = (c.get("M210101", 0) + c.get("M210201", 0)) / 2
        sleep = (c.get("M110101", 0) + c.get("M110201", 0)) / 2
        rows.append({"area": area, "pref": names.get(area, area),
                     "commute": commute, "sleep": sleep})
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    return df


df = load_data()

n = len(df)
print(f"対象都道府県数: {n}")
print(f"通勤・通学時間（有業者・男女平均）最長: "
      f"{df.loc[df['commute'].idxmax(), 'pref']} "
      f"{df['commute'].max():.1f}分")
print(f"通勤・通学時間 最短: "
      f"{df.loc[df['commute'].idxmin(), 'pref']} {df['commute'].min():.1f}分")
print(f"睡眠時間（有業者・男女平均）最長: "
      f"{df.loc[df['sleep'].idxmax(), 'pref']} {df['sleep'].max():.1f}分")
print(f"睡眠時間 最短: "
      f"{df.loc[df['sleep'].idxmin(), 'pref']} {df['sleep'].min():.1f}分")

# 通勤時間と睡眠時間の相関
r, p = stats.pearsonr(df["commute"], df["sleep"])
reg = stats.linregress(df["commute"], df["sleep"])
print(f"\n=== 通勤時間 vs 睡眠時間 ===")
print(f"相関 r={r:.3f}  p={p:.3g}")
print(f"回帰: 通勤が10分長いと睡眠が {reg.slope * 10:.1f}分 変化")

# --- 作図1: 通勤時間 vs 睡眠時間 散布図 ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df["commute"], df["sleep"], color="black", s=30, marker="o")
xs = [df["commute"].min(), df["commute"].max()]
ax.plot(xs, [reg.intercept + reg.slope * x for x in xs], color="black",
        linestyle="--", linewidth=1.5, label=f"回帰直線（r={r:.2f}）")
for label in ["東京都", "神奈川県", "宮崎県"]:
    row = df[df["pref"] == label]
    if len(row):
        rr = row.iloc[0]
        ax.annotate(label, (rr["commute"], rr["sleep"]),
                    textcoords="offset points", xytext=(5, 4))
ax.set_xlabel("通勤・通学の平均時間（有業者・男女平均, 分/日）")
ax.set_ylabel("睡眠の平均時間（有業者・男女平均, 分/日）")
ax.set_title("都道府県別 通勤時間と睡眠時間（2021年）")
ax.legend()
fig.tight_layout()
fig.savefig(IMG_SCATTER, dpi=200)

# --- 作図2: 通勤時間ランキング ---
ds = df.sort_values("commute", ascending=False).reset_index(drop=True)
mean_commute = ds["commute"].mean()
fig, ax = plt.subplots(figsize=(10, 10))
colors = ["black" if c in ("東京都", "神奈川県") else "lightgray"
          for c in ds["pref"]]
ax.barh(ds["pref"], ds["commute"], color=colors,
        edgecolor="black", linewidth=0.4)
ax.axvline(mean_commute, color="black", linestyle="--", linewidth=1.5,
           label=f"全国平均 {mean_commute:.1f}分")
ax.invert_yaxis()
ax.set_xlabel("通勤・通学の平均時間（有業者・男女平均, 分/日）")
ax.set_title("都道府県別 通勤・通学時間（2021年）　黒＝東京・神奈川")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(IMG_RANK, dpi=200)

print(f"\n保存: {os.path.relpath(IMG_SCATTER)}")
print(f"保存: {os.path.relpath(IMG_RANK)}")

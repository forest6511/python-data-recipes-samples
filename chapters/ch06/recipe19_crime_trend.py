"""Recipe 19: 日本の犯罪は本当に減っているか.

刑法犯の認知件数（警察が把握した事件の件数）が長期でどう動いたかを見る。
「治安が悪くなった」という体感に対し、データ上の事実を確認するのが狙い。

データ出典（いずれも警察庁。同じ「刑法犯総数 認知件数（件）」を接続）:
  e-Stat 0003191320  犯罪統計 第1表 刑法犯 罪種別 認知件数（2006-2016, appId 要）
  警察白書 令和6年 統計2-4 刑法犯罪種別認知件数の推移（2019-2023, キー不要 CSV）
両者は同一定義の「刑法犯総数 認知件数」。出典表が違うだけで指標は同じ。
2017-2018 は API/白書のどちらにも年次が無いため欠落（線は分けて描く）。
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
from dotenv import load_dotenv  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
APP_ID = os.environ["ESTAT_APP_ID"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe19_crime.csv")
IMG = os.path.join(
    os.path.dirname(__file__), "images", "recipe19_crime_trend.png"
)

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
HAKUSYO_CSV = "https://www.npa.go.jp/hakusyo/r06/toukei/02/4.csv"


def _fetch_estat():
    """e-Stat から刑法犯総数の認知件数（2006-2016）を取得。"""
    params = {"appId": APP_ID, "statsDataId": "0003191320",
              "cdCat01": "100", "cdCat02": "100", "metaGetFlg": "N"}
    j = requests.get(API, params=params, timeout=120).json()
    vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    rows = []
    for v in vals:
        year = int(v["@time"][:4])
        rows.append({"year": year, "recognized": int(v["$"]),
                     "source": "e-Stat 犯罪統計"})
    return pd.DataFrame(rows)


def _fetch_hakusyo():
    """警察白書 CSV から刑法犯総数認知件数（2019-2023）を取得。"""
    r = requests.get(HAKUSYO_CSV, timeout=120)
    txt = r.content.decode("shift_jis", errors="replace")
    df = pd.read_csv(io.StringIO(txt), header=None)
    # 年次行（令元,2,3,4,5）と刑法犯総数行を探す
    year_row = df[df.apply(
        lambda r: r.astype(str).str.contains("令元").any(), axis=1)].iloc[0]
    total_row = df[df[0].astype(str).str.strip() == "刑法犯総数"].iloc[0]
    years = {"令元": 2019, "2": 2020, "3": 2021, "4": 2022, "5": 2023}
    rows = []
    for i, cell in year_row.items():
        key = str(cell).strip()
        if key in years:
            v = str(total_row[i]).replace(",", "").strip()
            rows.append({"year": years[key], "recognized": int(float(v)),
                         "source": "警察白書"})
    return pd.DataFrame(rows)


def load_data():
    """両出典を結合。2回目以降はキャッシュを読む。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    df = pd.concat([_fetch_estat(), _fetch_hakusyo()], ignore_index=True)
    df = df.sort_values("year").reset_index(drop=True)
    df.to_csv(CACHE, index=False)
    return df


df = load_data()

peak = df.loc[df["recognized"].idxmax()]
trough = df.loc[df["recognized"].idxmin()]
latest = df.loc[df["year"].idxmax()]
earliest = df.loc[df["year"].idxmin()]

print("=== 刑法犯総数 認知件数 ===")
print(df.to_string(index=False))
print(f"\n最大: {int(peak['year'])}年 {int(peak['recognized']):,}件")
print(f"最小: {int(trough['year'])}年 {int(trough['recognized']):,}件")
print(f"ピーク比（最小/最大）: {trough['recognized'] / peak['recognized']:.3f}")
print(f"最古({int(earliest['year'])}): {int(earliest['recognized']):,}件")
print(f"最新({int(latest['year'])}): {int(latest['recognized']):,}件")
print(f"最古→最新 減少率: "
      f"{(1 - latest['recognized'] / earliest['recognized']) * 100:.1f}%")

# 減少局面（e-Stat 2006-2016）の線形回帰トレンド
decline = df[df["source"] == "e-Stat 犯罪統計"]
reg = stats.linregress(decline["year"], decline["recognized"])
print(f"\n=== 2006-2016 減少トレンド（線形回帰）===")
print(f"slope={reg.slope:,.0f}件/年  p={reg.pvalue:.3g}  r={reg.rvalue:.3f}")

# 直近の反転（2021最小 -> 2023）
recent = df[df["source"] == "警察白書"]
r21 = recent[recent["year"] == 2021]["recognized"].iloc[0]
r23 = recent[recent["year"] == 2023]["recognized"].iloc[0]
print(f"\n=== 直近の反転 ===")
print(f"2021年 {r21:,}件 → 2023年 {r23:,}件 "
      f"（+{(r23 / r21 - 1) * 100:.1f}%）")
print(f"ただし2023年も2006年ピークの "
      f"{r23 / peak['recognized'] * 100:.1f}%水準")

# --- 作図: 認知件数の推移（出典別にマーカーを分ける）---
fig, ax = plt.subplots(figsize=(10, 6))
for src, marker, ls in [("e-Stat 犯罪統計", "o", "-"),
                        ("警察白書", "s", "-")]:
    sub = df[df["source"] == src]
    ax.plot(sub["year"], sub["recognized"] / 10000, color="black",
            marker=marker, linestyle=ls, label=src, markersize=6)
ax.set_xlabel("年")
ax.set_ylabel("刑法犯 認知件数（万件）")
ax.set_title("刑法犯認知件数の推移（2006-2016 と 2019-2023）")
ax.axhline(peak["recognized"] / 10000, color="gray", linestyle=":",
           linewidth=1, label=f"2006年ピーク {peak['recognized'] / 10000:.0f}万件")
ax.legend()
ax.grid(axis="y", linestyle=":", alpha=0.5)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

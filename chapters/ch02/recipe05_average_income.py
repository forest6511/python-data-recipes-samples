"""Recipe 05: 平均年収は30年上がっていないか.

国税庁「民間給与実態統計調査」の「1年を通じて勤務した給与所得者の
平均給与（全体・計）」を分析する。e-Stat API で取得できる 2007-2021 年の
15年分を主データとして線形回帰でトレンドを確認し、1990年代後半のピーク
（国税庁公表値）と比較して「平均給与は伸びていない」かを検証する。

データ出典:
  国税庁 民間給与実態統計調査（第8表 業種別 総括表・1年勤続・平均給与）
  政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）
    - 2007年:       statsDataId 0003045917
    - 2008-2011年:  statsDataId 0003045945
    - 2012-2021年:  statsDataId 0003090531
  いずれも同一の集計方法（従来の復元推計）による系列で接続できる。
  1997年のピーク額は国税庁公表値（旧手法）を参考線として用いる。

事前準備: e-Stat (https://www.e-stat.go.jp/) で利用登録し appId を発行、
  このディレクトリに .env を置いて ESTAT_APP_ID=発行されたID と記述する。
"""

import os
import sys

import pandas as pd
import requests
from dotenv import load_dotenv
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe05_average_income.csv")
IMG = os.path.join(os.path.dirname(__file__), "images",
                   "recipe05_income_trend.png")

ESTAT_TABLES = ["0003045917", "0003045945", "0003090531"]
PEAK_YEAR = 1997
PEAK_SALARY_K = 4673  # 467.3万円（国税庁 平成9年分 公表値）


def fetch_estat_total(stats_data_id, app_id):
    """1表から 平均給与(0240)・業種=合計(15)・給与階級=計(15)・性別=計(3)。"""
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": stats_data_id,
        "cdTab": "0240",
        "cdCat01": "15",
        "cdCat02": "15",
        "cdCat03": "3",
        "limit": 100,
    }
    j = requests.get(url, params=params, timeout=60).json()
    v = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    v = [v] if isinstance(v, dict) else v
    return [{"year": int(x["@time"][:4]), "salary_k": int(x["$"])} for x in v]


def build_dataset():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError(
            "環境変数 ESTAT_APP_ID が未設定です。"
            "e-Stat で appId を発行し .env に記述してください。"
        )
    rows = []
    for tid in ESTAT_TABLES:
        rows.extend(fetch_estat_total(tid, app_id))
    df = pd.DataFrame(rows).drop_duplicates("year").sort_values("year")
    df = df.reset_index(drop=True)
    df.to_csv(CACHE, index=False)
    return df


df = build_dataset()
df["salary_man"] = df["salary_k"] / 10

reg = stats.linregress(df["year"], df["salary_man"])
first = df.loc[df["year"].idxmin()]
latest = df.loc[df["year"].idxmax()]
peak_man = PEAK_SALARY_K / 10

print("=== 平均給与の推移（1年勤続・全体）===")
print(f"分析対象（e-Stat 取得）: {int(first['year'])}-{int(latest['year'])}  "
      f"（{len(df)}年分）")
print(f"開始 {int(first['year'])}年: {first['salary_man']:.1f}万円")
print(f"直近 {int(latest['year'])}年: {latest['salary_man']:.1f}万円")
print(f"15年間の変化: {latest['salary_man'] - first['salary_man']:+.1f}万円")
print(f"回帰の傾き = {reg.slope:.2f} 万円/年  "
      f"p値 = {reg.pvalue:.3g}  r = {reg.rvalue:.3f}")
print(f"参考: {PEAK_YEAR}年ピーク（国税庁公表値）= {peak_man:.1f}万円  "
      f"→ 直近との差 {latest['salary_man'] - peak_man:+.1f}万円")

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(df["year"], df["salary_man"], color="black", linewidth=1.2,
        marker="o", markersize=4, label="平均給与（e-Stat 2007-2021）")
ax.plot(df["year"], reg.intercept + reg.slope * df["year"],
        color="black", linestyle="--", linewidth=1.5, label="回帰直線")
ax.axhline(peak_man, color="gray", linestyle=":", linewidth=1.2,
           label=f"{PEAK_YEAR}年ピーク {peak_man:.0f}万円（公表値）")
ax.set_xlabel("年")
ax.set_ylabel("平均給与（万円）")
ax.set_title("日本の平均給与の推移（国税庁 民間給与実態統計調査）")
ax.legend(loc="lower left")
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

"""Recipe 07: IT業界の平均年収は本当に高いか.

国税庁「民間給与実態統計調査」の業種別 平均給与（1年勤続）を使い、
「情報通信業」（IT・通信を含む業種区分）と全業種「合計」の平均給与を
年ごとに比較する。IT業界が本当に他業種より高いのか、その差は何倍かを
データで確かめる。

データ出典:
  国税庁 民間給与実態統計調査
    第8表 業種別 総括表（1年勤続・新たな復元推計手法）
    e-Stat statsDataId: 0004009617（2014-2024年）
  政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）
  「情報通信業」は日本標準産業分類の大分類で、ソフトウェア業・情報処理
  サービス業・通信業・放送業・出版業などを含む。

事前準備: e-Stat (https://www.e-stat.go.jp/) で利用登録し appId を発行、
  このディレクトリに .env を置いて ESTAT_APP_ID=発行されたID と記述する。
"""

import os
import sys

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe07_it_salary.csv")
IMG = os.path.join(os.path.dirname(__file__), "images",
                   "recipe07_it_salary.png")

STATS_DATA_ID = "0004009617"  # 第8表 業種別 総括表（新復元推計, 2014-2024）
INDUSTRIES = {"9": "情報通信業", "15": "全業種平均"}


def fetch_data():
    """e-Stat から 情報通信業 と 合計 の平均給与（千円）を取得。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError(
            "環境変数 ESTAT_APP_ID が未設定です。"
            "e-Stat で appId を発行し .env に記述してください。"
        )
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_DATA_ID,
        "cdTab": "0240",        # 平均給与
        "cdCat01": "9,15",      # 情報通信業, 合計
        "cdCat02": "15",        # 給与階級=計
        "cdCat03": "3",         # 性別=計
        "limit": 200,
    }
    j = requests.get(url, params=params, timeout=60).json()
    vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    rows = [{"year": int(v["@time"][:4]),
             "industry": INDUSTRIES[v["@cat01"]],
             "salary_k": int(v["$"])} for v in vals]
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()
df["salary_man"] = df["salary_k"] / 10

wide = df.pivot(index="year", columns="industry", values="salary_man")
wide = wide.sort_index()
wide["倍率"] = wide["情報通信業"] / wide["全業種平均"]

latest_year = int(wide.index.max())
it_latest = wide.loc[latest_year, "情報通信業"]
all_latest = wide.loc[latest_year, "全業種平均"]
ratio_latest = wide.loc[latest_year, "倍率"]
ratio_mean = wide["倍率"].mean()

print("=== 情報通信業 vs 全業種平均（平均給与・万円）===")
for y in wide.index:
    print(f"{y}: 情報通信業 {wide.loc[y, '情報通信業']:.1f}  "
          f"全業種 {wide.loc[y, '全業種平均']:.1f}  "
          f"倍率 {wide.loc[y, '倍率']:.3f}")
print(f"\n直近 {latest_year}年: 情報通信業 {it_latest:.1f}万円, "
      f"全業種 {all_latest:.1f}万円, 差 {it_latest - all_latest:.1f}万円")
print(f"直近の倍率: {ratio_latest:.3f}  期間平均の倍率: {ratio_mean:.3f}")

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(wide.index, wide["情報通信業"], color="black", linewidth=1.5,
        marker="o", markersize=5, label="情報通信業")
ax.plot(wide.index, wide["全業種平均"], color="black", linewidth=1.5,
        linestyle="--", marker="s", markersize=5, label="全業種平均")
ax.fill_between(wide.index, wide["全業種平均"], wide["情報通信業"],
                color="lightgray", alpha=0.5)
ax.set_xlabel("年")
ax.set_ylabel("平均給与（万円）")
ax.set_title("情報通信業と全業種平均の平均給与（国税庁 民間給与実態統計調査）")
ax.legend(loc="lower right")
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

"""Recipe 09: 都道府県別の物価差はどのくらいか.

総務省「小売物価統計調査（構造編）」の消費者物価地域差指数を使い、
「同じ生活でも住む場所で物価はどれだけ違うのか」を都道府県別に比較する。
全国平均を100としたとき、最も高い県と低い県でどのくらい差があるのか、
費目（食料・住居など）ごとにどの地域が高いのかをデータで確かめる。

データ出典:
  総務省 小売物価統計調査（構造編）地域別価格差
    10大費目別消費者物価地域差指数（全国平均=100, 2013年〜）
  e-Stat statsDataId: 0003441258
  政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）

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
CACHE = os.path.join(DATA_DIR, "recipe09_price_gap.csv")
IMG_BAR = os.path.join(os.path.dirname(__file__), "images",
                       "recipe09_price_ranking.png")
IMG_CAT = os.path.join(os.path.dirname(__file__), "images",
                       "recipe09_price_category.png")

STATS_DATA_ID = "0003441258"
# 47都道府県の地域コード（都道府県は code が NN000）
PREF_CODES = [f"{i:02d}000" for i in range(1, 48)]


def fetch_data():
    """e-Stat から都道府県別の消費者物価地域差指数を取得。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area_code": str})
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_DATA_ID,
        "cdArea": ",".join(PREF_CODES),  # 47都道府県
        "cdTime": "2024000000",          # 最新年
        "limit": 2000,
    }
    j = requests.get(url, params=params, timeout=60).json()
    info = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = info["DATA_INF"]["VALUE"]
    # cat01（10大費目）の code→名 マップを作る
    cat_map = {}
    for c in info["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "cat01":
            for o in c["CLASS"]:
                cat_map[o["@code"]] = o["@name"]
    area_map = {}
    for c in info["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "area":
            objs = c["CLASS"]
            objs = objs if isinstance(objs, list) else [objs]
            for o in objs:
                area_map[o["@code"]] = o["@name"]
    rows = [{"area_code": v["@area"],
             "pref": area_map.get(v["@area"], v["@area"]),
             "category": cat_map.get(v["@cat01"], v["@cat01"]),
             "index": float(v["$"])} for v in vals]
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()

# 総合指数だけ取り出して都道府県をランキング
total = df[df["category"] == "総合"].copy()
total = total.sort_values("index", ascending=False).reset_index(drop=True)

top = total.iloc[0]
bottom = total.iloc[-1]
gap = top["index"] - bottom["index"]

print("=== 消費者物価地域差指数（総合, 全国平均=100, 2024年）===")
print(f"最も高い: {top['pref']} {top['index']:.1f}")
print(f"最も低い: {bottom['pref']} {bottom['index']:.1f}")
print(f"最高と最低の差: {gap:.1f} ポイント")
print("\n--- 上位5県 ---")
for _, r in total.head(5).iterrows():
    print(f"  {r['pref']:<6} {r['index']:.1f}")
print("--- 下位5県 ---")
for _, r in total.tail(5).iterrows():
    print(f"  {r['pref']:<6} {r['index']:.1f}")

tokyo = total[total["pref"] == "東京都"].iloc[0]
print(f"\n東京都: {tokyo['index']:.1f}  順位 "
      f"{total.index[total['pref'] == '東京都'][0] + 1}位 / 47")

# 費目別に「最も高い県と最も低い県の差」を見る
print("\n=== 費目別の地域差（最高-最低のレンジ）===")
cat_range = []
for cat in df["category"].unique():
    sub = df[df["category"] == cat]
    rng = sub["index"].max() - sub["index"].min()
    cat_range.append((cat, rng, sub["index"].max(), sub["index"].min()))
cat_range.sort(key=lambda x: x[1], reverse=True)
for cat, rng, mx, mn in cat_range:
    print(f"  {cat:<10} レンジ {rng:5.1f}  (最高 {mx:.1f} / 最低 {mn:.1f})")

# --- 作図1: 都道府県別 総合指数の横棒（上位・下位を抜粋）---
show = pd.concat([total.head(8), total.tail(8)])
fig, ax = plt.subplots(figsize=(10, 7))
colors = ["dimgray" if v >= 100 else "white" for v in show["index"]]
hatches = ["" if v >= 100 else "//" for v in show["index"]]
bars = ax.barh(show["pref"][::-1], show["index"][::-1],
               color=colors[::-1], edgecolor="black")
for bar, h in zip(bars, hatches[::-1]):
    bar.set_hatch(h)
ax.axvline(100, color="black", linewidth=1.0, linestyle="-")
ax.set_xlim(90, 112)
ax.set_xlabel("消費者物価地域差指数（全国平均=100）")
ax.set_title("都道府県別の物価水準・総合（上位8県と下位8県, 2024年）")
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG_BAR, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_BAR)}")

# --- 作図2: 費目別の地域差レンジ（縦棒, 10大費目のみ）---
# 「総合」と参考系列（家賃を除く総合）は除外し、10大費目だけ並べる
_skip = {"総合", "(参考)家賃を除く総合"}
cats = [c[0] for c in cat_range if c[0] not in _skip]
ranges = [c[1] for c in cat_range if c[0] not in _skip]
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.bar(cats, ranges, color="white", edgecolor="black", hatch="//")
ax2.set_ylabel("最高県と最低県の差（ポイント）")
ax2.set_title("費目ごとの都道府県間の物価差（2024年, 大きいほど地域差が大）")
ax2.grid(axis="y", linestyle="--", alpha=0.4)
plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
fig2.tight_layout()
fig2.savefig(IMG_CAT, dpi=200)
print(f"保存: {os.path.relpath(IMG_CAT)}")

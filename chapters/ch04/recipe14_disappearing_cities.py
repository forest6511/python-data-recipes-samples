"""Recipe 14: 消滅可能性都市を自分で特定する.

「日本創成会議（増田レポート）が言う消滅可能性都市を、公開データから
自分で特定できないか」を試す。増田レポートの定義は『20〜39歳の若年女性人口が
将来（2010→2040年）に半減する自治体』で、これは将来推計に基づく。本レシピでは
将来推計の代わりに、実際の国勢調査（2015年→2020年）の市区町村別人口増減率を
使い、人口減少が大きい自治体＝消滅可能性が高い候補を自分でランキングする。

データ出典:
  総務省 国勢調査（2020年）人口等基本集計
    総人口・総世帯数・男女・年齢・配偶関係
    2015年の人口（組替）/ 5年間の人口増減数 / 5年間の人口増減率（市区町村別）
  e-Stat statsDataId: 0003445099
  tab: 2020_03(2015年人口組替) / 2020_34(5年間の人口増減数)
       / 2020_35(5年間の人口増減率) / 2020_48(人口密度)
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
CACHE = os.path.join(DATA_DIR, "recipe14_disappearing_cities.csv")
IMG = os.path.join(
    os.path.dirname(__file__), "images",
    "recipe14_disappearing_cities.png"
)

STATS_ID = "0003445099"
TAB = {
    "2020_03": "pop_2015",       # 2015年の人口（組替）
    "2020_34": "change_num",     # 5年間の人口増減数
    "2020_35": "change_pct",     # 5年間の人口増減率
}


def fetch_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, dtype={"area_code": str})
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_ID,
        "cdTab": ",".join(TAB.keys()),
        "limit": 100000,
    }
    j = requests.get(url, params=params, timeout=120).json()
    info = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = info["DATA_INF"]["VALUE"]
    area_map = {}
    for c in info["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "area":
            objs = c["CLASS"]
            objs = objs if isinstance(objs, list) else [objs]
            for o in objs:
                area_map[o["@code"]] = o["@name"]
    rows = []
    for v in vals:
        col = TAB.get(v.get("@tab"))
        if not col:
            continue
        try:
            val = float(v["$"])
        except (TypeError, ValueError):
            continue
        rows.append({"area_code": v["@area"],
                     "area": area_map.get(v["@area"], v["@area"]),
                     "metric": col, "value": val})
    long = pd.DataFrame(rows)
    df = long.pivot(index=["area_code", "area"], columns="metric",
                    values="value").reset_index()
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()

# 市区町村だけに絞る: 全国(00000)と都道府県(末尾000)を除外。
df = df[df["area_code"].str.match(r"^\d{5}$")].copy()
df = df[~df["area_code"].str.endswith("000")].copy()
# 「（旧：◯◯）」は市町村合併前の旧自治体（組替の名残）なので現存自治体だけに絞る
df = df[~df["area"].str.startswith("（旧")].copy()
# 人口規模が極端に小さい自治体（2015年で1000人未満）はノイズになるので除外
df = df[df["pop_2015"] >= 1000].copy()

print(f"=== 市区町村別 5年間の人口増減率（2015→2020, n={len(df)}）===")
print(f"全自治体の中央値: {df['change_pct'].median():+.1f}%")
print(f"人口が減少した自治体の割合: "
      f"{(df['change_pct'] < 0).mean()*100:.1f}%")
print(f"人口が増加した自治体の割合: "
      f"{(df['change_pct'] > 0).mean()*100:.1f}%")

declining = df.sort_values("change_pct")
print("\n--- 人口減少率が大きい自治体 トップ10 ---")
for _, r in declining.head(10).iterrows():
    print(f"  {r['area']:<14} {r['change_pct']:+.1f}%  "
          f"(2015年 {r['pop_2015']:,.0f}人)")

print("\n--- 人口増加率が大きい自治体 トップ5 ---")
for _, r in declining.tail(5).iloc[::-1].iterrows():
    print(f"  {r['area']:<14} {r['change_pct']:+.1f}%  "
          f"(2015年 {r['pop_2015']:,.0f}人)")

# 5年で10%以上減った自治体（このペースだと約35年で半減の目安）
n_10 = (df["change_pct"] <= -10).sum()
print(f"\n5年で10%以上減少した自治体: {n_10}件 "
      f"（全{len(df)}件の{n_10/len(df)*100:.1f}%）")
print("（5年で10%減は、このペースが続くと約35年で半減する水準）")

# --- 作図: 人口増減率の分布（ヒストグラム）---
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["change_pct"], bins=50, color="white", edgecolor="black",
        hatch="//")
ax.axvline(0, color="black", linewidth=1.2, label="増減なし")
ax.axvline(-10, color="black", linewidth=1.5, linestyle="--",
           label="5年で10%減（約35年で半減ペース）")
med = df["change_pct"].median()
ax.axvline(med, color="dimgray", linewidth=1.5, linestyle=":",
           label=f"中央値 {med:+.1f}%")
ax.set_xlabel("5年間の人口増減率（2015→2020, %）")
ax.set_ylabel("自治体数")
ax.set_title("市区町村別 人口増減率の分布（2015→2020）")
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

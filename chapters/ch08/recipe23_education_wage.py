"""Recipe 23: 大学進学率と生涯年収の関係.

学歴（高校卒・大学卒）で生涯に稼ぐ賃金がどれだけ違うのかを、賃金構造
基本統計調査の「学歴×年齢階級×職種」別の所定内給与額・年間賞与から
試算する。職種ごとに分かれた値を労働者数で加重平均して職種計の賃金
カーブを作り、20代前半から50代後半までの年収を積み上げて生涯賃金を
推計する。あわせて大学進学率の長期推移を補助的に確認する。

データ出典（e-Stat API・appId 必要）:
  賃金構造基本統計調査 一般_職種（大分類）_学歴、年齢階級別DB
    e-Stat statsDataId: 0003426415（賃金額は2020年が収録）
  学校基本調査 総括表 進学率（1948年～）
    e-Stat statsDataId: 0003147040（大学（学部）への進学率, 全国, ～2016年）
  政府統計の総合窓口 e-Stat API（環境変数 ESTAT_APP_ID）

caveat:
  - 生涯賃金は2020年断面の年齢階級別賃金を積み上げた試算であり、特定個人が
    実際に生涯で得る額の予測ではない。退職金・年金は含まない。
"""

import os
import sys

import numpy as np
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
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
WAGE_CACHE = os.path.join(DATA_DIR, "recipe23_wage.csv")
ADV_CACHE = os.path.join(DATA_DIR, "recipe23_advance.csv")
IMG = os.path.join(IMG_DIR, "recipe23_education_wage.png")

API = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
WAGE_ID = "0003426415"   # 一般_職種_学歴、年齢階級別DB
ADV_ID = "0003147040"    # 学校基本調査 総括表 進学率

EDU = {"03": "高校卒", "06": "大学卒"}
AGE = {
    "03": ("20～24歳", 5), "04": ("25～29歳", 5),
    "05": ("30～34歳", 5), "06": ("35～39歳", 5),
    "07": ("40～44歳", 5), "08": ("45～49歳", 5),
    "09": ("50～54歳", 5), "10": ("55～59歳", 5),
}


def _fetch_wage():
    """学歴×年齢×職種の月給・賞与・労働者数を取得（2020年）。"""
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    rows = []
    for tab in ("08", "12", "13"):  # 月給, 年間賞与, 労働者数
        params = {"appId": app_id, "statsDataId": WAGE_ID, "cdTab": tab,
                  "cdCat01": "01", "cdCat02": "01", "cdCat04": "03,06",
                  "limit": 3000}
        j = requests.get(API, params=params, timeout=120).json()
        vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        for v in vals:
            try:
                num = float(v["$"])  # "-" 等の秘匿値はスキップ
            except ValueError:
                continue
            rows.append({"tab": v["@tab"], "edu": v["@cat04"],
                         "age": v["@cat03"], "job": v["@cat05"],
                         "value": num})
    return pd.DataFrame(rows)


def load_wage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(WAGE_CACHE):
        return pd.read_csv(WAGE_CACHE, dtype={"tab": str, "edu": str,
                                              "age": str, "job": str})
    df = _fetch_wage()
    df.to_csv(WAGE_CACHE, index=False)
    return df


def load_advance():
    """大学（学部）への進学率の年次推移（全国）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(ADV_CACHE):
        return pd.read_csv(ADV_CACHE)
    app_id = os.environ.get("ESTAT_APP_ID")
    params = {"appId": app_id, "statsDataId": ADV_ID,
              "cdCat01": "0000000010", "cdCat02": "0000000070",
              "limit": 200}
    j = requests.get(API, params=params, timeout=120).json()
    vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    rows = [{"year": int(v["@time"][:4]), "rate": float(v["$"])}
            for v in vals if v["$"] not in ("-", "")]
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


os.makedirs(IMG_DIR, exist_ok=True)
wage = load_wage()

# 職種計の加重平均: 学歴×年齢ごとに労働者数を重みに月給・賞与を平均
piv = wage.pivot_table(index=["edu", "age", "job"], columns="tab",
                       values="value").reset_index()
piv = piv.rename(columns={"08": "monthly_k", "12": "bonus_k",
                          "13": "workers"})
piv = piv.dropna(subset=["monthly_k", "bonus_k", "workers"])
piv = piv[piv["workers"] > 0]


def weighted(group, col):
    return np.average(group[col], weights=group["workers"])


agg = (piv.groupby(["edu", "age"])
       .apply(lambda g: pd.Series({
           "monthly_k": weighted(g, "monthly_k"),
           "bonus_k": weighted(g, "bonus_k")}), include_groups=False)
       .reset_index())
agg["edu"] = agg["edu"].map(EDU)

# 年収（万円）= 月給(千円)×12/10 + 賞与(千円)/10
agg["annual_man"] = (agg["monthly_k"] * 12 + agg["bonus_k"]) / 10
agg = agg[agg["age"].isin(AGE)].copy()
agg["years"] = agg["age"].map(lambda a: AGE[a][1])
agg = agg.sort_values(["edu", "age"]).reset_index(drop=True)

lifetime = (agg.assign(span=agg["annual_man"] * agg["years"])
            .groupby("edu")["span"].sum())
lt_hs, lt_uni = lifetime["高校卒"], lifetime["大学卒"]

print("=== 学歴別 年齢階級別 年収（職種計・労働者数で加重, 2020年, 万円）===")
for edu in ("高校卒", "大学卒"):
    sub = agg[agg["edu"] == edu]
    print(f"[{edu}]")
    for _, r in sub.iterrows():
        print(f"  {AGE[r['age']][0]}: {r['annual_man']:.1f}万円")
print("\n=== 生涯賃金試算（20-59歳の8階級×5年, 退職金除く）===")
print(f"高校卒: {lt_hs / 10000:.2f}億円  ({lt_hs:,.0f}万円)")
print(f"大学卒: {lt_uni / 10000:.2f}億円  ({lt_uni:,.0f}万円)")
print(f"差: {lt_uni - lt_hs:,.0f}万円  倍率 {lt_uni / lt_hs:.3f}")

adv = load_advance()
print("\n=== 大学（学部）への進学率（全国, %）===")
print(f"{int(adv['year'].min())}年 {adv.iloc[0]['rate']:.1f}% -> "
      f"{int(adv['year'].max())}年 {adv.iloc[-1]['rate']:.1f}%")

# --- 作図: 左=学歴別賃金カーブ, 右=進学率推移 ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
labels = [AGE[a][0] for a in sorted(AGE)]
x = range(len(labels))
hs = agg[agg["edu"] == "高校卒"].sort_values("age")["annual_man"].values
uni = agg[agg["edu"] == "大学卒"].sort_values("age")["annual_man"].values
ax1.plot(x, hs, color="black", linewidth=1.5, marker="s",
         markersize=6, linestyle="--", label="高校卒")
ax1.plot(x, uni, color="black", linewidth=1.5, marker="o",
         markersize=6, label="大学卒")
ax1.fill_between(x, hs, uni, color="lightgray", alpha=0.5)
ax1.set_xticks(list(x))
ax1.set_xticklabels(labels, rotation=45, ha="right")
ax1.set_ylabel("推定年収（万円）")
ax1.set_title("学歴別 年齢階級別の年収（2020年・職種計）")
ax1.legend(loc="upper left")
ax1.grid(axis="y", linestyle="--", alpha=0.4)

ax2.plot(adv["year"], adv["rate"], color="black", linewidth=1.5)
ax2.set_xlabel("年")
ax2.set_ylabel("進学率（%）")
ax2.set_title("大学（学部）への進学率の推移（全国）")
ax2.grid(axis="y", linestyle="--", alpha=0.4)

fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

"""Recipe 11: 人口ピラミッドの変化を可視化する.

「日本の人口構成は戦後どう変わったのか」を人口ピラミッドで可視化する。
若年層が多い富士山型（1950年）から、高齢層が膨らむ釣鐘・つぼ型（2024年）への
変化を、年齢5歳階級・男女別の人口で左右対称の横棒グラフにして比べる。

データ出典:
  1950年: 国勢調査 年齢（5歳階級），男女別人口－全国（大正9年〜平成17年）
          e-Stat statsDataId: 0003406936
  2024年: 人口推計 年齢（5歳階級），男女別人口及び割合－総人口
          e-Stat statsDataId: 0003448230
  いずれも 政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）

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
from matplotlib.ticker import FuncFormatter  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe11_population_pyramid.csv")
IMG = os.path.join(
    os.path.dirname(__file__), "images", "recipe11_population_pyramid.png"
)

# 5歳階級ラベル（0〜4歳 … 85歳以上）の共通並び
AGE_LABELS = [
    "0〜4", "5〜9", "10〜14", "15〜19", "20〜24", "25〜29",
    "30〜34", "35〜39", "40〜44", "45〜49", "50〜54", "55〜59",
    "60〜64", "65〜69", "70〜74", "75〜79", "80〜84", "85歳以上",
]


def _api(stats_id, params_extra):
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {"appId": app_id, "statsDataId": stats_id, "limit": 5000}
    params.update(params_extra)
    j = requests.get(url, params=params, timeout=60).json()
    return j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]


def fetch_1950():
    """国勢調査 1950年の男女別・5歳階級別人口を取得。"""
    # tab=020(人口), cat01=110/120(男/女), time=1950
    vals = _api("0003406936", {"cdTab": "020", "cdTime": "1950000000"})
    age_code = {
        "110": "0〜4", "120": "5〜9", "130": "10〜14", "150": "15〜19",
        "160": "20〜24", "170": "25〜29", "180": "30〜34", "190": "35〜39",
        "200": "40〜44", "210": "45〜49", "220": "50〜54", "230": "55〜59",
        "240": "60〜64", "250": "65〜69", "260": "70〜74", "280": "75〜79",
        "290": "80〜84", "300": "85歳以上",
    }
    sex_code = {"110": "男", "120": "女"}
    rows = []
    for v in vals:
        s = sex_code.get(v.get("@cat01"))
        a = age_code.get(v.get("@cat02"))
        if s and a:
            # 国勢調査は単位「人」。2024年（千人）に揃えるため 1000 で割る
            rows.append({"year": 1950, "sex": s, "age": a,
                         "pop": float(v["$"]) / 1000.0})  # 単位: 千人
    return pd.DataFrame(rows)


def fetch_2024():
    """人口推計 2024年の男女別・5歳階級別人口を取得。"""
    # cat01=001/002(男/女), cat02=001(人口), time=2024
    vals = _api("0003448230",
                {"cdCat02": "001", "cdTime": "2024000000"})
    age_code = {
        "01001": "0〜4", "01002": "5〜9", "01003": "10〜14",
        "01004": "15〜19", "01005": "20〜24", "01006": "25〜29",
        "01007": "30〜34", "01008": "35〜39", "01009": "40〜44",
        "01010": "45〜49", "01011": "50〜54", "01012": "55〜59",
        "01013": "60〜64", "01014": "65〜69", "01015": "70〜74",
        "01016": "75〜79", "01017": "80〜84",
    }
    # 85歳以上は 85〜89 + 90〜94 + 95〜99 + 100歳以上 を合算
    age_85plus = {"01018", "01019", "01020", "01021"}
    sex_code = {"001": "男", "002": "女"}
    rows = []
    for v in vals:
        s = sex_code.get(v.get("@cat01"))
        if not s:
            continue
        c = v.get("@cat03")
        if c in age_code:
            rows.append({"year": 2024, "sex": s, "age": age_code[c],
                         "pop": float(v["$"])})  # 単位: 千人
        elif c in age_85plus:
            rows.append({"year": 2024, "sex": s, "age": "85歳以上",
                         "pop": float(v["$"])})
    df = pd.DataFrame(rows)
    # 85歳以上は複数階級を合算
    return df.groupby(["year", "sex", "age"], as_index=False)["pop"].sum()


def fetch_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    df = pd.concat([fetch_1950(), fetch_2024()], ignore_index=True)
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()

# 年×性で総人口（千人）を出す
print("=== 取得データの概要 ===")
for year in [1950, 2024]:
    sub = df[df["year"] == year]
    total = sub["pop"].sum()
    print(f"{year}年 総人口（千人）: {total:,.0f}")

# 高齢化率（65歳以上の割合）を年ごとに計算
old_ages = ["65〜69", "70〜74", "75〜79", "80〜84", "85歳以上"]
young_ages = ["0〜4", "5〜9", "10〜14"]
print("\n=== 年齢構成の変化 ===")
ratios = {}
for year in [1950, 2024]:
    sub = df[df["year"] == year]
    total = sub["pop"].sum()
    old = sub[sub["age"].isin(old_ages)]["pop"].sum()
    young = sub[sub["age"].isin(young_ages)]["pop"].sum()
    ratios[year] = {
        "old": old / total * 100,
        "young": young / total * 100,
    }
    print(f"{year}年: 65歳以上 {old/total*100:.1f}%  "
          f"15歳未満 {young/total*100:.1f}%")

print(f"\n高齢化率の変化: {ratios[1950]['old']:.1f}% "
      f"→ {ratios[2024]['old']:.1f}% "
      f"(+{ratios[2024]['old']-ratios[1950]['old']:.1f}pt)")
print(f"年少人口割合の変化: {ratios[1950]['young']:.1f}% "
      f"→ {ratios[2024]['young']:.1f}% "
      f"({ratios[2024]['young']-ratios[1950]['young']:.1f}pt)")

# --- 作図: 1950年と2024年の人口ピラミッドを並べる ---
fig, axes = plt.subplots(1, 2, figsize=(11, 7), sharey=True)
y = range(len(AGE_LABELS))

for ax, year in zip(axes, [1950, 2024]):
    male = [df[(df["year"] == year) & (df["sex"] == "男") &
               (df["age"] == a)]["pop"].sum() for a in AGE_LABELS]
    female = [df[(df["year"] == year) & (df["sex"] == "女") &
                 (df["age"] == a)]["pop"].sum() for a in AGE_LABELS]
    ax.barh(y, [-m for m in male], color="dimgray", edgecolor="black",
            label="男")
    ax.barh(y, female, color="white", edgecolor="black", hatch="//",
            label="女")
    ax.set_yticks(list(y))
    ax.set_yticklabels(AGE_LABELS)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(f"{year}年")
    ax.set_xlabel("人口（千人）　左:男　右:女")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    # x軸の絶対値表示（左側のマイナスを正に見せる）
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda t, _: f"{abs(int(t)):,}"))

axes[0].legend(loc="upper left")
fig.suptitle("日本の人口ピラミッドの変化（1950年 → 2024年）")
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

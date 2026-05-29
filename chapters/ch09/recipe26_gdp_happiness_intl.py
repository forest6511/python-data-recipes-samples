"""Recipe 26: 経済規模が大きい国は幸せか.

「国全体のGDPが大きい国は幸せか」を国際比較する。経済規模ランキングと
幸福度ランキングのズレ、地域差、そして幸福度トップ10の国で6要因
（1人あたりGDP・社会的支援・健康寿命・人生選択の自由・寛容さ・腐敗の
少なさ）のうち何が大きいかを見る。

データ出典（API キー不要）:
  World Happiness Report 2024（Ladder score と6要因の寄与, 地域区分）
    https://raw.githubusercontent.com/Escavine/World-Happiness/main/World-happiness-report-2024.csv
  世界銀行 GDP（current US$, 国全体）NY.GDP.MKTP.CD
    https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD

caveat:
  - 幸福度は主観的評価（自己申告）であり、文化や回答傾向の影響を受ける。
  - WHR の6要因は「寄与の推定値」であって、各要因の因果効果ではない。
"""

import io
import os
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
WHR_CACHE = os.path.join(DATA_DIR, "recipe25_whr2024.csv")  # R25 と共有
GDP_CACHE = os.path.join(DATA_DIR, "recipe26_wb_gdp_total.csv")
IMG = os.path.join(IMG_DIR, "recipe26_gdp_happiness_intl.png")

WHR_URL = (
    "https://raw.githubusercontent.com/Escavine/World-Happiness/"
    "main/World-happiness-report-2024.csv"
)
GDP_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    "NY.GDP.MKTP.CD?format=json&date=2023&per_page=400"
)

NAME_FIX = {
    "Russia": "Russian Federation",
    "South Korea": "Korea, Rep.",
    "Slovakia": "Slovak Republic",
    "Kyrgyzstan": "Kyrgyz Republic",
    "Hong Kong S.A.R. of China": "Hong Kong SAR, China",
    "Taiwan Province of China": None,
    "Congo (Brazzaville)": "Congo, Rep.",
    "Congo (Kinshasa)": "Congo, Dem. Rep.",
    "Ivory Coast": "Cote d'Ivoire",
    "Laos": "Lao PDR",
    "Egypt": "Egypt, Arab Rep.",
    "Iran": "Iran, Islamic Rep.",
    "Venezuela": "Venezuela, RB",
    "Gambia": "Gambia, The",
    "Yemen": "Yemen, Rep.",
    "State of Palestine": "West Bank and Gaza",
}

FACTORS = [
    "Log GDP per capita", "Social support", "Healthy life expectancy",
    "Freedom to make life choices", "Generosity",
    "Perceptions of corruption",
]
FACTOR_JP = {
    "Log GDP per capita": "1人あたりGDP",
    "Social support": "社会的支援",
    "Healthy life expectancy": "健康寿命",
    "Freedom to make life choices": "人生選択の自由",
    "Generosity": "寛容さ",
    "Perceptions of corruption": "腐敗の少なさ",
}


def load_whr():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(WHR_CACHE):
        return pd.read_csv(WHR_CACHE)
    txt = requests.get(WHR_URL, timeout=30).text
    df = pd.read_csv(io.StringIO(txt))
    df.to_csv(WHR_CACHE, index=False)
    return df


def load_gdp():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(GDP_CACHE):
        return pd.read_csv(GDP_CACHE)
    j = requests.get(GDP_URL, timeout=30).json()
    rows = [
        {"country": x["country"]["value"], "gdp": x["value"]}
        for x in j[1]
        if x["value"] is not None
    ]
    df = pd.DataFrame(rows)
    df.to_csv(GDP_CACHE, index=False)
    return df


whr = load_whr()
gdp = load_gdp()

whr["wb_name"] = whr["Country name"].map(lambda n: NAME_FIX.get(n, n))
whr = whr[whr["wb_name"].notna()]
m = whr.merge(gdp, left_on="wb_name", right_on="country", how="inner")
m = m.dropna(subset=["Ladder score", "gdp"])

m["happy_rank"] = m["Ladder score"].rank(ascending=False).astype(int)
m["gdp_rank"] = m["gdp"].rank(ascending=False).astype(int)
print(f"=== 突合できた国数: {len(m)} ===")

print("\n=== 経済規模（GDP総額）トップ10と幸福度ランク ===")
top_gdp = m.sort_values("gdp", ascending=False).head(10)
for _, r in top_gdp.iterrows():
    print(f"  GDP{r['gdp_rank']:>2}位 {r['Country name']:<16} "
          f"GDP {r['gdp'] / 1e12:5.2f}兆$  "
          f"幸福度{r['happy_rank']:>3}位 ({r['Ladder score']:.2f})")

print("\n=== 地域別 平均幸福度（国数）===")
reg = (m.groupby("Regional indicator")["Ladder score"]
       .agg(["mean", "count"]).sort_values("mean", ascending=False))
for name, row in reg.iterrows():
    print(f"  {name:<32} {row['mean']:.2f}  (n={int(row['count'])})")

print("\n=== 幸福度トップ5の要因構成 ===")
top5 = m.sort_values("Ladder score", ascending=False).head(5)
for _, r in top5.iterrows():
    gdp_share = r["Log GDP per capita"]
    others = sum(r[f] for f in FACTORS if f != "Log GDP per capita")
    print(f"  {r['Country name']:<12} 幸福度{r['Ladder score']:.2f}  "
          f"GDP寄与 {gdp_share:.2f} / その他要因合計 {others:.2f}")

us = m[m["Country name"] == "United States"]
if len(us):
    u = us.iloc[0]
    print(f"\n米国: GDP {u['gdp_rank']}位 だが 幸福度 {u['happy_rank']}位 "
          f"({u['Ladder score']:.2f})")

# --- 作図: 上位国の要因分解 積み上げ棒（白黒対応・ハッチング）---
os.makedirs(IMG_DIR, exist_ok=True)
plot_df = m.sort_values("Ladder score", ascending=False).head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(11, 6.5))
hatches = ["", "///", "...", "xxx", "\\\\\\", "ooo"]
grays = [0.15, 0.35, 0.5, 0.65, 0.8, 0.92]
left = [0.0] * len(plot_df)
for f, hh, gg in zip(FACTORS, hatches, grays):
    vals = plot_df[f].to_numpy(dtype=float)
    ax.barh(plot_df["Country name"], vals, left=left,
            color=str(gg), edgecolor="black", hatch=hh,
            label=FACTOR_JP[f])
    left = [a + b for a, b in zip(left, vals)]
ax.set_xlabel("幸福度スコアへの要因別寄与（World Happiness Report 2024）")
ax.set_title("幸福度トップ10の国：何が幸福度を支えているか")
ax.legend(loc="lower right", fontsize=9, ncol=2)
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

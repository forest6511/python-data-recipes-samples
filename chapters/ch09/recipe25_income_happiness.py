"""Recipe 25: 年収と幸福度は比例するか.

各国の幸福度（World Happiness Report の Cantril ladder スコア, 0-10）と
1人あたりの所得（世界銀行の1人あたりGDP, 購買力平価ドル）を突き合わせ、
所得が増えると幸福度がどう変わるかを見る。所得そのままの直線あてはめと、
所得を対数に変換したあてはめを比べ、「比例か、頭打ちか」を見分ける。

データ出典（API キー不要）:
  World Happiness Report 2024（Ladder score, Log GDP per capita 等）
    https://raw.githubusercontent.com/Escavine/World-Happiness/main/World-happiness-report-2024.csv
  世界銀行 1人あたりGDP（購買力平価, 現在の国際ドル）NY.GDP.PCAP.PP.CD
    https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.CD

caveat:
  - 国の平均値どうしの比較（生態学的相関）であり、個人の年収と幸福度の
    関係に直接読み替えることはできない。
  - 相関は因果ではない。幸福度には所得以外（社会的支援・健康・自由度
    など）も効いている。
"""

import io
import os
import sys

import numpy as np
import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
WHR_CACHE = os.path.join(DATA_DIR, "recipe25_whr2024.csv")
GDP_CACHE = os.path.join(DATA_DIR, "recipe25_wb_gdp_pc.csv")
IMG = os.path.join(IMG_DIR, "recipe25_income_happiness.png")

WHR_URL = (
    "https://raw.githubusercontent.com/Escavine/World-Happiness/"
    "main/World-happiness-report-2024.csv"
)
GDP_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    "NY.GDP.PCAP.PP.CD?format=json&date=2023&per_page=400"
)

# WHR と世界銀行で表記が異なる国名の対応
NAME_FIX = {
    "Russia": "Russian Federation",
    "South Korea": "Korea, Rep.",
    "Slovakia": "Slovak Republic",
    "Kyrgyzstan": "Kyrgyz Republic",
    "Hong Kong S.A.R. of China": "Hong Kong SAR, China",
    "Taiwan Province of China": None,  # 世界銀行に無い→除外
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
        {"country": x["country"]["value"], "gdp_pc": x["value"]}
        for x in j[1]
        if x["value"] is not None
    ]
    df = pd.DataFrame(rows)
    df.to_csv(GDP_CACHE, index=False)
    return df


whr = load_whr()
gdp = load_gdp()

whr = whr[["Country name", "Ladder score"]].copy()
whr["wb_name"] = whr["Country name"].map(lambda n: NAME_FIX.get(n, n))
whr = whr[whr["wb_name"].notna()]

m = whr.merge(gdp, left_on="wb_name", right_on="country", how="inner")
m = m.dropna(subset=["Ladder score", "gdp_pc"])
m = m.rename(columns={"Ladder score": "happiness"})

print(f"=== 突合できた国数: {len(m)} ===")

x = m["gdp_pc"].to_numpy(dtype=float)
y = m["happiness"].to_numpy(dtype=float)
logx = np.log(x)

r_lin, p_lin = stats.pearsonr(x, y)
lin = stats.linregress(x, y)
r_log, p_log = stats.pearsonr(logx, y)
log = stats.linregress(logx, y)

print("\n=== (1) 1人あたりGDP（そのまま）vs 幸福度 ===")
print(f"Pearson r = {r_lin:.3f}  p = {p_lin:.2e}")
print(f"線形回帰 R^2 = {lin.rvalue**2:.3f}")

print("\n=== (2) 1人あたりGDP（対数）vs 幸福度 ===")
print(f"Pearson r = {r_log:.3f}  p = {p_log:.2e}")
print(f"線形回帰 R^2 = {log.rvalue**2:.3f}")
print(f"対数あてはめ: 所得が2倍 → 幸福度 +{log.slope * np.log(2):.3f} ポイント")

m_sorted = m.sort_values("gdp_pc")
q1 = m_sorted.head(len(m) // 4)
q4 = m_sorted.tail(len(m) // 4)
print("\n=== 所得階層別の平均（下位25% vs 上位25%）===")
print(f"下位25%: GDP/人 平均 ${q1['gdp_pc'].mean():,.0f}  "
      f"幸福度 {q1['happiness'].mean():.2f}")
print(f"上位25%: GDP/人 平均 ${q4['gdp_pc'].mean():,.0f}  "
      f"幸福度 {q4['happiness'].mean():.2f}")
ratio_gdp = q4['gdp_pc'].mean() / q1['gdp_pc'].mean()
diff_hap = q4['happiness'].mean() - q1['happiness'].mean()
print(f"→ 所得は {ratio_gdp:.1f}倍だが幸福度の差は +{diff_hap:.2f}ポイントのみ")

jp = m[m["wb_name"] == "Japan"]
if len(jp):
    print(f"\n日本: GDP/人 ${jp['gdp_pc'].iloc[0]:,.0f}  "
          f"幸福度 {jp['happiness'].iloc[0]:.2f}")

# --- 作図: 散布図 + 直線あてはめ + 対数あてはめ（白黒対応）---
os.makedirs(IMG_DIR, exist_ok=True)
fig, ax = plt.subplots(figsize=(11, 6.5))
ax.scatter(x, y, s=28, facecolors="none", edgecolors="black",
           linewidths=0.8, label="各国（1点=1か国）")

xs = np.linspace(x.min(), x.max(), 200)
ax.plot(xs, lin.intercept + lin.slope * xs, color="black",
        linestyle="--", linewidth=1.5,
        label=f"直線あてはめ R²={lin.rvalue**2:.2f}")
ax.plot(xs, log.intercept + log.slope * np.log(xs), color="black",
        linestyle="-", linewidth=1.8,
        label=f"対数あてはめ R²={log.rvalue**2:.2f}")

if len(jp):
    ax.scatter(jp["gdp_pc"], jp["happiness"], s=90, color="black",
               marker="*", zorder=5)
    ax.annotate("日本", (jp["gdp_pc"].iloc[0], jp["happiness"].iloc[0]),
                textcoords="offset points", xytext=(8, -12), fontsize=10)

ax.set_xlabel("1人あたりGDP（購買力平価, 国際ドル, 2023年）")
ax.set_ylabel("幸福度（Cantril ladder, 0-10, 2024年報告）")
ax.set_title("1人あたり所得と幸福度の関係（世界の国々）")
ax.legend(loc="lower right", fontsize=10)
ax.grid(linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

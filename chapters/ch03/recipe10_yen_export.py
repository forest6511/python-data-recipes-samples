"""Recipe 10: 円安で日本の輸出は増えたか.

「円安になれば輸出が伸びる」という通説を、為替レートと輸出数量指数の
2つのデータで検証する。価格や為替の影響を含む「輸出額」ではなく、
実際にどれだけの量を輸出したかを示す「輸出数量指数」を使うのがポイント。
円安が進んだのに数量が伸びていなければ、通説は現実と食い違っている。

データ出典:
  為替レート（円/ドル）: FRED（米セントルイス連銀）DEXJPUS
    https://fred.stlouisfed.org/series/DEXJPUS （API キー不要・公開CSV）
  輸出数量指数: World Bank Open Data
    指標 TX.QTY.MRCH.XD.WD（商品輸出数量指数, 2015=100, API キー不要）
両方とも年次に集計して比較する。
"""

import os
import sys

import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe10_yen_export.csv")
IMG_TS = os.path.join(os.path.dirname(__file__), "images",
                      "recipe10_yen_export_ts.png")
IMG_SC = os.path.join(os.path.dirname(__file__), "images",
                      "recipe10_yen_export_scatter.png")

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS"
WB_URL = ("https://api.worldbank.org/v2/country/JPN/indicator/"
          "TX.QTY.MRCH.XD.WD?format=json&per_page=70")


def fetch_fx():
    """FRED から円/ドル日次レートを取得し年平均にする。"""
    df = pd.read_csv(FRED_URL, na_values=["."])
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df["year"] = df["observation_date"].dt.year
    df = df.dropna(subset=["DEXJPUS"])
    yearly = df.groupby("year")["DEXJPUS"].mean().rename("yen_per_usd")
    return yearly.reset_index()


def fetch_export_volume():
    """World Bank から輸出数量指数を取得。"""
    j = requests.get(WB_URL, timeout=60).json()
    rows = [{"year": int(d["date"]), "export_vol": d["value"]}
            for d in j[1] if d["value"] is not None]
    return pd.DataFrame(rows)


def build():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    fx = fetch_fx()
    ev = fetch_export_volume()
    df = fx.merge(ev, on="year").sort_values("year")
    df.to_csv(CACHE, index=False)
    return df


df = build()
# 輸出数量指数が揃う期間（2000年以降）に絞る
df = df[df["year"] >= 2000].dropna().reset_index(drop=True)

# 円安局面（2012年→直近）の変化を見る
y2012 = df[df["year"] == 2012].iloc[0]
latest = df.iloc[-1]
fx_change = (latest["yen_per_usd"] / y2012["yen_per_usd"] - 1) * 100
vol_change = (latest["export_vol"] / y2012["export_vol"] - 1) * 100

print("=== 為替と輸出数量指数（年平均）===")
print(f"対象期間: {int(df['year'].min())}-{int(df['year'].max())}")
print(f"2012年: 為替 {y2012['yen_per_usd']:.1f}円/$  "
      f"輸出数量指数 {y2012['export_vol']:.1f}")
print(f"{int(latest['year'])}年: 為替 {latest['yen_per_usd']:.1f}円/$  "
      f"輸出数量指数 {latest['export_vol']:.1f}")
print(f"\n2012年→{int(latest['year'])}年の変化:")
print(f"  円は対ドルで {fx_change:+.1f}% 動いた（プラス＝円安）")
print(f"  輸出数量指数は {vol_change:+.1f}% 変化")

# 為替と輸出数量の相関（円安＝輸出増 なら正の相関のはず）
r, p = stats.pearsonr(df["yen_per_usd"], df["export_vol"])
print(f"\n為替（円/$）と輸出数量指数の相関係数 r={r:.3f}, p={p:.4f}")

# --- 作図1: 二軸で為替と輸出数量指数の推移 ---
fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.plot(df["year"], df["yen_per_usd"], color="black", linewidth=1.5,
         marker="o", markersize=4, label="為替（円/ドル・年平均）")
ax1.set_xlabel("年")
ax1.set_ylabel("為替レート（円/ドル）")
ax1.axvline(2012, color="gray", linestyle=":", linewidth=1.0)
ax2 = ax1.twinx()
ax2.plot(df["year"], df["export_vol"], color="black", linewidth=1.5,
         linestyle="--", marker="s", markersize=4,
         label="輸出数量指数（2015=100）")
ax2.set_ylabel("輸出数量指数（2015=100）")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
ax1.set_title("円/ドル為替と輸出数量指数の推移（点線は2012年）")
ax1.grid(axis="y", linestyle="--", alpha=0.3)
fig.tight_layout()
fig.savefig(IMG_TS, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_TS)}")

# --- 作図2: 散布図（為替 vs 輸出数量指数）---
fig2, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df["yen_per_usd"], df["export_vol"], color="black", s=40)
for _, row in df.iterrows():
    if int(row["year"]) % 4 == 0:  # 4年おきに年ラベル
        ax.annotate(str(int(row["year"])),
                    (row["yen_per_usd"], row["export_vol"]),
                    textcoords="offset points", xytext=(5, 3), fontsize=8)
ax.set_xlabel("為替レート（円/ドル・年平均）　右ほど円安")
ax.set_ylabel("輸出数量指数（2015=100）")
ax.set_title(f"為替と輸出数量指数の関係（r={r:.2f}）")
ax.grid(linestyle="--", alpha=0.4)
fig2.tight_layout()
fig2.savefig(IMG_SC, dpi=200)
print(f"保存: {os.path.relpath(IMG_SC)}")

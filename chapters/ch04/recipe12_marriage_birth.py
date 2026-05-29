"""Recipe 12: 少子化と婚姻率、どっちが原因か.

「結婚が減ったから子どもが減ったのか、それとも別の理由なのか」を、
人口動態統計の婚姻件数・出生数の長期推移と相関で確かめる。日本では
婚外子が少ないため、婚姻と出生は強く連動する。ただし相関が強くても
それは『因果』を意味しない――本章の核心テーマである「相関≠因果」を、
婚姻と出生のラグ相関（結婚の数年後に出生が動くか）を例に検証する。

データ出典:
  厚生労働省 人口動態調査 上巻 年次別にみた人口動態総覧
  e-Stat statsDataId: 0003411561
  cat01: 00110 出生数 / 00270 婚姻件数 / 00300 合計特殊出生率 / 00420 婚姻率
  政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）

事前準備: e-Stat (https://www.e-stat.go.jp/) で利用登録し appId を発行、
  このディレクトリに .env を置いて ESTAT_APP_ID=発行されたID と記述する。
"""

import os
import sys

import pandas as pd
import requests
from scipy import stats
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe12_marriage_birth.csv")
IMG_TS = os.path.join(
    os.path.dirname(__file__), "images", "recipe12_marriage_birth_ts.png"
)
IMG_LAG = os.path.join(
    os.path.dirname(__file__), "images", "recipe12_lag_corr.png"
)

STATS_ID = "0003411561"
# cat01 コード → 列名
CAT = {
    "00110": "births",      # 出生数
    "00270": "marriages",   # 婚姻件数
    "00300": "tfr",         # 合計特殊出生率
    "00420": "marriage_rate",  # 婚姻率（人口千対）
}


def fetch_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_ID,
        "cdCat01": ",".join(CAT.keys()),
        "limit": 5000,
    }
    j = requests.get(url, params=params, timeout=60).json()
    vals = j["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    rows = []
    for v in vals:
        col = CAT.get(v.get("@cat01"))
        if not col:
            continue
        year = int(v["@time"][:4])
        raw = v.get("$")
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue  # "-" や空欄はスキップ
        rows.append({"year": year, "metric": col, "value": val})
    long = pd.DataFrame(rows)
    df = long.pivot(index="year", columns="metric",
                    values="value").reset_index()
    df = df.sort_values("year").reset_index(drop=True)
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()

# 戦後（1947年以降）に絞る。戦前・戦中は統計の連続性が乏しいため
df = df[df["year"] >= 1947].dropna(
    subset=["births", "marriages"]).reset_index(drop=True)

print("=== 婚姻件数と出生数の推移（戦後）===")
print(f"対象期間: {df['year'].min()}〜{df['year'].max()}年")
peak_m = df.loc[df["marriages"].idxmax()]
peak_b = df.loc[df["births"].idxmax()]
last = df.iloc[-1]
print(f"婚姻件数のピーク: {int(peak_m['year'])}年 "
      f"{peak_m['marriages']:,.0f}件")
print(f"出生数のピーク: {int(peak_b['year'])}年 {peak_b['births']:,.0f}人")
print(f"直近 {int(last['year'])}年: 婚姻 {last['marriages']:,.0f}件 / "
      f"出生 {last['births']:,.0f}人")

# 同年の相関（婚姻件数 vs 出生数）
r0, p0 = stats.pearsonr(df["marriages"], df["births"])
print(f"\n同年の相関 (婚姻件数 vs 出生数): r={r0:.3f} (p={p0:.2e})")

# ラグ相関: 婚姻件数を 0〜5 年ずらして出生数との相関を見る
print("\n=== ラグ相関（婚姻を n 年ずらして出生数と相関）===")
best_lag, best_r = 0, -2.0
lags, rs = [], []
for lag in range(0, 6):
    m = df["marriages"].iloc[:len(df) - lag].reset_index(drop=True) \
        if lag else df["marriages"]
    b = df["births"].iloc[lag:].reset_index(drop=True) \
        if lag else df["births"]
    n = min(len(m), len(b))
    r, _ = stats.pearsonr(m.iloc[:n], b.iloc[:n])
    lags.append(lag)
    rs.append(r)
    print(f"  婚姻 → {lag}年後の出生: r={r:.3f}")
    if r > best_r:
        best_r, best_lag = r, lag

print(f"\n相関が最大になるラグ: {best_lag}年 (r={best_r:.3f})")

# 合計特殊出生率の推移
if "tfr" in df.columns:
    tfr = df.dropna(subset=["tfr"])
    print(f"\n合計特殊出生率: {int(tfr['year'].min())}年 "
          f"{tfr['tfr'].iloc[0]:.2f} → {int(tfr['year'].max())}年 "
          f"{tfr['tfr'].iloc[-1]:.2f}")

# --- 作図1: 婚姻件数と出生数の長期推移（2軸）---
fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.plot(df["year"], df["births"] / 10000, color="black",
         linestyle="-", marker="", label="出生数（万人）")
ax1.set_xlabel("年")
ax1.set_ylabel("出生数（万人）")
ax2 = ax1.twinx()
ax2.plot(df["year"], df["marriages"] / 10000, color="dimgray",
         linestyle="--", marker="", label="婚姻件数（万件）")
ax2.set_ylabel("婚姻件数（万件）")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
ax1.set_title("婚姻件数と出生数の長期推移（日本・戦後）")
ax1.grid(linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG_TS, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_TS)}")

# --- 作図2: ラグ相関の棒グラフ ---
fig2, ax = plt.subplots(figsize=(10, 6))
ax.bar([str(x) for x in lags], rs, color="white", edgecolor="black",
       hatch="//")
ax.set_ylim(min(0, min(rs) - 0.05), 1.0)
ax.set_xlabel("婚姻件数を何年ずらして出生数と相関を取ったか（年）")
ax.set_ylabel("相関係数 r")
ax.set_title("婚姻件数と出生数のラグ相関（ずらす年数別）")
ax.grid(axis="y", linestyle="--", alpha=0.4)
for i, r in enumerate(rs):
    ax.text(i, r + 0.01, f"{r:.3f}", ha="center", va="bottom")
fig2.tight_layout()
fig2.savefig(IMG_LAG, dpi=200)
print(f"保存: {os.path.relpath(IMG_LAG)}")

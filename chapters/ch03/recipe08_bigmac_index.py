"""Recipe 08: ビッグマック指数で購買力を比較する.

The Economist が公開しているビッグマック指数のデータを使い、
「日本の物価は世界の中で本当に安いのか」を購買力平価の観点から確かめる。
各国のビッグマック価格を米ドル換算し、米国を基準に何%割安/割高かを比較する。
さらに、日本円のビッグマック価格の推移から「安い日本」がいつ始まったかを見る。

データ出典:
  The Economist Big Mac index（GitHub 公開データ, CC BY-ND）
  https://github.com/TheEconomist/big-mac-data
  output-data/big-mac-full-index.csv（2000-2026, API キー不要）
  USD_raw = 対米ドルの raw index。0 が購買力平価どおり、
  マイナスが「ドルに対して通貨が割安（＝物価が安い）」を意味する。
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe08_bigmac.csv")
IMG_BAR = os.path.join(os.path.dirname(__file__), "images",
                       "recipe08_bigmac_ranking.png")
IMG_JP = os.path.join(os.path.dirname(__file__), "images",
                      "recipe08_bigmac_japan.png")

URL = ("https://raw.githubusercontent.com/TheEconomist/big-mac-data/"
       "master/output-data/big-mac-full-index.csv")


def fetch_data():
    """ビッグマック指数 CSV を取得しキャッシュする。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, parse_dates=["date"])
    df = pd.read_csv(URL, parse_dates=["date"])
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()

# 最新時点のスナップショットで国際比較する
latest = df["date"].max()
snap = df[df["date"] == latest].copy()

# ドル換算価格でランキング（高い順＝割高、安い順＝割安）
snap = snap.sort_values("dollar_price", ascending=False).reset_index(drop=True)

jp = snap[snap["iso_a3"] == "JPN"].iloc[0]
us = snap[snap["iso_a3"] == "USA"].iloc[0]

print(f"=== ビッグマック指数 スナップショット（{latest.date()}）===")
print(f"対象国数: {len(snap)}")
print(f"米国のビッグマック価格: ${us['dollar_price']:.2f}")
print(f"日本のビッグマック価格: ${jp['dollar_price']:.2f} "
      f"(現地 {jp['local_price']:.0f}円, 為替 {jp['dollar_ex']:.2f}円/$)")
# USD_raw はドル基準の割安・割高度（マイナス＝割安）
print(f"日本の対ドル指数 USD_raw: {jp['USD_raw']:.4f} "
      f"(＝米国より約 {abs(jp['USD_raw'])*100:.0f}% 割安)")

# 日本の順位（安い方から）
asc = snap.sort_values("dollar_price").reset_index(drop=True)
jp_rank_cheap = asc.index[asc["iso_a3"] == "JPN"][0] + 1
print(f"日本はドル換算価格の安い順で {jp_rank_cheap}位 / {len(snap)}カ国")

# 主要国の割安・割高度（USD_raw）
majors = ["CHE", "USA", "GBR", "JPN", "CHN", "KOR", "TWN"]
print("\n=== 主要国の対ドル割安・割高度（USD_raw, %）===")
for code in majors:
    row = snap[snap["iso_a3"] == code]
    if not row.empty:
        r = row.iloc[0]
        print(f"  {r['name']:<14} {r['USD_raw']*100:+6.1f}%  "
              f"(${r['dollar_price']:.2f})")

# --- 作図1: 割安・割高度の横棒ランキング（白黒・ハッチで正負を区別）---
plot_df = snap[snap["iso_a3"].isin(
    ["CHE", "NOR", "USA", "EUZ", "GBR", "CAN", "AUS", "KOR",
     "CHN", "JPN", "TWN", "THA", "EGY"])].copy()
plot_df = plot_df.sort_values("USD_raw")
fig, ax = plt.subplots(figsize=(10, 6))
colors = ["white" if v < 0 else "dimgray" for v in plot_df["USD_raw"]]
hatches = ["//" if v < 0 else "" for v in plot_df["USD_raw"]]
bars = ax.barh(plot_df["name"], plot_df["USD_raw"] * 100,
               color=colors, edgecolor="black")
for bar, h in zip(bars, hatches):
    bar.set_hatch(h)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("対ドル割安・割高度（%）　左＝割安 / 右＝割高")
ax.set_title(f"ビッグマック指数による主要国の割安・割高度（{latest.date()}）")
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG_BAR, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_BAR)}")

# --- 作図2: 日本のドル換算価格の推移（「安い日本」の時系列）---
jp_ts = df[df["iso_a3"] == "JPN"].sort_values("date")
us_ts = df[df["iso_a3"] == "USA"].sort_values("date")
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.plot(jp_ts["date"], jp_ts["dollar_price"], color="black",
         linewidth=1.5, marker="o", markersize=4, label="日本")
ax2.plot(us_ts["date"], us_ts["dollar_price"], color="black",
         linewidth=1.5, linestyle="--", marker="s", markersize=4,
         label="米国")
ax2.set_xlabel("年")
ax2.set_ylabel("ビッグマックのドル換算価格（$）")
ax2.set_title("日本と米国のビッグマック価格（ドル換算）の推移")
ax2.legend(loc="upper left")
ax2.grid(axis="y", linestyle="--", alpha=0.4)
fig2.tight_layout()
fig2.savefig(IMG_JP, dpi=200)
print(f"保存: {os.path.relpath(IMG_JP)}")

# 日本の最初期と直近の比較
jp_first = jp_ts.iloc[0]
jp_last = jp_ts.iloc[-1]
print(f"\n日本のドル換算価格: {jp_first['date'].date()} ${jp_first['dollar_price']:.2f}"
      f" -> {jp_last['date'].date()} ${jp_last['dollar_price']:.2f}")

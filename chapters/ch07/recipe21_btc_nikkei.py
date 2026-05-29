"""Recipe 21: ビットコインと日経平均は連動しているか.

「リスク資産はみんな同じ方向に動く」「ビットコインと株は連動している」
という体感を、日次リターンの相関で検証する。価格そのものを比べると
水準やトレンドに引きずられて見かけ上似て見えるため、前日比リターン
（変化率）に変換してから相関を取るのがポイント。さらに相関は時期に
よって変わるので、ローリング相関で「連動が強まる時期/弱まる時期」も見る。

データ出典（いずれも API キー不要・FRED 公開CSV）:
  ビットコイン価格（USD）: FRED CBBTCUSD
    https://fred.stlouisfed.org/series/CBBTCUSD
  日経平均株価: FRED NIKKEI225
    https://fred.stlouisfed.org/series/NIKKEI225
両方を日次の終値で取得し、共通営業日に揃えてから日次リターンを計算する。
"""

import os
import sys

import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe21_btc_nikkei.csv")
IMG_SC = os.path.join(IMG_DIR, "recipe21_btc_nikkei_scatter.png")
IMG_RL = os.path.join(IMG_DIR, "recipe21_btc_nikkei_rolling.png")

BTC_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CBBTCUSD"
NK_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NIKKEI225"


def fetch_fred(url, col):
    """FRED 公開CSV から1系列を取得する。"""
    df = pd.read_csv(url, na_values=["."])
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.dropna(subset=[col]).rename(
        columns={"observation_date": "date", col: col.lower()})
    return df[["date", col.lower()]]


def build():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, parse_dates=["date"])
    btc = fetch_fred(BTC_URL, "CBBTCUSD")
    nk = fetch_fred(NK_URL, "NIKKEI225")
    # 共通営業日に揃える（両方に終値がある日だけ残す = inner join）
    df = btc.merge(nk, on="date", how="inner").sort_values("date")
    df.to_csv(CACHE, index=False)
    return df


df = build()
df = df.reset_index(drop=True)

# 日次リターン（前日比変化率）に変換してから相関を取る
df["btc_ret"] = df["cbbtcusd"].pct_change()
df["nk_ret"] = df["nikkei225"].pct_change()
ret = df.dropna(subset=["btc_ret", "nk_ret"]).reset_index(drop=True)

start = df["date"].min().date()
end = df["date"].max().date()
print("=== ビットコインと日経平均の日次リターン相関 ===")
print(f"対象期間: {start} 〜 {end}（共通営業日 {len(ret)} 日）")

r_price, p_price = stats.pearsonr(df["cbbtcusd"], df["nikkei225"])
r_ret, p_ret = stats.pearsonr(ret["btc_ret"], ret["nk_ret"])
print(f"価格水準どうしの相関 r={r_price:.3f} (p={p_price:.2e})")
print(f"日次リターンの相関   r={r_ret:.3f} (p={p_ret:.2e})")

# 年ごとのリターン相関（連動の強さが年で変わるか）
ret["year"] = ret["date"].dt.year
print("\n年ごとの日次リターン相関:")
for y, g in ret.groupby("year"):
    if len(g) >= 100:
        ry, _ = stats.pearsonr(g["btc_ret"], g["nk_ret"])
        print(f"  {y}: r={ry:+.3f} (n={len(g)})")

# --- 作図1: 日次リターンの散布図 ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(ret["nk_ret"] * 100, ret["btc_ret"] * 100,
           color="black", s=8, alpha=0.3)
ax.axhline(0, color="gray", linewidth=0.8)
ax.axvline(0, color="gray", linewidth=0.8)
ax.set_xlabel("日経平均の日次リターン（％）")
ax.set_ylabel("ビットコインの日次リターン（％）")
ax.set_title(f"日次リターンの関係（r={r_ret:.2f}・{start.year}-{end.year}）")
ax.grid(linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG_SC, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_SC)}")

# --- 作図2: 90営業日ローリング相関 ---
window = 90
roll = ret["btc_ret"].rolling(window).corr(ret["nk_ret"])
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.plot(ret["date"], roll, color="black", linewidth=1.0)
ax2.axhline(0, color="gray", linestyle=":", linewidth=1.0)
ax2.set_xlabel("年")
ax2.set_ylabel(f"{window}営業日ローリング相関")
ax2.set_title("ビットコインと日経のリターン相関は時期で変わる")
ax2.grid(linestyle="--", alpha=0.3)
print(f"ローリング相関の範囲: {roll.min():.2f} 〜 {roll.max():.2f}")
fig2.tight_layout()
fig2.savefig(IMG_RL, dpi=200)
print(f"保存: {os.path.relpath(IMG_RL)}")

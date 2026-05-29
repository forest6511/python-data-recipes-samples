"""Recipe 22: 日経平均は米大統領選の年に上がるか.

「大統領選の年は株が上がる」という相場の経験則（プレジデンシャル・
サイクル）が、日本の日経平均にも当てはまるかを検証する。米大統領選は
4年ごと（2024, 2020, 2016, ...）。1年を「選挙年・選挙翌年・中間選挙年・
選挙前年」の4局面に分け、日経平均の年間リターン（年初→年末の変化率）を
局面ごとに平均して比べる。サンプル年数が少ないため、平均の差だけでなく
分布のばらつき・勝率も併記し、断定しすぎないのがポイント。

データ出典: 日経平均株価 FRED NIKKEI225（API キー不要・公開CSV）
  https://fred.stlouisfed.org/series/NIKKEI225
日次終値から各年の年初・年末終値を取り、年間リターンを計算する。
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe22_nikkei.csv")
IMG = os.path.join(IMG_DIR, "recipe22_nikkei_election.png")

NK_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NIKKEI225"

# 米大統領選の4年サイクルにおける各局面のラベル
# 選挙年: 2024,2020,2016,... → year % 4 == 0
PHASE = {
    0: "選挙年",
    1: "選挙翌年",
    2: "中間選挙年",
    3: "選挙前年",
}


def build():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, parse_dates=["date"])
    df = pd.read_csv(NK_URL, na_values=["."])
    df = df.rename(columns={"observation_date": "date", "NIKKEI225": "close"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"]).sort_values("date")
    df.to_csv(CACHE, index=False)
    return df


df = build()
df["year"] = df["date"].dt.year

# 各年の年初（最初の営業日）・年末（最後の営業日）終値から年間リターン
rows = []
for y, g in df.groupby("year"):
    g = g.sort_values("date")
    first = g.iloc[0]["close"]
    last = g.iloc[-1]["close"]
    ret = (last / first - 1) * 100
    rows.append({"year": int(y), "ret": ret, "ndays": len(g)})
ann = pd.DataFrame(rows)
# 年間を通したデータがない端の年を除く
ann = ann[ann["ndays"] >= 200].reset_index(drop=True)
ann["phase"] = ann["year"].apply(lambda y: PHASE[y % 4])

start_y = int(ann["year"].min())
end_y = int(ann["year"].max())
print("=== 日経平均の年間リターンと米大統領選サイクル ===")
print(f"対象年: {start_y}-{end_y}（{len(ann)}年分）")
print(f"全期間の年間リターン平均: {ann['ret'].mean():+.2f}%  "
      f"中央値: {ann['ret'].median():+.2f}%")

order = ["選挙年", "選挙翌年", "中間選挙年", "選挙前年"]
print("\n局面ごとの年間リターン:")
for ph in order:
    g = ann[ann["phase"] == ph]["ret"]
    win = (g > 0).mean() * 100
    print(f"  {ph:　<5s} n={len(g):2d}  "
          f"平均{g.mean():+6.2f}%  中央値{g.median():+6.2f}%  "
          f"標準偏差{g.std():5.1f}  上昇年率{win:4.0f}%")

# --- 作図: 局面ごとの年間リターン箱ひげ + 平均点 ---
fig, ax = plt.subplots(figsize=(10, 6))
data = [ann[ann["phase"] == ph]["ret"].values for ph in order]
ax.boxplot(data, tick_labels=order, showmeans=True,
           meanprops={"marker": "D", "markerfacecolor": "black",
                      "markeredgecolor": "black"},
           medianprops={"color": "black"},
           boxprops={"color": "black"},
           whiskerprops={"color": "black"},
           capprops={"color": "black"})
ax.axhline(0, color="gray", linestyle=":", linewidth=1.0)
for i, d in enumerate(data):
    ax.annotate(f"平均{np.mean(d):+.1f}%", (i + 1, np.mean(d)),
                textcoords="offset points", xytext=(8, 0), fontsize=9)
ax.set_ylabel("日経平均の年間リターン（％）")
ax.set_title(f"米大統領選サイクル別の日経年間リターン（{start_y}-{end_y}・◆＝平均）")
ax.grid(axis="y", linestyle="--", alpha=0.3)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

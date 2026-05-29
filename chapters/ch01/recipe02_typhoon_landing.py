"""Recipe 02: 台風の上陸数は増えているか.

気象庁「台風の上陸数（年別）」(1951-) から日本への年間上陸数を取得し、
長期トレンドを線形回帰で分析する。

データ出典: 気象庁 台風の上陸数
  https://www.data.jma.go.jp/yoho/typhoon/statistics/landing/landing.html
API キー不要。
"""

import io
import os
import sys

import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe02_typhoon_landing.csv")
IMG = os.path.join(os.path.dirname(__file__), "images", "recipe02_typhoon_landing.png")
URL = "https://www.data.jma.go.jp/yoho/typhoon/statistics/landing/landing.html"


def fetch_landing():
    """年別の台風上陸数（年間合計）を {年: 上陸数} の DataFrame で返す。"""
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)

    r = requests.get(URL, timeout=30)
    r.encoding = "utf-8"
    # 当年(集計途中)と過去実績の2テーブルがある。過去実績側を使う
    tables = pd.read_html(io.StringIO(r.text))
    tbl = max(tables, key=len)  # 行数の多い方が過去実績

    df = tbl[["年", "年間"]].copy()
    # 4桁年のみ残す（途中に混じるヘッダ行「年」を除去）
    df = df[df["年"].astype(str).str.fullmatch(r"\d{4}")]
    df["year"] = df["年"].astype(int)
    df["landings"] = pd.to_numeric(df["年間"], errors="coerce").fillna(0).astype(int)
    df = df[["year", "landings"]].sort_values("year").reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


def main():
    df = fetch_landing()
    y0, y1 = int(df["year"].min()), int(df["year"].max())

    reg = stats.linregress(df["year"], df["landings"])

    # 10年移動平均（年ごとのばらつきが大きいため傾向を見やすくする）
    df["ma10"] = df["landings"].rolling(10, center=True).mean()

    print("=== Recipe 02: 台風の上陸数 ===")
    print(f"期間: {y0}-{y1}  年数: {len(df)}")
    print(f"年間上陸数 平均: {df['landings'].mean():.2f}")
    print(f"最多: {df['landings'].max()} 年 "
          f"({df.loc[df['landings'].idxmax(), 'year']})")
    print(f"最少: {df['landings'].min()}")
    print(f"回帰の傾き slope = {reg.slope:.4f} 個/年")
    print(f"p値 = {reg.pvalue:.5g}  r = {reg.rvalue:.4f}  r^2 = {reg.rvalue**2:.4f}")
    first10 = df.head(10)["landings"].mean()
    last10 = df.tail(10)["landings"].mean()
    print(f"最初の10年平均 = {first10:.2f}  直近10年平均 = {last10:.2f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        df["year"], df["landings"], color="lightgray",
        edgecolor="black", linewidth=0.4, label="年間上陸数",
    )
    ax.plot(
        df["year"], df["ma10"], color="black", linestyle="-",
        linewidth=2, label="10年移動平均",
    )
    ax.plot(
        df["year"], reg.intercept + reg.slope * df["year"],
        color="black", linestyle="--", linewidth=1.5,
        label=f"回帰直線（{reg.slope:+.3f} 個/年）",
    )
    ax.set_title(f"日本への台風の年間上陸数（{y0}-{y1}）")
    ax.set_xlabel("年")
    ax.set_ylabel("上陸数（個）")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(IMG), exist_ok=True)
    fig.savefig(IMG, dpi=200)
    print(f"saved: {IMG}")


if __name__ == "__main__":
    main()

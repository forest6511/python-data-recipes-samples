"""Recipe 04: ゲリラ豪雨は増えているか.

気象庁「全国（アメダス）の1時間降水量50mm以上の年間発生回数」(1976-)を取得し、
短時間強雨（いわゆるゲリラ豪雨）の長期トレンドを線形回帰で分析する。

データ出典: 気象庁 大雨や猛暑日など（極端現象）の長期変化
  https://www.data.jma.go.jp/cpdinfo/extreme/extreme_p.html
  CSV: https://www.data.jma.go.jp/cpdinfo/extreme/csv/amdhour50mm_p.csv
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
CACHE = os.path.join(DATA_DIR, "recipe04_heavy_rain_50mm.csv")
IMG = os.path.join(os.path.dirname(__file__), "images", "recipe04_heavy_rain.png")
URL = "https://www.data.jma.go.jp/cpdinfo/extreme/csv/amdhour50mm_p.csv"


def fetch_heavy_rain():
    """1時間降水量50mm以上の年間発生回数を {year, count} で返す。"""
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)

    r = requests.get(URL, timeout=30)
    # 気象庁の極端現象 CSV は Shift_JIS
    df = pd.read_csv(io.BytesIO(r.content), encoding="shift_jis")
    df.columns = ["year", "count"]
    df = df.dropna().astype({"year": int, "count": int})
    df = df.sort_values("year").reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


def main():
    df = fetch_heavy_rain()
    y0, y1 = int(df["year"].min()), int(df["year"].max())

    reg = stats.linregress(df["year"], df["count"])
    per_decade = reg.slope * 10

    # 5年移動平均（気象庁の公表図にならう）
    df["ma5"] = df["count"].rolling(5, center=True).mean()

    first10 = df[df["year"] <= y0 + 9]["count"].mean()
    last10 = df[df["year"] >= y1 - 9]["count"].mean()

    print("=== Recipe 04: ゲリラ豪雨（1時間50mm以上） ===")
    print(f"期間: {y0}-{y1}  年数: {len(df)}")
    print(f"年間発生回数 全期間平均: {df['count'].mean():.1f} 回")
    print(f"回帰の傾き slope = {reg.slope:.3f} 回/年 "
          f"(= {per_decade:.1f} 回/10年)")
    print(f"p値 = {reg.pvalue:.5g}  r = {reg.rvalue:.4f}  r^2 = {reg.rvalue**2:.4f}")
    print(f"最初の10年({y0}-{y0 + 9})平均 = {first10:.1f} 回")
    print(f"直近10年({y1 - 9}-{y1})平均 = {last10:.1f} 回")
    print(f"倍率 = {last10 / first10:.2f} 倍")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        df["year"], df["count"], color="lightgray",
        edgecolor="black", linewidth=0.4, label="年間発生回数",
    )
    ax.plot(
        df["year"], df["ma5"], color="black", linestyle="-",
        linewidth=2, label="5年移動平均",
    )
    ax.plot(
        df["year"], reg.intercept + reg.slope * df["year"],
        color="black", linestyle="--", linewidth=1.5,
        label=f"回帰直線（{per_decade:+.1f} 回/10年）",
    )
    ax.set_title(
        f"全国（アメダス）1時間降水量50mm以上の年間発生回数（{y0}-{y1}）"
    )
    ax.set_xlabel("年")
    ax.set_ylabel("発生回数（回）")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(IMG), exist_ok=True)
    fig.savefig(IMG, dpi=200)
    print(f"saved: {IMG}")


if __name__ == "__main__":
    main()

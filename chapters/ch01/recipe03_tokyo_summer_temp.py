"""Recipe 03: 東京の夏は暑くなっているか.

気象庁「過去の気象データ」から東京の月別平均気温(1875-)を取得し、
夏(7月・8月)の平均気温の長期トレンドを線形回帰で分析する。

データ出典: 気象庁 過去の気象データ（東京: prec_no=44, block_no=47662）
  https://www.data.jma.go.jp/obd/stats/etrn/view/monthly_s3.php
API キー不要。
"""

import io
import os
import re
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
CACHE = os.path.join(DATA_DIR, "recipe03_tokyo_temp.csv")
IMG = os.path.join(os.path.dirname(__file__), "images", "recipe03_tokyo_summer_temp.png")
URL = (
    "https://www.data.jma.go.jp/obd/stats/etrn/view/monthly_s3.php"
    "?prec_no=44&block_no=47662&year=&month=&day=&view="
)


def _clean(val):
    """'26.0 )' や '17.0 ]' のような注釈記号を除いて float にする。"""
    if pd.isna(val):
        return None
    s = re.sub(r"[^\d.\-]", "", str(val))
    return float(s) if s else None


def fetch_tokyo_temp():
    """東京の年・7月・8月平均気温の DataFrame を返す。"""
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)

    r = requests.get(URL, timeout=30)
    r.encoding = "utf-8"
    tbl = pd.read_html(io.StringIO(r.text))[0]

    df = tbl[["年", "7月", "8月"]].copy()
    df = df[df["年"].astype(str).str.fullmatch(r"\d{4}")]
    df["year"] = df["年"].astype(int)
    df["jul"] = df["7月"].map(_clean)
    df["aug"] = df["8月"].map(_clean)
    # 7月・8月が揃う年のみ（2026年など欠測年を除外）
    df = df.dropna(subset=["jul", "aug"])
    df["summer"] = (df["jul"] + df["aug"]) / 2
    df = df[["year", "jul", "aug", "summer"]].sort_values("year")
    df = df.reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


def main():
    df = fetch_tokyo_temp()
    y0, y1 = int(df["year"].min()), int(df["year"].max())

    reg = stats.linregress(df["year"], df["summer"])
    total_rise = reg.slope * (y1 - y0)
    per_century = reg.slope * 100

    first30 = df[df["year"] <= y0 + 29]["summer"].mean()
    last30 = df[df["year"] >= y1 - 29]["summer"].mean()

    print("=== Recipe 03: 東京の夏の気温 ===")
    print(f"期間: {y0}-{y1}  年数: {len(df)}")
    print(f"夏(7-8月)平均気温 全期間平均: {df['summer'].mean():.2f}℃")
    print(f"回帰の傾き slope = {reg.slope:.4f} ℃/年 "
          f"(= {per_century:.2f} ℃/100年)")
    print(f"p値 = {reg.pvalue:.5g}  r = {reg.rvalue:.4f}  r^2 = {reg.rvalue**2:.4f}")
    print(f"{y0}->{y1} の累積上昇 = {total_rise:.2f}℃")
    print(f"最初の30年平均 = {first30:.2f}℃  直近30年平均 = {last30:.2f}℃ "
          f"(差 {last30 - first30:+.2f}℃)")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        df["year"], df["summer"], color="black", linestyle="-",
        linewidth=0.8, marker="o", markersize=2.5, label="夏(7-8月)平均気温",
    )
    ax.plot(
        df["year"], reg.intercept + reg.slope * df["year"],
        color="black", linestyle="--", linewidth=2,
        label=f"回帰直線（{per_century:+.2f} ℃/100年）",
    )
    ax.set_title(f"東京の夏（7-8月）平均気温の推移（{y0}-{y1}）")
    ax.set_xlabel("年")
    ax.set_ylabel("夏の平均気温（℃）")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(IMG), exist_ok=True)
    fig.savefig(IMG, dpi=200)
    print(f"saved: {IMG}")


if __name__ == "__main__":
    main()

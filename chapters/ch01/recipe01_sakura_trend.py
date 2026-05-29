"""Recipe 01: 桜の開花日は早まっているか.

気象庁「過去のさくらの開花日」(1961-2025) から東京の開花日を取得し、
1月1日からの通算日数に変換して長期トレンドを線形回帰で分析する。

データ出典: 気象庁 過去のさくらの開花日
  https://www.data.jma.go.jp/sakura/data/sakura003_07.html ほか
API キー不要。
"""

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

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe01_sakura_tokyo.csv")
IMG = os.path.join(os.path.dirname(__file__), "images", "recipe01_sakura_trend.png")
STATION = "東京"
# 003_01(1961-70) ～ 003_07(2021-25) の年代別ページ
PAGES = [f"sakura003_0{n}.html" for n in range(1, 8)]
BASE = "https://www.data.jma.go.jp/sakura/data/"


def _parse_pre(html):
    """<pre> 内の固定長テキストから {年: '月 日'} を東京分だけ抜き出す。"""
    m = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.S | re.I)
    text = re.sub(r"<[^>]+>", "", m.group(1))
    lines = text.splitlines()
    # ヘッダ行から対象年（西暦4桁）を順に取得
    header = next(l for l in lines if re.search(r"(19|20)\d\d", l))
    years = [int(y) for y in re.findall(r"(19\d\d|20\d\d)", header)]
    # 地点名が「東京」で始まる行を探す
    row = next(l for l in lines if l.startswith(STATION))
    # 「*」や記号を除き、月 日 ペア（または「-」）を抽出
    body = row[len(STATION):]
    tokens = body.replace("*", " ").split()
    # 平年値・代替種目を落とすため、年数ぶんだけ「月 日」ペアを取る
    result = {}
    i = 0
    yi = 0
    while i < len(tokens) and yi < len(years):
        tok = tokens[i]
        if tok == "-":
            result[years[yi]] = None
            i += 1
            yi += 1
        elif tok.isdigit():
            month = int(tok)
            day = int(tokens[i + 1])
            result[years[yi]] = (month, day)
            i += 2
            yi += 1
        else:
            i += 1
    return result


def fetch_sakura_tokyo():
    """全年代ページを取得して東京の {年: (月, 日)} を結合し DataFrame で返す。"""
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)

    records = {}
    for page in PAGES:
        r = requests.get(BASE + page, timeout=30)
        r.encoding = "utf-8"
        records.update(_parse_pre(r.text))

    rows = []
    for year, md in sorted(records.items()):
        if md is None:
            continue
        month, day = md
        rows.append({"year": year, "month": month, "day": day})
    df = pd.DataFrame(rows)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


def main():
    df = fetch_sakura_tokyo()

    # 月 日 → その年の1月1日からの通算日数（day-of-year）に変換
    df["doy"] = pd.to_datetime(
        df["year"].astype(str)
        + "-"
        + df["month"].astype(str)
        + "-"
        + df["day"].astype(str)
    ).dt.dayofyear

    df = df.dropna(subset=["doy"]).sort_values("year").reset_index(drop=True)

    y0, y1 = int(df["year"].min()), int(df["year"].max())
    n = len(df)

    # 線形回帰: 開花日(doy) を 年 で説明
    reg = stats.linregress(df["year"], df["doy"])
    slope = reg.slope            # 日/年（負なら早まり）
    total_shift = slope * (y1 - y0)

    print("=== Recipe 01: 桜の開花日 ===")
    print(f"対象: {STATION}  期間: {y0}-{y1}  観測年数: {n}")
    print(f"開花日の平均: {df['doy'].mean():.1f} (1月1日からの日数)")
    print(f"最早: {df['doy'].min()} 最遅: {df['doy'].max()}")
    print(f"回帰の傾き slope = {slope:.4f} 日/年")
    print(f"p値 = {reg.pvalue:.5g}  r = {reg.rvalue:.4f}  r^2 = {reg.rvalue**2:.4f}")
    print(f"{y0}->{y1} の累積変化 = {total_shift:.1f} 日")

    # 作図（白黒印刷対応: マーカー + 実線回帰 + 破線で系列を区別）
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        df["year"], df["doy"], s=28, color="black",
        marker="o", label="開花日（実測）",
    )
    xs = df["year"]
    ax.plot(
        xs, reg.intercept + reg.slope * xs,
        color="black", linestyle="--", linewidth=2,
        label=f"回帰直線（{slope:.3f} 日/年）",
    )
    ax.set_title(f"東京の桜の開花日の推移（{y0}-{y1}）")
    ax.set_xlabel("年")
    ax.set_ylabel("開花日（1月1日からの通算日数）")
    ax.invert_yaxis()  # 上が「早い開花」になるよう反転
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(IMG), exist_ok=True)
    fig.savefig(IMG, dpi=200)
    print(f"saved: {IMG}")


if __name__ == "__main__":
    main()

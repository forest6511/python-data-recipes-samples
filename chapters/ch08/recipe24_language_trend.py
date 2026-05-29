"""Recipe 24: プログラミング言語の人気推移.

プログラミング言語の「人気」を、Stack Overflow に新しく投稿された質問数で
近似する。主要言語ごとに、各年に投稿された質問数を Stack Exchange API
（Stack Overflow）から取得し、2009年から2024年までの推移を比較する。

データ出典（API キー不要）:
  Stack Exchange API v2.3（Stack Overflow サイト, /questions）
    https://api.stackexchange.com/2.3/questions
  言語タグごとに fromdate/todate を1年単位で指定し、その年に作成された
  質問の総数（filter=total）を集計する。

caveat:
  - 質問数は「人気」そのものではなく、つまずきや学習者の多さも反映する。
  - 2022年以降の全体的な減少には、生成AI（ChatGPT 等）の普及で Stack
    Overflow への質問自体が減った影響が含まれる。
"""

import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe24_so_questions.csv")
IMG = os.path.join(IMG_DIR, "recipe24_language_trend.png")

API = "https://api.stackexchange.com/2.3/questions"
LANGS = {
    "Python": "python", "JavaScript": "javascript",
    "Java": "java", "C#": "c#", "C++": "c++",
    "TypeScript": "typescript", "Go": "go", "Rust": "rust",
}
YEARS = list(range(2009, 2025))  # 2009-2024（完全な年のみ）


def _count(tag, year):
    """その年に作成された tag 付き質問の総数を返す。"""
    fr = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    to = int(datetime(year, 12, 31, 23, 59, 59,
                      tzinfo=timezone.utc).timestamp())
    params = {"site": "stackoverflow", "tagged": tag,
              "fromdate": fr, "todate": to,
              "filter": "total", "pagesize": 1}
    return int(requests.get(API, params=params, timeout=30).json()["total"])


def load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    rows = []
    for name, tag in LANGS.items():
        for y in YEARS:
            rows.append({"lang": name, "tag": tag, "year": y,
                         "questions": _count(tag, y)})
            time.sleep(0.3)  # API への配慮
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    return df


os.makedirs(IMG_DIR, exist_ok=True)
df = load()
wide = df.pivot(index="year", columns="lang", values="questions")
wide = wide[list(LANGS.keys())].sort_index()

print("=== Stack Overflow 年間質問数（言語別）===")
print(wide.to_string())

print("\n=== 各言語のピーク年 ===")
for lang in LANGS:
    s = wide[lang]
    py = int(s.idxmax())
    print(f"{lang}: ピーク {py}年 {int(s.loc[py]):,}件  "
          f"2024年 {int(s.loc[2024]):,}件")

total = wide.sum(axis=1)
pk = int(total.idxmax())
print(f"\n2009年首位: {wide.loc[2009].idxmax()} "
      f"({int(wide.loc[2009].max()):,}件)")
print(f"2024年首位: {wide.loc[2024].idxmax()} "
      f"({int(wide.loc[2024].max()):,}件)")
print(f"8言語合計ピーク: {pk}年 {int(total.loc[pk]):,}件")
print(f"8言語合計 2024年: {int(total.loc[2024]):,}件 "
      f"(ピーク比 {total.loc[2024] / total.loc[pk] * 100:.1f}%)")

# --- 作図: 主要言語の質問数推移（白黒対応・線種とマーカーで区別）---
fig, ax = plt.subplots(figsize=(11, 6.5))
styles = [
    ("Python", "-", "o"), ("JavaScript", "--", "s"),
    ("Java", "-.", "^"), ("C#", ":", "D"),
    ("C++", "-", "v"), ("TypeScript", "--", "P"),
    ("Go", "-.", "X"), ("Rust", ":", "*"),
]
for lang, ls, mk in styles:
    ax.plot(wide.index, wide[lang], color="black", linewidth=1.3,
            linestyle=ls, marker=mk, markersize=5, label=lang)
ax.set_xlabel("年")
ax.set_ylabel("Stack Overflow 年間質問数（件）")
ax.set_title("主要プログラミング言語の質問数推移（Stack Overflow, 2009-2024）")
ax.legend(loc="upper right", ncol=2, fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

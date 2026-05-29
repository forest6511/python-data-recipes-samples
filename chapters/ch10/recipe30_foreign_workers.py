"""Recipe 30: 外国人労働者はどの都道府県に多いか.

都道府県別の外国人労働者数をランキングし、全国に占める構成比（シェア）と
上位への集中度を見る。絶対数のランキングだけでなく「上位N都道府県で全体の
何パーセントか」という偏りに注目する。

データ出典:
  厚生労働省「外国人雇用状況」の届出状況（令和6年10月末時点）
    別表２ 都道府県別外国人雇用事業所数及び外国人労働者数
    https://www.mhlw.go.jp/content/11655000/001389472.xlsx
    API キー不要（Excel を pandas.read_excel で取得）

caveat:
  - 外国人雇用状況届出制度に基づく事業所からの届出の集計で、届出義務のない
    一部（特別永住者や外交・公用など）は含まれない。
  - 労働者数の絶対数は人口の多い都道府県ほど大きくなりやすい。
"""

import io
import os
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe30_foreign_workers.csv")
IMG = os.path.join(IMG_DIR, "recipe30_foreign_workers.png")

URL = "https://www.mhlw.go.jp/content/11655000/001389472.xlsx"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    content = requests.get(URL, headers=HEADERS, timeout=60).content
    raw = pd.read_excel(io.BytesIO(content), "別表２", header=None)
    body = raw.iloc[6:].copy()  # 6行目までは見出しと全国計
    df = pd.DataFrame({
        "pref": body.iloc[:, 1].astype(str).str.strip(),
        "workers": pd.to_numeric(body.iloc[:, 6], errors="coerce"),
    }).dropna(subset=["workers"])
    df = df[df["pref"].str.len() > 0].reset_index(drop=True)
    df["workers"] = df["workers"].astype(int)
    df.to_csv(CACHE, index=False)
    return df


df = load()
total = df["workers"].sum()
print(f"=== 都道府県数: {len(df)} / 外国人労働者 合計: {total:,}人 ===")

df["share"] = df["workers"] / total * 100
df = df.sort_values("workers", ascending=False).reset_index(drop=True)
df["rank"] = df.index + 1

print("\n=== 外国人労働者数 上位10都道府県 ===")
for _, r in df.head(10).iterrows():
    print(f"  {r['rank']:>2}位 {r['pref']:<6} {r['workers']:>9,}人  "
          f"（シェア {r['share']:4.1f}%）")

top1 = df.iloc[0]
print(f"\n1位 {top1['pref']} だけで全国の {top1['share']:.1f}%")
print(f"上位5で {df.head(5)['share'].sum():.1f}%、"
      f"上位10で {df.head(10)['share'].sum():.1f}%")
print(f"1位 {top1['pref']} は最下位 {df.iloc[-1]['pref']} の "
      f"{top1['workers'] / df.iloc[-1]['workers']:.0f}倍")

# --- 作図: 上位15都道府県の横棒グラフ ---
os.makedirs(IMG_DIR, exist_ok=True)
top15 = df.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(top15["pref"], top15["workers"] / 10000, color="0.5",
        edgecolor="black")
for y, (w, s) in enumerate(zip(top15["workers"], top15["share"])):
    ax.text(w / 10000 + 1, y, f"{s:.1f}%", va="center", fontsize=9)
ax.set_xlabel("外国人労働者数（万人）")
ax.set_title("都道府県別の外国人労働者数 上位15（令和6年10月末, 数値はシェア）")
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

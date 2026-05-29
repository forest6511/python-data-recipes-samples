"""Recipe 28: 再生回数が多いのは長い動画か、短い動画か.

日本で人気の動画を YouTube Data API から集め、動画の長さ（秒）と再生回数の
関係を見る。まず動画の長さの分布をヒストグラムで眺め、次に長さと再生回数の
相関、最後に長さ別の再生回数の中央値を比べる。偏った分布では平均より中央値
で見るのが基本、という点を体感する。

データ出典:
  YouTube Data API v3（videos: mostPopular チャート, regionCode=JP）
    https://www.googleapis.com/youtube/v3/videos
    API キー必要（YOUTUBE_API_KEY）。Google Cloud Console で無料発行し、
    この章のディレクトリの .env に YOUTUBE_API_KEY=... を書く（.gitignore 済）。

caveat:
  - これは「人気動画（mostPopular）」の標本であり、YouTube 全体を代表しない。
  - 再生回数は公開からの経過時間にも左右される。相関は因果ではない。
  - mostPopular チャートは時々刻々と変わるため、取得日時点のスナップショット。
"""

import os
import re
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from scipy import stats  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
API_KEY = os.environ["YOUTUBE_API_KEY"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
CACHE = os.path.join(DATA_DIR, "recipe28_youtube.csv")
IMG = os.path.join(IMG_DIR, "recipe28_youtube_duration.png")

API = "https://www.googleapis.com/youtube/v3/videos"
CATEGORIES = ["10", "20", "24", "25", "26", "28", "17"]


def _iso_to_seconds(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def fetch():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    rows = {}
    for cat in CATEGORIES:
        params = {"part": "snippet,contentDetails,statistics",
                  "chart": "mostPopular", "regionCode": "JP",
                  "videoCategoryId": cat, "maxResults": 50, "key": API_KEY}
        j = requests.get(API, params=params, timeout=30).json()
        for it in j.get("items", []):
            dur = _iso_to_seconds(it["contentDetails"]["duration"])
            views = it["statistics"].get("viewCount")
            if dur and views:
                rows[it["id"]] = {"video_id": it["id"], "category": cat,
                                  "duration_sec": dur, "views": int(views),
                                  "title": it["snippet"]["title"]}
    df = pd.DataFrame(rows.values())
    df.to_csv(CACHE, index=False)
    return df


df = fetch()
df = df[df["duration_sec"] <= 3 * 3600].reset_index(drop=True)
df["duration_min"] = df["duration_sec"] / 60

print(f"=== 収集した人気動画数: {len(df)} ===")
print(f"長さ 中央値 {df['duration_sec'].median():.0f}秒 "
      f"({df['duration_min'].median():.1f}分) / "
      f"平均 {df['duration_sec'].mean():.0f}秒 "
      f"({df['duration_min'].mean():.1f}分)")
print(f"1分未満の割合: {(df['duration_sec'] < 60).mean() * 100:.1f}%")

r, p = stats.pearsonr(df["duration_sec"], np.log10(df["views"]))
print(f"長さ vs log10(再生回数) r = {r:.3f} (p = {p:.3f})")

bins = [0, 60, 300, 600, 1200, 10800]
labels = ["〜1分", "1〜5分", "5〜10分", "10〜20分", "20分〜"]
df["len_band"] = pd.cut(df["duration_sec"], bins=bins, labels=labels,
                        right=False)
band = df.groupby("len_band", observed=True)["views"].median()
print("\n=== 長さ別の再生回数（中央値）===")
for name, v in band.items():
    print(f"  {name:<8} {v:>12,.0f} 回")

# --- 作図: 左=長さの分布ヒストグラム / 右=長さ別の再生回数中央値 ---
os.makedirs(IMG_DIR, exist_ok=True)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))
ax1.hist(df["duration_min"], bins=30, color="0.5", edgecolor="black")
ax1.axvline(df["duration_min"].median(), color="black", linestyle="--",
            linewidth=1.5,
            label=f"中央値 {df['duration_min'].median():.1f}分")
ax1.set_xlabel("動画の長さ（分）")
ax1.set_ylabel("動画数")
ax1.set_title("人気動画の長さの分布")
ax1.legend()
ax2.bar(range(len(band)), band.values, color="0.5", edgecolor="black")
ax2.set_xticks(range(len(band)))
ax2.set_xticklabels(band.index, rotation=30, ha="right")
ax2.set_ylabel("再生回数の中央値（回）")
ax2.set_title("動画の長さ別の再生回数（中央値）")
ax2.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

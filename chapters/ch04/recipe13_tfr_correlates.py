"""Recipe 13: 出生率と何が相関するか.

「合計特殊出生率（TFR）は、どんな指標と一緒に動いているのか」を
47都道府県の横断データ（2024年）で確かめる。婚姻率・離婚率・人口規模
など複数の指標とTFRの相関を計算し、相関の強い順に並べる。Recipe 12 に
続き「相関≠因果」を意識しながら、『出生率と最も連動する指標は何か』を探る。

データ出典:
  厚生労働省 人口動態調査 上巻 都道府県別にみた人口動態総覧（2024年）
  e-Stat statsDataId: 0003411562
  cat01: 00100 人口 / 00290 出生率 / 00300 合計特殊出生率
         00420 婚姻率 / 00430 離婚率
  政府統計の総合窓口 e-Stat API（appId が必要。環境変数 ESTAT_APP_ID）

事前準備: e-Stat (https://www.e-stat.go.jp/) で利用登録し appId を発行、
  このディレクトリに .env を置いて ESTAT_APP_ID=発行されたID と記述する。
"""

import os
import sys

import numpy as np
import pandas as pd
import requests
from scipy import stats
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import jp_font  # noqa: E402,F401  日本語フォント設定（import するだけで有効）

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe13_tfr_correlates.csv")
IMG_BAR = os.path.join(
    os.path.dirname(__file__), "images", "recipe13_corr_ranking.png"
)
IMG_SCAT = os.path.join(
    os.path.dirname(__file__), "images", "recipe13_tfr_scatter.png"
)

STATS_ID = "0003411562"
CAT = {
    "00100": "population",     # 人口
    "00290": "birth_rate",     # 出生率（人口千対）
    "00300": "tfr",            # 合計特殊出生率
    "00420": "marriage_rate",  # 婚姻率（人口千対）
    "00430": "divorce_rate",   # 離婚率（人口千対）
}
# 47都道府県のコード（00000=全国, 政令市再掲は別コードなので除外）
PREF_CODES = [f"{i:02d}000" for i in range(1, 48)]


def fetch_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("環境変数 ESTAT_APP_ID が未設定です")
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": STATS_ID,
        "cdCat01": ",".join(CAT.keys()),
        "cdArea": ",".join(PREF_CODES),
        "cdTime": "2024000000",
        "limit": 2000,
    }
    j = requests.get(url, params=params, timeout=60).json()
    info = j["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = info["DATA_INF"]["VALUE"]
    area_map = {}
    for c in info["CLASS_INF"]["CLASS_OBJ"]:
        if c["@id"] == "area":
            objs = c["CLASS"]
            objs = objs if isinstance(objs, list) else [objs]
            for o in objs:
                area_map[o["@code"]] = o["@name"]
    rows = []
    for v in vals:
        col = CAT.get(v.get("@cat01"))
        if not col:
            continue
        try:
            val = float(v["$"])
        except (TypeError, ValueError):
            continue
        rows.append({"pref": area_map.get(v["@area"], v["@area"]),
                     "metric": col, "value": val})
    long = pd.DataFrame(rows)
    df = long.pivot(index="pref", columns="metric",
                    values="value").reset_index()
    df.to_csv(CACHE, index=False)
    return df


df = fetch_data()
df = df.dropna(subset=["tfr"]).reset_index(drop=True)
# 人口規模は桁が大きいので対数を取る（大都市の影響を見るため）
df["log_population"] = np.log10(df["population"])

print(f"=== 都道府県別 合計特殊出生率（2024年, n={len(df)}）===")
top = df.sort_values("tfr", ascending=False)
print("--- TFR 上位5県 ---")
for _, r in top.head(5).iterrows():
    print(f"  {r['pref']:<6} {r['tfr']:.2f}")
print("--- TFR 下位5県 ---")
for _, r in top.tail(5).iterrows():
    print(f"  {r['pref']:<6} {r['tfr']:.2f}")

# TFR と各指標の相関を計算
factors = {
    "marriage_rate": "婚姻率",
    "birth_rate": "出生率",
    "divorce_rate": "離婚率",
    "log_population": "人口規模（対数）",
}
print("\n=== TFR と各指標の相関（47都道府県横断, 2024年）===")
results = []
for col, label in factors.items():
    sub = df.dropna(subset=[col, "tfr"])
    r, p = stats.pearsonr(sub[col], sub["tfr"])
    results.append((label, col, r, p))
    print(f"  {label:<14} r={r:+.3f}  (p={p:.3f}, n={len(sub)})")

results.sort(key=lambda x: abs(x[2]), reverse=True)
print(f"\nTFRと最も強く相関する指標: {results[0][0]} (r={results[0][2]:+.3f})")

# --- 作図1: TFRと各指標の相関係数（横棒, 絶対値の大きい順）---
labels = [x[0] for x in results]
rvals = [x[2] for x in results]
fig, ax = plt.subplots(figsize=(10, 6))
colors = ["dimgray" if r >= 0 else "white" for r in rvals]
hatches = ["" if r >= 0 else "//" for r in rvals]
bars = ax.barh(labels[::-1], rvals[::-1], color=colors[::-1],
               edgecolor="black")
for bar, h in zip(bars, hatches[::-1]):
    bar.set_hatch(h)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlim(-1, 1)
ax.set_xlabel("合計特殊出生率との相関係数 r（正=同方向, 負=逆方向）")
ax.set_title("都道府県別・出生率と各指標の相関（2024年, 47都道府県）")
ax.grid(axis="x", linestyle="--", alpha=0.4)
for i, r in enumerate(rvals[::-1]):
    ax.text(r + (0.03 if r >= 0 else -0.03), i, f"{r:+.3f}",
            va="center", ha="left" if r >= 0 else "right")
fig.tight_layout()
fig.savefig(IMG_BAR, dpi=200)
print(f"\n保存: {os.path.relpath(IMG_BAR)}")

# --- 作図2: TFR vs 最も強い相関の指標の散布図 ---
# 軸ラベル（指標ごとに正しい単位を出す）
AXIS_LABEL = {
    "marriage_rate": "婚姻率（人口千対）",
    "birth_rate": "出生率（人口千対）",
    "divorce_rate": "離婚率（人口千対）",
    "log_population": "人口規模（常用対数, 大きいほど大都市）",
}
strongest_col = results[0][1]
strongest_label = results[0][0]
sub = df.dropna(subset=[strongest_col, "tfr"])
r, _ = stats.pearsonr(sub[strongest_col], sub["tfr"])
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.scatter(sub[strongest_col], sub["tfr"], color="dimgray",
            edgecolor="black", s=50, zorder=3)
# 回帰直線
slope, intercept, _, _, _ = stats.linregress(sub[strongest_col], sub["tfr"])
xs = np.linspace(sub[strongest_col].min(), sub[strongest_col].max(), 100)
ax2.plot(xs, slope * xs + intercept, color="black", linestyle="--",
         label=f"回帰直線 (r={r:+.3f})")
# 東京・沖縄をラベル
for name in ["東京都", "沖縄県"]:
    row = sub[sub["pref"] == name]
    if not row.empty:
        ax2.annotate(name, (row[strongest_col].iloc[0], row["tfr"].iloc[0]),
                     textcoords="offset points", xytext=(6, 4))
ax2.set_xlabel(AXIS_LABEL.get(strongest_col, strongest_label))
ax2.set_ylabel("合計特殊出生率")
ax2.set_title(f"都道府県別 出生率 vs {strongest_label}（2024年）")
ax2.legend()
ax2.grid(linestyle="--", alpha=0.4)
fig2.tight_layout()
fig2.savefig(IMG_SCAT, dpi=200)
print(f"保存: {os.path.relpath(IMG_SCAT)}")

"""Recipe 29: プロ野球の打率は「3割で一流」か.

規定打席に到達した打者の打率を集め、打率の分布を描く。3割が分布のどこに
位置するか（上位何パーセントか）、3割以上が全体の何パーセントかを見て、
「3割は一流」という目安をデータで確かめる。

データ出典:
  NPB.jp 日本野球機構 個人打撃成績（規定打席以上, 2024年）
    https://npb.jp/bis/2024/stats/bat_c.html （セ・リーグ）
    https://npb.jp/bis/2024/stats/bat_p.html （パ・リーグ）
    API キー不要（HTML テーブルを pandas.read_html で取得）

caveat:
  - 対象は「規定打席に到達した打者」のみ。控え選手や打席の少ない選手は
    含まれず、レギュラー級の中での分布である（全選手なら3割はさらに希少）。
  - 単年（2024年）のデータで、年によって分布は多少変動する。
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
CACHE = os.path.join(DATA_DIR, "recipe29_npb_batting.csv")
IMG = os.path.join(IMG_DIR, "recipe29_batting_average.png")

URLS = {
    "セ": "https://npb.jp/bis/2024/stats/bat_c.html",
    "パ": "https://npb.jp/bis/2024/stats/bat_p.html",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _parse_league(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.encoding = r.apparent_encoding
    raw = pd.read_html(io.StringIO(r.text))[0]
    body = raw.iloc[1:].copy()  # 1行目は見出し
    out = pd.DataFrame({
        "player": body.iloc[:, 1].astype(str).str.replace(r"\s+", "",
                                                          regex=True),
        "avg": pd.to_numeric(body.iloc[:, 3], errors="coerce"),
    })
    return out.dropna(subset=["avg"])


def load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    parts = []
    for lg, url in URLS.items():
        d = _parse_league(url)
        d["league"] = lg
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df.to_csv(CACHE, index=False)
    return df


df = load()
n = len(df)
print(f"=== 規定打席到達打者数（2024, セ+パ）: {n} ===")
print(f"打率 平均 {df['avg'].mean():.3f} / 中央値 {df['avg'].median():.3f}")
print(f"最高 {df['avg'].max():.3f} / 最低 {df['avg'].min():.3f}")

over3 = df[df["avg"] >= 0.300]
print(f"\n3割（.300）以上: {len(over3)}人 ({len(over3) / n * 100:.1f}%)")
print(f".300 は上位 {(df['avg'] >= 0.300).mean() * 100:.1f}%")
over25 = (df["avg"] >= 0.250).sum()
print(f"参考: .250以上は {over25}人 ({over25 / n * 100:.1f}%)")

print("\n=== .300 以上の打者 ===")
for _, r in over3.sort_values("avg", ascending=False).iterrows():
    print(f"  {r['avg']:.3f}  {r['player']} ({r['league']})")

# --- 作図: 打率の分布ヒストグラム + 3割の位置 ---
os.makedirs(IMG_DIR, exist_ok=True)
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["avg"], bins=20, color="0.6", edgecolor="black")
ax.axvline(0.300, color="black", linestyle="-", linewidth=2,
           label="3割（.300）")
ax.axvline(df["avg"].median(), color="black", linestyle="--",
           linewidth=1.5, label=f"中央値 {df['avg'].median():.3f}")
ax.set_xlabel("打率")
ax.set_ylabel("打者数")
ax.set_title("規定打席到達打者の打率の分布（2024年, セ・パ両リーグ）")
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

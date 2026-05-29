"""Recipe 20: 特殊詐欺の被害額は増えているか.

オレオレ詐欺・架空料金請求詐欺などの特殊詐欺について、認知件数と被害総額が
年次でどう動いたかを見る。全体の刑法犯が減るなか特殊詐欺がどうかを問う
（Recipe 19「犯罪は減っている」と対になる章テーマ）。

データ出典: 警察庁「特殊詐欺の認知・検挙状況等について」CSV（キー不要）
  https://www.npa.go.jp/bureau/criminal/souni/tokusyusagi/hurikomesagi_toukei.csv
  年次の認知件数・被害総額（単位: 円）が平成16年(2004)から収録されている。
重要な注意（CSV注記・警察庁確定値より）:
  - この CSV の「特殊詐欺」総数は、2023(令和5)年から SNS 型投資詐欺・
    ロマンス詐欺を含む。2024 年の内訳は 特殊詐欺のみ=認知 21,043 件/
    被害 717.6 億円、SNS 型投資・ロマンス詐欺=認知 10,237 件/被害 1,271.9 億円。
    両者の合計が CSV の 2024 値（認知 31,280 件/被害 約 1,990 億円）。
    つまり 2023→2024 の急増は、新たに集計対象へ加わった SNS 型の影響が大きい。
  - 集計手口数も年により拡大（2004 は 3 手口 → 2024 は 10 手口相当）。
  - 被害総額は 2010(平成22)年以降「実質的な被害総額」（だまし取った
    キャッシュカードで ATM から引き出された額等を含む）。
  - 令和7年(2025)以降は暫定値のため確定値の 2024 までを対象にする。
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

import jp_font  # noqa: E402,F401  日本語フォント設定

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(DATA_DIR, "recipe20_fraud.csv")
RAW = os.path.join(DATA_DIR, "recipe20_fraud_raw.csv")
IMG = os.path.join(
    os.path.dirname(__file__), "images", "recipe20_fraud_trend.png"
)
URL = ("https://www.npa.go.jp/bureau/criminal/souni/tokusyusagi/"
       "hurikomesagi_toukei.csv")

# 和暦→西暦（CSV の年見出しは全角数字: 例「平成１６年」）
_Z = str.maketrans("0123456789", "０１２３４５６７８９")


def _z(n):
    return str(n).translate(_Z)


ERA = {}
for i, y in enumerate(range(2004, 2009)):   # 平成16-20
    ERA[f"平成{_z(16 + i)}年"] = y
for i, y in enumerate(range(2009, 2019)):   # 平成21-30
    ERA[f"平成{_z(21 + i)}年"] = y
ERA["令和元年"] = 2019
for i, y in enumerate(range(2020, 2026)):   # 令和2-7
    ERA[f"令和{_z(2 + i)}年"] = y


def _download():
    r = requests.get(URL, timeout=120)
    txt = r.content.decode("shift_jis", errors="replace")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RAW, "w", encoding="utf-8") as f:
        f.write(txt)
    return txt


def parse_annual(txt):
    """年次ブロック（見出しに和暦年が並ぶ行）から認知件数・被害総額を抽出。"""
    df = pd.read_csv(io.StringIO(txt), header=None, dtype=str)
    # 特殊詐欺「全体」の年次表だけを対象にする。手口別内訳
    # （「２−１ ＳＮＳ型投資詐欺」以降）は重複年見出しを持つため除外。
    col0 = df[0].fillna("").astype(str).str.strip()
    sub_mask = col0.str.match(r"^[０-９0-9]+[−-][０-９0-9]+")
    limit = sub_mask.idxmax() if sub_mask.any() else len(df)
    df = df.iloc[:limit]
    records = {}
    n = len(df)
    for i in range(n):
        row = df.iloc[i].fillna("")
        # 年見出し行: 複数の「平成NN年/令和N年」を含み「合計」を含まない
        labels = [(j, c.strip()) for j, c in row.items() if c.strip() in ERA]
        if len(labels) < 2:
            continue
        # 直後の数行から「認知件数」「被害総額」行を探す
        for k in range(i + 1, min(i + 6, n)):
            r2 = df.iloc[k].fillna("")
            head = r2[0].strip()
            is_known = head == "認知件数"
            is_loss = head.startswith("被害総額")
            if not (is_known or is_loss):
                continue
            for j, era in labels:
                val = str(r2[j]).replace(",", "").strip()
                if val in ("", "nan"):
                    continue
                year = ERA[era]
                rec = records.setdefault(year, {})
                if is_known:
                    rec["recognized"] = int(float(val))
                elif is_loss:
                    rec["loss_yen"] = int(float(val))
    rows = [{"year": y, **v} for y, v in sorted(records.items())]
    return pd.DataFrame(rows)


def load_data():
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE)
    df = parse_annual(_download())
    df = df[df["year"] <= 2024].reset_index(drop=True)  # 確定値のみ
    df.to_csv(CACHE, index=False)
    return df


df = load_data()
df["loss_oku"] = df["loss_yen"] / 1e8  # 円→億円

first = df.iloc[0]
last = df.iloc[-1]
peak_known = df.loc[df["recognized"].idxmax()]
peak_loss = df.loc[df["loss_oku"].idxmax()]

print("=== 特殊詐欺 年次推移（2004-2024）===")
print(df[["year", "recognized", "loss_oku"]].to_string(
    index=False, float_format=lambda x: f"{x:,.1f}"))

print(f"\n認知件数: {int(first['year'])}年 {int(first['recognized']):,}件"
      f" → {int(last['year'])}年 {int(last['recognized']):,}件")
print(f"被害総額: {int(first['year'])}年 {first['loss_oku']:,.1f}億円"
      f" → {int(last['year'])}年 {last['loss_oku']:,.1f}億円"
      f"（{last['loss_oku'] / first['loss_oku']:.1f}倍）")
print(f"被害額ピーク: {int(peak_loss['year'])}年 "
      f"{peak_loss['loss_oku']:,.1f}億円")
print(f"認知件数ピーク: {int(peak_known['year'])}年 "
      f"{int(peak_known['recognized']):,}件")

# 1件あたり被害額（2024）
df["per_case_man"] = df["loss_yen"] / df["recognized"] / 1e4  # 万円
print(f"\n1件あたり被害額 {int(last['year'])}年: "
      f"{last['loss_yen'] / last['recognized'] / 1e4:.1f}万円")

# 直近の急増（2022 -> 2024）被害額
l22 = df[df["year"] == 2022]["loss_oku"].iloc[0]
l24 = df[df["year"] == 2024]["loss_oku"].iloc[0]
print(f"被害総額 2022年 {l22:,.1f}億円 → 2024年 {l24:,.1f}億円"
      f"（{l24 / l22:.1f}倍）")

# 2024年の内訳（警察庁確定値: 特殊詐欺のみ vs SNS型投資・ロマンス詐欺）
print("\n=== 2024年の内訳（警察庁確定値）===")
print("特殊詐欺のみ:          認知 21,043件 / 被害 717.6億円")
print("SNS型投資・ロマンス詐欺: 認知 10,237件 / 被害 1,271.9億円")
print("合計（CSV の値）:       認知 31,280件 / 被害 約1,990億円")
print("→ 2023→2024 の急増は新規集計の SNS 型が主因。"
      "特殊詐欺のみでも 717.6 億円で過去最悪。")

# トレンド（被害額の線形回帰, 全期間）
reg = stats.linregress(df["year"], df["loss_oku"])
print(f"\n被害総額トレンド: slope={reg.slope:,.1f}億円/年 "
      f"p={reg.pvalue:.3g} r={reg.rvalue:.3f}")

# --- 作図: 認知件数（棒）と被害総額（折れ線, 第2軸）---
fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.bar(df["year"], df["recognized"], color="lightgray",
        edgecolor="black", linewidth=0.5, label="認知件数（左軸）")
ax1.set_xlabel("年")
ax1.set_ylabel("認知件数（件）")
ax2 = ax1.twinx()
ax2.plot(df["year"], df["loss_oku"], color="black", marker="o",
         linewidth=2, label="被害総額（右軸）")
ax2.set_ylabel("被害総額（億円）")
# 2023年以降は SNS 型投資・ロマンス詐欺を含む（定義拡大）
ax1.axvline(2022.5, color="black", linestyle="--", linewidth=1)
ax1.text(2022.6, ax1.get_ylim()[1] * 0.95, "→ SNS型投資・\nロマンス詐欺を含む",
         fontsize=9, va="top")
ax1.set_title("特殊詐欺の認知件数と被害総額の推移（2004-2024）")
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left")
fig.tight_layout()
fig.savefig(IMG, dpi=200)
print(f"\n保存: {os.path.relpath(IMG)}")

# python-data-recipes-samples

「**Python × 公開データ分析 30選 — 日本の年収・睡眠時間・物価 ・実データで答える30のレシピ**」（森川 陽介 著）のサンプルコード集です。

本書の各レシピで使う Python コードを、そのまま動かせる形で収録しています。すべて日本の公開データ（気象庁・e-Stat・World Bank など）を扱い、問い → データ取得 → 前処理 → 分析 → 可視化 → 結論の流れで完結します。

## 構成

```
chapters/
  ch01/   第1章 気象 — 桜・台風・猛暑・豪雨（Recipe 01-04）
  ch02/   第2章 年収・賃金 — 平均年収・労働時間・IT年収（Recipe 05-07）
  ch03/   第3章 物価・購買力 — ビッグマック指数・都道府県物価差・円安と輸出（Recipe 08-10）
  ch04/   第4章 人口・少子化 — 人口ピラミッド・婚姻と出生・出生率の相関・消滅可能性都市（Recipe 11-14）
  ch05/   第5章 健康・生活 — 睡眠を含む生活時間・平均寿命の相関・コンビニと人口・通勤と睡眠（Recipe 15-18）
  ch06/   第6章 犯罪・安全 — 刑法犯認知件数の推移・特殊詐欺の被害額（Recipe 19-20）
  ch07/   第7章 株価・金融 — ビットコインと日経の連動性・大統領選サイクル（Recipe 21-22）
  ch08/   第8章 教育・キャリア — 大学進学率と生涯年収・プログラミング言語の人気推移（Recipe 23-24）
  ...     （以降の章は刊行に合わせて追加）
```

第2章の Recipe 05・07、第3章の Recipe 09、第4章の Recipe 11-14（全レシピ）、第5章の Recipe 16-18、第6章の Recipe 19、第8章の Recipe 23 は e-Stat の API を使うため、無料のアプリケーション ID（`appId`）が必要です。発行手順は各章の README（[`chapters/ch02/README.md`](chapters/ch02/README.md) / [`chapters/ch03/README.md`](chapters/ch03/README.md) / [`chapters/ch04/README.md`](chapters/ch04/README.md) / [`chapters/ch05/README.md`](chapters/ch05/README.md) / [`chapters/ch06/README.md`](chapters/ch06/README.md) / [`chapters/ch08/README.md`](chapters/ch08/README.md)）を参照してください。第3章の Recipe 08（GitHub CSV）・Recipe 10（FRED / World Bank）、第5章の Recipe 15（OECD）、第6章の Recipe 20（警察庁 CSV）、第7章の Recipe 21・22（FRED 公開 CSV）、第8章の Recipe 24（Stack Exchange API）はキー不要です。

各章ディレクトリには次が含まれます。

- `recipeNN_*.py` — 各レシピの実行スクリプト（単独で動作）
- `jp_font.py` — 日本語フォント設定ヘルパー（matplotlib の文字化け防止）
- `images/` — 出力されたグラフ（スクリプト実行で再生成されます）
- `data/` — 取得した実データのキャッシュ（再現性確保のため同梱）
- `README.md` — その章の各レシピの説明と分析結果

## 動かし方

Python 3.10 以上を推奨します。

```bash
git clone https://github.com/forest6511/python-data-recipes-samples.git
cd python-data-recipes-samples
pip install -r requirements.txt

cd chapters/ch01
python recipe01_sakura_trend.py
```

各スクリプトは初回にデータを取得して `data/` にキャッシュし、2 回目以降はキャッシュを使うため、ネットワークがなくても再実行できます。

## 日本語フォントについて

本書のグラフは `jp_font.py` で日本語フォントを設定します。`japanize-matplotlib` は Python 3.12 以降では動作しないため、本リポジトリでは OS 標準の日本語フォント（macOS は Hiragino、Windows は Yu Gothic / Meiryo、Linux は Noto / IPAex）を順に探して設定する方式を採っています。フォントが見つからない場合は警告が出ます。

## データの利用について

各レシピが扱うデータは、気象庁・e-Stat・World Bank などが公開しているものです。データそのものの利用条件は各機関の利用規約に従ってください。本リポジトリのコードは書籍購入者の学習用サンプルです。

## ライセンス

コード（`*.py`）は MIT License で公開します。出力グラフ・キャッシュデータは各データ提供機関の利用規約に従います。

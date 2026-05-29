# python-data-recipes-samples

「**Python × 公開データ分析 30選 — 日本の年収・睡眠時間・物価・実データで答える30のレシピ**」（森川 陽介 著）のサンプルコード集です。

本書の全 30 レシピで使う Python コードを、そのまま動かせる形で収録しています。日本や世界の公開データ（気象庁・e-Stat・World Bank・World Happiness Report・NPB・厚生労働省など）を扱い、**問い → データ取得 → 前処理 → 分析 → 可視化 → 結論**の流れで完結します。

## 構成（全 10 章・30 レシピ）

```
chapters/
  ch01/  第1章 気象          桜・台風・猛暑・豪雨                          （Recipe 01-04）
  ch02/  第2章 年収・賃金     平均年収・労働時間・IT年収                    （Recipe 05-07）
  ch03/  第3章 物価・購買力   ビッグマック指数・都道府県物価差・円安と輸出   （Recipe 08-10）
  ch04/  第4章 人口・少子化   人口ピラミッド・婚姻と出生・出生率の相関・消滅可能性都市（Recipe 11-14）
  ch05/  第5章 健康・生活     生活時間と睡眠・平均寿命の相関・コンビニと人口・通勤と睡眠（Recipe 15-18）
  ch06/  第6章 犯罪・安全     刑法犯認知件数の推移・特殊詐欺の被害額         （Recipe 19-20）
  ch07/  第7章 株価・金融     ビットコインと日経の連動性・大統領選サイクル   （Recipe 21-22）
  ch08/  第8章 教育・キャリア 大学進学率と生涯年収・プログラミング言語の人気推移（Recipe 23-24）
  ch09/  第9章 国際比較       年収と幸福度・GDPと幸福度・都道府県幸福度ランキング（Recipe 25-27）
  ch10/  第10章 SNS・エンタメ YouTube再生数と動画の長さ・打率3割は一流か・外国人労働者の分布（Recipe 28-30）
```

各章ディレクトリには次が含まれます。

- `recipeNN_*.py` — 各レシピの実行スクリプト（単独で動作）
- `jp_font.py` — 日本語フォント設定ヘルパー（matplotlib の文字化け防止）
- `images/` — 出力されたグラフ（スクリプト実行で再生成されます）
- `data/` — 取得した実データのキャッシュ（再現性確保のため同梱）
- `README.md` — その章の各レシピの説明と分析結果

## API キーについて

ほとんどのレシピは API キーなしで動きます。キーが必要なのは次のレシピだけです。

### e-Stat の appId（政府統計）が必要

Recipe 05・07（第2章）、Recipe 09（第3章）、Recipe 11-14（第4章）、Recipe 16-18（第5章）、Recipe 19（第6章）、Recipe 23（第8章）、Recipe 27（第9章）は、政府統計の総合窓口 [e-Stat](https://www.e-stat.go.jp/) の API を使います。無料のアプリケーション ID（`appId`）を発行し、その章のディレクトリの `.env` に `ESTAT_APP_ID=...` を書きます（発行手順は各章 README 参照）。

### YouTube Data API のキーが必要

Recipe 28（第10章）は YouTube Data API v3 を使います。[Google Cloud Console](https://console.cloud.google.com/) で無料の API キーを発行し、`chapters/ch10/.env` に `YOUTUBE_API_KEY=...` を書きます（手順は [`chapters/ch10/README.md`](chapters/ch10/README.md) 参照）。同梱の取得済みキャッシュをそのまま使えば、キーなしでも書籍の数値を再現できます。

### キー不要

上記以外はすべてキー不要で、公開データを直接取得します。気象庁（第1章）、The Economist の GitHub CSV（Recipe 08）、FRED / World Bank（Recipe 10・21・22・25・26）、OECD（Recipe 15）、警察庁 CSV（Recipe 20）、Stack Exchange API（Recipe 24）、World Happiness Report の GitHub CSV（Recipe 25・26）、NPB.jp（Recipe 29）、厚生労働省の Excel（Recipe 30）などです。

`.env` ファイルはいずれも `.gitignore` 済みで、リポジトリにはコミットされません。

## 動かし方

Python 3.10 以上を推奨します。

```bash
git clone https://github.com/forest6511/python-data-recipes-samples.git
cd python-data-recipes-samples
pip install -r requirements.txt

cd chapters/ch01
python recipe01_sakura_trend.py
```

各スクリプトは初回にデータを取得して `data/` にキャッシュし、2 回目以降はキャッシュを使うため、ネットワークがなくても再実行できます（最新データで取り直したい場合は `data/` の該当 CSV を削除して再実行します）。

## 日本語フォントについて

本書のグラフは `jp_font.py` で日本語フォントを設定します。`japanize-matplotlib` は Python 3.12 以降では動作しないため、本リポジトリでは OS 標準の日本語フォント（macOS は Hiragino、Windows は Yu Gothic / Meiryo、Linux は Noto / IPAex）を順に探して設定する方式を採っています。フォントが見つからない場合は警告が出ます。

なお本書のグラフは白黒印刷でも判別できるよう、色だけに頼らず線種・マーカー・ハッチング（網掛け）で系列を区別しています。

## データの利用について

各レシピが扱うデータは、気象庁・e-Stat・World Bank・World Happiness Report・NPB・厚生労働省などが公開しているものです。データそのものの利用条件は各機関の利用規約に従ってください。`data/` のキャッシュは再現性確保のために同梱した取得時点のスナップショットで、最新値とは異なる場合があります。本リポジトリのコードは書籍購入者の学習用サンプルです。

## ライセンス

コード（`*.py`）は MIT License で公開します。出力グラフ・キャッシュデータは各データ提供機関の利用規約に従います。

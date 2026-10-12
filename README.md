# aozora_to_mp3

青空文庫のHTML作品ページを自然な日本語音声のMP3に変換するCLIです。Macなどで作成したMP3を任意のプレイヤーで再生し、途中で停止・再開できます（再生位置の保存はプレイヤー側の機能です）。

音声合成には非公式の [edge-tts](https://github.com/rany2/edge-tts) を使用します。インターネット接続が必要で、サービス仕様の変更により動作しなくなる可能性があります。

## セットアップ

Python 3.9以降を用意してください。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 使い方

```bash
# 芥川龍之介『羅生門』をMP3化
python aozora_to_mp3.py \
  "https://www.aozora.gr.jp/cards/000879/files/127_15260.html" \
  -o rashomon.mp3

# 読み上げる文字列の冒頭を確認（音声生成なし）
python aozora_to_mp3.py \
  "https://www.aozora.gr.jp/cards/000879/files/127_15260.html" \
  --preview

# 男性の日本語音声に変更
python aozora_to_mp3.py "作品URL" -o book.mp3 --voice ja-JP-KeitaNeural

# 読み上げ速度を調整
python aozora_to_mp3.py "作品URL" -o book.mp3 --rate=-5%

# 長編向け：文字数で分割して複数のMP3を作成
python aozora_to_mp3.py "作品URL" -o book.mp3 --chunk-chars 3000

# ダウンロード済み作品HTMLも利用可能
python aozora_to_mp3.py ./work.html -o book.mp3
```

分割時は `book_001.mp3`、`book_002.mp3` のように出力されます。デフォルトは `ja-JP-NanamiNeural`（女性音声）、読み上げ速度は `-10%` です。

## 青空文庫のHTMLについて

* 作品ページの `.main_text` 部分を抽出します。
* HTMLの `<ruby>` に含まれるルビを読みとして採用し、親文字との二重読みを防ぎます。
* 未指定の難読漢字、古い仮名遣い、注記の一部は正しく読み上げられない場合があります。
* 青空文庫のすべてのHTML表現・レイアウトに対応するわけではありません。

## 注意

* 本ツールは個人利用向けの簡易実装です。長い作品を一つの巨大なMP3として生成するより、`--chunk-chars` を使った分割を推奨します。
* 音声合成への送信前に、作品の著作権と配布条件を確認してください。青空文庫の掲載作品であってもすべての利用・再配布が自由とは限りません。
* 音声サービスへの接続を含むエンドツーエンドの動作確認は未実施です。

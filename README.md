# aozora_to_mp3

青空文庫のHTML作品ページを自然な日本語音声のMP3に変換するCLIです。Macなどで作成したMP3を任意のプレイヤーで再生し、途中で停止・再開できます（再生位置の保存はプレイヤー側の機能です）。

音声合成には手元で動く [VOICEVOX ENGINE](https://github.com/VOICEVOX/voicevox_engine) を使用します（既定）。`--engine edge` で非公式の [edge-tts](https://github.com/rany2/edge-tts) も選べますが、2026年10月時点ではサービス側の仕様変更により403エラーで動作しません（[rany2/edge-tts#490](https://github.com/rany2/edge-tts/issues/490)）。

## セットアップ

Python 3.9以降を用意してください。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
brew install ffmpeg
```

VOICEVOX ENGINE を起動します。Docker を使う場合（初回はイメージ取得に数分かかります）:

```bash
docker run -d --name voicevox -p 127.0.0.1:50021:50021 --restart unless-stopped voicevox/voicevox_engine:cpu-latest
```

[VOICEVOX アプリ](https://voicevox.hiroshiba.jp/) を起動している間も同じURL（`http://127.0.0.1:50021`）でエンジンが使えます。

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

# 話者を変更（IDは http://127.0.0.1:50021/speakers の styles[].id。例: 13 = 青山龍星、11 = 玄野武宏）
python aozora_to_mp3.py "作品URL" -o book.mp3 --speaker 8

# 読み上げ速度を調整
python aozora_to_mp3.py "作品URL" -o book.mp3 --rate=-5%

# 長編向け：文字数で分割して複数のMP3を作成
python aozora_to_mp3.py "作品URL" -o book.mp3 --chunk-chars 3000

# ダウンロード済み作品HTMLも利用可能
python aozora_to_mp3.py ./work.html -o book.mp3
```

分割時は `book_001.mp3`、`book_002.mp3` のように出力されます。デフォルトの話者は冥鳴ひまり（ID 14）、読み上げ速度は `-10%` です。生成時間の目安は、CPU版で『羅生門』（約6000文字、音声約18分）が約8分です。

## 青空文庫のHTMLについて

* 作品ページの `.main_text` 部分を抽出します。
* HTMLの `<ruby>` に含まれるルビを読みとして採用し、親文字との二重読みを防ぎます。
* 未指定の難読漢字、古い仮名遣い、注記の一部は正しく読み上げられない場合があります。
* 青空文庫のすべてのHTML表現・レイアウトに対応するわけではありません。

## 注意

* 本ツールは個人利用向けの簡易実装です。長い作品を一つの巨大なMP3として生成するより、`--chunk-chars` を使った分割を推奨します。
* 音声合成への送信前に、作品の著作権と配布条件を確認してください。青空文庫の掲載作品であってもすべての利用・再配布が自由とは限りません。
* VOICEVOX で作成した音声を公開する場合は「VOICEVOX:冥鳴ひまり」のようなクレジット表記が必要です。条件は話者ごとに異なるため、各キャラクターの利用規約を確認してください。

## AivisSpeech（追加エンジン）

[AivisSpeech](https://aivis-project.com/speech/)のmacOS版をインストールして起動します。
エンジン単独なら同梱の実行ファイルを起動できます（初回はモデル取得に時間がかかります）。

```bash
/Applications/AivisSpeech.app/Contents/Resources/AivisSpeech-Engine/run

# インストール済みモデルのスタイルIDを確認
python aozora_to_mp3.py --engine aivis --list-speakers

# STYLE_IDを一覧の整数に置き換える。VOICEVOXの話者IDは流用しない
python aozora_to_mp3.py ./work.html -o book.mp3 \
  --engine aivis --speaker STYLE_ID --rate=-10% --chunk-chars 3000
```

接続先は既定で `http://127.0.0.1:10101`、変更は `--aivis-url` です。
AivisSpeechでは話者を明示指定します。VOICEVOXの既定エンジン・話者は維持しています。
AudioQueryの本文や独自パラメータを保持して、読み上げ速度だけ変更します。
MP3出力・分割命名・150文字単位の合成は共通です。

[API調査、朗読向け候補、同じ本文での品質・生成速度比較手順](docs/aivisspeech.md)を参照してください。
実エンジンでの音声生成・品質評価は未実施です。音声公開条件はAivisHubの各モデルで確認してください。

開発時の検証: `python -m unittest discover -s tests -v`（MP3検証にはffmpegが必要）。

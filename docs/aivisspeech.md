# AivisSpeech対応と朗読評価

調査日: 2026-10-13。公式ソースの確認基点は
[a81c43576ea26514fb7fd94f920b50c956e6d22e](https://github.com/Aivis-Project/AivisSpeech-Engine/tree/a81c43576ea26514fb7fd94f920b50c956e6d22e)。
導入版の `/docs` も確認すること。

## API互換性と最小変更

| 項目 | 確認結果と対応 |
| --- | --- |
| audio_query → synthesis | 同じPOST手順。返されたJSON全体を送り、speedScaleのみ変更 |
| kana | Aivisでは通常の本文。audio_queryが本文を返す実装を確認。再構築・空欄化せず保持 |
| tempoDynamicsScale | Aivis独自。未知の追加フィールドとともに保持 |
| intonationScale / pitchScale | 意味・音質への影響が異なるため、エンジンの既定値を保持 |
| speaker | `/speakers` の `styles[].id`。local_idやspeaker_uuidではない。符号付き32bit整数にも対応。VOICEVOXの14は流用しない |
| speedScale | Aivis実装は `length = 1 / max(0.1, speedScale)`。既存の -10% → 0.9 を再利用。音声時間が厳密に10%変わる保証はない |
| 接続先 | aivisは10101。VOICEVOXは従来どおり50021・話者14 |
| 長文 | 出力用chunk-charsと合成用150文字上限の二段階分割を維持。逐次合成→WAV連結→MP3 |
| 境界 | 各合成で文脈が切れ、前後無音が入る可能性。文末優先だが長い一文は途中分割。声質・会話・間の連続性は試聴が必要 |
| WAV | 断片のch数・サンプル幅・サンプルレート不一致を拒否 |

正しいAivisスタイルIDとURLを指定すれば、既存処理を利用できる構造だった。
差分はエンジン選択・URL・話者一覧・誤った既定話者の使用防止を明示するもの。
抑揚やテンポの調整項目は追加していない。

一次資料:

- [公式README: 互換性、AudioQuery、macOS起動](https://github.com/Aivis-Project/AivisSpeech-Engine)
- [audio_query実装](https://github.com/Aivis-Project/AivisSpeech-Engine/blob/a81c43576ea26514fb7fd94f920b50c956e6d22e/voicevox_engine/app/routers/tts_pipeline.py)
- [speedScale・合成実装](https://github.com/Aivis-Project/AivisSpeech-Engine/blob/a81c43576ea26514fb7fd94f920b50c956e6d22e/voicevox_engine/tts_pipeline/style_bert_vits2_tts_engine.py)

## 日本語小説の試聴候補

[AivisHub公式一覧](https://hub.aivis-project.com/search)の声分類・スタイル名を基に選んだ候補。
朗読への適性は仮説であり、品質順位ではない。導入後に `/speakers` で実際の名前・IDを確認する。

| 候補 | 試すスタイル | 比較する目的（仮説） |
| --- | --- | --- |
| 阿井田 茂（中年男性） | ノーマル、Calm | 落ち着いた地の文と会話の両立 |
| まお（若い女性） | ノーマル、おちつき | 女性声で長時間聞きやすいか |
| fumifumi（壮年男性） | ノーマル | 男性声の別候補として声質を比較 |
| VOICEVOX:冥鳴ひまり | ノーマル、ID14 | 現行出力との基準比較 |

自然さ・誤読・速度は**全候補未実施**。ダウンロード数から優劣を決めない。
モデルページの利用条件・クレジット・モデル版を記録する。
デフォルトモデルは変更され得るため、名前やIDをCLIに固定しない。

## 比較方法

1. 同じ保存済みHTMLを使う。まず地の文・会話・固有名詞・数字・旧仮名を含む500〜1000文字程度の抜粋HTMLを用意する（`.main_text`が必要）。
2. `--preview`でルビ置換後の本文を確認する。ルビの有無を固定する。
3. 同じMac・エンジン版・rate・chunk-charsで各スタイルを2回生成。1回目はモデルロードを含み、2回目を暖機後の比較に使う。他の重い処理は止める。
4. JSONに本文SHA256、話者情報、エンジン版、壁時計時間、音声秒数、RTFを保存。RTF = 生成＋MP3変換秒数 / 出力音声秒数（小さいほど速い）。合成単独の速度ではない。
5. ファイル名を隠して試聴し、naturalness_1_to_5、reading_errors（箇所と期待読み）、boundary_artifacts、notesを記入し、quality_statusを「試聴済み」に変更する。疲れやすさ、会話、語尾、長い無音も記録する。
6. 最後に同じ長編をchunk-chars 3000で生成し、全出力数、欠落・重複、150文字付近とMP3境界、プレイヤーでの途中再開を確認する。

```bash
python aozora_to_mp3.py --engine aivis --list-speakers
# ID_A / ID_B は一覧の整数IDに置き換える
python tools/compare_voices.py ./sample.html --engine aivis \
  --speakers ID_A ID_B --rate=-10% --output-dir comparison/aivis
python tools/compare_voices.py ./sample.html --engine voicevox \
  --speakers 14 --rate=-10% --output-dir comparison/voicevox
```

同じ出力ディレクトリは上書きされるため、比較条件ごとに別ディレクトリを使う。
品質欄は自動採点せずnullで作成する。音声長も比較し、語や文の欠落を速度と取り違えない。
モデル版・CPU・メモリ・電源設定などもnotesへ記録する。

## 検証状況

- Queryの本文・独自フィールド保持、速度変更、正負style ID: モックテスト済み。
- 二段階分割、全断片の順序・欠落なし、複数MP3出力: ダミーPCM＋実ffmpegでテスト済み。
- 実Aivis/VOICEVOX接続・合成、話者の実音声、速度実測、試聴品質、Macのプレイヤー再開: **未実施**。
- この実行環境の10101/50021にはエンジンが起動していない。品質の評価値は記載していない。

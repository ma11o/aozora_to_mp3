#!/usr/bin/env python3
"""青空文庫のXHTML作品ページから読み上げ用MP3を作成する。

依存: pip install beautifulsoup4 edge-tts / ffmpeg / VOICEVOX ENGINE (既定エンジン)
使い方: python aozora_to_mp3.py <青空文庫のHTML URL> -o book.mp3
"""

import argparse
import asyncio
import io
import json
from pathlib import Path
import re
import subprocess
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import wave

from bs4 import BeautifulSoup


SPEAKER = 13  # 青山龍星（ノーマル）。低く落ち着いた男性の声で朗読向き。


def read_html(source: str) -> bytes:
    if source.startswith(("https://", "http://")):
        request = Request(source, headers={"User-Agent": "Mozilla/5.0 (AozoraPersonalTTS/1.0)"})
        with urlopen(request, timeout=30) as response:
            return response.read()
    return Path(source).read_bytes()


def html_to_speech_text(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one(".main_text")
    if main is None:
        raise ValueError("本文(.main_text)が見つかりません。青空文庫の作品HTMLのURLを指定してください。")

    # 底本の注記は読まない（編集注を発声しない）。
    for note in main.select(".notes"):
        note.decompose()

    # ルビ付きの漢字はルビの読みへ置換。漢字と読みの二重読みを防ぐ。
    for ruby in main.find_all("ruby"):
        readings = [rt.get_text(strip=True) for rt in ruby.find_all("rt")]
        if readings:
            ruby.replace_with("".join(readings))
        else:
            for marker in ruby.find_all("rp"):
                marker.decompose()
            ruby.unwrap()

    for br in main.find_all("br"):
        br.replace_with("\n")
    for tag in main.find_all(["p", "h3", "h4", "h5"]):
        tag.append("\n")

    text = main.get_text()
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    # 文の切れ目を優先して分割。極端に長い1文だけは文字数で分割。
    for sentence in re.split(r"(?<=[。！？!?])", text):
        while len(sentence) > max_chars:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.append(sentence[:max_chars].strip())
            sentence = sentence[max_chars:]
        if len(current) + len(sentence) > max_chars and current.strip():
            chunks.append(current.strip())
            current = ""
        current += sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_paths(chunks: list[str], output: Path) -> list[Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(chunks) == 1:
        return [output]
    return [output.with_name(f"{output.stem}_{i:03d}{output.suffix}") for i in range(1, len(chunks) + 1)]


async def render_edge(chunks: list[str], output: Path, voice: str, rate: str) -> None:
    import edge_tts

    for index, (chunk, path) in enumerate(zip(chunks, chunk_paths(chunks, output)), 1):
        print(f"[{index}/{len(chunks)}] 生成中: {path} ({len(chunk)}文字)", flush=True)
        await edge_tts.Communicate(chunk, voice=voice, rate=rate).save(str(path))
    print("完了", flush=True)


def voicevox_post(url: str, path: str, params: dict, body: bytes = b"") -> bytes:
    request = Request(
        f"{url}{path}?{urlencode(params)}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=600) as response:
        return response.read()


def voicevox_wav(url: str, text: str, speaker: int, speed: float) -> bytes:
    query = json.loads(voicevox_post(url, "/audio_query", {"text": text, "speaker": speaker}))
    query["speedScale"] = speed
    return voicevox_post(url, "/synthesis", {"speaker": speaker}, json.dumps(query).encode())


def render_voicevox(chunks: list[str], output: Path, url: str, speaker: int, rate: str) -> None:
    speed = 1 + float(rate.rstrip("%")) / 100
    try:
        urlopen(f"{url}/version", timeout=5).close()
    except URLError:
        raise SystemExit(f"VOICEVOX ENGINE に接続できません ({url})。VOICEVOX を起動してください。")

    for index, (chunk, path) in enumerate(zip(chunks, chunk_paths(chunks, output)), 1):
        print(f"[{index}/{len(chunks)}] 生成中: {path} ({len(chunk)}文字)", flush=True)
        # 1リクエストが長いと遅く不安定なため、文単位の短い断片で合成して連結する。
        pieces = [p for p in split_text(chunk, 150) if p.strip()]
        joined = io.BytesIO()
        with wave.open(joined, "wb") as out:
            for n, piece in enumerate(pieces, 1):
                print(f"\r  {n}/{len(pieces)}", end="", flush=True)
                with wave.open(io.BytesIO(voicevox_wav(url, piece, speaker, speed))) as src:
                    if n == 1:
                        out.setparams(src.getparams())
                    out.writeframes(src.readframes(src.getnframes()))
        print(flush=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-b:a", "128k", str(path)],
            input=joined.getvalue(),
            check=True,
        )
    print("完了", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="青空文庫の作品HTML URL、または保存済みHTMLのパス")
    parser.add_argument("-o", "--output", type=Path, default=Path("book.mp3"), help="出力MP3名")
    parser.add_argument("--engine", choices=["voicevox", "edge"], default="voicevox", help="音声合成エンジン")
    parser.add_argument("--speaker", type=int, default=SPEAKER, help="VOICEVOXの話者ID（GET /speakers の style id）")
    parser.add_argument("--voicevox-url", default="http://127.0.0.1:50021", help="VOICEVOX ENGINE のURL")
    parser.add_argument("--voice", default="ja-JP-NanamiNeural", help="edge用の音声。例: ja-JP-KeitaNeural")
    parser.add_argument("--rate", default="-10%", help="読み上げ速度。例: -10%% / +0%%")
    parser.add_argument("--chunk-chars", type=int, default=0, help="長編向け。指定文字数ごとに分割MP3を作る（例: 3000）")
    parser.add_argument("--preview", action="store_true", help="音声生成せず、読み上げる文字列の先頭を確認")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".mp3":
        parser.error("--output には .mp3 ファイル名を指定してください")
    text = html_to_speech_text(read_html(args.source))
    if not text:
        parser.error("作品本文が空です")
    if args.preview:
        print(f"読み上げ対象: {len(text)}文字\n\n{text[:1200]}")
        return
    chunks = split_text(text, args.chunk_chars)
    if args.engine == "voicevox":
        render_voicevox(chunks, args.output, args.voicevox_url, args.speaker, args.rate)
    else:
        asyncio.run(render_edge(chunks, args.output, args.voice, args.rate))


if __name__ == "__main__":
    main()

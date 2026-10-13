#!/usr/bin/env python3
"""同じHTMLを指定スタイルで合成し、速度と試聴用の未記入評価をJSONに保存。"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from urllib.request import urlopen
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aozora_to_mp3 as tts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument("--engine", choices=["voicevox", "aivis"], required=True)
    p.add_argument("--url", help="未指定ならエンジンの既定URL")
    p.add_argument("--speakers", type=int, nargs="+", required=True)
    p.add_argument("--rate", default="-10%")
    p.add_argument("--chunk-chars", type=int, default=3000)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    tts.rate_to_speed(a.rate)
    url = (a.url or ("http://127.0.0.1:10101" if a.engine == "aivis"
                    else "http://127.0.0.1:50021")).rstrip("/")
    text = tts.html_to_speech_text(tts.read_html(a.source))
    if not text:
        p.error("本文が空です")
    chunks = tts.split_text(text, a.chunk_chars)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    with urlopen(url + "/version", timeout=5) as response:
        version = json.load(response)
    metadata = tts.list_speakers(url)
    report = dict(engine=a.engine, engine_version=version, speakers=metadata,
                  machine=platform.platform(), source=a.source,
                  text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  chars=len(text), rate=a.rate, chunk_chars=a.chunk_chars,
                  synthesis_piece_chars=150, runs=[])
    # 初回はモデルロードを含む。2回目を暖機後の比較に使う。
    for speaker in a.speakers:
        for repeat in (1, 2):
            output = a.output_dir / f"speaker_{speaker}_run{repeat}.mp3"
            start = time.perf_counter()
            tts.render_voicevox(chunks, output, url, speaker, a.rate, a.engine)
            elapsed = time.perf_counter() - start
            paths = ([output] if len(chunks) == 1 else [
                output.with_name(f"{output.stem}_{i:03d}.mp3")
                for i in range(1, len(chunks) + 1)])
            duration = sum(float(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path)
            ])) for path in paths)
            report["runs"].append(dict(
                speaker=speaker, repeat=repeat, elapsed_seconds=elapsed,
                audio_seconds=duration, real_time_factor=elapsed / duration,
                files=[str(path) for path in paths],
                quality_status="未実施", naturalness_1_to_5=None,
                reading_errors=None, boundary_artifacts=None, notes=""))
            (a.output_dir / "comparison.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import aozora_to_mp3 as tts


def wav():
    data = io.BytesIO()
    with wave.open(data, "wb") as out:
        out.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        out.writeframes(b"\0\0" * 2400)
    return data.getvalue()


class EnginesTest(unittest.TestCase):
    def test_query_roundtrip(self):
        query = dict(kana="雨の夜。", speedScale=1.0,
                     tempoDynamicsScale=1.2, intonationScale=1.0,
                     accent_phrases=[], extension={"future": True})
        for speaker in (14, 888753760, -123456):
            with patch.object(tts, "voicevox_post", side_effect=[
                json.dumps(query).encode(), wav()
            ]) as post:
                tts.voicevox_wav("http://localhost", query["kana"], speaker, 0.9)
                call = post.call_args_list[1]
                self.assertEqual(call.args[2], {"speaker": speaker})
                expected = dict(query, speedScale=0.9)
                self.assertEqual(json.loads(call.args[3]), expected)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg required")
    def test_split_mp3_pipeline(self):
        text = "雨の夜、彼は駅へ向かった。" * 40
        chunks = tts.split_text(text, 250)
        sent = []
        def synth(url, piece, speaker, speed):
            sent.append(piece)
            self.assertLessEqual(len(piece), 150)
            self.assertEqual((speaker, speed), (-123456, 0.9))
            return wav()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "book.mp3"
            with patch.object(tts, "urlopen"), patch.object(tts, "voicevox_wav", side_effect=synth):
                tts.render_voicevox(chunks, output, "http://localhost/", -123456, "-10%", "AivisSpeech")
            paths = sorted(Path(tmp).glob("*.mp3"))
            self.assertEqual(len(paths), len(chunks))
            self.assertTrue(all(p.stat().st_size > 0 for p in paths))
        self.assertEqual("".join(sent), text)

    def test_cli_defaults_and_aivis(self):
        for argv, expected_url, expected_id in (
            (["cli", "work.html"], "http://127.0.0.1:50021", 14),
            (["cli", "work.html", "--engine", "aivis", "--speaker=-123456"],
             "http://127.0.0.1:10101", -123456),
        ):
            with patch.object(sys, "argv", argv), patch.object(tts, "read_html"), \
                 patch.object(tts, "html_to_speech_text", return_value="本文。"), \
                 patch.object(tts, "render_voicevox") as render:
                tts.main()
                self.assertEqual(render.call_args.args[2:4], (expected_url, expected_id))
        with patch.object(sys, "argv", ["cli", "--engine", "aivis", "--list-speakers"]), \
             patch.object(tts, "list_speakers", return_value=[]) as speakers:
            tts.main()
            speakers.assert_called_once_with("http://127.0.0.1:10101")

    def test_rate_and_ruby(self):
        self.assertEqual(tts.rate_to_speed("-10%"), 0.9)
        self.assertEqual(tts.rate_to_speed("-90%"), 0.1)
        for value in ("-100%", "nan", "inf", "bad"):
            with self.assertRaises(ValueError):
                tts.rate_to_speed(value)
        self.assertEqual(tts.html_to_speech_text(
            '<div class="main_text"><ruby>羅生門<rt>らしょうもん</rt></ruby>。</div>'.encode()
        ), "らしょうもん。")


if __name__ == "__main__":
    unittest.main()

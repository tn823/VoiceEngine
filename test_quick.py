# -*- coding: utf-8 -*-
"""
Script kiểm thử nhanh các thành phần của VoiceEngine
"""
import sys
import numpy as np

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== 1. KIỂM THỬ NORMALIZER & PARSER ===")
from core.whisper_normalizer import normalize_whisper_text
from core.command_parser import parse_command

test_phrases = [
    ("pass", "pass"),
    ("đạt", "pass"),
    ("mũi", "position"),
    ("gót", "position"),
    ("a một", "inspection"),
    ("mũi một", "inspection"),
    ("gót mười bảy sửa", "reins_fail"),
    ("sửa đạt", "reins_pass"),
    ("hủy", "cancel"),
]

for phrase, expected_intent in test_phrases:
    clean = normalize_whisper_text(phrase)
    cmd = parse_command(clean)
    intent = cmd.get("intent") if cmd else None
    ok = (intent == expected_intent)
    print(f"[{'PASS' if ok else 'FAIL'}] '{phrase}' -> norm: '{clean}' -> intent: {intent} (mong đợi: {expected_intent})")
    assert ok, f"Sai logic parse cho '{phrase}'"

print("\n=== 2. KIỂM THỬ SILERO VAD ONNX ===")
from core.audio_preprocessor import AudioPreprocessor
prep = AudioPreprocessor()
print(f"Silero VAD available: {prep.vad is not None and prep.vad.is_available}")
assert prep.vad is not None and prep.vad.is_available, "Không nạp được Silero VAD ONNX!"

dummy_chunk = np.zeros(1600, dtype=np.float32)
is_speech, prob = prep.is_speech(dummy_chunk, rms=0)
print(f"Test silence chunk: is_speech={is_speech}, prob={prob:.4f}")
assert not is_speech, "Silence chunk không được báo là speech"

print("\n=== 3. KIỂM THỬ PHOWHISPER CT2 INT8 ===")
from core.phowhisper_engine import get_phowhisper_engine
from config import Config
engine = get_phowhisper_engine(Config.PHOWHISPER_MODEL_PATH)
dummy_audio = np.zeros(16000 * 2, dtype=np.float32) # 2 giây khoảng lặng
res = engine.transcribe_detailed(dummy_audio)
print(f"Inference silence 2s: text='{res.get('text')}', latency={res.get('compute_time_ms'):.1f}ms")

print("\n✅ TOÀN BỘ CÁC THÀNH PHẦN VOICEENGINE ĐÃ VƯỢT QUA TEST THÀNH CÔNG!")

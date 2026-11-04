# -*- coding: utf-8 -*-
"""
Cấu hình VoiceEngine Headless
Tối giản, chuyên dụng cho nhận diện giọng nói QA công nghiệp
"""
import os
import sys
from core.__version__ import __version__

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = get_base_dir()
    return os.path.join(base_path, relative_path)

class Config:
    VERSION = __version__
    BASE_DIR = get_base_dir()
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")

    # Đường dẫn model PhoWhisper CT2 INT8
    _default_whisper = os.path.join(MODELS_DIR, "phowhisper-tiny-ct2-int8")
    PHOWHISPER_MODEL_PATH = os.getenv("PHOWHISPER_MODEL_PATH", _default_whisper)
    if not os.path.isabs(PHOWHISPER_MODEL_PATH):
        PHOWHISPER_MODEL_PATH = resource_path(PHOWHISPER_MODEL_PATH)

    # Đường dẫn model Silero VAD
    _default_vad = os.path.join(MODELS_DIR, "silero_vad.onnx")
    SILERO_VAD_MODEL_PATH = os.getenv("SILERO_VAD_MODEL_PATH", _default_vad)
    if not os.path.isabs(SILERO_VAD_MODEL_PATH):
        SILERO_VAD_MODEL_PATH = resource_path(SILERO_VAD_MODEL_PATH)

    # Cấu hình Whisper Engine
    PHOWHISPER_INITIAL_PROMPT = os.getenv("PHOWHISPER_INITIAL_PROMPT", None)
    PHOWHISPER_CPU_THREADS = int(os.getenv("PHOWHISPER_CPU_THREADS", "2"))
    VOICE_MIN_CONFIDENCE = float(os.getenv("VOICE_MIN_CONFIDENCE", "0.45"))

    # Cấu hình tiền xử lý âm thanh (Audio DSP)
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 1600  # 100ms chunk @ 16kHz
    AUDIO_NOISE_GATE = int(os.getenv("AUDIO_NOISE_GATE", "180"))
    AUDIO_ADAPTIVE_GATE = os.getenv("AUDIO_ADAPTIVE_GATE", "true").lower() in ("true", "1", "yes")
    AUDIO_ENABLE_LIMITER = os.getenv("AUDIO_ENABLE_LIMITER", "true").lower() in ("true", "1", "yes")
    AUDIO_ENABLE_HIGHPASS = os.getenv("AUDIO_ENABLE_HIGHPASS", "true").lower() in ("true", "1", "yes")
    AUDIO_ENABLE_AGC = os.getenv("AUDIO_ENABLE_AGC", "true").lower() in ("true", "1", "yes")
    AUDIO_AGC_TARGET_RMS = float(os.getenv("AUDIO_AGC_TARGET_RMS", "1500"))
    AUDIO_AGC_MAX_GAIN = float(os.getenv("AUDIO_AGC_MAX_GAIN", "6.0"))

    # Silero VAD AI
    AUDIO_ENABLE_SILERO_VAD = os.getenv("AUDIO_ENABLE_SILERO_VAD", "true").lower() in ("true", "1", "yes")
    AUDIO_SILERO_VAD_THRESHOLD = float(os.getenv("AUDIO_SILERO_VAD_THRESHOLD", "0.55"))
    AUDIO_ENABLE_DENOISE = os.getenv("AUDIO_ENABLE_DENOISE", "false").lower() in ("true", "1", "yes")
    AUDIO_DENOISE_PROP = float(os.getenv("AUDIO_DENOISE_PROP", "0.50"))

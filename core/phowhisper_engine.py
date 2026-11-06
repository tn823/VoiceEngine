# -*- coding: utf-8 -*-
"""
PhoWhisper Inference Engine
Sử dụng CTranslate2 (faster-whisper) chạy CPU INT8 siêu nhẹ, độ trễ thấp.
Hỗ trợ cả streaming buffer (numpy float32) và file audio.
Tự động fallback về HuggingFace (ntn823/phowhisper-tiny-cuchi-int8) nếu thiếu model offline.
"""

import os
import sys
import time
import math
import threading
import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from .whisper_normalizer import normalize_whisper_text

_engine_instance = None
_engine_lock = threading.Lock()

_DEFAULT_INITIAL_PROMPT = (
    "Một, hai, ba, bốn, năm, sáu, mười, mười một, mười hai, mười ba, mười bốn, mười lăm, "
    "mười sáu, mười bảy, mười tám, mười chín, hai mươi, hai mốt, hai hai, hai ba, hai tư, "
    "đạt, đạt lại, lỗi, lỗi lại, sửa lại, sửa, pass, re-ins pass, hủy, quay lại."
)

_HF_REPO_ID = "ntn823/phowhisper-tiny-cuchi-int8"


class PhoWhisperEngine:
    def __init__(self, model_path: str = "", cpu_threads: int = 2):
        self.model_path = model_path or getattr(Config, "PHOWHISPER_MODEL_PATH", "")
        self.initial_prompt = getattr(Config, "PHOWHISPER_INITIAL_PROMPT", None) or _DEFAULT_INITIAL_PROMPT
        if not self.model_path or not os.path.exists(self.model_path):
            candidates = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "phowhisper-tiny-ct2-int8"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "phowhisper-tiny-ct2-int8"),
                os.path.join("models", "phowhisper-tiny-ct2-int8"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    self.model_path = c
                    break

        self.cpu_threads = getattr(Config, "PHOWHISPER_CPU_THREADS", cpu_threads)
        self.model = None
        self._init_model()

    def _init_model(self):
        if WhisperModel is None:
            raise ImportError("Chưa cài đặt thư viện faster-whisper! Chạy: pip install faster-whisper")

        target_model = self.model_path
        if not os.path.exists(target_model):
            print(f"[PHOWHISPER] Không tìm thấy model tại local ({target_model}) -> Tự động nạp từ HuggingFace: {_HF_REPO_ID}...")
            target_model = _HF_REPO_ID

        print(f"[PHOWHISPER] Đang nạp mô hình CT2 INT8: {target_model} (cpu_threads={self.cpu_threads})...")
        self.model = WhisperModel(
            target_model,
            device="cpu",
            compute_type="int8",
            cpu_threads=self.cpu_threads,
            num_workers=1
        )
        print("[PHOWHISPER] Nạp mô hình PhoWhisper thành công!")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Nhận diện âm thanh, trả về chuỗi text đã qua normalizer."""
        res = self.transcribe_detailed(audio, sample_rate)
        return res.get("text", "")

    def transcribe_detailed(self, audio: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Nhận diện âm thanh chi tiết, đo chính xác compute_time, conf, no_speech_prob.
        Không dùng vad_filter nội bộ của whisper (đã qua VAD tiền xử lý trước).
        """
        if self.model is None or len(audio) == 0:
            return {
                "text": "",
                "raw_text": "",
                "conf": 0.0,
                "avg_logprob": -99.0,
                "no_speech_prob": 1.0,
                "compute_time_ms": 0.0,
            }

        t_start = time.perf_counter()

        segments, info = self.model.transcribe(
            audio,
            language="vi",
            task="transcribe",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            initial_prompt=self.initial_prompt,
            condition_on_previous_text=False,
            vad_filter=False,
            without_timestamps=True,
            max_new_tokens=20,
            repetition_penalty=1.3,
            no_repeat_ngram_size=2,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )

        texts = []
        logprobs = []
        no_speech_probs = []

        for seg in segments:
            texts.append(seg.text)
            if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
                logprobs.append(seg.avg_logprob)
            if hasattr(seg, "no_speech_prob") and seg.no_speech_prob is not None:
                no_speech_probs.append(seg.no_speech_prob)

        compute_ms = (time.perf_counter() - t_start) * 1000.0
        raw_text = " ".join(texts).strip()

        avg_logprob = float(np.mean(logprobs)) if logprobs else -99.0
        no_speech_prob = float(np.mean(no_speech_probs)) if no_speech_probs else 0.0

        if avg_logprob > -90:
            conf = float(math.exp(max(-10.0, min(0.0, avg_logprob))))
        else:
            conf = 0.0

        clean_text = normalize_whisper_text(raw_text)

        return {
            "text": clean_text,
            "raw_text": raw_text,
            "conf": conf,
            "avg_logprob": avg_logprob,
            "no_speech_prob": no_speech_prob,
            "compute_time_ms": compute_ms,
        }


def get_phowhisper_engine(model_path: str = "", cpu_threads: int = 2) -> PhoWhisperEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = PhoWhisperEngine(model_path, cpu_threads)
        return _engine_instance

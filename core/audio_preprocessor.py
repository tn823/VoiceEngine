# -*- coding: utf-8 -*-
"""
Audio Preprocessor for QA Voice Recognition
Chuyên dụng cho môi trường nhà xưởng công nghiệp:
1. DC-Offset Removal: Triệt tiêu điện áp một chiều gây lệch trục 0.
2. High-Pass Filter (Butterworth 2nd-order, fc=60Hz):
   Cắt hoàn toàn tiếng ù băng tải, rung động mặt bàn, tần số AC 50/60Hz.
3. Soft Limiter / Peak Normalizer:
   Nén mượt tín hiệu khi âm lượng quá lớn (>24000), chống vỡ tiếng (clipping).
4. Silero VAD (ONNX Runtime):
   Phát hiện tiếng nói người với độ chính xác cao bằng AI Deep Learning.
5. Automatic Gain Control (AGC): Nâng giọng nói yếu lên dải chuẩn.
6. Trim & Pad (chuẩn bị đầu vào cho PhoWhisper): cắt khoảng lặng thừa ở 2 đầu
   và bọc 300ms silence mỗi bên.
"""

import os
import numpy as np


class SileroVADDetector:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.55):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.session = None
        self.buffer = np.zeros(0, dtype=np.float32)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._sr = np.array([self.sample_rate], dtype=np.int64)

        # Ưu tiên load ONNX model cục bộ
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "models", "silero_vad.onnx"),
            os.path.join(os.path.dirname(__file__), "models", "silero_vad.onnx"),
            os.path.join("models", "silero_vad.onnx"),
        ]
        try:
            from config import Config
            if hasattr(Config, "SILERO_VAD_MODEL_PATH") and Config.SILERO_VAD_MODEL_PATH:
                candidates.insert(0, Config.SILERO_VAD_MODEL_PATH)
        except Exception:
            pass

        model_path = None
        for p in candidates:
            if os.path.exists(p):
                model_path = p
                break

        if model_path:
            try:
                import onnxruntime as ort
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                self.session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
                print(f"[AUDIO_PREPROCESSOR] Đã nạp Silero VAD Pure ONNX ({os.path.basename(model_path)}, threshold={self.threshold})", flush=True)
            except Exception as e:
                print(f"[AUDIO_PREPROCESSOR] Cảnh báo: Không thể nạp Silero VAD ({e})", flush=True)
                self.session = None
        else:
            print("[AUDIO_PREPROCESSOR] Cảnh báo: Không tìm thấy file silero_vad.onnx", flush=True)

    @property
    def is_available(self) -> bool:
        return self.session is not None

    def process_chunk(self, chunk_f32: np.ndarray) -> tuple[bool, float]:
        """
        Nhận 1 chunk audio float32, chia thành các frame 512 samples
        và chạy qua Silero VAD Pure ONNX. Trả về (is_speech, max_probability).
        """
        if self.session is None or chunk_f32 is None or len(chunk_f32) == 0:
            return False, 0.0

        self.buffer = np.concatenate((self.buffer, chunk_f32))
        probs = []
        while len(self.buffer) >= 512:
            frame = self.buffer[:512].reshape(1, 512).astype(np.float32)
            self.buffer = self.buffer[512:]
            try:
                out, self._state = self.session.run(None, {
                    'input': frame,
                    'state': self._state,
                    'sr': self._sr
                })
                probs.append(float(out[0][0]))
            except Exception as e:
                if not getattr(self, "_logged_inference_err", False):
                    print(f"[AUDIO_PREPROCESSOR] Cảnh báo lỗi Silero VAD ONNX: {e} -> Tự động fallback về RMS VAD", flush=True)
                    self._logged_inference_err = True
                self.session = None
                return False, 0.0

        if probs:
            max_p = max(probs)
            return (max_p >= self.threshold), max_p
        return False, 0.0

    def reset(self):
        self.buffer = np.zeros(0, dtype=np.float32)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)


class AudioPreprocessor:
    def __init__(
        self,
        sample_rate: int = 16000,
        noise_gate_threshold: int = 180,
        highpass_cutoff: float = 60.0,
        enable_highpass: bool = True,
        enable_limiter: bool = True,
        peak_limit: float = 24000.0,
        enable_agc: bool = True,
        agc_target_rms: float = 1500.0,
        agc_max_gain: float = 6.0,
        enable_vad: bool = True,
        vad_threshold: float = 0.55,
        enable_denoise: bool = False,
        denoise_prop: float = 0.50,
    ):
        self.sample_rate = sample_rate
        self.noise_gate_threshold = noise_gate_threshold
        self.highpass_cutoff = highpass_cutoff
        self.enable_highpass = enable_highpass
        self.enable_limiter = enable_limiter
        self.peak_limit = peak_limit
        self.enable_agc = enable_agc
        self.agc_target_rms = agc_target_rms
        self.agc_max_gain = agc_max_gain
        self.enable_vad = enable_vad
        self.enable_denoise = enable_denoise
        self.denoise_prop = denoise_prop

        self._zi = None
        self._b = None
        self._a = None

        if self.enable_highpass:
            try:
                from scipy import signal
                self._b, self._a = signal.butter(2, self.highpass_cutoff, btype='highpass', fs=self.sample_rate)
                self._zi = signal.lfilter_zi(self._b, self._a)
            except Exception as e:
                print(f"[AUDIO_PREPROCESSOR] Cảnh báo: không khởi tạo được High-Pass Filter ({e})", flush=True)
                self.enable_highpass = False

        self.vad = None
        if self.enable_vad:
            self.vad = SileroVADDetector(sample_rate=self.sample_rate, threshold=vad_threshold)
            if not self.vad.is_available:
                self.vad = None

    def reset(self):
        """Reset trạng thái bộ lọc (ví dụ khi đổi mic hoặc restart stream)."""
        if self.enable_highpass and self._b is not None:
            from scipy import signal
            self._zi = signal.lfilter_zi(self._b, self._a)
        if self.vad is not None:
            self.vad.reset()

    def process_chunk(self, raw_bytes: bytes) -> tuple[bytes, int]:
        """
        Xử lý 1 chunk audio PCM int16 (16kHz mono).
        Trả về: (processed_bytes, rms)
        """
        if not raw_bytes:
            return raw_bytes, 0

        # Chuyển int16 -> float32 để tính toán biên độ không bị tràn số
        data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)

        # 1. Khử DC Offset (Đưa điểm cân bằng sóng âm về đúng trục 0)
        data = data - np.mean(data)

        # 2. Lọc thông cao (Cắt ù rung băng tải, động cơ < 60Hz)
        if self.enable_highpass and self._zi is not None:
            from scipy import signal
            data, self._zi = signal.lfilter(self._b, self._a, data, zi=self._zi)

        # Tính RMS sau khi lọc tần số thấp
        rms = int(np.sqrt(np.mean(data ** 2)))

        # 3. Soft Limiter (Chống vỡ tiếng / clipping khi nói quá to hoặc sát mic)
        if self.enable_limiter:
            peak = np.max(np.abs(data))
            if peak > self.peak_limit:
                scale = self.peak_limit / peak
                data = data * scale

        # Đưa về int16 an toàn
        processed = np.clip(data, -32768, 32767).astype(np.int16)
        return processed.tobytes(), rms

    def is_speech(self, chunk_f32: np.ndarray, rms: int) -> tuple[bool, float]:
        """
        Kiểm tra chunk hiện tại có tiếng người nói hay không.
        Sử dụng RMS làm cổng phát hiện chính. Silero VAD hỗ trợ cộng hưởng.
        """
        is_rms_speech = (rms >= self.noise_gate_threshold)

        if self.vad is not None and self.vad.is_available:
            is_vad_speech, vad_prob = self.vad.process_chunk(chunk_f32)
            return (is_rms_speech or (is_vad_speech and rms >= 60)), vad_prob

        return is_rms_speech, (1.0 if is_rms_speech else 0.0)

    def prepare_for_asr(self, audio: np.ndarray, sample_rate: int | None = None) -> np.ndarray:
        """
        Chuẩn hoá 1 câu nói (float32, dải [-1, 1]) trước khi đưa vào ASR:
        1. Cắt bỏ khoảng lặng dư ở hai đầu (trim).
        2. Khử tạp âm nền công nghiệp (nếu bật denoise).
        3. AGC: nâng biên độ về dải chuẩn (agc_target_rms).
        4. Bù 300ms silence mỗi bên cho PhoWhisper.
        """
        if audio is None or len(audio) == 0:
            return np.zeros(0, dtype=np.float32)

        sr = int(sample_rate or self.sample_rate)
        x = np.asarray(audio, dtype=np.float32).flatten()

        # 1. Trim khoảng lặng dư ở 2 đầu (giữ lại 250ms đệm an toàn để không chém vào âm đầu)
        floor = max(30.0, float(self.noise_gate_threshold) * 0.50) / 32768.0
        loud = np.flatnonzero(np.abs(x) > floor)
        if loud.size:
            keep = int(sr * 0.25)
            start = max(0, int(loud[0]) - keep)
            stop = min(x.size, int(loud[-1]) + keep + 1)
            x = x[start:stop]

        # 2. Khử tạp âm nền nếu bật
        if self.enable_denoise and x.size > sr * 0.2:
            try:
                import noisereduce as nr
                x = nr.reduce_noise(y=x, sr=sr, stationary=True, prop_decrease=self.denoise_prop)
            except Exception:
                pass

        # 3. AGC - nâng biên độ về dải chuẩn:
        if self.enable_agc and x.size:
            rms = float(np.sqrt(np.mean(x ** 2))) * 32768.0
            if rms >= 70.0:
                gain = float(self.agc_target_rms) / rms
                gain = float(np.clip(gain, 1.0, self.agc_max_gain))
                if gain > 1.0:
                    x = x * gain
                    peak = float(np.max(np.abs(x)))
                    if peak > 0.95:
                        x = x * (0.95 / peak)

        # 4. Bọc silence 2 đầu (300ms mỗi bên)
        pad = np.zeros(int(sr * 0.30), dtype=np.float32)
        x = np.concatenate((pad, x, pad))

        return np.clip(x, -1.0, 1.0).astype(np.float32)

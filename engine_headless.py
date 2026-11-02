# -*- coding: utf-8 -*-
"""
VoiceEngine Headless Entry Point
Chạy ngầm độc lập hoặc tích hợp với NetTMC qua Standard I/O Pipe (NDJSON).
Hoàn toàn loại bỏ PyQt5, không mở GUI, sử dụng 100% PhoWhisper CT2 INT8 + Silero VAD.
"""

import os
import sys
import json
import time
import queue
import signal
import argparse
import numpy as np

# Cấu hình UTF-8 cho stream
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from core.audio_preprocessor import AudioPreprocessor
from core.phowhisper_engine import get_phowhisper_engine
from core.command_parser import parse_command

# Giữ lại stdout gốc trước khi chuyển hướng sang stderr (phục vụ IPC)
_REAL_STDOUT = sys.stdout
_IS_IPC_MODE = False


def emit_ipc_event(data: dict):
    """Gửi 1 dòng NDJSON duy nhất qua Standard Output gốc tới NetTMC."""
    global _REAL_STDOUT
    if _REAL_STDOUT is None:
        return
    try:
        line = json.dumps(data, ensure_ascii=False)
        _REAL_STDOUT.write(line + "\n")
        _REAL_STDOUT.flush()
    except Exception as e:
        sys.stderr.write(f"[IPC_ERROR] Không thể gửi dữ liệu qua pipe: {e}\n")
        sys.stderr.flush()


def resolve_audio_device(device_spec, sd):
    """
    Xác định device index phù hợp từ chỉ định của người dùng hoặc tự động chọn.
    Ưu tiên Windows WASAPI để đạt độ trễ thấp và độ ổn định cao.
    """
    devices = sd.query_devices()
    wasapi_id = next((i for i, api in enumerate(sd.query_hostapis()) if "wasapi" in api["name"].lower()), None)

    if isinstance(device_spec, int):
        return device_spec

    spec_str = str(device_spec).strip().lower() if device_spec else ""

    # 1. Nếu có tên thiết bị chỉ định (vd: 'oris', 'realtek', 'usb'):
    if spec_str:
        if wasapi_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == wasapi_id and spec_str in dev["name"].lower():
                    return idx
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0 and spec_str in dev["name"].lower():
                return idx

    # 2. Không chỉ định: tìm mic mặc định qua WASAPI
    default_in = sd.default.device[0] if sd.default.device else None
    if wasapi_id is not None and default_in is not None and default_in < len(devices):
        def_name = devices[default_in]["name"]
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == wasapi_id and dev["name"] == def_name:
                return idx

    return default_in


def run_engine(ipc_mode: bool = False, device_spec=None, noise_gate: int = 180):
    global _IS_IPC_MODE, _REAL_STDOUT
    _IS_IPC_MODE = ipc_mode

    if _IS_IPC_MODE:
        # Cách ly hoàn toàn stdout: mọi print() từ các thư viện con sẽ chảy vào stderr
        sys.stdout = sys.stderr

    print("=" * 60)
    print("VoiceEngine Headless (PhoWhisper CT2 INT8 + Silero VAD)")
    print(f"Chế độ: {'IPC PIPE (cho NetTMC)' if _IS_IPC_MODE else 'CONSOLE TEST'}")
    print("=" * 60)

    try:
        import sounddevice as sd
    except ImportError as e:
        err = f"Lỗi thiếu thư viện sounddevice: {e}"
        print(f"[ERROR] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "message": err})
        return

    # Khởi tạo DSP Audio Preprocessor
    preprocessor = AudioPreprocessor(
        sample_rate=Config.SAMPLE_RATE,
        noise_gate_threshold=noise_gate,
        highpass_cutoff=60.0,
        enable_highpass=Config.AUDIO_ENABLE_HIGHPASS,
        enable_limiter=Config.AUDIO_ENABLE_LIMITER,
        enable_agc=Config.AUDIO_ENABLE_AGC,
        agc_target_rms=Config.AUDIO_AGC_TARGET_RMS,
        agc_max_gain=Config.AUDIO_AGC_MAX_GAIN,
        enable_vad=Config.AUDIO_ENABLE_SILERO_VAD,
        vad_threshold=Config.AUDIO_SILERO_VAD_THRESHOLD,
        enable_denoise=Config.AUDIO_ENABLE_DENOISE,
        denoise_prop=Config.AUDIO_DENOISE_PROP,
    )

    # Nạp PhoWhisper Engine
    print("[INIT] Đang nạp mô hình PhoWhisper CT2 INT8...")
    try:
        phowhisper = get_phowhisper_engine(Config.PHOWHISPER_MODEL_PATH, cpu_threads=Config.PHOWHISPER_CPU_THREADS)
    except Exception as e:
        err = f"Lỗi không nạp được PhoWhisper: {e}"
        print(f"[ERROR] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "message": err})
        return

    # Xác định microphone
    target_device = resolve_audio_device(device_spec, sd)
    dev_name = "Default"
    if target_device is not None:
        try:
            info = sd.query_devices(target_device)
            dev_name = info.get("name", str(target_device))
        except Exception:
            dev_name = str(target_device)

    print(f"[MIC] Thiết bị sử dụng: Index={target_device} ('{dev_name}')")

    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(bytes(indata))

    try:
        stream = sd.RawInputStream(
            samplerate=Config.SAMPLE_RATE,
            blocksize=Config.BLOCK_SIZE,
            dtype="int16",
            channels=1,
            device=target_device,
            callback=audio_callback,
        )
        stream.start()
    except Exception as e:
        err = f"Không mở được Microphone: {e}"
        print(f"[ERROR] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "message": err})
        return

    print("[READY] VoiceEngine đã sẵn sàng và đang lắng nghe microphone...")
    if _IS_IPC_MODE:
        emit_ipc_event({
            "event": "ready",
            "device": dev_name,
            "sample_rate": Config.SAMPLE_RATE,
            "engine": "phowhisper-tiny-ct2-int8"
        })

    # Vòng lặp lắng nghe và xử lý VAD + Whisper
    from collections import deque
    pre_ring = deque(maxlen=5)  # 500ms đệm trước khi nói
    speech_buffer = []
    silent_count = 0
    is_speaking = False

    min_speech_chunks = 3     # >= 0.3s
    max_silence_chunks = 4    # 0.4s dừng nói -> chốt câu
    max_speech_chunks = 28    # 2.8s tối đa cho 1 câu lệnh

    running = True

    def sig_handler(sig, frame):
        nonlocal running
        print("\n[STOP] Đang dừng VoiceEngine...")
        running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    while running:
        try:
            raw_data = audio_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        proc_data, rms = preprocessor.process_chunk(raw_data)
        chunk_f32 = np.frombuffer(proc_data, dtype=np.int16).astype(np.float32) / 32768.0

        is_speech_chunk, vad_prob = preprocessor.is_speech(chunk_f32, rms)

        if is_speech_chunk:
            if not is_speaking:
                is_speaking = True
                speech_buffer = list(pre_ring)
                pre_ring.clear()
                if not _IS_IPC_MODE:
                    print("\r🎙️  [VAD] Đang thu âm...", end="", flush=True)
            speech_buffer.append(chunk_f32)
            silent_count = 0
        else:
            if is_speaking:
                speech_buffer.append(chunk_f32)
                silent_count += 1
            else:
                pre_ring.append(chunk_f32)

        # Chốt câu nói
        should_commit = is_speaking and (
            (silent_count >= max_silence_chunks and len(speech_buffer) >= min_speech_chunks)
            or len(speech_buffer) >= max_speech_chunks
        )

        if should_commit:
            audio_full = np.concatenate(speech_buffer)
            speech_buffer = []
            silent_count = 0
            is_speaking = False

            if not _IS_IPC_MODE:
                print("\r⏳ [ASR] Đang nhận diện PhoWhisper...", end="", flush=True)

            # Lọc năng lượng thô
            peak_amp = float(np.max(np.abs(audio_full))) * 32768.0
            rms_amp = float(np.sqrt(np.mean(audio_full ** 2))) * 32768.0
            if peak_amp < 2500 or rms_amp < 80:
                if not _IS_IPC_MODE:
                    print("\r" + " " * 50 + "\r", end="", flush=True)
                continue

            # Chuẩn hóa qua DSP
            audio_asr = preprocessor.prepare_for_asr(audio_full)

            # Transcribe qua PhoWhisper
            w_res = phowhisper.transcribe_detailed(audio_asr)
            text = w_res.get("text", "").strip()
            raw_text = w_res.get("raw_text", "").strip()
            conf = w_res.get("conf", 0.0)
            lat_ms = w_res.get("compute_time_ms", 0.0)

            if not _IS_IPC_MODE:
                print("\r" + " " * 50 + "\r", end="", flush=True)

            if not text or text in (".", "...", ".."):
                continue

            # Phân tích câu lệnh QA
            cmd = parse_command(text)

            # Hiển thị hoặc gửi IPC
            if _IS_IPC_MODE:
                # Gửi sự kiện âm thanh nhận dạng
                emit_ipc_event({
                    "event": "speech",
                    "text": text,
                    "raw_text": raw_text,
                    "conf": round(conf, 4),
                    "latency_ms": round(lat_ms, 1),
                })
                # Nếu khớp lệnh hợp lệ -> gửi sự kiện command
                if cmd is not None:
                    emit_ipc_event({
                        "event": "command",
                        "cmd": cmd,
                        "text": text,
                        "conf": round(conf, 4),
                        "latency_ms": round(lat_ms, 1),
                    })
            else:
                # Chế độ Console cho kỹ sư test trực tiếp
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] Nghe được: '{text}' (thô: '{raw_text}', conf={conf:.2f}, {lat_ms:.0f}ms)")
                if cmd:
                    print(f"     👉 LỆNH KHỚP: {json.dumps(cmd, ensure_ascii=False)}")
                else:
                    print(f"     ⚠️  Không khớp lệnh QA hợp lệ.")

    try:
        stream.stop()
        stream.close()
    except Exception:
        pass
    print("[STOP] VoiceEngine đã dừng hoàn toàn.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceEngine Headless (PhoWhisper CT2 INT8 + Silero VAD)")
    parser.add_argument("--ipc", action="store_true", help="Chạy ở chế độ IPC Pipe (gửi NDJSON qua stdout)")
    parser.add_argument("--device", type=str, default=None, help="Chỉ định Microphone (index hoặc tên thiết bị)")
    parser.add_argument("--gate", type=int, default=180, help="Ngưỡng phát hiện âm thanh Noise Gate RMS (mặc định 180)")
    args = parser.parse_args()

    run_engine(ipc_mode=args.ipc, device_spec=args.device, noise_gate=args.gate)

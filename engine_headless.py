# -*- coding: utf-8 -*-
"""
VoiceEngine Headless Entry Point
Chạy ngầm độc lập hoặc tích hợp với NetTMC qua Standard I/O Pipe (NDJSON).
Hoàn toàn loại bỏ PyQt5, không mở GUI, sử dụng 100% PhoWhisper CT2 INT8 + Silero VAD.
Bao gồm:
- Visual Box Log ANSI trực quan, dễ nhìn như bản CC_QA_VOICE (chế độ Console Test).
- Cơ chế Shadowing: Ghi nhận file âm thanh .wav và audit JSONL để kiểm tra và huấn luyện lại.
"""

import os
import sys
import wave
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

_REAL_STDOUT = sys.stdout
_IS_IPC_MODE = False

_POS_BASE_NAMES = {
    1: "Mũi",
    2: "Hông ngoài",
    3: "Hông trong",
    4: "Lưỡi gà",
    5: "Gót",
    6: "Đế"
}


def get_pos_label(pos_id: int, bold: bool = True) -> str:
    """Trả về nhãn vị trí: Mũi (1) với số in đậm ANSI."""
    name = _POS_BASE_NAMES.get(pos_id, f"Vị trí #{pos_id}")
    if bold:
        return f"{name} (\033[1m{pos_id}\033[0m)"
    return f"{name} ({pos_id})"


_DEFECT_SHORT_MAP = {
    1: "01 - Da xù / Sai liệu",
    2: "02 - Lưới xéo / Hư liệu",
    3: "03 - Tách lớp / Sai liệu",
    4: "04 - Hư đế / Bọng khí / Nhăn",
    5: "05 - Khác màu",
    6: "06 - Sai hướng chặt",
    7: "07 - Lạng / Gấp mép sai",
    8: "08 - Thêu / In / No sew",
    9: "09 - Bung chỉ / Bỏ mũi / Tưa",
    10: "10 - Sụp mí / Lỗ kim",
    11: "11 - Đục lỗ",
    12: "12 - Mặt giày / Cộm / Nhăn",
    13: "13 - To nhỏ các chi tiết",
    14: "14 - Phụ liệu / Kim loại",
    15: "15 - Mũi / Gót lệch tâm",
    16: "16 - Độ cao mũi / Hông / Gót",
    17: "17 - Mài / Lem keo / Lem nước",
    18: "18 - Hở keo",
    19: "19 - Miếng lót giày",
    20: "20 - Dây giày",
    21: "21 - Vệ sinh giày",
    22: "22 - Tem nhãn / Đóng gói",
    23: "23 - Ngay thẳng tâm",
    24: "24 - Lỗi khác"
}


def _print_visual_command(text: str, cmd: dict | None, lat_ms: float = 0.0, conf: float = 0.0):
    """Hiển thị visual log dạng box màu ANSI đẹp mắt y như CC_QA_VOICE."""
    perf_str = f"⏱️ {lat_ms:.0f}ms | 🎯 Tin cậy: {int(conf * 100)}%" if lat_ms > 0 else ""

    if cmd:
        intent = cmd.get("intent")
        if intent == "inspection":
            pos_id = cmd.get("position", 0)
            def_id = cmd.get("defect", 0)
            pos_label = get_pos_label(pos_id, bold=True)
            def_label = _DEFECT_SHORT_MAP.get(def_id, f"Lỗi #{def_id:02d}")
            print(f"\n┌── 🎙️ [P211] NHẬN DIỆN THÀNH CÔNG: CHẤM LỖI QA " + "─" * 28 + "┐", flush=True)
            print(f"│  📍 Vị trí : \033[96m{pos_label:<26}\033[0m  ⚠️ Lỗi: \033[93m{def_label:<32}\033[0m │", flush=True)
            print(f"│  📝 Giọng  : \"\033[92m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "pass":
            print(f"\n┌── ✅ [P211] KẾT QUẢ QUY TRÌNH: SẢN PHẨM ĐẠT (PASS) " + "─" * 23 + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[92m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "reins_pass":
            print(f"\n┌── 🔄 [P211] TÁI KIỂM: ĐẠT LẠI / SỬA ĐẠT (RE-PASS) " + "─" * 21 + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[92m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "reins_fail":
            pos_id = cmd.get("position", 0)
            def_id = cmd.get("defect", 0)
            pos_label = get_pos_label(pos_id, bold=True)
            def_label = _DEFECT_SHORT_MAP.get(def_id, f"Lỗi #{def_id:02d}")
            print(f"\n┌── 🔄 [P211] TÁI KIỂM: LỖI LẠI / SỬA LẠI (RE-FAIL) " + "─" * 20 + "┐", flush=True)
            print(f"│  📍 Vị trí : \033[96m{pos_label:<26}\033[0m  ⚠️ Lỗi: \033[93m{def_label:<32}\033[0m │", flush=True)
            print(f"│  📝 Giọng  : \"\033[92m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "fail":
            print(f"\n┌── ❌ [P211] KẾT QUẢ QUY TRÌNH: SẢN PHẨM LỖI (FAIL) " + "─" * 20 + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[93m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "sua":
            print(f"\n┌── 🔄 [P211] TÁI KIỂM: LỖI LẠI / SỬA LẠI (RE-FAIL) " + "─" * 20 + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[93m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "cancel":
            print(f"\n┌── ↩️ [P211] LỆNH ĐIỀU KHIỂN: HỦY BỎ / QUAY LẠI " + "─" * 24 + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[91m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "bare_number":
            idx = cmd.get("index", 0)
            def_label = _DEFECT_SHORT_MAP.get(idx, f"Lỗi #{idx:02d}")
            print(f"\n┌── 🔢 [P211] NHẬN SỐ LỖI: {def_label} " + "─" * max(1, 45 - len(def_label)) + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[96m{text}\033[0m\"" + " " * max(1, 38 - len(text)) + f"{perf_str:<25} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        elif intent == "position":
            pos_id = cmd.get("position", 0)
            pos_label = get_pos_label(pos_id, bold=True)
            print(f"\n┌── 📍 [P211] CHỌN VỊ TRÍ: {pos_label} " + "─" * max(1, 50 - len(pos_label)) + "┐", flush=True)
            print(f"│  📝 Giọng  : \"\033[96m{text}\033[0m\" (Chờ đọc số lỗi...)" + " " * max(1, 18 - len(text)) + f"{perf_str:<20} │", flush=True)
            print("└──" + "─" * 70 + "┘\n", flush=True)

        else:
            print(f"🎤 [P211] Lệnh: {cmd} | \"{text}\" ({perf_str})", flush=True)
    else:
        print(f"\n⚠️  [P211] Nghe được: \"\033[90m{text}\033[0m\" ({perf_str}) -> Không khớp lệnh QA.", flush=True)


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


def resolve_audio_device(device_spec, sd, target_sr: int = Config.SAMPLE_RATE):
    """
    Xác định device index phù hợp từ chỉ định của người dùng hoặc tự động chọn.
    Tự động kiểm tra tính tương thích của sample rate (16000Hz).
    Ưu tiên: WASAPI (nếu hỗ trợ 16kHz) -> DirectSound -> MME.
    """
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    wasapi_id = next((i for i, api in enumerate(hostapis) if "wasapi" in api["name"].lower()), None)
    dsound_id = next((i for i, api in enumerate(hostapis) if "directsound" in api["name"].lower()), None)
    mme_id = next((i for i, api in enumerate(hostapis) if "mme" in api["name"].lower()), None)

    def is_rate_supported(idx):
        if idx is None or idx < 0 or idx >= len(devices):
            return False
        if devices[idx].get("max_input_channels", 0) <= 0:
            return False
        try:
            sd.check_input_settings(device=idx, samplerate=target_sr, channels=1, dtype="int16")
            return True
        except Exception:
            return False

    # Xử lý khi người dùng truyền số (dạng int hoặc chuỗi số "1", "7")
    target_idx = None
    if isinstance(device_spec, int):
        target_idx = device_spec
    elif isinstance(device_spec, str) and device_spec.strip().isdigit():
        target_idx = int(device_spec.strip())

    if target_idx is not None:
        if is_rate_supported(target_idx):
            return target_idx
        # Nếu index chỉ định không hỗ trợ 16kHz (ví dụ WASAPI Realtek), tự động tìm phiên bản DirectSound/MME của thiết bị đó
        if 0 <= target_idx < len(devices):
            dev_name = devices[target_idx]["name"]
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev["name"] == dev_name and is_rate_supported(idx):
                    return idx
        return target_idx

    spec_str = str(device_spec).strip().lower() if device_spec else ""

    # 1. Nếu có tên thiết bị chỉ định (vd: 'realtek', 'redmi', 'usb'):
    if spec_str:
        # Thử WASAPI trước nếu hỗ trợ 16kHz
        if wasapi_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == wasapi_id and spec_str in dev["name"].lower():
                    if is_rate_supported(idx):
                        return idx
        # Thử DirectSound
        if dsound_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == dsound_id and spec_str in dev["name"].lower():
                    if is_rate_supported(idx):
                        return idx
        # Thử bất kỳ API nào khác
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0 and spec_str in dev["name"].lower():
                if is_rate_supported(idx):
                    return idx

    # 2. Không chỉ định: tìm mic mặc định (ưu tiên WASAPI -> DirectSound -> MME)
    default_in = sd.default.device[0] if sd.default.device else None
    if default_in is not None and default_in < len(devices):
        def_name = devices[default_in]["name"]
        # Ưu tiên WASAPI cùng tên nếu chạy được 16kHz
        if wasapi_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == wasapi_id and dev["name"] == def_name:
                    if is_rate_supported(idx):
                        return idx
        # Ưu tiên DirectSound cùng tên
        if dsound_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == dsound_id and dev["name"] == def_name:
                    if is_rate_supported(idx):
                        return idx
        # MME cùng tên
        if mme_id is not None:
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == mme_id and dev["name"] == def_name:
                    if is_rate_supported(idx):
                        return idx
        # Kiểm tra default_in gốc
        if is_rate_supported(default_in):
            return default_in

    # 3. Fallback: tìm bất kỳ thiết bị input nào hỗ trợ 16kHz
    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0 and is_rate_supported(idx):
            return idx

    return default_in


def run_engine(ipc_mode: bool = False, device_spec=None, noise_gate: int = 180, wav_mode: str = "matched_only"):
    """
    wav_mode:
      - 'matched_only': Chỉ lưu file .wav cho các câu lệnh QA hợp lệ (tiết kiệm ổ cứng).
      - 'all': Lưu toàn bộ mọi đoạn âm thanh được nhận diện.
      - 'none': Không lưu file .wav nào.
    """
    global _IS_IPC_MODE, _REAL_STDOUT
    _IS_IPC_MODE = ipc_mode

    if _IS_IPC_MODE:
        # Cách ly stdout: mọi print() từ thư viện con đi vào stderr
        sys.stdout = sys.stderr

    if not _IS_IPC_MODE:
        print("=" * 72)
        print("  VOICE ENGINE HEADLESS (PhoWhisper CT2 INT8 + Silero VAD)")
        print(f"  Chế độ: {'IPC PIPE (cho NetTMC)' if _IS_IPC_MODE else 'CONSOLE TEST'}")
        print(f"  Chế độ ghi âm (.wav): {wav_mode.upper()}")
        print("=" * 72)

    try:
        import sounddevice as sd
    except ImportError as e:
        err = f"Lỗi thiếu thư viện sounddevice: {e}"
        print(f"[ERROR] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "message": err})
        return

    # Khởi tạo thư mục shadow logs
    shadow_wav_dir = os.path.join(Config.LOGS_DIR, "shadow_wav")
    shadow_audit_file = os.path.join(Config.LOGS_DIR, "shadow_audit.jsonl")
    if wav_mode != "none":
        os.makedirs(shadow_wav_dir, exist_ok=True)
    os.makedirs(Config.LOGS_DIR, exist_ok=True)

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
    if not _IS_IPC_MODE:
        print("[INIT] Đang nạp mô hình PhoWhisper CT2 INT8...")
    try:
        phowhisper = get_phowhisper_engine(Config.PHOWHISPER_MODEL_PATH, cpu_threads=Config.PHOWHISPER_CPU_THREADS)
    except Exception as e:
        err = f"Lỗi không nạp được PhoWhisper: {e}"
        print(f"[ERROR] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "message": err})
        return

    # Microphone
    target_device = resolve_audio_device(device_spec, sd)
    dev_name = "Default"
    if target_device is not None:
        try:
            info = sd.query_devices(target_device)
            dev_name = info.get("name", str(target_device))
        except Exception:
            dev_name = str(target_device)

    if not _IS_IPC_MODE:
        print(f"[MIC] Thiết bị đang dùng: Index={target_device} ('{dev_name}')")

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

    if not _IS_IPC_MODE:
        print("\n🚀 [READY] VoiceEngine đã sẵn sàng! Mời bạn đọc lệnh (Đạt, Đạt lại, Lỗi, Lỗi lại, Số - Số: 1.17, 2.18, 3.17...):")
        print("   (Bấm Ctrl+C để thoát)\n")
    else:
        emit_ipc_event({
            "event": "ready",
            "device": dev_name,
            "sample_rate": Config.SAMPLE_RATE,
            "engine": "phowhisper-tiny-ct2-int8"
        })

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
        if not _IS_IPC_MODE:
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
            is_valid_cmd = (cmd is not None)

            # Bỏ qua tạp âm độ tin cậy thấp nếu không khớp bất kỳ lệnh QA nào
            if not is_valid_cmd and conf < Config.VOICE_MIN_CONFIDENCE:
                continue

            # Xác định có ghi file .wav hay không theo wav_mode
            should_save_wav = False
            if wav_mode == "all":
                should_save_wav = True
            elif wav_mode == "matched_only" and is_valid_cmd:
                should_save_wav = True

            wav_filename = ""
            if should_save_wav:
                try:
                    ts_str = time.strftime("%Y%m%d_%H%M%S")
                    ms_val = int((time.time() % 1) * 1000)
                    wav_filename = f"{ts_str}_{ms_val:03d}.wav"
                    wav_filepath = os.path.join(shadow_wav_dir, wav_filename)

                    pcm_16 = (audio_asr * 32767.0).clip(-32768, 32767).astype(np.int16).tobytes()
                    with wave.open(wav_filepath, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(Config.SAMPLE_RATE)
                        wf.writeframes(pcm_16)
                except Exception:
                    wav_filename = ""

            # LUÔN LUÔN ghi nhật ký JSON đầy đủ (bất kể lệnh đúng hay không)
            try:
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
                audit_record = {
                    "timestamp": time.time(),
                    "time_str": ts_str,
                    "wav_file": wav_filename if wav_filename else None,
                    "raw_whisper": raw_text,
                    "norm_text": text,
                    "conf": round(conf, 4),
                    "latency_ms": round(lat_ms, 1),
                    "intent": cmd.get("intent") if cmd else None,
                    "cmd": cmd,
                    "status": "VALID_COMMAND" if is_valid_cmd else "UNMATCHED"
                }
                with open(shadow_audit_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")
            except Exception:
                pass

            # Xử lý output
            if _IS_IPC_MODE:
                emit_ipc_event({
                    "event": "speech",
                    "text": text,
                    "raw_text": raw_text,
                    "conf": round(conf, 4),
                    "latency_ms": round(lat_ms, 1),
                })
                if is_valid_cmd:
                    emit_ipc_event({
                        "event": "command",
                        "cmd": cmd,
                        "text": text,
                        "conf": round(conf, 4),
                        "latency_ms": round(lat_ms, 1),
                    })
            else:
                _print_visual_command(text, cmd, lat_ms=lat_ms, conf=conf)

    try:
        stream.stop()
        stream.close()
    except Exception:
        pass
    if not _IS_IPC_MODE:
        print("[STOP] VoiceEngine đã dừng hoàn toàn.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceEngine Headless (PhoWhisper CT2 INT8 + Silero VAD)")
    parser.add_argument("--ipc", action="store_true", help="Chạy ở chế độ IPC Pipe (gửi NDJSON qua stdout)")
    parser.add_argument("--device", type=str, default=None, help="Chỉ định Microphone (index hoặc tên thiết bị)")
    parser.add_argument("--gate", type=int, default=180, help="Ngưỡng phát hiện âm thanh Noise Gate RMS (mặc định 180)")
    parser.add_argument(
        "--wav-mode",
        type=str,
        default="matched_only",
        choices=["matched_only", "all", "none"],
        help="Chế độ lưu file .wav: 'matched_only' (chỉ lệnh đúng), 'all' (tất cả), 'none' (không lưu)"
    )
    args = parser.parse_args()

    run_engine(
        ipc_mode=args.ipc,
        device_spec=args.device,
        noise_gate=args.gate,
        wav_mode=args.wav_mode
    )

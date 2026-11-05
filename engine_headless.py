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
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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


# ==============================================================================
# QUẢN LÝ TIẾN TRÌNH & TRẠNG THÁI SỬ DỤNG MICROPHONE
# ==============================================================================
ACTIVE_MICS_FILE = os.path.join(Config.LOGS_DIR, ".active_mics.json")


def _is_pid_alive(pid: int) -> bool:
    """Kiểm tra một Process ID có đang thực sự chạy trên Windows hay không."""
    if not pid or pid <= 0:
        return False
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def get_active_devices() -> dict:
    """Lấy danh sách các Microphone đang được VoiceEngine khác sử dụng."""
    if not os.path.exists(ACTIVE_MICS_FILE):
        return {}
    try:
        with open(ACTIVE_MICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        alive = {}
        my_pid = os.getpid()
        for dev_name, info in data.items():
            pid = info.get("pid")
            if pid and pid != my_pid and _is_pid_alive(pid):
                alive[dev_name] = info
        return alive
    except Exception:
        return {}


def register_active_device(dev_name: str):
    """Đăng ký Microphone đang được sử dụng bởi tiến trình này."""
    try:
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        active = get_active_devices()
        active[dev_name] = {
            "pid": os.getpid(),
            "time": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(ACTIVE_MICS_FILE, "w", encoding="utf-8") as f:
            json.dump(active, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def unregister_active_device(dev_name: str):
    """Gỡ bỏ Microphone khỏi danh sách đang dùng khi tiến trình kết thúc."""
    try:
        if not os.path.exists(ACTIVE_MICS_FILE):
            return
        with open(ACTIVE_MICS_FILE, "r", encoding="utf-8") as f:
            active = json.load(f)
        my_pid = os.getpid()
        if dev_name in active and active[dev_name].get("pid") == my_pid:
            del active[dev_name]
            with open(ACTIVE_MICS_FILE, "w", encoding="utf-8") as f:
                json.dump(active, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def prompt_select_device(sd) -> str | None:
    """
    Hiển thị danh sách Microphone WASAPI để người dùng chọn bằng số (1, 2, 3...)
    Tự động hiển thị trạng thái ĐANG DÙNG (màu đỏ) hoặc SẴN SÀNG (màu xanh).
    Tự động gợi ý mặc định là Mic rảnh đầu tiên để người dùng chỉ cần gõ Enter.
    """
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    wasapi_id = next((i for i, api in enumerate(hostapis) if "wasapi" in api["name"].lower()), None)
    if wasapi_id is None:
        print("[LỖI] Không tìm thấy chuẩn âm thanh Windows WASAPI trên máy này.")
        return None

    wasapi_mics = []
    seen_names = set()
    for idx, dev in enumerate(devices):
        if dev.get("hostapi") == wasapi_id and dev.get("max_input_channels", 0) > 0:
            name = dev["name"].strip()
            if name not in seen_names:
                seen_names.add(name)
                wasapi_mics.append({"index": idx, "name": name, "channels": dev.get("max_input_channels", 1)})

    if not wasapi_mics:
        print("[LỖI] Không phát hiện bất kỳ Microphone WASAPI nào đang cắm trên máy.")
        return None

    active_map = get_active_devices()

    print("\n" + "=" * 76)
    print("           DANH SÁCH MICROPHONE WASAPI TRÊN MÁY TÍNH")
    print("=" * 76)

    default_pick = None
    for i, m in enumerate(wasapi_mics, start=1):
        name = m["name"]
        if name in active_map:
            info = active_map[name]
            status_tag = f"\033[91m🔴 ĐANG SỬ DỤNG (PID {info.get('pid')})\033[0m"
        else:
            if default_pick is None:
                default_pick = i
                status_tag = f"\033[92m🟢 SẴN SÀNG (Gợi ý)\033[0m"
            else:
                status_tag = f"\033[92m🟢 SẴN SÀNG\033[0m"

        print(f"  [{i}] {name:<38} : {status_tag}")

    if default_pick is None:
        default_pick = 1

    print("-" * 76)
    prompt_msg = f"👉 Chọn Microphone (1-{len(wasapi_mics)}) [Mặc định: {default_pick}]: "
    try:
        user_input = input(prompt_msg).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[ĐÃ HỦY] Thoát chương trình.")
        sys.exit(0)

    if not user_input:
        selected_idx = default_pick
    else:
        try:
            selected_idx = int(user_input)
            if not (1 <= selected_idx <= len(wasapi_mics)):
                print(f"[CẢNH BÁO] Số lựa chọn không hợp lệ, tự động chọn [{default_pick}].")
                selected_idx = default_pick
        except ValueError:
            print(f"[CẢNH BÁO] Giá trị nhập không phải là số, tự động chọn [{default_pick}].")
            selected_idx = default_pick

    chosen_dev = wasapi_mics[selected_idx - 1]
    chosen_name = chosen_dev["name"]
    print(f"✅ Đã chọn Microphone [{selected_idx}]: \"{chosen_name}\"\n")
    return chosen_name


def resolve_audio_device(device_spec, sd, target_sr: int = Config.SAMPLE_RATE):
    """
    Xác định device index phù hợp từ chỉ định của người dùng hoặc tự động chọn.
    Hỗ trợ:
      - Khớp tên đầy đủ hoặc từ khóa (substring/alias, vd: 'BY-V', 'Realtek', 'USB').
      - Số thứ tự WASAPI (1, 2...).
      - Tự động gán microphone WASAPI rảnh tiếp theo nếu không chỉ định thiết bị (--device để trống).
      - Tự động nhận diện native sample rate (48000Hz/44100Hz) để resample về 16000Hz.
    Trả về: (target_idx: int | None, stream_sr: int, stream_channels: int, err_code: str | None, err_msg: str | None)
    """
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    wasapi_id = next((i for i, api in enumerate(hostapis) if "wasapi" in api["name"].lower()), None)
    dsound_id = next((i for i, api in enumerate(hostapis) if "directsound" in api["name"].lower()), None)
    mme_id = next((i for i, api in enumerate(hostapis) if "mme" in api["name"].lower()), None)

    def check_device_capability(idx):
        """Kiểm tra khả năng mở stream của thiết bị, trả về (ok, actual_sr, actual_channels)."""
        if idx is None or idx < 0 or idx >= len(devices):
            return False, target_sr, 1
        dev = devices[idx]
        max_in = dev.get("max_input_channels", 0)
        if max_in <= 0:
            return False, target_sr, 1

        # 1. Thử trực tiếp 16000Hz (mono -> stereo)
        test_channels = [1] if max_in == 1 else [1, min(2, max_in)]
        for ch in test_channels:
            try:
                sd.check_input_settings(device=idx, samplerate=target_sr, channels=ch, dtype="int16")
                return True, target_sr, ch
            except Exception:
                pass

        # 2. Thử tần số gốc của phần cứng (native samplerate, vd: 48000Hz, 44100Hz)
        native_sr = int(dev.get("default_samplerate", 48000))
        for ch in test_channels:
            try:
                sd.check_input_settings(device=idx, samplerate=native_sr, channels=ch, dtype="int16")
                return True, native_sr, ch
            except Exception:
                pass

        return False, target_sr, 1

    # Thu thập danh sách các Microphone WASAPI hợp lệ trên máy
    wasapi_mics = []
    if wasapi_id is not None:
        seen_names = set()
        for idx, dev in enumerate(devices):
            if dev.get("hostapi") == wasapi_id and dev.get("max_input_channels", 0) > 0:
                name = dev["name"].strip()
                if name not in seen_names:
                    seen_names.add(name)
                    ok, actual_sr, actual_ch = check_device_capability(idx)
                    if ok:
                        wasapi_mics.append({"index": idx, "name": name, "sr": actual_sr, "channels": actual_ch})

    active_map = get_active_devices()

    # 1. Trường hợp người dùng truyền số nguyên (hoặc chuỗi số "1", "2")
    num_val = None
    if isinstance(device_spec, int):
        num_val = device_spec
    elif isinstance(device_spec, str) and device_spec.strip().isdigit():
        num_val = int(device_spec.strip())

    if num_val is not None:
        # Ưu tiên theo số thứ tự menu WASAPI (1-based: 1, 2...)
        if 1 <= num_val <= len(wasapi_mics):
            m = wasapi_mics[num_val - 1]
            return m["index"], m["sr"], m["channels"], None, None
        # Nếu không khớp menu 1-based, thử theo sounddevice raw index (0-based)
        if 0 <= num_val < len(devices):
            ok, actual_sr, actual_ch = check_device_capability(num_val)
            if ok:
                return num_val, actual_sr, actual_ch, None, None
            dev_name = devices[num_val].get("name", str(num_val))
            return None, target_sr, 1, "unsupported_device", f"Thiết bị index {num_val} ('{dev_name}') không hỗ trợ ghi âm định dạng int16."
        return None, target_sr, 1, "device_not_found", f"Device index {num_val} nằm ngoài danh sách thiết bị ({len(devices)} devices)."

    spec_str = str(device_spec).strip() if device_spec else ""

    # 2. Trường hợp KHÔNG chỉ định thiết bị (spec_str rỗng):
    if not spec_str:
        if not wasapi_mics:
            return None, target_sr, 1, "device_not_found", "Không tìm thấy bất kỳ Microphone WASAPI hợp lệ nào trên máy tính."

        # Ưu tiên chọn mic rảnh đầu tiên (không nằm trong active_map)
        for m in wasapi_mics:
            if m["name"] not in active_map:
                return m["index"], m["sr"], m["channels"], None, None

        # Nếu tất cả mic đều đã được đăng ký, fallback chọn mic đầu tiên
        m = wasapi_mics[0]
        return m["index"], m["sr"], m["channels"], None, None

    spec_lower = spec_str.lower()

    # 3. Khớp tên thiết bị trên WASAPI (Hỗ trợ Substring / Alias):
    if wasapi_mics:
        # Khớp chính xác
        exact = [m for m in wasapi_mics if m["name"].lower() == spec_lower]
        if len(exact) == 1:
            return exact[0]["index"], exact[0]["sr"], exact[0]["channels"], None, None

        # Khớp từ khóa trong tên (ví dụ "BY-V" trong "Microphone (BY-V)" hoặc "Realtek" trong "마이크 (Realtek(R) Audio)")
        matched = [m for m in wasapi_mics if spec_lower in m["name"].lower()]

        if len(matched) == 1:
            return matched[0]["index"], matched[0]["sr"], matched[0]["channels"], None, None

        if len(matched) > 1:
            # Nếu có nhiều thiết bị cùng chứa từ khóa, ưu tiên thiết bị đang rảnh
            free_matched = [m for m in matched if m["name"] not in active_map]
            if len(free_matched) == 1:
                return free_matched[0]["index"], free_matched[0]["sr"], free_matched[0]["channels"], None, None
            if len(free_matched) > 1:
                matched_names = ", ".join(f"'{m['name']}'" for m in free_matched)
                return None, target_sr, 1, "ambiguous_device_name", f"Phát hiện nhiều Microphone rảnh cùng khớp với từ khóa '{spec_str}': {matched_names}."
            matched_names = ", ".join(f"'{m['name']}'" for m in matched)
            return None, target_sr, 1, "ambiguous_device_name", f"Phát hiện {len(matched)} thiết bị cùng khớp với từ khóa '{spec_str}': {matched_names}."

    # Trong chế độ IPC: không tìm thấy WASAPI khớp là lỗi
    if _IS_IPC_MODE:
        return None, target_sr, 1, "device_not_found", f"Không tìm thấy thiết bị Microphone WASAPI khớp với từ khóa: '{spec_str}'"

    # 4. Fallback chỉ dành cho Console Test Mode (DirectSound -> MME)
    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0 and spec_lower in dev["name"].lower():
            ok, actual_sr, actual_ch = check_device_capability(idx)
            if ok:
                return idx, actual_sr, actual_ch, None, None

    return None, target_sr, 1, "device_not_found", f"Không tìm thấy Microphone phù hợp với '{spec_str}'."


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

    # 0. Nếu không chỉ định thiết bị và đang ở Console Test Mode -> Bật Menu chọn Microphone trực quan
    if device_spec is None and not _IS_IPC_MODE:
        device_spec = prompt_select_device(sd)
        if device_spec is None:
            return

    # 1. Kiểm tra phần cứng Microphone trước tiên (Fast Fail - chống lãng phí nạp AI nếu mic lỗi)
    target_device, stream_sr, stream_channels, err_code, err_msg = resolve_audio_device(device_spec, sd)
    if target_device is None:
        err = err_msg or f"Không tìm thấy hoặc không chỉ định thiết bị Microphone hợp lệ (device='{device_spec}')"
        print(f"[FATAL] {err}")
        if _IS_IPC_MODE:
            emit_ipc_event({"event": "error", "code": err_code or "device_not_found", "message": err})
            sys.exit(2)
        return

    dev_name = "Default"
    try:
        info = sd.query_devices(target_device)
        dev_name = info.get("name", str(target_device))
    except Exception:
        dev_name = str(target_device)

    # Đăng ký Microphone này đang bận để các tiến trình VoiceEngine khác phát hiện
    register_active_device(dev_name)
    import atexit
    atexit.register(unregister_active_device, dev_name)

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

    if not _IS_IPC_MODE:
        sr_desc = f"{stream_sr}Hz" if stream_sr == Config.SAMPLE_RATE else f"{stream_sr}Hz -> {Config.SAMPLE_RATE}Hz (Auto-Resample)"
        print(f"[MIC] Thiết bị đang dùng: Index={target_device} ('{dev_name}') | Kênh={stream_channels} | Tần số: {sr_desc}")

    audio_queue = queue.Queue()

    # Tính toán blocksize theo tần số thực tế của stream (đảm bảo luôn là chunk 100ms)
    stream_blocksize = int(round(stream_sr * 0.10))
    needs_resample = (stream_sr != Config.SAMPLE_RATE)
    needs_channel_mix = (stream_channels > 1)

    gcd_val = None
    up_rate, down_rate = None, None
    if needs_resample and stream_sr != 48000:
        import math
        gcd_val = math.gcd(Config.SAMPLE_RATE, stream_sr)
        up_rate = Config.SAMPLE_RATE // gcd_val
        down_rate = stream_sr // gcd_val

    def audio_callback(indata, frames, time_info, status):
        if not needs_resample and not needs_channel_mix:
            audio_queue.put(bytes(indata))
            return

        data = np.frombuffer(indata, dtype=np.int16)
        if needs_channel_mix:
            data = data.reshape(-1, stream_channels)[:, 0]

        if needs_resample:
            if stream_sr == 48000:
                data_16k = data[::3]
            else:
                from scipy import signal
                data_16k = signal.resample_poly(data.astype(np.float32), up_rate, down_rate).astype(np.int16)
        else:
            data_16k = data

        audio_queue.put(data_16k.astype(np.int16).tobytes())

    try:
        stream = sd.RawInputStream(
            samplerate=stream_sr,
            blocksize=stream_blocksize,
            dtype="int16",
            channels=stream_channels,
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
        print(f"\n🚀 [READY] VoiceEngine v{Config.VERSION} đã sẵn sàng! Mời bạn đọc lệnh (Đạt, Đạt lại, Lỗi, Lỗi lại, Số - Số: 1.17, 2.18, 3.17...):")
        print("   (Bấm Ctrl+C để thoát)\n")
    else:
        emit_ipc_event({
            "event": "ready",
            "version": Config.VERSION,
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

    last_chunk_time = time.monotonic()
    last_heartbeat_time = 0.0

    while running:
        try:
            raw_data = audio_queue.get(timeout=0.1)
            last_chunk_time = time.monotonic()
        except queue.Empty:
            raw_data = None

        now = time.monotonic()
        if _IS_IPC_MODE and (now - last_heartbeat_time >= 1.5):
            emit_ipc_event({
                "event": "heartbeat",
                "audio_age": round(now - last_chunk_time, 2),
                "stream_active": bool(stream and stream.active),
                "speaking": is_speaking
            })
            last_heartbeat_time = now

        if raw_data is None:
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

            # Kiểm tra ngưỡng tin cậy (Confidence Guard)
            # Đối với câu ngắn (<= 4 từ): yêu cầu conf >= 0.45
            # Đối với câu dài (> 4 từ, nghi ngờ nói chuyện phiếm): yêu cầu conf >= 0.65
            min_conf = Config.VOICE_MIN_CONFIDENCE
            if len(text.split()) > 4:
                min_conf = max(min_conf, 0.65)

            is_valid_cmd = False
            status_str = "UNMATCHED"

            if cmd is not None:
                if conf >= min_conf:
                    is_valid_cmd = True
                    status_str = "VALID_COMMAND"
                else:
                    cmd = None  # Hủy bỏ lệnh vì độ tin cậy quá thấp (tạp âm / nói chuyện ngoài luồng)
                    status_str = "LOW_CONFIDENCE"
            else:
                if conf < 0.40:
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

            # LUÔN LUÔN ghi nhật ký JSON đầy đủ (bổ sung tên thiết bị để đối chiếu đa mic)
            try:
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
                audit_record = {
                    "timestamp": time.time(),
                    "time_str": ts_str,
                    "device": dev_name,
                    "wav_file": wav_filename if wav_filename else None,
                    "raw_whisper": raw_text,
                    "norm_text": text,
                    "conf": round(conf, 4),
                    "latency_ms": round(lat_ms, 1),
                    "intent": cmd.get("intent") if cmd else None,
                    "cmd": cmd,
                    "status": status_str
                }
                with open(shadow_audit_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")
            except Exception:
                pass

            # Xử lý output
            if _IS_IPC_MODE:
                emit_ipc_event({
                    "event": "speech",
                    "device": dev_name,
                    "text": text,
                    "raw_text": raw_text,
                    "conf": round(conf, 4),
                    "latency_ms": round(lat_ms, 1),
                })
                if is_valid_cmd:
                    emit_ipc_event({
                        "event": "command",
                        "device": dev_name,
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
    unregister_active_device(dev_name)
    if not _IS_IPC_MODE:
        print("[STOP] VoiceEngine đã dừng hoàn toàn.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"VoiceEngine Headless v{Config.VERSION} (PhoWhisper CT2 INT8 + Silero VAD)")
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"VoiceEngine v{Config.VERSION}",
        help="Hiển thị phiên bản VoiceEngine"
    )
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

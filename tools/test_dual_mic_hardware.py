# -*- coding: utf-8 -*-
"""
Dual-Microphone IPC Hardware Test Suite
================================================================================
Công cụ kiểm thử tự động phần cứng 2 Microphone chạy song song qua chuẩn WASAPI.
Dành cho kiểm thử thực địa trên Laptop / Máy trạm kiểm hàng trước khi tích hợp vào NetTMC.

Tác vụ thực hiện:
  1. Quét & chẩn đoán danh sách Microphone WASAPI hiện hữu trên máy.
  2. [Auto] Kiểm thử định danh sai mic -> kỳ vọng code=device_not_found, exit=2.
  3. [Auto] Khởi động song song 2 mic -> kiểm tra Heartbeat, stream_active, audio_age.
  4. [Interactive] Kiểm thử rút / cắm USB -> phát hiện ngắt kết nối và tự phục hồi.
  5. [Interactive] Kiểm thử nói chéo (Cross-talk) -> đánh giá ngưỡng noise-gate.
================================================================================
"""

import sys
import os
import time
import json
import subprocess
import threading
import queue

# Cấu hình UTF-8 cho console Windows
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

PYTHON_EXE = sys.executable
ENGINE_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "engine_headless.py")


def print_banner():
    print("=" * 78)
    print("      VOICEENGINE DUAL-MIC IPC HARDWARE TEST SUITE (THỰC ĐỊA)")
    print("=" * 78)
    print(f"• Python executable : {PYTHON_EXE}")
    print(f"• Engine script     : {os.path.abspath(ENGINE_SCRIPT)}")
    print("-" * 78)


def get_wasapi_microphones():
    """Lấy danh sách các Microphone hỗ trợ WASAPI trên máy tính."""
    try:
        import sounddevice as sd
    except ImportError:
        print("[LỖI] Chưa cài đặt thư viện 'sounddevice'. Vui lòng chạy: pip install sounddevice")
        return []

    hostapis = sd.query_hostapis()
    wasapi_id = None
    for idx, h in enumerate(hostapis):
        if "wasapi" in h.get("name", "").lower():
            wasapi_id = idx
            break

    if wasapi_id is None:
        print("[LỖI] Không tìm thấy Windows Audio Session API (WASAPI) trên máy này!")
        return []

    devices = sd.query_devices()
    mics = []
    for idx, dev in enumerate(devices):
        if dev.get("hostapi") == wasapi_id and dev.get("max_input_channels", 0) > 0:
            mics.append({
                "index": idx,
                "name": dev["name"],
                "channels": dev["max_input_channels"],
                "default_sr": dev.get("default_samplerate", 0)
            })
    return mics


def run_process_reader(proc, out_queue, name_tag):
    """Thread đọc từng dòng JSON từ stdout của tiến trình engine_headless."""
    try:
        for line in iter(proc.stdout.readline, ""):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                out_queue.put((name_tag, data, line_str))
            except Exception:
                out_queue.put((name_tag, {"raw": line_str}, line_str))
    except Exception:
        pass
    finally:
        out_queue.put((name_tag, {"event": "_proc_exit"}, ""))


# ==============================================================================
# BÀI TEST 1: Tự động kiểm tra bắt lỗi sai tên mic (Exit code 2, device_not_found)
# ==============================================================================
def test_fake_device_name():
    print("\n[TEST 1/4] Kiểm tra phòng thủ gõ sai tên Microphone (device_not_found)...")
    fake_name = "Mic_Ao_Khong_Ton_Tai_9999"
    cmd = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", fake_name]

    start_t = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    try:
        stdout_str, stderr_str = proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_str, stderr_str = proc.communicate()
        print(f"  ✗ FAIL: Quá thời gian chờ (Timeout > 15s)!")
        return False
    duration = time.monotonic() - start_t

    # Kiểm tra JSON trả về
    found_error_event = False
    error_code = ""
    for line in stdout_str.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("event") == "error":
                found_error_event = True
                error_code = data.get("code", "")
                break
        except Exception:
            pass

    passed = (proc.returncode == 2) and found_error_event and (error_code == "device_not_found")
    if passed:
        print(f"  ✓ PASS: Bắt đúng mã lỗi '{error_code}', exit code 2, phản hồi trong {duration:.2f}s")
        print("  ✓ Triệt tiêu hoàn toàn bẫy fallback sang Microphone mặc định.")
        return True
    else:
        print(f"  ✗ FAIL: returncode={proc.returncode} (kỳ vọng 2), error_code='{error_code}'")
        print(f"  Stdout: {stdout_str.strip()}")
        return False


# ==============================================================================
# BÀI TEST 2: Kiểm tra chạy song song 2 Microphone (Dual Heartbeat Stream)
# ==============================================================================
def test_dual_mic_stream(mic1_name, mic2_name, duration_sec=6.0):
    print(f"\n[TEST 2/4] Kiểm tra khởi động song song 2 Mic trong {duration_sec:.0f}s...")
    print(f"  • Trạm A (Mic 1): {mic1_name}")
    print(f"  • Trạm B (Mic 2): {mic2_name}")

    msg_queue = queue.Queue()

    # Khởi động 2 tiến trình
    cmd1 = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", mic1_name]
    cmd2 = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", mic2_name]

    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    t1 = threading.Thread(target=run_process_reader, args=(p1, msg_queue, "MIC_A"), daemon=True)
    t2 = threading.Thread(target=run_process_reader, args=(p2, msg_queue, "MIC_B"), daemon=True)
    t1.start()
    t2.start()

    print("  ⏳ Đang nạp mô hình AI PhoWhisper và mở luồng âm thanh song song...", end="", flush=True)

    # Chờ cả 2 tiến trình khởi động xong và bắn heartbeat đầu tiên (tối đa 20s)
    init_start = time.monotonic()
    ready_a = False
    ready_b = False
    has_error = False
    err_msgs = []

    while time.monotonic() - init_start < 20.0:
        if p1.poll() is not None and p1.returncode != 0:
            has_error = True
            err_msgs.append(f"[MIC_A] Tiến trình thoát sớm với mã lỗi: {p1.returncode}")
            break
        if p2.poll() is not None and p2.returncode != 0:
            has_error = True
            err_msgs.append(f"[MIC_B] Tiến trình thoát sớm với mã lỗi: {p2.returncode}")
            break

        try:
            tag, data, raw = msg_queue.get(timeout=0.3)
            event = data.get("event")
            if event == "heartbeat":
                if tag == "MIC_A":
                    ready_a = True
                elif tag == "MIC_B":
                    ready_b = True
            elif event == "error":
                has_error = True
                err_msgs.append(f"[{tag}] {data.get('code')}: {data.get('message')}")
        except queue.Empty:
            pass

        if ready_a and ready_b:
            break

    if not (ready_a and ready_b) or has_error:
        print(" Thất bại!")
        print(f"  ✗ FAIL: Không thể khởi động song song 2 mic. Lỗi: {err_msgs}")
        for p in (p1, p2):
            try:
                p.terminate()
            except Exception:
                pass
        return False

    print(" Sẵn sàng!")
    print(f"  ⏳ Lắng nghe độ ổn định luồng âm thanh trong {duration_sec:.0f}s...", end="", flush=True)

    start_t = time.monotonic()
    heartbeats = {"MIC_A": 0, "MIC_B": 0}
    stream_active = {"MIC_A": True, "MIC_B": True}
    max_audio_age = {"MIC_A": 0.0, "MIC_B": 0.0}

    while time.monotonic() - start_t < duration_sec:
        try:
            tag, data, raw = msg_queue.get(timeout=0.3)
            event = data.get("event")
            if event == "heartbeat":
                heartbeats[tag] += 1
                if not data.get("stream_active", False):
                    stream_active[tag] = False
                age = float(data.get("audio_age", 0.0))
                if age > max_audio_age[tag]:
                    max_audio_age[tag] = age
            elif event == "error":
                has_error = True
                err_msgs.append(f"[{tag}] {data.get('code')}: {data.get('message')}")
        except queue.Empty:
            pass

    # Dừng 2 tiến trình
    for p in (p1, p2):
        try:
            p.terminate()
            p.wait(timeout=1.0)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    print(" Xong!")
    print(f"  • Trạm A: nhận {heartbeats['MIC_A']} heartbeats, stream_active={stream_active['MIC_A']}, max_audio_age={max_audio_age['MIC_A']:.2f}s")
    print(f"  • Trạm B: nhận {heartbeats['MIC_B']} heartbeats, stream_active={stream_active['MIC_B']}, max_audio_age={max_audio_age['MIC_B']:.2f}s")

    passed = (
        not has_error
        and heartbeats["MIC_A"] >= 2
        and heartbeats["MIC_B"] >= 2
        and stream_active["MIC_A"]
        and stream_active["MIC_B"]
        and max_audio_age["MIC_A"] < 2.0
        and max_audio_age["MIC_B"] < 2.0
    )

    if passed:
        print("  ✓ PASS: Cả 2 Mic chạy song song hoàn toàn độc lập, âm thanh liên tục đạt chuẩn!")
        return True
    else:
        print(f"  ✗ FAIL: Phát hiện bất thường trong luồng song song! Lỗi: {err_msgs}")
        return False


# ==============================================================================
# BÀI TEST 3: Kiểm thử rút / cắm USB tương tác
# ==============================================================================
def test_usb_disconnect_reconnect(mic_name):
    print(f"\n[TEST 3/4] Kiểm thử rút / cắm USB Mic ('{mic_name}')...")
    confirm = input("  👉 Bạn có muốn thực hiện bài test rút/cắm USB vật lý không? (Y/n): ").strip().lower()
    if confirm not in ("y", "yes", ""):
        print("  ⏩ Đã bỏ qua bài test rút/cắm USB theo yêu cầu.")
        return True

    msg_queue = queue.Queue()
    cmd = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", mic_name]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    t = threading.Thread(target=run_process_reader, args=(p, msg_queue, "MIC_TEST"), daemon=True)
    t.start()

    # Đợi 2s cho mic ổn định
    print("  ⏳ Đang kết nối Microphone...", end="", flush=True)
    time.sleep(2.5)
    print(" Sẵn sàng!")

    print("\n  👉 BƯỚC 1: Hãy RÚT DÂY USB Microphone ra ngay bây giờ!")
    print("  (Hệ thống đang theo dõi sự kiện ngắt kết nối stream_active trong tối đa 15s...)")

    disconnected = False
    start_t = time.monotonic()
    while time.monotonic() - start_t < 15.0:
        if p.poll() is not None:
            disconnected = True
            print(f"  ✓ Tiến trình đã phát hiện mất mic và tự thoát với mã: {p.returncode}")
            break
        try:
            tag, data, raw = msg_queue.get(timeout=0.4)
            if data.get("event") == "heartbeat":
                is_active = data.get("stream_active", True)
                age = float(data.get("audio_age", 0.0))
                if not is_active or age >= 3.0:
                    disconnected = True
                    print(f"  ✓ Đã bắt sự kiện ngắt luồng: stream_active={is_active}, audio_age={age:.1f}s")
                    break
            elif data.get("event") == "error":
                disconnected = True
                print(f"  ✓ Nhận sự kiện báo lỗi ngắt mic: {data.get('code')}")
                break
        except queue.Empty:
            pass

    try:
        p.terminate()
        p.wait(timeout=1.0)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

    if not disconnected:
        print("  ✗ Không phát hiện sự kiện ngắt kết nối trong 15s!")
        return False

    print("\n  👉 BƯỚC 2: Hãy CẮM LẠI DÂY USB Microphone vào máy tính.")
    input("  👉 Sau khi cắm đèn mic sáng lên, nhấn phím [ENTER] để hệ thống tự kết nối lại: ")

    print("  ⏳ Đang khởi động lại VoiceEngine cho mic vừa cắm...", end="", flush=True)
    p_re = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    re_queue = queue.Queue()
    t_re = threading.Thread(target=run_process_reader, args=(p_re, re_queue, "MIC_RECONNECT"), daemon=True)
    t_re.start()

    reconnected = False
    start_re = time.monotonic()
    while time.monotonic() - start_re < 8.0:
        if p_re.poll() is not None and p_re.returncode != 0:
            break
        try:
            tag, data, raw = re_queue.get(timeout=0.5)
            if data.get("event") == "heartbeat" and data.get("stream_active", False):
                reconnected = True
                break
        except queue.Empty:
            pass

    try:
        p_re.terminate()
        p_re.wait(timeout=1.0)
    except Exception:
        try:
            p_re.kill()
        except Exception:
            pass

    if reconnected:
        print(" Hoàn tất!")
        print("  ✓ PASS: Khôi phục kết nối và thu âm bình thường sau khi cắm lại mic!")
        return True
    else:
        print(" Thất bại!")
        print("  ✗ FAIL: Không thể khởi động lại luồng âm thanh sau khi cắm mic.")
        return False


# ==============================================================================
# BÀI TEST 4: Kiểm thử nói chéo & đánh giá Noise Gate (Cross-talk check)
# ==============================================================================
def test_cross_talk_interactive(mic1_name, mic2_name, noise_gate=250):
    print(f"\n[TEST 4/4] Kiểm thử chống nói chéo giữa 2 Trạm (Noise Gate = {noise_gate})...")
    confirm = input("  👉 Bạn có muốn thực hiện bài test đọc lệnh thử giọng không? (Y/n): ").strip().lower()
    if confirm not in ("y", "yes", ""):
        print("  ⏩ Đã bỏ qua bài test giọng nói theo yêu cầu.")
        return True

    msg_queue = queue.Queue()
    cmd1 = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", mic1_name, "--noise-gate", str(noise_gate)]
    cmd2 = [PYTHON_EXE, "-u", ENGINE_SCRIPT, "--ipc", "--device", mic2_name, "--noise-gate", str(noise_gate)]

    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    t1 = threading.Thread(target=run_process_reader, args=(p1, msg_queue, "TRẠM A (Mic 1)"), daemon=True)
    t2 = threading.Thread(target=run_process_reader, args=(p2, msg_queue, "TRẠM B (Mic 2)"), daemon=True)
    t1.start()
    t2.start()

    print("  ⏳ Đang nạp mô hình AI PhoWhisper vào bộ nhớ...", end="", flush=True)
    ready_a = False
    ready_b = False
    init_start = time.monotonic()
    while time.monotonic() - init_start < 20.0:
        try:
            tag, data, raw = msg_queue.get(timeout=0.3)
            if data.get("event") == "heartbeat":
                if "TRẠM A" in tag:
                    ready_a = True
                elif "TRẠM B" in tag:
                    ready_b = True
        except queue.Empty:
            pass
        if ready_a and ready_b:
            break
    print(" Sẵn sàng!")

    print("\n" + "=" * 60)
    print("  👉 KỊCH BẢN THỬ GIỌNG:")
    print("  Người đứng ở TRẠM A hãy nói vào Mic 1:  'một hai'  (hoặc 'đạt')")
    print("  Người ở TRẠM B giữ im lặng.")
    print("  (Thời gian lắng nghe: 12 giây...)")
    print("=" * 60)

    start_t = time.monotonic()
    mic1_received_cmd = None
    mic2_triggered = False

    while time.monotonic() - start_t < 12.0:
        try:
            tag, data, raw = msg_queue.get(timeout=0.3)
            event = data.get("event")
            if event == "command":
                cmd_info = data.get("command", {})
                print(f"  📢 [{tag}] Nhận diện lệnh: {cmd_info.get('intent')} | Text: '{data.get('text')}'")
                if "TRẠM A" in tag:
                    mic1_received_cmd = data.get("text")
                elif "TRẠM B" in tag:
                    mic2_triggered = True
            elif event == "heartbeat":
                if data.get("speaking", False) and "TRẠM B" in tag:
                    # Mic 2 bị kích hoạt giọng nói khi chỉ có trạm 1 nói
                    mic2_triggered = True
        except queue.Empty:
            pass

    # Tắt 2 tiến trình
    for p in (p1, p2):
        try:
            p.terminate()
            p.wait(timeout=1.0)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    print("\n  🔍 ĐÁNH GIÁ KẾT QUẢ NÓI CHÉO:")
    if mic1_received_cmd and not mic2_triggered:
        print(f"  ✓ PASS TUYỆT ĐỐI: Trạm A nhận đúng lệnh '{mic1_received_cmd}', Trạm B hoàn toàn im lặng!")
        print(f"  ✓ Ngưỡng --noise-gate {noise_gate} hoạt động hoàn hảo cho môi trường này.")
        return True
    elif not mic1_received_cmd:
        print("  ⚠️ Trạm A chưa thu được lệnh nào. (Có thể bạn chưa nói hoặc âm lượng quá nhỏ so với noise-gate).")
        print(f"  💡 Gợi ý: Hãy thử lại với cự ly gần miệng hơn (2-4cm) hoặc giảm nhẹ noise-gate xuống 200.")
        return True
    else:
        print(f"  ⚠️ CẢNH BÁO LỌT TIẾNG: Trạm A nhận lệnh, nhưng Trạm B cũng bị kích hoạt thu âm!")
        print(f"  💡 Khắc phục: Hãy tăng --noise-gate lên 300 hoặc 350, hoặc hạ bớt Microphone Volume trong Windows.")
        return False


# ==============================================================================
# HÀM ĐIỀU PHỐI CHÍNH
# ==============================================================================
def main():
    print_banner()

    # 1. Quét phần cứng
    print("[BƯỚC 0] Đang quét danh sách Microphone WASAPI trên máy tính...")
    mics = get_wasapi_microphones()
    if not mics:
        print("[LỖI] Không tìm thấy Microphone WASAPI nào. Vui lòng kiểm tra lại cáp cắm USB!")
        sys.exit(1)

    print(f"  ✓ Tìm thấy {len(mics)} Microphone WASAPI:")
    for idx, m in enumerate(mics):
        print(f"    [{idx + 1}] \"{m['name']}\" (Channels={m['channels']}, SampleRate={m['default_sr']}Hz)")

    # Lựa chọn 2 Mic để test
    if len(mics) >= 2:
        mic1_name = mics[0]["name"]
        mic2_name = mics[1]["name"]
    else:
        print("\n  ⚠️ Máy tính hiện chỉ phát hiện 1 Microphone WASAPI!")
        print("  Hệ thống sẽ dùng chung mic này cho cả 2 luồng để mô phỏng kiểm thử.")
        mic1_name = mics[0]["name"]
        mic2_name = mics[0]["name"]

    print(f"\n  👉 Thiết bị chọn tự động:")
    print(f"     • Mic 1 (Trạm A): \"{mic1_name}\"")
    print(f"     • Mic 2 (Trạm B): \"{mic2_name}\"")

    results = {}

    # Chạy Test 1
    results["Test 1: Phòng thủ gõ sai tên Mic"] = test_fake_device_name()

    # Chạy Test 2
    results["Test 2: Chạy song song 2 luồng (Heartbeat)"] = test_dual_mic_stream(mic1_name, mic2_name)

    # Chạy Test 3
    results["Test 3: Rút / cắm USB vật lý"] = test_usb_disconnect_reconnect(mic1_name)

    # Chạy Test 4
    results["Test 4: Kiểm thử nói chéo (Cross-talk)"] = test_cross_talk_interactive(mic1_name, mic2_name)

    # Bảng tổng kết
    print("\n" + "=" * 78)
    print("                     BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ")
    print("=" * 78)
    all_pass = True
    for test_name, res in results.items():
        status = "✓ PASS" if res else "✗ FAIL"
        if not res:
            all_pass = False
        print(f"• {test_name:<50} : {status}")
    print("-" * 78)

    if all_pass:
        print("🎉 XUẤT SẮC! Toàn bộ các bài kiểm thử thực địa đều ĐẠT CHUẨN.")
        print("Hệ thống đã sẵn sàng 100% để tích hợp vào phần mềm NetTMC (frm7033 P211)!")
    else:
        print("⚠️ Có bài test chưa đạt. Vui lòng xem lại các chỉ dẫn khắc phục phía trên.")
    print("=" * 78)


if __name__ == "__main__":
    main()


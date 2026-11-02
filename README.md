# VoiceEngine

**Lightweight Headless Vietnamese Voice Recognition Engine for Industrial QA Inspection**

VoiceEngine là engine nhận diện giọng nói tiếng Việt chạy ngầm siêu nhẹ, độ trễ cực thấp (< 0.5s trên CPU), được thiết kế chuyên biệt cho hệ thống kiểm tra chất lượng sản phẩm (QA / End of Line Inspection) trong các nhà máy sản xuất.

---

## 🚀 Tính năng nổi bật

- **Kiến trúc Headless & Microservice**: Không đồ họa GUI, không PyQt5, khởi động tức thì trong < 1s, tiết kiệm tối đa CPU/RAM.
- **AI Core hiện đại**:
  - **ASR Model**: [PhoWhisper-tiny CT2 INT8](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8) tối ưu hóa suy luận CPU qua CTranslate2.
  - **VAD Neural**: Silero VAD (ONNX Runtime) lọc sạch 100% tiếng ồn nhà xưởng, súng khí, máy móc.
- **Tiền xử lý âm thanh DSP**: DC-offset removal, High-pass Butterworth filter 60Hz, Soft Limiter 24000, AGC (Automatic Gain Control).
- **Hỗ trợ đầy đủ khẩu lệnh công nghiệp**:
  - Cặp số: `[Vị trí 1..6] + [Mã lỗi 1..24]` (VD: *"một mười bảy"*, *"hai mười tám"*, *"năm hai mươi mốt"*...).
  - Ghép vị trí + lỗi: *"mũi một"*, *"gót mười bảy"*, *"đế mười tám"*, *"a một"*, *"bê hai"*...
  - Thao tác: *"pass"*, *"đạt"*, *"sửa đạt"*, *"sửa lại"*, *"hủy"*, *"quay lại"*.
- **Giao tiếp IPC Pipe (Standard I/O NDJSON)**:
  - Truyền dữ liệu trực tiếp qua Anonymous Pipe RAM ($< 0.5\text{ms}$).
  - Không mở cổng mạng TCP, không bị chặn bởi Windows Firewall / Antivirus.
  - Tự động dọn dẹp tiến trình qua Windows Job Object khi ứng dụng chính (NetTMC) kết thúc.
- **Shadowing Audit**: Tự động lưu nhật ký JSON Lines và file ghi âm `.wav` các lệnh hợp lệ phục vụ kiểm tra chất lượng và huấn luyện AI.

---

## 📦 Cài đặt

```bash
git clone https://github.com/tn823/VoiceEngine.git
cd VoiceEngine
pip install -r requirements.txt
```

### 🧠 Model Weights
Model PhoWhisper-tiny CT2 INT8 được lưu sẵn trong thư mục `models/` hoặc tải trực tiếp từ HuggingFace:
👉 **HuggingFace Repository**: [ntn823/phowhisper-tiny-cuchi-int8](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8)

---

## 🎙️ Hướng dẫn sử dụng

### 1. Chạy thử nghiệm trực tiếp bằng Microphone (Console Test)
```bash
python engine_headless.py
```
Màn hình sẽ hiển thị visual log dạng box ANSI màu sắc trực quan:
```text
┌── 🎙️ [P211] NHẬN DIỆN THÀNH CÔNG: CHẤM LỖI QA ────────────────────────────┐
│  📍 Vị trí : Mũi (1)             ⚠️ Lỗi: 17 - Mài / Lem keo / Lem nước   │
│  📝 Giọng  : "mũi mười bảy"            ⏱️ 115ms | 🎯 Tin cậy: 98%         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. Chạy chế độ IPC Pipe (Dành cho phần mềm C# WinForms / NetTMC)
```bash
python engine_headless.py --ipc
```
Ở chế độ này, VoiceEngine phát sự kiện dạng NDJSON qua `stdout`:
```json
{"event": "ready", "device": "Microphone", "engine": "phowhisper-tiny-ct2-int8"}
{"event": "command", "cmd": {"intent": "inspection", "position": 1, "defect": 17, "result": "fail"}}
{"event": "command", "cmd": {"intent": "pass"}}
```

### 3. Tùy chọn tham số
- `--device <name/index>`: Chỉ định microphone cụ thể (tự động ưu tiên Windows WASAPI).
- `--gate <number>`: Ngưỡng năng lượng phát hiện giọng nói RMS (mặc định: 180).
- `--wav-mode <matched_only|all|none>`: Chế độ lưu file `.wav` (mặc định: `matched_only`).

---

## 🧪 Kiểm thử tự động (Unit Test)
Chạy bộ kiểm thử toàn diện phủ 54 test cases:
```bash
python test_all_cases.py
```

---

## 📄 License
MIT License.

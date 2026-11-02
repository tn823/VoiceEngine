# 🎙️ VoiceEngine

> **Ultra-Low Latency, Headless Vietnamese Speech Recognition Engine for Industrial QA Inspection**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Hugging Face Model](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-ntn823%2Fphowhisper--tiny--cuchi--int8-yellow)](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

VoiceEngine là bộ nhận diện giọng nói tiếng Việt chạy ngầm siêu nhẹ, độ trễ cực thấp ($< 0.5\text{s}$ trên CPU), được thiết kế chuyên biệt cho hệ thống kiểm tra chất lượng sản phẩm (QA / End of Line Inspection) trong các nhà máy sản xuất.

---

## 🌟 Tính năng nổi bật

- **Kiến trúc Headless & Microservice**: Không đồ họa GUI (loại bỏ hoàn toàn PyQt5), khởi động tức thì trong $< 1\text{s}$, tối ưu hóa 100% tài nguyên CPU và RAM.
- **Lõi AI Chuyên Dụng**:
  - **ASR Engine**: Mô hình [PhoWhisper-tiny CT2 INT8](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8) tối ưu hóa suy luận CPU qua CTranslate2.
  - **Neural VAD**: Silero VAD (ONNX Runtime) lọc sạch 100% tiếng ồn nhà xưởng, tiếng va chạm, súng khí và máy móc.
- **Tiền xử lý âm thanh DSP**: DC-offset removal, High-pass Butterworth filter 60Hz (cắt ù rung băng tải), Soft Limiter 24000 (chống vỡ tiếng clipping), AGC (Automatic Gain Control).
- **Hỗ trợ đầy đủ khẩu lệnh công nghiệp**:
  - **Cặp số**: `[Vị trí 1..6] + [Mã lỗi 1..24]` (VD: *"một mười bảy"*, *"hai mười tám"*, *"năm hai mươi mốt"*...).
  - **Ghép vị trí + lỗi**: *"mũi một"*, *"gót mười bảy"*, *"đế mười tám"*, *"a một"*, *"bê hai"*...
  - **Thao tác nhanh**: *"pass"*, *"đạt"*, *"sửa đạt"*, *"sửa lại"*, *"hủy"*, *"quay lại"*.
- **Giao tiếp IPC Pipe (Standard I/O NDJSON)**:
  - Truyền dữ liệu trực tiếp 1 chiều qua Anonymous Pipe RAM ($< 0.5\text{ms}$).
  - Không mở cổng mạng TCP, 100% không bị Windows Firewall / Antivirus can thiệp.
  - Quản lý vòng đời chặt chẽ qua Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), ngăn ngừa hoàn toàn Zombie Process.
- **Shadowing Audit**: Tự động lưu nhật ký JSON Lines và file ghi âm `.wav` các lệnh hợp lệ phục vụ kiểm tra chất lượng và tinh chỉnh mô hình.

---

## 🚀 Cài đặt & Khởi chạy nhanh (Plug & Play)

Toàn bộ trọng số mô hình ($47.5\text{MB}$) đã được nhúng sẵn trong repository. Bạn chỉ cần clone về là có thể chạy offline ngay lập tức!

```bash
# 1. Clone repository
git clone https://github.com/tn823/VoiceEngine.git
cd VoiceEngine

# 2. Cài đặt thư viện phụ thuộc
pip install -r requirements.txt

# 3. Khởi chạy thử nghiệm trực tiếp bằng Microphone
python engine_headless.py
```

> **Ghi chú về Model**: Trọng số mô hình được lưu tại `models/phowhisper-tiny-ct2-int8/`. Nếu thư mục local bị xóa, engine sẽ tự động nạp từ HuggingFace: [`ntn823/phowhisper-tiny-cuchi-int8`](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8).

---

## 🖥️ Chế độ hoạt động

### 1. Chế độ Thử nghiệm Trực tiếp (Console Test Mode)
```bash
python engine_headless.py
```
Màn hình sẽ hiển thị visual log dạng box màu ANSI trực quan:
```text
┌── 🎙️ [P211] NHẬN DIỆN THÀNH CÔNG: CHẤM LỖI QA ────────────────────────────┐
│  📍 Vị trí : Mũi (1)             ⚠️ Lỗi: 17 - Mài / Lem keo / Lem nước   │
│  📝 Giọng  : "mũi mười bảy"            ⏱️ 115ms | 🎯 Tin cậy: 98%         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. Chế độ IPC Pipe (Chạy ngầm kết nối với NetTMC / C# WinForms)
```bash
python engine_headless.py --ipc
```
Khi chạy với cờ `--ipc`, toàn bộ stdout thông thường được chuyển sang stderr, riêng các sự kiện nhận dạng được phát dưới dạng **NDJSON (1 dòng JSON + `\n`)** qua `stdout`:
```json
{"event": "ready", "device": "마이크 (Realtek(R) Audio)", "engine": "phowhisper-tiny-ct2-int8"}
{"event": "command", "cmd": {"intent": "inspection", "position": 1, "defect": 17, "result": "fail"}, "conf": 0.98, "latency_ms": 115.2}
{"event": "command", "cmd": {"intent": "pass"}, "conf": 0.99, "latency_ms": 95.0}
```

---

## ⚙️ Tham số dòng lệnh (CLI Arguments)

| Tham số | Mặc định | Ý nghĩa |
| :--- | :---: | :--- |
| `--ipc` | `False` | Kích hoạt chế độ Standard I/O Pipe cho Master Application. |
| `--device` | `None` | Chỉ định Microphone theo index hoặc tên (ưu tiên Windows WASAPI). |
| `--gate` | `180` | Ngưỡng năng lượng âm thanh RMS (Noise Gate) để kích hoạt VAD. |
| `--wav-mode` | `matched_only` | Chế độ ghi file âm thanh: `matched_only` (chỉ lưu lệnh đúng), `all` (lưu toàn bộ), `none` (tắt ghi .wav). |

---

## 📋 Bảng Ánh Xạ Khẩu Lệnh QA

### 1. Vị trí trên giày (Part IDs: 1..6)
| Mã | Tên vị trí | Ký hiệu quy ước | Các từ khóa nhận diện |
| :-: | :--- | :-: | :--- |
| **1** | **Mũi** | A / K | `mũi`, `mũi giày`, `a`, `k`, `ca` |
| **2** | **Hông ngoài** | B | `hông ngoài`, `b`, `bê`, `pê` |
| **3** | **Hông trong** | D | `hông trong`, `d`, `đ`, `đê` |
| **4** | **Lưỡi gà** | F | `lưỡi gà`, `f`, `ép`, `ét` |
| **5** | **Gót** | C | `gót`, `gót giày`, `c`, `x`, `xê`, `cê` |
| **6** | **Đế** | E / G | `đế`, `đế giày`, `e`, `ê`, `g`, `gờ`, `h`, `hát` |

### 2. Danh mục Mã lỗi (Defect IDs: 1..24)
- **01**: Da xù / Sai liệu / Hư liệu
- **02**: Lưới xéo / Hư liệu
- **03**: Tách lớp / Sai liệu
- **04**: Hư đế / Bọng khí / Nhăn / Tróc sơn
- **05**: Khác màu
- **06**: Sai hướng chặt / Chặt xấu
- **07**: Lạng / Gấp mép sai
- **08**: Thêu / In lụa / No sew / In 3D
- **09**: Bung chỉ / Chỉ thừa / Bỏ mũi / Tưa
- **10**: Sụp mí / Lỗ kim
- **11**: Đục lỗ
- **12**: Mặt giày / Cộm / Nhăn
- **13**: To nhỏ các chi tiết trên Upper
- **14**: Nút kim loại / Phụ liệu
- **15**: Mũi / Gót bị lệch tâm
- **16**: Độ cao mũi / Cao hông / Cao gót
- **17**: Mài / Lem nước xử lý / Lem keo
- **18**: Hở keo
- **19**: Miếng lót giày / An chang
- **20**: Dây giày
- **21**: Vệ sinh giày
- **22**: Tem nhãn / Đóng gói
- **23**: Ngay thẳng tâm / Cân đối chiếc trái - phải
- **24**: Lỗi khác (Other)

---

## 🧪 Kiểm thử tự động (Unit Test Suite)

Chạy bộ kiểm thử toàn diện phủ **54 kịch bản khẩu lệnh**:
```bash
python test_all_cases.py
```
Kết quả kiểm thử chuẩn:
```text
TỔNG KẾT: 54/54 PASS (100.0%), 0 FAIL
```

Kiểm thử nhanh toàn bộ pipeline ASR, DSP và VAD:
```bash
python test_quick.py
```

---

## 📁 Cấu trúc thư mục

```text
VoiceEngine/
├── .gitignore                   # Loại trừ file tạm, cache, logs
├── README.md                    # Hướng dẫn chi tiết
├── requirements.txt             # Danh sách dependencies tối giản
├── config.py                    # Cấu hình đường dẫn, âm thanh và ngưỡng VAD
├── engine_headless.py           # Entry point chính (Console Test & IPC Pipe)
├── test_all_cases.py            # Suite kiểm thử toàn diện 54 kịch bản QA
├── test_quick.py                # Kiểm thử nhanh DSP, VAD và PhoWhisper
├── core/
│   ├── __init__.py
│   ├── phowhisper_engine.py     # Lõi ASR PhoWhisper CT2 INT8
│   ├── audio_preprocessor.py    # DSP lọc âm và Silero VAD Pure ONNX
│   ├── whisper_normalizer.py    # Chuẩn hóa âm học Nam Bộ & số tiếng Việt
│   └── command_parser.py        # Bộ phân tích intent khẩu lệnh công nghiệp
└── models/
    ├── phowhisper-tiny-ct2-int8/ # Trọng số mô hình PhoWhisper CT2 INT8
    └── silero_vad.onnx           # Trọng số mô hình Silero VAD ONNX
```

---

## 📄 License

Dự án phát triển nội bộ cho dây chuyền sản xuất Samho. Phát hành theo giấy phép MIT.

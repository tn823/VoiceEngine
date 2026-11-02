# 🎙️ VoiceEngine

> **Ultra-Low Latency, Headless Vietnamese Speech Recognition Engine for Industrial Quality Inspection**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Hugging Face Model](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-ntn823%2Fphowhisper--tiny--cuchi--int8-yellow)](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8)
[![Inference Engine](https://img.shields.io/badge/Inference-CTranslate2%20INT8-orange.svg)](https://github.com/OpenNMT/CTranslate2)
[![VAD](https://img.shields.io/badge/VAD-Silero%20ONNX-blueviolet.svg)](https://github.com/snakers4/silero-vad)
[![Platform](https://img.shields.io/badge/Platform-Windows%20WASAPI-lightgrey.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 Overview

**VoiceEngine** is a specialized, headless speech recognition service engineered for high-noise industrial manufacturing lines (specifically End-of-Line QA Inspection). 

By combining digital signal processing (DSP), neural Voice Activity Detection (Silero VAD), and an INT8-quantized PhoWhisper model via CTranslate2, VoiceEngine achieves deterministic **sub-second inference latency ($< 0.5\text{s}$)** on standard x86/x64 CPUs with **zero GPU dependency**.

It operates as an isolated worker controlled by host industrial applications (e.g., C# WinForms / MES clients) via **Windows Anonymous Pipes (NDJSON)**, completely decoupled from graphical UI overheads.

```
                     ┌──────────────────────────────────────────────┐
                     │              Industrial Host App             │
                     │          (NetTMC / C# WinForms Client)       │
                     └──────────────────────┬───────────────────────┘
                                            │ Anonymous Pipe (stdout)
                                            ▼ NDJSON Event Stream (< 0.5ms)
┌───────────────────────────────────────────────────────────────────┐
│                      VoiceEngine (Headless Python)                │
│                                                                   │
│  [Microphone] ──> [WASAPI 16kHz] ──> [High-Pass & Limiter DSP]   │
│                                                   │               │
│                                                   ▼               │
│                                         [Silero Neural VAD]       │
│                                                   │               │
│                                                   ▼               │
│                                      [PhoWhisper CT2 INT8 Engine] │
│                                                   │               │
│                                                   ▼               │
│                                        [QA Command Parser]        │
└───────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **🚀 Headless Microservice Architecture**: Completely eliminates GUI dependencies (no PyQt5, no WebEngine). Cold starts in $< 1\text{s}$ with minimal CPU footprint ($< 150\text{MB}$ RAM).
- **🧠 Industrial-Grade Speech Pipeline**:
  - **ASR Engine**: Local quantized [PhoWhisper-tiny CT2 INT8](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8).
  - **Neural VAD**: Silero VAD (ONNX Runtime) tuned with an energy threshold to reject factory ambient noise, air guns, and machinery clatter.
  - **Audio DSP**: 60Hz 2nd-order Butterworth High-pass filter (eliminating conveyor rumble), soft limiter (24,000 ceiling against clipping), and Automatic Gain Control (AGC).
- **⚡ Anonymous Pipe IPC Protocol**:
  - One-way, ultra-low latency ($< 0.5\text{ms}$) kernel memory communication.
  - Zero open TCP ports — 100% immune to Windows Firewall or corporate endpoint security blocks.
  - Full lifecycle isolation via Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) to prevent zombie processes.
- **🎯 Deterministic Grammar & Fuzzy Normalizer**:
  - Handles Southern Vietnamese acoustic variants (*"đệt" $\rightarrow$ "đạt"*, *"hói" $\rightarrow$ "hủy"*).
  - Supports 2-digit continuous QA defect codes without phonetic collapse.
- **🛡️ Production Shadowing & Audit**:
  - Automatic structured JSONL event logging.
  - Optional `.wav` recording exclusively for verified valid QA commands.

---

## 🚀 Quickstart (Plug & Play)

All essential neural weights ($47.5\text{MB}$) are bundled within the repository. No external weights setup is required.

```bash
# 1. Clone repository
git clone https://github.com/tn823/VoiceEngine.git
cd VoiceEngine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch interactive test mode
python engine_headless.py
```

> **Automatic Remote Fallback**: If the local `models/` directory is missing, the engine automatically fetches and caches weights directly from Hugging Face: [`ntn823/phowhisper-tiny-cuchi-int8`](https://huggingface.co/ntn823/phowhisper-tiny-cuchi-int8).

---

## 🖥️ Operating Modes

### 1. Interactive Console Test Mode (For QA Engineers)
```bash
python engine_headless.py
```
Outputs colored ANSI box frames indicating position, defect code, acoustic confidence, and latency:

```text
┌── 🎙️ [P211] NHẬN DIỆN THÀNH CÔNG: CHẤM LỖI QA ────────────────────────────┐
│  📍 Vị trí : Mũi (1)             ⚠️ Lỗi: 17 - Mài / Lem keo / Lem nước   │
│  📝 Giọng  : "mũi mười bảy"            ⏱️ 115ms | 🎯 Tin cậy: 98%         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. Headless IPC Pipe Mode (For Host Integration)
```bash
python engine_headless.py --ipc
```
Standard output is isolated to emit only **Newline-Delimited JSON (NDJSON)** events directly to the parent process:

```json
{"event": "ready", "device": "Microphone (Realtek(R) Audio)", "engine": "phowhisper-tiny-ct2-int8"}
{"event": "command", "cmd": {"intent": "inspection", "position": 1, "defect": 17, "result": "fail"}, "conf": 0.985, "latency_ms": 115.2}
{"event": "command", "cmd": {"intent": "pass"}, "conf": 0.992, "latency_ms": 94.0}
```

---

## ⚙️ CLI Reference

```text
usage: engine_headless.py [-h] [--ipc] [--device DEVICE] [--gate GATE]
                          [--wav-mode {matched_only,all,none}]

options:
  -h, --help            Show this help message and exit
  --ipc                 Enable IPC Pipe mode (transmits NDJSON via stdout)
  --device DEVICE       Audio device name or index (defaults to system WASAPI input)
  --gate GATE           Audio Energy Gate RMS threshold (default: 180)
  --wav-mode {matched_only,all,none}
                        Audio shadowing mode: 'matched_only' (default: valid QA commands only),
                        'all' (debug all chunks), 'none' (disabled)
```

---

## 📋 Industrial QA Command Specification

### 1. Shoe Part Mapping (Part IDs: 1..6)
| Part ID | Name (VN) | Formal Label | Recognized Keywords / Aliases |
| :---: | :--- | :---: | :--- |
| **1** | Mũi giày | **Mũi (1)** | `mũi`, `mũi giày`, `a`, `k`, `ca` |
| **2** | Hông ngoài | **Hông ngoài (2)** | `hông ngoài`, `b`, `bê`, `pê` |
| **3** | Hông trong | **Hông trong (3)** | `hông trong`, `d`, `đ`, `đê` |
| **4** | Lưỡi gà | **Lưỡi gà (4)** | `lưỡi gà`, `f`, `ép`, `ét` |
| **5** | Gót giày | **Gót (5)** | `gót`, `gót giày`, `c`, `x`, `xê`, `cê` |
| **6** | Đế giày | **Đế (6)** | `đế`, `đế giày`, `e`, `ê`, `g`, `gờ`, `h`, `hát` |

### 2. Defect Catalog (Defect IDs: 1..24)
- **01**: Materials - Leathers / Synthetics *(Da xù láng / Sai liệu / Hư liệu)*
- **02**: Materials - Textiles *(Lưới xéo / Hư liệu)*
- **03**: Materials - Components *(Tách lớp / Sai liệu)*
- **04**: Material - Soleunit *(Hư đế / Bọng khí / Nhăn / Tróc sơn)*
- **05**: Color Variation *(Khác màu)*
- **06**: Cutting *(Sai hướng chặt / Chặt xấu)*
- **07**: Skiving / Folding / Trimming *(Lạng / Gấp mép sai quy trình)*
- **08**: Embroidery / Embossing / Printing / No Sew *(Thêu / In / HF / No sew)*
- **09**: Stitching - Open / Tension / Trimming *(Bung chỉ / Bỏ mũi / Tưa chỉ)*
- **10**: Stitching - Margin / Stitches / Needle Holes *(Sụp mí / Lỗ kim)*
- **11**: Punching *(Đục lỗ)*
- **12**: Upper / Lining Lumps / Wrinkles *(Mặt giày / Cộm / Nhăn)*
- **13**: Tip / Vamp / Tongue / Eyestay Dimensions *(To nhỏ các chi tiết upper)*
- **14**: Hardware *(Nút kim loại / Phụ liệu hỏng)*
- **15**: Toe / Side / Heel Lasting *(Mũi / Gót lệch tâm)*
- **16**: Toe Spring / Quarter Height / Back Height *(Độ cao mũi / Hông / Gót)*
- **17**: Roughing / Priming / Cementing *(Mài / Lem nước xử lý / Lem keo)*
- **18**: Upper / Outsole Adhesion *(Hở keo)*
- **19**: Inserts *(Miếng lót giày / An chang)*
- **20**: Laces *(Dây giày)*
- **21**: Cleanliness *(Vệ sinh giày)*
- **22**: Labeling / Packing *(Tem nhãn / Đóng gói)*
- **23**: Alignment *(Ngay thẳng tâm / Cân đối trái - phải)*
- **24**: Other Defects *(Lỗi khác)*

### 3. Workflow Actions
- **Pass (Inspection Passed)**: `"pass"`, `"đạt"`, `"qua"`, `"cho pass"`, `"ok"`
- **Re-Pass (Rework Passed)**: `"sửa đạt"`, `"đạt lại"`
- **Compound Inspection (1-step)**: `<position> <defect>` *(e.g., "mũi mười bảy", "một mười bảy", "hai mười tám")*
- **Re-Fail (Rework Defect)**: `<position> <defect> sửa` *(e.g., "gót mười tám sửa lại")*
- **Cancel / Clear**: `"hủy"`, `"hủy bỏ"`, `"bỏ"`, `"quay lại"`

---

## 🧪 Comprehensive Verification Suite

Execute the automated test suite covering **54 industry verification scenarios**:

```bash
python test_all_cases.py
```

Standard benchmark output:
```text
=====================================================================================
SUMMARY: 54/54 PASS (100.0%), 0 FAIL
=====================================================================================
```

Perform end-to-end DSP, VAD, and model inference verification:
```bash
python test_quick.py
```

---

## 📂 Project Structure

```text
VoiceEngine/
├── .gitignore                   # Excludes logs, audio cache, and local secrets
├── README.md                    # Engineering documentation and technical specs
├── requirements.txt             # Lightweight runtime dependencies
├── config.py                    # Audio DSP and model configurations
├── engine_headless.py           # Core entry point (Console Test & IPC Pipe)
├── test_all_cases.py            # Comprehensive 54-case verification suite
├── test_quick.py                # Quick verification for ASR, DSP, and VAD
├── core/
│   ├── __init__.py
│   ├── phowhisper_engine.py     # CTranslate2 INT8 PhoWhisper inference core
│   ├── audio_preprocessor.py    # DSP filters & pure ONNX Silero VAD
│   ├── whisper_normalizer.py    # Vietnamese numeric & dialect normalizer
│   └── command_parser.py        # Industrial QA intent & grammar parser
└── models/
    ├── phowhisper-tiny-ct2-int8/ # Quantized INT8 PhoWhisper model weights
    └── silero_vad.onnx           # Silero neural VAD ONNX model
```

---

## 📄 License

Internal industrial software developed for factory floor deployment. Released under the [MIT License](LICENSE).

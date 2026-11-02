# VoiceEngine

<p align="center">
  <strong>Ultra-Low Latency, Headless Vietnamese Speech Recognition Engine for Industrial QA Inspection</strong>
</p>

<p align="center">
  <a href="#key-features"><img src="https://img.shields.io/badge/Architecture-Headless%20%7C%20Zero%20GUI-blue?style=flat-square" alt="Headless Architecture" /></a>
  <a href="#inference--models"><img src="https://img.shields.io/badge/ASR-PhoWhisper%20CTranslate2%20INT8-brightgreen?style=flat-square" alt="PhoWhisper CT2 INT8" /></a>
  <a href="#inference--models"><img src="https://img.shields.io/badge/VAD-Silero%20VAD%20ONNX-orange?style=flat-square" alt="Silero VAD ONNX" /></a>
  <a href="#inter-process-communication-ipc"><img src="https://img.shields.io/badge/IPC-Standard%20I%2FO%20(NDJSON)-purple?style=flat-square" alt="NDJSON IPC" /></a>
  <a href="requirements.txt"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python Version" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License" /></a>
</p>

---

## Overview

**VoiceEngine** is a production-grade, headless Automatic Speech Recognition (ASR) service tailored for harsh, noisy manufacturing and quality assurance (QA) inspection lines. 

Engineered specifically for Vietnamese industrial speech, VoiceEngine combines an advanced DSP audio pre-filter pipeline, on-device neural Voice Activity Detection (Silero VAD), and a CPU-quantized PhoWhisper engine (CTranslate2 INT8) to deliver deterministic sub-second voice command extraction with minimal CPU footprint and zero GPU requirement.

It operates entirely without a GUI, communicating with host factory control software (e.g., NetTMC) via high-throughput **Newline-Delimited JSON (NDJSON)** over standard input/output pipes.

```
                              ┌────────────────────────────────────────┐
                              │           Industrial Ambient Noise     │
                              └───────────────────┬────────────────────┘
                                                  ▼
┌──────────────┐   WASAPI   ┌──────────────────────────────────────────┐
│  Microphone  │ ─────────► │             DSP Audio Filter             │
│ (16kHz / S16)│            │ (DC Offset + 60Hz HPF + AGC + Soft Limit)│
└──────────────┘            └─────────────────────┬────────────────────┘
                                                  │
                                                  ▼
┌──────────────┐   NDJSON   ┌──────────────────────────────────────────┐
│ Host System  │ ◄───────── │   Phonetic Normalizer & QA Parser        │
│  (e.g. NetTMC│            │      (Defect codes, zones, pass/fail)    │
└──────────────┘            └─────────────────────▲────────────────────┘
                                                  │
                                                  ▼
                            ┌──────────────────────────────────────────┐
                            │    PhoWhisper Tiny (CT2 INT8 CPU)        │
                            │       Triggered by Silero VAD ONNX       │
                            └──────────────────────────────────────────┘
```

---

## Key Features

- **⚡ Sub-Second Edge Inference**: Powered by `phowhisper-tiny-ct2-int8`, achieving ~60–120ms transcription latency on standard quad-core industrial x86 CPUs without dedicated GPUs.
- **🏭 Industrial-Grade Audio DSP**:
  - **DC-Offset Removal**: Eliminates electrical DC drift.
  - **2nd-Order Butterworth High-Pass (60 Hz)**: Cancels factory floor hum, conveyor rumblings, and AC 50/60 Hz power noise.
  - **Automatic Gain Control (AGC)** & **Soft Peak Limiter**: Normalizes soft whispering while preventing digital clipping when operators speak directly into close-proximity mics.
- **🧠 Zero-Latency Neural VAD**: Pure ONNX runtime implementation of **Silero VAD** with a circular ring-buffer (`pre_ring`), dynamically capturing speech onsets while cutting silence within ~400ms.
- **🎯 Vietnamese QA Command Parsing & Normalization**:
  - Handles manufacturing shorthand, regional dialect variations, and acoustic sound-alikes (e.g., phonetic confusion between `A/Ca/K`, `B/Pê`, `C/Xê`, `D/Đê`, `F/Ép`).
  - Maps natural speech to structured defect positions (`Mũi`, `Gót`, `Hông trong`, `Hông ngoài`, `Lưỡi gà`, `Đế`), defect ID numbers (1–24), re-inspection workflows, and pass/fail verdicts.
- **🔌 Seamless Headless IPC**: Designed for embedding into parent desktop wrappers (C#, Electron, Java, or Python) via standard `stdout`/`stderr` separation using line-delimited JSON events.
- **🚫 Lean Architecture**: Completely decoupled from heavy GUI frameworks (strictly **No PyQt / PySide**), eliminating UI thread locks, memory bloat, and external database dependencies.

---

## Directory Structure

```plaintext
VoiceEngine/
├── config.py                 # Central engine configuration & environment bindings
├── engine_headless.py        # Main headless daemon & IPC pipe controller
├── test_quick.py             # Integration test suite for VAD, ASR, and parser
├── requirements.txt          # Python dependencies
├── core/
│   ├── audio_preprocessor.py # Industrial DSP (HPF, AGC, Limiter) + Silero VAD
│   ├── command_parser.py     # Deterministic QA command & regex intent parser
│   ├── phowhisper_engine.py  # CTranslate2 PhoWhisper wrapper & thread manager
│   └── whisper_normalizer.py # Acoustic error correction & phonetic normalizer
└── models/
    ├── silero_vad.onnx       # Silero VAD deep learning model (ONNX)
    └── phowhisper-tiny-ct2-int8/ # Quantized INT8 PhoWhisper weights & vocab
```

---

## Installation

### Prerequisites

- **OS**: Windows 10/11 (Optimized for Windows WASAPI audio subsystem)
- **Python**: 3.10 or 3.11 (64-bit recommended)

### Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/your-org/VoiceEngine.git
cd VoiceEngine

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Models Placement

Ensure the model files are placed inside the `models/` folder:
- `models/silero_vad.onnx`
- `models/phowhisper-tiny-ct2-int8/` (`model.bin`, `config.json`, `vocabulary.json`, `tokenizer.json`)

---

## Usage

### 1. Interactive Console Test Mode

Run directly in console to view real-time VAD indicators, transcribed text, confidence scores, and extracted QA intent commands:

```bash
python engine_headless.py
```

Optional CLI flags:
```bash
# Specify audio input device (by index or partial name)
python engine_headless.py --device "USB Audio"

# Adjust Noise Gate RMS threshold (default: 180)
python engine_headless.py --gate 200
```

### 2. Headless IPC Mode (For NetTMC / Host App Integration)

In IPC mode, stdout is isolated strictly for NDJSON data packets, while internal logs are redirected to stderr:

```bash
python engine_headless.py --ipc
```

---

## Inter-Process Communication (IPC) Protocol

When launched with `--ipc`, VoiceEngine transmits NDJSON events to `stdout`. Each message is a single-line JSON string followed by `\n`.

### Event Types

#### 1. Engine Ready (`ready`)
Emitted once all AI models, DSP pipelines, and audio capture devices are initialized.
```json
{
  "event": "ready",
  "device": "Microphone (Realtek High Definition Audio)",
  "sample_rate": 16000,
  "engine": "phowhisper-tiny-ct2-int8"
}
```

#### 2. Raw Speech Recognized (`speech`)
Emitted after each speech segment is transcribed and normalized.
```json
{
  "event": "speech",
  "text": "mũi một",
  "raw_text": "Mũi 1.",
  "conf": 0.9421,
  "latency_ms": 78.4
}
```

#### 3. Structured QA Command (`command`)
Emitted when recognized speech matches a valid industrial QA intent.
```json
{
  "event": "command",
  "cmd": {
    "intent": "inspection",
    "pos": 1,
    "pos_name": "Mũi",
    "err_code": 1
  },
  "text": "mũi một",
  "conf": 0.9421,
  "latency_ms": 78.4
}
```

#### 4. Error (`error`)
Emitted when an unrecoverable hardware or model initialization error occurs.
```json
{
  "event": "error",
  "message": "Microphone device index out of range or disconnected."
}
```

---

## Configuration Reference

VoiceEngine can be customized via environment variables or modified directly in [`config.py`](file:///d:/VS/VoiceEngine/config.py):

| Variable | Default | Description |
|:---|:---:|:---|
| `PHOWHISPER_MODEL_PATH` | `models/phowhisper-tiny-ct2-int8` | Path to PhoWhisper CTranslate2 model directory |
| `SILERO_VAD_MODEL_PATH` | `models/silero_vad.onnx` | Path to Silero VAD ONNX weight file |
| `PHOWHISPER_CPU_THREADS` | `2` | Number of CPU compute threads for INT8 inference |
| `VOICE_MIN_CONFIDENCE` | `0.45` | Minimum confidence score to accept recognition |
| `AUDIO_NOISE_GATE` | `180` | Noise gate threshold in RMS amplitude |
| `AUDIO_ENABLE_HIGHPASS` | `true` | Enable 60Hz 2nd-order Butterworth high-pass filter |
| `AUDIO_ENABLE_LIMITER` | `true` | Soft limiter to prevent clipping on loud inputs |
| `AUDIO_ENABLE_AGC` | `true` | Dynamic speech amplification for low-volume mics |
| `AUDIO_AGC_TARGET_RMS` | `1500` | Target RMS level for Automatic Gain Control |
| `AUDIO_SILERO_VAD_THRESHOLD` | `0.55` | Speech probability threshold for Silero VAD |

---

## Verification & Testing

To verify the installation and benchmark model execution without needing an active microphone:

```bash
python test_quick.py
```

Expected output:
```plaintext
=== 1. KIỂM THỬ NORMALIZER & PARSER ===
[PASS] 'pass' -> norm: 'pass' -> intent: pass
[PASS] 'đạt' -> norm: 'đạt' -> intent: pass
[PASS] 'mũi' -> norm: 'mũi' -> intent: position
[PASS] 'a một' -> norm: 'a một' -> intent: inspection
...
=== 2. KIỂM THỬ SILERO VAD ONNX ===
Silero VAD available: True
=== 3. KIỂM THỬ PHOWHISPER CT2 INT8 ===
[PHOWHISPER] Nạp mô hình PhoWhisper thành công!
✅ TOÀN BỘ CÁC THÀNH PHẦN VOICEENGINE ĐÃ VƯỢT QUA TEST THÀNH CÔNG!
```

---

## Standalone Executable Packaging

VoiceEngine can be packaged into a standalone zero-dependency executable using PyInstaller:

```bash
pyinstaller --noconfirm --onedir --console `
  --name "VoiceEngine" `
  --add-data "models;models" `
  engine_headless.py
```

The resulting distribution supports self-contained execution without requiring a system Python environment.

---

## License

This project is licensed under the [MIT License](LICENSE).

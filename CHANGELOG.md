# Nhật Ký Thay Đổi (Changelog)

Tất cả các thay đổi đáng chú ý của dự án **VoiceEngine** được lưu lại trong tài liệu này.  
Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/) và tuân thủ [Semantic Versioning (SemVer 2.0.0)](https://semver.org/).

---

## [1.2.0] - 2026-11-04

### Added
- **Single Source of Truth cho Version**: Tạo `core/__version__.py` và gán vào `Config.VERSION`.
- **CLI & IPC Version Inspection**:
  - Hỗ trợ cờ dòng lệnh `python engine_headless.py --version` (hoặc `-v`).
  - Gói tin sự kiện IPC `{"event": "ready", "version": "1.2.0", ...}` gửi trực tiếp sang host C# / NetTMC.
- **Tự động hóa phát hành**: Script `tools/bump_version.py` hỗ trợ nâng cấp version tự động (SemVer, Changelog, PDF Guide, Git commit, Git tag).
- **Tài liệu PDF tự động đồng bộ**: Hiển thị phiên bản `v1.2.0` trên `VoiceEngine_QA_Voice_Command_Guide.pdf`.
- **Cấu trúc dự án chuẩn hóa**: Tách riêng thư mục `tests/`, `tools/`, `docs/`.

### Changed
- **Chuẩn hóa 5 nhóm khẩu lệnh QA**: Áp dụng quy tắc kiểm tra nghiêm ngặt theo `.agent/rules/voiceengine_qa_scope.md`.
  - Nhóm 1: Số - Số (`[Vị trí 1..6] + [Mã lỗi 1..24]`).
  - Nhóm 2: Đạt (`đạt`, `pass`, `ok`, `cho pass`, `qua`...).
  - Nhóm 3: Đạt lại (`đạt lại`, `sửa đạt`, `sửa ok`, `re-ins pass`...).
  - Nhóm 4: Lỗi (`lỗi`, `báo lỗi` hoặc kèm vị trí + lỗi).
  - Nhóm 5: Lỗi lại (`lỗi lại`, `sửa lại`, `sửa` hoặc `[1..6] [1..24] sửa`).
- Loại bỏ hoàn toàn mã vị trí chữ cái (`A-F`) và tên bộ phận giày cũ không thuộc nghiệp vụ QA.
- Cải thiện từ điển `whisper_normalizer.py` xử lý phương ngữ và biến thể âm thanh nhà máy.

### Verified
- Đạt **100% test coverage** với 136/136 ca kiểm thử phương ngữ và âm thanh trong `tests/test_all_cases.py`.

---

## [1.1.0] - 2026-11-02

### Added
- **Cơ chế Acoustic Shadowing**: Tự động lưu file âm thanh `.wav` tại `logs/shadow_wav` theo các chế độ: `matched_only` (mặc định), `all`, `none`.
- **Ghi nhật ký Audit JSONL**: Lưu vết chi tiết toàn bộ phiên nhận diện vào `logs/shadow_audit.jsonl` phục vụ giám sát và tái huấn luyện.
- **Visual ANSI Box Logging**: Bảng hiển thị kết quả nhận diện trực quan trên Terminal khi chạy kiểm thử độc lập (Console Test Mode).
- **Tự động tích hợp Model Weight**: Hỗ trợ nạp model INT8 trực tiếp từ Hugging Face (`ntn823/phowhisper-tiny-cuchi-int8`).

---

## [1.0.0] - 2026-11-01

### Added
- **Tách độc lập thành VoiceEngine Headless Microservice**: Tách hoàn toàn mã nguồn lõi nhận diện giọng nói ra khỏi kiến trúc GUI nguyên khối (CC_QA_VOICE Monolith).
- **Loại bỏ hoàn toàn Vosk & PyQt5**: Tinh gọn hệ thống, tối ưu RAM ($< 150\text{MB}$), không phụ thuộc giao diện đồ họa.
- **Pipeline nhận diện công nghiệp độ trễ siêu thấp**:
  - Tích hợp **PhoWhisper CT2 INT8** cho độ chính xác cao đối với tiếng Việt.
  - Tích hợp **Silero VAD (ONNX)** lọc tạp âm máy móc, tiếng súng hơi và tiếng ồn nhà máy.
  - Bộ tiền xử lý âm thanh DSP: Bộ lọc High-pass Butterworth 60Hz, Soft Limiter chống méo tiếng, và Automatic Gain Control (AGC).
- **Giao tiếp IPC Anonymous Pipe**: Truyền tải sự kiện NDJSON tốc độ cao ($< 0.5\text{ms}$) kết nối hai chiều với phần mềm chủ C# WinForms / MES.

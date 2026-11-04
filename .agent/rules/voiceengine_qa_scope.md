---
trigger: always_on
description: Strictly enforce the 5 QA voice command groups supported by VoiceEngine and exclude legacy position/part names.
---

# VoiceEngine QA Command Scope Rule

- **Supported Command Groups (5 Only)**:
  1. **Number-Number (`Số - Số`)**: `[Position 1..6] + [Defect 1..24]` -> `{"intent": "inspection", "position": P, "defect": D, "result": "fail"}`
  2. **Pass (`Đạt`)**: `đạt`, `pass`, `ok`, `ô kê`, `cho pass`, `qua` -> `{"intent": "pass"}`
  3. **Re-Pass (`Đạt lại / Sửa đạt`)**: `đạt lại`, `sửa đạt`, `sửa ok`, `sửa ô kê`, `sửa rồi`, `re-ins pass`, `rì bát` -> `{"intent": "reins_pass"}`
  4. **Fail (`Lỗi`)**: standalone `lỗi` -> `{"intent": "fail"}`, or `lỗi + [Position 1..6] + [Defect 1..24]` -> `{"intent": "inspection", ...}`
  5. **Re-Fail (`Lỗi lại / Sửa lại`)**: standalone `lỗi lại`, `sửa lại`, `sửa` -> `{"intent": "sua"}`, or `[Position 1..6] + [Defect 1..24] + sửa/sửa lại/lỗi lại/lại` -> `{"intent": "reins_fail", "position": P, "defect": D}`
  *(Plus auxiliary `hủy`, `quay lại` -> `{"intent": "cancel"}`)*
- **Strictly Excluded**:
  - Do NOT support letter positions (`A–F`, `Ca`, `Bê`, `Xê`, `Đê`, `Ép`, `Gờ`).
  - Do NOT support shoe part names (`mũi`, `gót`, `hông ngoài`, `hông trong`, `lưỡi gà`, `đế`).
  - Do NOT support standalone single defect numbers (`bare_number`) without a position (1..6).
- **PDF Documentation Synchronization**:
  - Whenever voice commands, aliases, or grammar rules are updated, ALWAYS update `tools/generate_pdf_guide.py` and recompile `docs/VoiceEngine_QA_Voice_Command_Guide.pdf` (and the root PDF copy) so the documentation stays 100% in sync with the codebase.


# -*- coding: utf-8 -*-
"""
Bộ kiểm thử toàn diện (Comprehensive Test Suite) cho VoiceEngine
Kiểm tra toàn bộ các case:
1. Cặp "Số Số" (1..6 + 1..24)
2. Pass / Đạt
3. Re-Pass / Sửa đạt
4. Fail (1 hơi: Vị trí + Lỗi)
5. Re-Fail (Vị trí + Lỗi + Sửa / Sửa lại)
6. Lệnh 2 bước: Vị trí đơn lẻ, Số lỗi đơn lẻ
7. Hủy / Quay lại
"""
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.whisper_normalizer import normalize_whisper_text
from core.command_parser import parse_command

TEST_CASES = [
    # ===== 1. CÁC BIẾN THỂ "PASS" (ĐẠT) =====
    ("pass", "pass", {}),
    ("đạt", "pass", {}),
    ("cho pass", "pass", {}),
    ("qua", "pass", {}),
    ("ok", "pass", {}),

    # ===== 2. CÁC BIẾN THỂ "RE-PASS" (SỬA ĐẠT) =====
    ("sửa đạt", "reins_pass", {}),
    ("đạt lại", "reins_pass", {}),

    # ===== 3. CẶP "SỐ SỐ" (Vị trí 1..6 + Mã lỗi 1..24) =====
    # Vị trí 1 (Mũi)
    ("một mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}),
    ("một chấm mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}),
    ("một phẩy mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}),
    ("một một", "inspection", {"position": 1, "defect": 1, "result": "fail"}),
    ("một hai", "inspection", {"position": 1, "defect": 2, "result": "fail"}),
    # Vị trí 2 (Hông ngoài)
    ("hai mười tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}),
    ("hai chấm mười tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}),
    ("hai ba", "inspection", {"position": 2, "defect": 3, "result": "fail"}),
    # Vị trí 3 (Hông trong)
    ("ba mười bảy", "inspection", {"position": 3, "defect": 17, "result": "fail"}),
    ("ba chín", "inspection", {"position": 3, "defect": 9, "result": "fail"}),
    # Vị trí 4 (Lưỡi gà)
    ("bốn một", "inspection", {"position": 4, "defect": 1, "result": "fail"}),
    ("bốn mười hai", "inspection", {"position": 4, "defect": 12, "result": "fail"}),
    # Vị trí 5 (Gót)
    ("năm mười bảy", "inspection", {"position": 5, "defect": 17, "result": "fail"}),
    ("năm hai mươi mốt", "inspection", {"position": 5, "defect": 21, "result": "fail"}),
    # Vị trí 6 (Đế)
    ("sáu mười tám", "inspection", {"position": 6, "defect": 18, "result": "fail"}),
    ("sáu bốn", "inspection", {"position": 6, "defect": 4, "result": "fail"}),

    # ===== 4. CÂU GHÉP TÊN VỊ TRÍ + MÃ LỖI (FAIL 1 HƠI) =====
    ("mũi một", "inspection", {"position": 1, "defect": 1, "result": "fail"}),
    ("mũi mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}),
    ("hông ngoài mười tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}),
    ("hông trong chín", "inspection", {"position": 3, "defect": 9, "result": "fail"}),
    ("lưỡi gà một", "inspection", {"position": 4, "defect": 1, "result": "fail"}),
    ("gót mười bảy", "inspection", {"position": 5, "defect": 17, "result": "fail"}),
    ("đế mười tám", "inspection", {"position": 6, "defect": 18, "result": "fail"}),
    ("a một", "inspection", {"position": 1, "defect": 1, "result": "fail"}),
    ("bê hai", "inspection", {"position": 2, "defect": 2, "result": "fail"}),
    ("xê mười bảy", "inspection", {"position": 5, "defect": 17, "result": "fail"}),
    ("đê chín", "inspection", {"position": 3, "defect": 9, "result": "fail"}),
    ("ép một", "inspection", {"position": 4, "defect": 1, "result": "fail"}),

    # ===== 5. TÁI KIỂM LỖI (RE-FAIL / SỬA LẠI) =====
    ("mũi mười bảy sửa", "reins_fail", {"position": 1, "defect": 17}),
    ("gót mười tám sửa lại", "reins_fail", {"position": 5, "defect": 18}),
    ("đế bốn sửa", "reins_fail", {"position": 6, "defect": 4}),
    ("một mười bảy sửa", "reins_fail", {"position": 1, "defect": 17}),

    # ===== 6. LỆNH 2 BƯỚC: VỊ TRÍ ĐƠN LẺ =====
    ("mũi", "position", {"position": 1}),
    ("hông ngoài", "position", {"position": 2}),
    ("hông trong", "position", {"position": 3}),
    ("lưỡi gà", "position", {"position": 4}),
    ("gót", "position", {"position": 5}),
    ("đế", "position", {"position": 6}),
    ("vị trí một", "position", {"position": 1}),
    ("vị trí gót", "position", {"position": 5}),

    # ===== 7. LỆNH 2 BƯỚC: SỐ LỖI ĐƠN LẺ =====
    ("lỗi một", "bare_number", {"index": 1}),
    ("lỗi mười bảy", "bare_number", {"index": 17}),
    ("mười tám", "bare_number", {"index": 18}),

    # ===== 8. HỦY / QUAY LẠI =====
    ("hủy", "cancel", {}),
    ("hủy bỏ", "cancel", {}),
    ("bỏ", "cancel", {}),
    ("quay lại", "cancel", {}),
]

def run_tests():
    passed = 0
    failed = 0
    print(f"{'KẾT QUẢ':<8} | {'CÂU NÓI THỬ NGHIỆM':<28} | {'INTENT':<12} | {'CHI TIẾT LỆNH PARSE ĐƯỢC'}")
    print("-" * 85)

    for phrase, expected_intent, expected_fields in TEST_CASES:
        clean = normalize_whisper_text(phrase)
        cmd = parse_command(clean)
        intent = cmd.get("intent") if cmd else None

        # Kiểm tra khớp intent và các trường chi tiết
        is_match = (intent == expected_intent)
        if is_match and expected_fields:
            for k, v in expected_fields.items():
                if cmd.get(k) != v:
                    is_match = False
                    break

        status_str = "✅ PASS" if is_match else "❌ FAIL"
        if is_match:
            passed += 1
        else:
            failed += 1

        cmd_repr = str(cmd) if cmd else "None"
        print(f"{status_str:<8} | {phrase:<28} | {str(intent):<12} | {cmd_repr}")

    print("-" * 85)
    print(f"TỔNG KẾT: {passed}/{len(TEST_CASES)} PASS ({passed/len(TEST_CASES)*100:.1f}%), {failed} FAIL")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

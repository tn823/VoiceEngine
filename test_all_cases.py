# -*- coding: utf-8 -*-
"""
Bộ kiểm thử chuyên biệt (Test Suite) cho VoiceEngine:
Chỉ tập trung đúng 5 nhóm nghiệp vụ:
1. ĐẠT (Pass)
2. ĐẠT LẠI / SỬA ĐẠT (Re-Pass)
3. LỖI (Đơn lẻ & Đọc lỗi Số - Số: Vị trí 1..6 + Mã lỗi 1..24)
4. LỖI LẠI / SỬA LẠI (Đơn lẻ & Đọc lỗi lại Số - Số: Vị trí 1..6 + Mã lỗi 1..24 + Sửa/Lỗi lại)
5. Khử toàn bộ lỗi Whisper thực tế từ mic người dùng (mươi -> mười, trăm -> chấm, mỗi/mòn -> một, oa -> ba, tháng -> tám, sáng -> sáu...)
"""
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.whisper_normalizer import normalize_whisper_text
from core.command_parser import parse_command

TEST_SUITE = [
    # =========================================================================
    # 1. ĐẠT (PASS) & BIẾN ÂM THỰC TẾ TỪ MIC
    # =========================================================================
    ("đạt", "pass", {}, "Đạt chuẩn"),
    ("pass", "pass", {}, "Pass chuẩn"),
    ("cho pass", "pass", {}, "Cho pass"),
    ("cho đạt", "pass", {}, "Cho đạt"),
    ("ok", "pass", {}, "OK"),
    ("ô kê", "pass", {}, "Ô kê"),
    ("qua", "pass", {}, "Qua"),
    # Biến âm thực tế từ log mic của user
    ("đạc.", "pass", {}, "Log mic: 'đạc.' -> đạt"),
    ("tệt.", "pass", {}, "Log mic: 'tệt.' -> đạt"),
    ("bát.", "pass", {}, "Log mic: 'bát.' -> pass"),
    ("bác.", "pass", {}, "Log mic: 'bác.' -> pass"),
    ("cho bán.", "pass", {}, "Log mic: 'cho bán.' -> cho pass"),

    # =========================================================================
    # 2. ĐẠT LẠI / SỬA ĐẠT (RE-PASS) & BIẾN ÂM THỰC TẾ TỪ MIC
    # =========================================================================
    ("đạt lại", "reins_pass", {}, "Đạt lại chuẩn"),
    ("đại lại", "reins_pass", {}, "Biến âm đại lại"),
    ("sửa đạt", "reins_pass", {}, "Sửa đạt chuẩn"),
    ("sửa ok", "reins_pass", {}, "Sửa ok"),
    ("sửa ô kê", "reins_pass", {}, "Sửa ô kê"),
    ("sửa tốt", "reins_pass", {}, "Sửa tốt"),
    # Biến âm thực tế từ log mic của user
    ("đang lai.", "reins_pass", {}, "Log mic: 'đang lai.' -> đạt lại"),
    ("sửa đạn.", "reins_pass", {}, "Log mic: 'sửa đạn.' -> sửa đạt"),
    ("rửa đạn.", "reins_pass", {}, "Log mic: 'rửa đạn.' -> sửa đạt"),
    ("sửa đàn.", "reins_pass", {}, "Log mic: 'sửa đàn.' -> sửa đạt"),
    ("rửa đen.", "reins_pass", {}, "Log mic: 'rửa đen.' -> sửa đạt"),
    ("sửa đêm", "reins_pass", {}, "Log mic: 'sửa đêm' -> sửa đạt"),
    ("xưa ok.", "reins_pass", {}, "Log mic: 'xưa ok.' -> sửa ô kê"),
    ("số ok.", "reins_pass", {}, "Log mic: 'số ok.' -> sửa ô kê"),
    ("sửa rồi.", "reins_pass", {}, "Log mic: 'sửa rồi.' -> sửa đạt"),

    # =========================================================================
    # 3. LỖI & LỖI LẠI ĐƠN LẺ
    # =========================================================================
    ("lỗi", "fail", {}, "Lỗi đơn lẻ"),
    ("báo lỗi", "fail", {}, "Báo lỗi"),
    ("lỗi lại", "sua", {}, "Lỗi lại đơn lẻ"),
    ("sửa lại", "sua", {}, "Sửa lại đơn lẻ"),
    ("sửa", "sua", {}, "Sửa đơn lẻ"),
    ("xửa.", "sua", {}, "Log mic: 'xửa.' -> sửa"),

    # =========================================================================
    # 4. ĐỌC LỖI SỐ - SỐ (Vị trí 1..6 + Mã lỗi 1..24) - CHUẨN & BIẾN ÂM "MƯƠI"
    # =========================================================================
    # Vị trí 1
    ("một một", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Số-Số: 1.1"),
    ("một hai", "inspection", {"position": 1, "defect": 2, "result": "fail"}, "Số-Số: 1.2"),
    ("một ba", "inspection", {"position": 1, "defect": 3, "result": "fail"}, "Số-Số: 1.3"),
    ("một mười", "inspection", {"position": 1, "defect": 10, "result": "fail"}, "Số-Số: 1.10"),
    ("một mười sáu", "inspection", {"position": 1, "defect": 16, "result": "fail"}, "Số-Số: 1.16"),
    ("một mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Số-Số: 1.17"),
    ("một mười tám", "inspection", {"position": 1, "defect": 18, "result": "fail"}, "Số-Số: 1.18"),
    ("một hai mươi", "inspection", {"position": 1, "defect": 20, "result": "fail"}, "Số-Số: 1.20"),
    ("một hai mươi tư", "inspection", {"position": 1, "defect": 24, "result": "fail"}, "Số-Số: 1.24"),
    ("một chấm mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Số-Số: 1 chấm 17"),
    # Biến âm thực tế Vị trí 1 từ log mic của user
    ("mỗi một.", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Log mic: 'mỗi một.' -> 1.1"),
    ("mỗi mươi bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'mỗi mươi bảy' -> 1.17"),
    ("một mươi bảy.", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'một mươi bảy.' -> 1.17"),
    ("một mươi sáu.", "inspection", {"position": 1, "defect": 16, "result": "fail"}, "Log mic: 'một mươi sáu.' -> 1.16"),
    ("mòn mười tám.", "inspection", {"position": 1, "defect": 18, "result": "fail"}, "Log mic: 'mòn mười tám.' -> 1.18"),
    ("một trăm mười bảy.", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'một trăm mười bảy.' -> 1.17"),
    ("một bác.", "inspection", {"position": 1, "defect": 3, "result": "fail"}, "Log mic: 'một bác.' -> 1.3"),
    ("một bờ.", "inspection", {"position": 1, "defect": 4, "result": "fail"}, "Log mic: 'một bờ.' -> 1.4"),
    ("một bộ.", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Log mic: 'một bộ.' -> 1.1"),
    ("một mét.", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Log mic: 'một mét.' -> 1.1"),
    ("bột bột.", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Log mic: 'bột bột.' -> 1.1"),
    ("một con.", "inspection", {"position": 1, "defect": 1, "result": "fail"}, "Log mic: 'một con.' -> 1.1"),
    ("môm mười tám.", "inspection", {"position": 1, "defect": 18, "result": "fail"}, "Log mic: 'môm mười tám.' -> 1.18"),

    # Vị trí 2 (Đặc biệt xử lý "hai mươi X" -> "hai mười X")
    ("hai một", "inspection", {"position": 2, "defect": 1, "result": "fail"}, "Số-Số: 2.1"),
    ("hai ba", "inspection", {"position": 2, "defect": 3, "result": "fail"}, "Số-Số: 2.3"),
    ("hai mười", "inspection", {"position": 2, "defect": 10, "result": "fail"}, "Số-Số: 2.10"),
    ("hai mươi", "inspection", {"position": 2, "defect": 10, "result": "fail"}, "Whisper 'hai mươi' -> 2.10"),
    ("hai mươi mốt", "inspection", {"position": 2, "defect": 11, "result": "fail"}, "Whisper 'hai mươi mốt' -> 2.11"),
    ("hai mươi hai.", "inspection", {"position": 2, "defect": 12, "result": "fail"}, "Log mic: 'hai mươi hai.' -> 2.12"),
    ("hai mươi ba", "inspection", {"position": 2, "defect": 13, "result": "fail"}, "Whisper 'hai mươi ba' -> 2.13"),
    ("hai mươi bốn", "inspection", {"position": 2, "defect": 14, "result": "fail"}, "Whisper 'hai mươi bốn' -> 2.14"),
    ("hai mươi lăm", "inspection", {"position": 2, "defect": 15, "result": "fail"}, "Whisper 'hai mươi lăm' -> 2.15"),
    ("hai mươi sáu", "inspection", {"position": 2, "defect": 16, "result": "fail"}, "Whisper 'hai mươi sáu' -> 2.16"),
    ("hai mươi sáng.", "inspection", {"position": 2, "defect": 16, "result": "fail"}, "Log mic: 'hai mươi sáng.' -> 2.16"),
    ("hai mươi bảy", "inspection", {"position": 2, "defect": 17, "result": "fail"}, "Log mic: 'hai mươi bảy' -> 2.17"),
    ("hai mươi tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Log mic: 'hai mươi tám' -> 2.18"),
    ("hai mươi tháng.", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Log mic: 'hai mươi tháng.' -> 2.18"),
    ("hai mươi chín", "inspection", {"position": 2, "defect": 19, "result": "fail"}, "Whisper 'hai mươi chín' -> 2.19"),
    ("hai hai mươi", "inspection", {"position": 2, "defect": 20, "result": "fail"}, "Số-Số: 2.20"),
    ("hai hai mươi mốt", "inspection", {"position": 2, "defect": 21, "result": "fail"}, "Số-Số: 2.21"),
    ("hai hai mươi hai", "inspection", {"position": 2, "defect": 22, "result": "fail"}, "Số-Số: 2.22"),
    ("hai chấm mười tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Số-Số: 2 chấm 18"),
    ("em mười tám.", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Log mic: 'em mười tám.' -> 2.18"),

    # Vị trí 3 (Xử lý "ba mươi X" -> "ba mười X")
    ("ba một", "inspection", {"position": 3, "defect": 1, "result": "fail"}, "Số-Số: 3.1"),
    ("ba chín", "inspection", {"position": 3, "defect": 9, "result": "fail"}, "Số-Số: 3.9"),
    ("oa chín.", "inspection", {"position": 3, "defect": 9, "result": "fail"}, "Log mic: 'oa chín.' -> 3.9"),
    ("ba mươi", "inspection", {"position": 3, "defect": 10, "result": "fail"}, "Whisper 'ba mươi' -> 3.10"),
    ("ba mười bảy", "inspection", {"position": 3, "defect": 17, "result": "fail"}, "Số-Số: 3.17"),
    ("ba mươi bảy", "inspection", {"position": 3, "defect": 17, "result": "fail"}, "Whisper 'ba mươi bảy' -> 3.17"),
    ("ba mươi tám", "inspection", {"position": 3, "defect": 18, "result": "fail"}, "Whisper 'ba mươi tám' -> 3.18"),

    # Vị trí 4 (Xử lý "bốn mươi X" -> "bốn mười X")
    ("bốn một", "inspection", {"position": 4, "defect": 1, "result": "fail"}, "Số-Số: 4.1"),
    ("bốn mươi", "inspection", {"position": 4, "defect": 10, "result": "fail"}, "Whisper 'bốn mươi' -> 4.10"),
    ("bốn mười hai", "inspection", {"position": 4, "defect": 12, "result": "fail"}, "Số-Số: 4.12"),
    ("bốn mươi hai", "inspection", {"position": 4, "defect": 12, "result": "fail"}, "Whisper 'bốn mươi hai' -> 4.12"),
    ("bốn mươi bảy", "inspection", {"position": 4, "defect": 17, "result": "fail"}, "Whisper 'bốn mươi bảy' -> 4.17"),

    # Vị trí 5 (Xử lý "năm mươi X" -> "năm mười X")
    ("năm mười bảy", "inspection", {"position": 5, "defect": 17, "result": "fail"}, "Số-Số: 5.17"),
    ("năm mươi bảy", "inspection", {"position": 5, "defect": 17, "result": "fail"}, "Whisper 'năm mươi bảy' -> 5.17"),
    ("năm hai mươi mốt", "inspection", {"position": 5, "defect": 21, "result": "fail"}, "Số-Số: 5.21"),

    # Vị trí 6 (Xử lý "sáu mươi X" -> "sáu mười X")
    ("sáu bốn", "inspection", {"position": 6, "defect": 4, "result": "fail"}, "Số-Số: 6.4"),
    ("sáu mười tám", "inspection", {"position": 6, "defect": 18, "result": "fail"}, "Số-Số: 6.18"),
    ("sáu mươi tám.", "inspection", {"position": 6, "defect": 18, "result": "fail"}, "Log mic: 'sáu mươi tám.' -> 6.18"),
    ("sáu hai mươi tư", "inspection", {"position": 6, "defect": 24, "result": "fail"}, "Số-Số: 6.24"),
    ("sáu hai mười tư.", "inspection", {"position": 6, "defect": 24, "result": "fail"}, "Log mic: 'sáu hai mười tư.' -> 6.24"),

    # Có chữ "lỗi" đi kèm Số - Số (Chuẩn & biến âm thực tế từ mic)
    ("lỗi một mười bảy", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Lỗi 1.17"),
    ("lỗi hai mươi tám", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Lỗi 2.18"),
    ("lỗi ba mươi bảy", "inspection", {"position": 3, "defect": 17, "result": "fail"}, "Lỗi 3.17"),
    ("gỏi một mươi bảy.", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'gỏi một mươi bảy.' -> Lỗi 1.17"),
    ("lỏi một mươi bảy.", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'lỏi một mươi bảy.' -> Lỗi 1.17"),
    ("lối một mươi bảy.", "inspection", {"position": 1, "defect": 17, "result": "fail"}, "Log mic: 'lối một mươi bảy.' -> Lỗi 1.17"),
    ("gói hai mười tám.", "inspection", {"position": 2, "defect": 18, "result": "fail"}, "Log mic: 'gói hai mười tám.' -> Lỗi 2.18"),
    ("nội ba mười bảy.", "inspection", {"position": 3, "defect": 17, "result": "fail"}, "Log mic: 'nội ba mười bảy.' -> Lỗi 3.17"),

    # =========================================================================
    # 5. ĐỌC LỖI LẠI / SỬA LẠI KÈM SỐ - SỐ (RE-FAIL)
    # =========================================================================
    ("một mười bảy sửa", "reins_fail", {"position": 1, "defect": 17}, "1.17 sửa"),
    ("một mươi bảy sữa.", "reins_fail", {"position": 1, "defect": 17}, "Log mic: 'một mươi bảy sữa.' -> 1.17 sửa"),
    ("một mươi tám sửa.", "reins_fail", {"position": 1, "defect": 18}, "Log mic: 'một mươi tám sửa.' -> 1.18 sửa"),
    ("hai mươi sữa", "reins_fail", {"position": 2, "defect": 10}, "Log mic: 'hai mươi sữa' -> 2.10 sửa"),
    ("hai mươi tám sửa lại", "reins_fail", {"position": 2, "defect": 18}, "2.18 sửa lại"),
    ("ba mươi bảy lỗi lại", "reins_fail", {"position": 3, "defect": 17}, "3.17 lỗi lại"),
    ("lỗi lại một mười bảy", "reins_fail", {"position": 1, "defect": 17}, "Lỗi lại 1.17"),
    ("sửa lại hai mươi tám", "reins_fail", {"position": 2, "defect": 18}, "Sửa lại 2.18"),

    # =========================================================================
    # 6. LỆNH HỦY & LỌC ẢO GIÁC / VƯỢT NGƯỠNG
    # =========================================================================
    ("hủy", "cancel", {}, "Hủy"),
    ("quay lại", "cancel", {}, "Quay lại"),
    ("còn thế nhưng thế thì tôi không thể tìm thấy.", None, {}, "Ảo giác Whisper khi im lặng"),
    ("đừng có thể tự tử từ từ từ từ", None, {}, "Ảo giác Whisper lặp từ"),
    ("cũng tôi đã từng mong mỏi mong mỏi", None, {}, "Ảo giác Whisper lặp từ"),
    ("bảy mười", None, {}, "Vượt ngưỡng vị trí 7 (>6)"),
    ("một hai mươi lăm", None, {}, "Vượt ngưỡng mã lỗi 25 (>24)"),
]


def run_tests():
    total = len(TEST_SUITE)
    passed = 0
    failures = []

    print("=" * 95)
    print("  KIỂM THỬ VOICE ENGINE (CHẾ ĐỘ: SỐ-SỐ, ĐẠT, ĐẠT LẠI, LỖI, LỖI LẠI)")
    print("=" * 95)
    for phrase, exp_intent, exp_fields, desc in TEST_SUITE:
        norm = normalize_whisper_text(phrase)
        cmd = parse_command(norm)
        act_intent = cmd.get("intent") if cmd else None

        ok = (act_intent == exp_intent)
        if ok and exp_fields:
            for k, v in exp_fields.items():
                if cmd.get(k) != v:
                    ok = False
                    break

        if ok:
            passed += 1
            print(f"✅ PASS | {phrase:<28} -> {norm:<22} | {str(cmd)}")
        else:
            failures.append((phrase, norm, exp_intent, exp_fields, cmd, desc))
            print(f"❌ FAIL | {phrase:<28} -> {norm:<22} | Thực tế: {cmd} (Mong đợi: {exp_intent} {exp_fields})")

    print("=" * 95)
    print(f"TỔNG KẾT: {passed}/{total} PASS ({passed / total * 100:.2f}%)")
    return len(failures) == 0


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)

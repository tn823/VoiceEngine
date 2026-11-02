# -*- coding: utf-8 -*-
"""
Whisper Normalizer cho VoiceEngine (Phiên bản chuyên biệt: Số-Số, Đạt, Đạt lại, Lỗi, Lỗi lại)
Chuẩn hoá đầu ra từ PhoWhisper trước khi đưa vào Command Parser:
1. Lọc bỏ triệt để các câu ảo giác (hallucination) của PhoWhisper khi im lặng/thở.
2. Chuẩn hoá biến âm thực tế của: Đạt, Đạt lại, Lỗi, Lỗi lại.
3. Chuẩn hoá cặp Số - Số ([Vị trí 1..6] + [Mã lỗi 1..24]):
   - Khôi phục "mươi" -> "mười" khi đọc vị trí 1..6 kèm lỗi 10..19 (VD: "hai mươi tám" -> "hai mười tám", "ba mươi bảy" -> "ba mười bảy", "hai mươi hai" -> "hai mười hai").
   - Khôi phục "trăm" -> "chấm" khi đọc giữa 2 số (VD: "một trăm mười bảy" -> "một chấm mười bảy").
   - Sửa triệt để biến âm của "1 1" ("một một"): "một bộ", "một mét", "bột bột", "một con", "mỗi một"... -> "một một".
   - Sửa các biến âm số thực chiến: mỗi/mòn/môm/mong -> một, em/ai/sai -> hai, oa/pa/ra -> ba, tháng -> tám, sáng -> sáu, một bác -> một ba...
"""

import re
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ánh xạ chữ số sang tiếng Việt chuẩn
_DIGIT_MAP = {
    "1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm",
    "6": "sáu", "7": "bảy", "8": "tám", "9": "chín", "10": "mười",
    "01": "một", "02": "hai", "03": "ba", "04": "bốn", "05": "năm",
    "06": "sáu", "07": "bảy", "08": "tám", "09": "chín",
    "11": "mười một", "12": "mười hai", "13": "mười ba", "14": "mười bốn", "15": "mười lăm",
    "16": "mười sáu", "17": "mười bảy", "18": "mười tám", "19": "mười chín", "20": "hai mươi",
    "21": "hai mươi mốt", "22": "hai mươi hai", "23": "hai mươi ba", "24": "hai mươi bốn",
}

# Các cụm từ ảo giác kinh điển của PhoWhisper khi thu phải tiếng thở / tạp âm nền
_HALLUCINATION_PATTERNS = (
    "còn thế nhưng",
    "còn thế thì",
    "tôi không thể tìm",
    "tôi không tìm thiếu",
    "đừng có thể tự tử",
    "có thể tự tử",
    "cũng tôi đã từng",
    "có thể trong lòng",
    "có thể từ ngày hôm nay",
    "còn bản thân mình",
    "tỏ ra tình cảm",
    "hôm nay anh ta biết nhau",
    "trở về trường hợp của mình",
    "mong mỏi mong mỏi",
    "từng từng từng",
    "từ từ từ từ",
)

_FILLER_EXACT = {
    "còn", "ừ", "à", "ờ", "ạ", "vâng", "dạ", "điều này", "thế nhưng", "thế nhưng mà", "sao"
}

# Bảng khớp toàn câu (Whole-phrase exact mapping)
_EXACT_PHRASE_MAP = {
    # 1. ĐẠT (PASS)
    "đạt": "đạt",
    "đạc": "đạt",
    "đặt": "đạt",
    "đạp": "đạt",
    "đạch": "đạt",
    "tệt": "đạt",
    "đệt": "đạt",
    "đàn": "đạt",
    "đang": "đạt",
    "bạc": "đạt",
    "pass": "pass",
    "pas": "pass",
    "pat": "pass",
    "pát": "pass",
    "bas": "pass",
    "bát": "pass",
    "bác": "pass",
    "qua": "pass",
    "ok": "ok",
    "ô kê": "ô kê",
    "oke": "ok",
    "okê": "ô kê",
    "ông kê": "ô kê",
    "út kê": "ô kê",
    "được": "đạt",
    "đúng": "đạt",
    "cho pass": "cho pass",
    "cho đạt": "đạt",
    "cho bán": "cho pass",
    "cho bát": "cho pass",
    "cho bác": "cho pass",
    "cho phát": "cho pass",
    "cho mát": "cho pass",

    # 2. ĐẠT LẠI / SỬA ĐẠT (RE-PASS)
    "đạt lại": "đạt lại",
    "đại lại": "đạt lại",
    "đang lai": "đạt lại",
    "đang lại": "đạt lại",
    "đặt lại": "đạt lại",
    "đạc lại": "đạt lại",
    "đạt lạy": "đạt lại",
    "đạt loài": "đạt lại",
    "đạt lai": "đạt lại",
    "tốt lại": "đạt lại",
    "ok lại": "đạt lại",
    "ô kê lại": "đạt lại",
    "sửa đạt": "sửa đạt",
    "sửa đạn": "sửa đạt",
    "rửa đạn": "sửa đạt",
    "sửa đàn": "sửa đạt",
    "rửa đàn": "sửa đạt",
    "sửa đạc": "sửa đạt",
    "sửa đặt": "sửa đạt",
    "rửa đạt": "sửa đạt",
    "rủa đảng": "sửa đạt",
    "rỡ nạt": "sửa đạt",
    "rửa đen": "sửa đạt",
    "sửa đen": "sửa đạt",
    "sửa đêm": "sửa đạt",
    "rửa đêm": "sửa đạt",
    "sửa đẹp": "sửa đạt",
    "sửa đèn": "sửa đạt",
    "sửa tốt": "sửa đạt",
    "sửa rồi": "sửa đạt",
    "rửa rồi": "sửa đạt",
    "xửa rồi": "sửa đạt",
    "sửa ok": "sửa ok",
    "sửa ô kê": "sửa ô kê",
    "sửa oke": "sửa ok",
    "xưa ok": "sửa ô kê",
    "xưa ô kê": "sửa ô kê",
    "số ok": "sửa ô kê",
    "số ô kê": "sửa ô kê",
    "rửa ok": "sửa ô kê",
    "rửa ô kê": "sửa ô kê",
    "sửa kê": "sửa ô kê",
    "sửa xong": "sửa đạt",
    "sửa được": "sửa đạt",

    # 3. LỖI ĐƠN LẺ (FAIL)
    "lỗi": "lỗi",
    "lổi": "lỗi",
    "lỏi": "lỗi",
    "lối": "lỗi",
    "lội": "lỗi",
    "nỗi": "lỗi",
    "nổi": "lỗi",
    "nỏi": "lỗi",
    "nối": "lỗi",
    "nội": "lỗi",
    "gỏi": "lỗi",
    "gói": "lỗi",
    "báo lỗi": "lỗi",
    "hàng lỗi": "lỗi",
    "fail": "lỗi",

    # 4. LỖI LẠI / SỬA LẠI ĐƠN LẺ (RE-FAIL)
    "lỗi lại": "lỗi lại",
    "lổi lại": "lỗi lại",
    "lỏi lại": "lỗi lại",
    "lối lại": "lỗi lại",
    "lội lại": "lỗi lại",
    "nỗi lại": "lỗi lại",
    "nổi lại": "lỗi lại",
    "nội lại": "lỗi lại",
    "gỏi lại": "lỗi lại",
    "gói lại": "lỗi lại",
    "lỗi lai": "lỗi lại",
    "báo lỗi lại": "lỗi lại",
    "sửa lại": "lỗi lại",
    "sữa lại": "lỗi lại",
    "xửa lại": "lỗi lại",
    "rửa lại": "lỗi lại",
    "sửa lỗi": "lỗi lại",
    "sữa lỗi": "lỗi lại",
    "giữa lỗi": "lỗi lại",
    "sửa": "sửa",
    "sữa": "sửa",
    "xửa": "sửa",
    "xữa": "sửa",
    "tái kiểm": "lỗi lại",

    # 5. CẶP "1 1" ("MỘT MỘT") BỊ WHISPER NGHE NHẦM NGUYÊN CÂU
    "một bộ": "một một",
    "một bột": "một một",
    "bột bột": "một một",
    "bột một": "một một",
    "bộ một": "một một",
    "bộ bộ": "một một",
    "một mét": "một một",
    "một mép": "một một",
    "một mốt": "một một",
    "mốt mốt": "một một",
    "một con": "một một",
    "một món": "một một",
    "một hộp": "một một",
    "một hột": "một một",
    "một cột": "một một",
    "một cục": "một một",
    "mỗi một": "một một",
    "mòn một": "một một",

    # 6. HỦY / QUAY LẠI
    "hủy": "hủy",
    "huỷ": "hủy",
    "hói": "hủy",
    "hỏi": "hủy",
    "thôi": "hủy",
    "hủy bỏ": "hủy",
    "huỷ bỏ": "hủy",
    "bỏ": "hủy",
    "xóa": "hủy",
    "xoá": "hủy",
    "quay lại": "hủy",
    "cancel": "hủy",
    "clear": "hủy",
}


def normalize_whisper_text(text: str) -> str:
    """
    Chuẩn hoá chuỗi trả về từ PhoWhisper cho chế độ:
    Số - Số, Đạt, Đạt lại, Lỗi, Lỗi lại.
    """
    if not text:
        return ""

    t = text.lower().strip()

    # 1. Loại bỏ toàn bộ dấu câu
    t = re.sub(r"[.,!?;:\"'()\[\]\-_]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if not t or t in _FILLER_EXACT:
        return ""

    # 2. Lọc bỏ ảo giác (hallucination) của Whisper khi im lặng
    for hp in _HALLUCINATION_PATTERNS:
        if hp in t:
            return ""

    # Lọc câu lặp bất thường (ví dụ lặp cùng 1 từ >= 4 lần liên tiếp)
    if re.search(r"\b(\w+)(?:\s+\1){3,}\b", t):
        return ""

    # 3. Kiểm tra khớp nguyên câu (Đạt, Đạt lại, Lỗi, Lỗi lại, 1.1, Hủy)
    if t in _EXACT_PHRASE_MAP:
        return _EXACT_PHRASE_MAP[t]

    # 4. Tách chữ và số dính nhau, tách cụm số 3 chữ số (VD: "117" -> "1 17", "218" -> "2 18")
    t = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", t)
    t = re.sub(r"\b([1-6])(1[0-9]|2[0-4]|0[1-9])\b", r"\1 \2", t)

    # Đổi các con số dạng chữ số sang chữ tiếng Việt
    tokens = t.split()
    tokens = [_DIGIT_MAP.get(tok, tok) for tok in tokens]
    t = " ".join(tokens)

    # 5. Chuẩn hoá các cụm từ khóa đi kèm trong câu ghép Số - Số
    # Biến âm của "lỗi lại" và "lỗi" (gỏi, lỏi, gói, nội, lối, lổi, nỗi...)
    t = re.sub(r"\b(lỗi|lổi|lỏi|lối|lội|nỗi|nổi|nỏi|nối|nội|gỏi|gói|gọi|đổi|đội)\s+(lại|lai|lạy|loài)\b", "lỗi lại", t)
    t = re.sub(r"\b(lổi|lỏi|lối|lội|nỗi|nổi|nỏi|nối|nội|gỏi|gói|gọi|đổi|đội)\b", "lỗi", t)
    t = re.sub(r"\b(đại|đang|đặt|đạc)\s+(lại|lai|lạy)\b", "đạt lại", t)
    t = re.sub(r"\b(sửa|sữa|rửa|giữa|xưa|xửa|sủa)\s+(ok|ô kê|oke|kê)\b", "sửa ô kê", t)
    t = re.sub(r"\b(sửa|sữa|rửa|giữa|xưa|xửa|sủa)\s+(đạt|đạn|đàn|đạc|đặt|đẹp|đèn|đen|đêm|xong|được|tốt|rồi)\b", "sửa đạt", t)
    t = re.sub(r"\b(sữa|xửa|xữa|rửa|giữa|xưa|sủa)\s+lại\b", "sửa lại", t)
    t = re.sub(r"\b(sữa|xửa|xữa|rửa|sủa)\b", "sửa", t)

    if t in _EXACT_PHRASE_MAP:
        return _EXACT_PHRASE_MAP[t]

    # 6. Chuẩn hoá biến âm của SỐ ĐẦU TIÊN (Vị trí 1..6)
    # "mỗi", "mòn", "mộc", "mốc", "mọt", "mọi", "mọp", "mồng", "mong", "mồm", "môm", "môn", "mông", "bột" -> "một"
    t = re.sub(
        r"\b(mỗi|mòn|mộc|mốc|mọt|mọi|mọp|mồng|mong|mồm|môm|môn|mông|bột|bộ)\s+(một|mốt|bộ|bột|mét|mép|con|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy|bác|bát|bờ)\b",
        r"một \2",
        t
    )
    # "ai", "hhai", "hay", "sai", "em" đứng đầu trước số -> "hai" (VD: "em mười tám" -> "hai mười tám", "sai mười bảy" -> "hai mười bảy")
    t = re.sub(
        r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa)\s+)*)(ai|hhai|hay|sai|em)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy)\b",
        r"\1hai \3",
        t
    )
    # "oa", "pa", "ra" đứng đầu trước số -> "ba" (VD: "oa chín" -> "ba chín", "ra hai" -> "ba hai")
    t = re.sub(
        r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa)\s+)*)(oa|pa|ra)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy)\b",
        r"\1ba \3",
        t
    )
    # "bó", "bồn", "bổn" trước số -> "bốn"
    t = re.sub(
        r"\b(bó|bồn|bổn)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy)\b",
        r"bốn \2",
        t
    )
    # "dăm", "nằm", "nắm" trước số -> "năm"
    t = re.sub(
        r"\b(dăm|nằm|nắm)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy)\b",
        r"năm \2",
        t
    )
    # "sáo", "xáu", "xáo", "sau" trước số -> "sáu"
    t = re.sub(
        r"\b(sáo|xáu|xáo|sau)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|bẩy|tám|tháng|chín|chính|mười|mươi|trăm|chấm|phẩy)\b",
        r"sáu \2",
        t
    )

    # 7. Khắc phục lỗi Whisper nghe nhầm "chấm" thành "trăm" giữa 2 số
    # VD: "một trăm mười bảy" -> "một chấm mười bảy", "một trăm linh một" -> "một chấm một"
    t = re.sub(
        r"\b(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu)\s+trăm(?:\s+linh|\s+lẻ)?\s+",
        r"\1 chấm ",
        t
    )

    # 8. Chuẩn hoá biến âm của SỐ THỨ HAI (Mã lỗi 1..24)
    # "người bảy" -> "mười bảy", "bùi lăm" -> "mười lăm"
    t = re.sub(r"\b(người|mùi|bùi|buổi|mồi)\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|lắm|sáu|sáng|bảy|bẩy|tám|tháng|chín|chính)\b", r"mười \2", t)

    # "tháng", "táng", "tánh", "tắm" sau số/mười/mươi/chấm -> "tám" (VD: "hai mươi tháng" -> "hai mươi tám")
    t = re.sub(r"\b(một|hai|ba|bốn|tư|năm|lăm|sáu|mười|mươi|chấm|phẩy)\s+(tháng|táng|tánh|tắm)\b", r"\1 tám", t)
    # "sáng", "sáo", "xáu" sau số/mười/mươi/chấm -> "sáu" (VD: "hai mươi sáng" -> "hai mươi sáu")
    t = re.sub(r"\b(một|hai|ba|bốn|tư|năm|lăm|sáu|mười|mươi|chấm|phẩy)\s+(sáng|sáo|xáu)\b", r"\1 sáu", t)
    # "bẩy", "bẫy" -> "bảy"
    t = re.sub(r"\b(bẩy|bẫy)\b", "bảy", t)
    # "chính", "chíng" -> "chín"
    t = re.sub(r"\b(chính|chíng)\b", "chín", t)
    # "bống" -> "bốn"
    t = re.sub(r"\bbống\b", "bốn", t)
    # "lắm", "lam" sau mười/mươi -> "lăm"
    t = re.sub(r"\b(mười|mươi)\s+(lắm|lam|năm)\b", r"\1 lăm", t)
    # "một ai" -> "một hai", "ai ai" -> "hai hai"
    t = re.sub(r"\bmột\s+ai\b", "một hai", t)
    t = re.sub(r"\bai\s+ai\b", "hai hai", t)

    # Khắc phục triệt để lỗi "1 1" ("một một") và "<vị trí> một" bị nghe thành "một bộ", "một mét", "một bột", "một con"...
    t = re.sub(
        r"\b(một|hai|ba|bốn|tư|năm|sáu)\s+(bộ|bột|bậc|bọc|bọt|bộp|mét|mép|mọp|mọt|mộc|mốc|món|môn|mông|mồm|môm|con|hột|cột|cục|hộp)\b",
        r"\1 một",
        t
    )
    # "một bác", "một bát", "một pass" -> "một ba"
    t = re.sub(r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa)\s+)*)(một|hai|ba|bốn|tư|năm|sáu)\s+(bác|bát|pát|pat|bas|pass|bả|bá)\b", r"\1\2 ba", t)
    # "một bờ" -> "một bốn"
    t = re.sub(r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa)\s+)*)(một|hai|ba|bốn|tư|năm|sáu)\s+bờ\b", r"\1\2 bốn", t)

    # 9. QUY TẮC VÀNG CHO CẶP SỐ - SỐ: KHÔI PHỤC "MƯƠI" -> "MƯỜI"
    # a) Với vị trí 1, 3, 4, 5, 6 ("một", "ba", "bốn", "tư", "năm", "lăm", "sáu"):
    #    Vì mã lỗi chỉ từ 1..24 (không có lỗi 30, 40, 50, 60), mọi cụm "(một|ba|bốn|tư|năm|lăm|sáu) mươi [1..9]"
    #    ở bất kỳ đâu trong câu đều CHẮC CHẮN 100% là "mười"!
    t = re.sub(
        r"\b(một|ba|bốn|tư|năm|lăm|sáu)\s+mươi\s+(một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|tám|chín)\b",
        r"\1 mười \2",
        t
    )
    # b) Với vị trí 2 ("hai mươi [lăm/sáu/bảy/tám/chín]"):
    #    Vì mã lỗi chỉ đến 24 (không có lỗi 25..29), mọi cụm "hai mươi (lăm|năm|sáu|bảy|tám|chín)"
    #    ở bất kỳ đâu trong câu đều CHẮC CHẮN 100% là "hai mười (15..19)"!
    t = re.sub(
        r"\bhai\s+mươi\s+(lăm|năm|sáu|bảy|tám|chín)\b",
        r"hai mười \1",
        t
    )
    # c) Khi từ đầu tiên là Vị trí (1..6) + "mươi" (cho cả lỗi 10 và lỗi 11..14 của vị trí 2):
    t = re.sub(
        r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa|vị\s+trí)\s+)*(?:một|hai|ba|bốn|tư|năm|lăm|sáu)(?:\s+(?:chấm|phẩy|lỗi))?)\s+mươi\b",
        r"\1 mười",
        t
    )
    t = re.sub(r"\bmười\s+mốt\b", "mười một", t)

    # Nếu chỉ có đúng 2 âm tiết số: "<vị trí 1..6> mốt" -> "<vị trí 1..6> một" (VD: "ba mốt" -> "ba một" = 3.1)
    # Còn nếu có 3 âm tiết số: "<vị trí 1..6> hai mốt" -> giữ nguyên "hai mốt" (= 21, VD: "năm hai mốt" = 5.21)
    t = re.sub(
        r"^((?:(?:lỗi\s+lại|lỗi|sửa\s+lại|sửa)\s+)*)(một|hai|ba|bốn|tư|năm|sáu)\s+mốt(\s+(?:sửa|sửa\s+lại|lỗi\s+lại|lỗi))?$",
        r"\1\2 một\3",
        t
    )

    # Xử lý hậu tố "số" thừa ở cuối câu (VD: "một mười bảy số" -> "một mười bảy")
    t = re.sub(r"^((?:một|hai|ba|bốn|tư|năm|sáu)\s+mười(?:\s+\w+)?)\s+số$", r"\1", t)

    return re.sub(r"\s+", " ", t).strip()

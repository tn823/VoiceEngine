# -*- coding: utf-8 -*-
"""
Whisper Normalizer cho CC_QA_VOICE
Chuẩn hoá đầu ra từ PhoWhisper trước khi đưa vào Command Parser:
1. Tách chữ và số dính nhau ("A1" -> "A 1", "1a" -> "1 a")
2. Chuyển số dạng ký tự (1-25) thành từ tiếng Việt chuẩn
3. Loại bỏ dấu câu phát sinh từ Whisper (. , ! ? ; : " ' - _)
"""

import re
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ánh xạ số 1-25 sang tiếng Việt chuẩn
_DIGIT_MAP = {
    "1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm",
    "6": "sáu", "7": "bảy", "8": "tám", "9": "chín", "10": "mười",
    "01": "một", "02": "hai", "03": "ba", "04": "bốn", "05": "năm",
    "06": "sáu", "07": "bảy", "08": "tám", "09": "chín",
    "11": "mười một", "12": "mười hai", "13": "mười ba", "14": "mười bốn", "15": "mười lăm",
    "16": "mười sáu", "17": "mười bảy", "18": "mười tám", "19": "mười chín", "20": "hai mươi",
    "21": "hai mươi mốt", "22": "hai mươi hai", "23": "hai mươi ba", "24": "hai mươi bốn", "25": "hai mươi lăm"
}


def normalize_whisper_text(text: str) -> str:
    """
    Chuẩn hoá triệt để chuỗi trả về từ PhoWhisper.
    Ví dụ:
      "A1."       -> "a một"
      "a 1"       -> "a một"
      "Một A."    -> "một a"
      "21"        -> "hai mươi mốt"
      "Pass."     -> "pass"
      "Đạt!"      -> "đạt"
    """
    if not text:
        return ""

    t = text.lower().strip()

    # 1. Bỏ toàn bộ dấu câu Whisper hay tự động thêm vào
    t = re.sub(r"[.,!?;:\"'\-_]+", " ", t)

    # 1b. Khắc phục lỗi Whisper nghe nhầm 'chấm' thành 'trăm' khi đọc giữa 2 số
    t = re.sub(
        r"\b((?:một|hai|ba|bốn|tư|năm|lăm|sáu|bảy|tám|chín|mười|mười\s+[^\s]+|hai\s+[^\s]+|\d+))\s+trăm\s+(một|hai|ba|bốn|tư|năm|lăm|sáu|\d+)\b",
        r"\1 chấm \2",
        t
    )

    # 1c. Khôi phục từ "mười" cho các lỗi 10-17 trên Chuyền P211:
    # Do Whisper có xu hướng viết "mươi" thay vì "mười" khi đi sau vị trí (1..6)
    # Ví dụ: "ba mươi ba" -> "ba mười ba" (Lỗi 13), "ba mươi lăm" -> "ba mười lăm" (Lỗi 15),
    #        "ba mươi sáu" -> "ba mười sáu" (Lỗi 16), "ba mươi bảy" -> "ba mười bảy" (Lỗi 17),
    #        "bốn mươi" -> "bốn mười" (Lỗi 10).
    t = re.sub(r"\b([1-6]|một|ba|bốn|tư|năm|sáu)\s+mươi\b", r"\1 mười", t)
    t = re.sub(r"\bmười\s+mốt\b", "mười một", t)
    t = re.sub(r"\b(một|hai|ba|bốn|tư|năm|sáu)\s+mốt\b", r"\1 một", t)

    # 1d. Tách số 3 chữ số nếu Whisper xuất ra dạng số liền: Vị trí (1..6) + Mã lỗi (10..17)
    # Ví dụ: "313" -> "3 13", "316" -> "3 16", "117" -> "1 17", "510" -> "5 10"
    t = re.sub(r"\b([1-6])(1[0-7]|0[1-9])\b", r"\1 \2", t)

    # 1e. Bổ sung chuẩn hóa âm học thực tế (Nam Bộ & tiếng ồn nhà xưởng):
    t_strip = t.strip()
    if t_strip in ("hói", "hỏi", "thôi"):
        return "hủy"
    if t_strip in ("đệt", "đang", "đàn", "tệt", "bạc"):
        return "đạt"

        # Chuẩn hoá tiếng ồn phòng & biến thể âm học:
    t = re.sub(r'\b(sổ|rổ|rủa|rửa|giữa|xưa|số|sủa|giỗ)\s+(ok|ô kê|oke|kê)\b', 'sửa ô kê', t)
    t = re.sub(r'\b(rủa\s+đảng|rỡ\s+nạt)\b', 'sửa đạt', t)
    t = re.sub(r'\bút\s+kê\b', 'ô kê', t)
    t = re.sub(r'\bô kê\s+rồi\s+lắc\b', 'ô kê', t)
    t = re.sub(r'\bai\s+ai\b', 'hai hai', t)
    t = re.sub(r'\bra\s+hai\b', 'ba hai', t)
    t = re.sub(r'\bmột\s+mươi\s+bảy\s+số\b', 'một mười bảy', t)
    t = re.sub(r'\b(mười\s+\w+)\s+số\b', r'\1', t)
    t = re.sub(r'\b(sửa|rửa)\s+mỏ\s+', r'sửa một ', t)
    t = re.sub(r'\bai\s+(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\b', r'hai \1', t)
    t = re.sub(r'\bmột\s+(bậc|bột)\b', 'một một', t)
    t = re.sub(r'\b(số|rửa|giữa|xưa|sữa|xửa|sủa)\s+(mười|mươi)\b', r'sửa \2', t)
    t = re.sub(r'\b(ok|ô kê|oke)\s+(sửa|sữa|xưa)\b', 'sửa ô kê', t)
    t = re.sub(r'\b(sửa|sữa|rửa|giữa|xưa)\s+(đạt|đạn|đẹp|đèn)\b', 'sửa đạt', t)
    t = re.sub(r'\bsự\s+bỏ\s+(mời|mười|mươi)\b', 'sửa bốn mười', t)
    t = re.sub(r'\b(về\s+chín|về\s+trí)\s+', 'vị trí ', t)
    t = re.sub(r'\bhai\s+máu\b', 'hai mốt', t)

    # Âm 'sửa' bị nghe nhầm thành 'số', 'rửa', 'giữa', 'xưa', 'sữa', 'xửa'
    t = re.sub(r'\b(xưa\s+sữa|sửa\s+sữa|sữa\s+sửa|sửa\s+xưa|xưa\s+sửa)\b', 'sửa', t)
    t = re.sub(r'\b(số|rửa|giữa|xưa|sữa|xửa)\s+(ok|ô kê|oke|kê|xong|đạt|đạn)\b', r'sửa \2', t)
    t = re.sub(r'\bsửa\s+kê\b', 'sửa ô kê', t)
    t = re.sub(r'\bsửa\s+(xong|đạn)\b', 'sửa đạt', t)
    t = re.sub(r'\b(số|rửa|giữa|xưa|sữa|xửa)\s+(một|hai|ba|bốn|năm|sáu|ca|a|b|bê|d|đê|f|ép|c|xê|e|g|gờ|h|hát|hắt)\b', r'sửa \2', t)

    # Âm 'bó' trước số -> bốn
    t = re.sub(r'\bbó\s+(mười|mươi|\d+|một|hai|ba|bốn|năm|sáu)\b', r'bốn \1', t)

    # 'hát một hai' / 'hắt một hai' -> vị trí 6 lỗi 12: 'sáu mười hai'
    t = re.sub(r'\b(hát|hắt)\s+một\s+hai\b', 'sáu mười hai', t)
    t = re.sub(r'\bmột\s+ai\b', 'một hai', t)

    # Khử lặp cụm từ (vd: 'bốn mười sữa bốn mười' -> 'sửa bốn mười', 'sửa đạt sửa đạt' -> 'sửa đạt')
    t = re.sub(r'\b(\w+\s+\w+)\s+sửa\s+\1\b', r'sửa \1', t)
    t = re.sub(r'\b(sửa\s+\w+)\s+\1\b', r'\1', t)
    t = re.sub(r'\b(sửa\s+đạt)\s+\1\b', r'\1', t)

    # 2. Tách chữ và số dính liền nhau (Bug 1: A1 -> a 1, 1a -> 1 a)
    t = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", t)

    # 3. Thay thế các con số dạng chữ số (1-25) thành chữ tiếng Việt
    _NUM_WORDS = set(_DIGIT_MAP.values()) | set(_DIGIT_MAP.keys()) | {
        "một", "mốt", "hai", "ba", "bốn", "tư", "năm", "lăm", "sáu", "bảy", "tám", "chín", "mười", "chính"
    }
    _POS_WORDS = {
        "k", "ca", "a", "b", "bê", "d", "đ", "đê", "f", "ép", "ét", "c", "xê", "g", "gờ", "e",
        "đen", "đêm", "đây", "đi", "đến"
    }
    tokens = t.split()
    norm_tokens = []
    for i, tok in enumerate(tokens):
        is_prev_num = (i > 0 and norm_tokens[-1] in _NUM_WORDS)
        is_next_num = (i + 1 < len(tokens) and tokens[i + 1] in _NUM_WORDS)
        is_adjacent_num = is_prev_num or is_next_num

        is_prev_pos = (i > 0 and norm_tokens[-1] in _POS_WORDS)
        is_next_pos = (i + 1 < len(tokens) and tokens[i + 1] in _POS_WORDS)
        is_adjacent_pos = is_prev_pos or is_next_pos

        if tok in _DIGIT_MAP:
            norm_tokens.append(_DIGIT_MAP[tok])
        elif re.match(r"^h+ai$", tok):
            norm_tokens.append("hai")
        elif tok == "ai" and is_adjacent_pos:
            norm_tokens.append("hai")
        elif tok in ("mọi", "mọt", "mọc", "mộc", "mọp", "mò", "mồng", "mong") and (is_adjacent_pos or is_adjacent_num):
            norm_tokens.append("một")
        elif tok in ("đen", "đêm", "đây", "đi", "đến") and is_adjacent_num:
            norm_tokens.append("đê")
        elif tok in ("kẹt", "kẹp") and is_adjacent_num:
            norm_tokens.append("ca")
        elif tok == "de":
            norm_tokens.append("đê")
        elif tok == "say":
            norm_tokens.append("xê")
        elif tok in ("bể", "bề", "bế", "bệ", "bễ"):
            norm_tokens.append("bê")
        elif tok in ("k", "ca"):
            norm_tokens.append("ca")
        elif tok in ("cả", "cá", "cà", "cơ", "cớ") and is_adjacent_num:
            norm_tokens.append("ca")
        elif tok in ("g", "rờ"):
            norm_tokens.append("gờ")
        elif tok in ("rồi", "rổi", "rỗi", "gửi", "gởi", "giờ") and is_adjacent_num:
            norm_tokens.append("gờ")
        else:
            norm_tokens.append(tok)

    result = " ".join(norm_tokens).strip()

    # 4. Thay thế cụm từ dính âm / nhầm âm thường gặp từ Whisper
    _QUIRKS = {
        # Đ (Đê) fixes
        "mọi đêm": "một đê",
        "mọi đê": "một đê",
        "hhai đê": "hai đê",
        "ai đây": "hai đê",
        "hai đây": "hai đê",
        "mười ba đen": "mười ba đê",
        # K (Ca) & G (Gờ) fixes
        "cà ruột": "ca một",
        "hai kẹt": "hai ca",
        "xin lắm gờ": "mười lăm gờ",
        "xin lăm gờ": "mười lăm gờ",
        "xin lắm": "mười lăm",
        "xin lăm": "mười lăm",
        "cô mười ba giờ": "mười ba gờ",
        "bố ma": "bốn a",
        "sexy": "xê hai",
        "mười lăm he": "mười lăm e",
        "mười lăm è": "mười lăm e",
        "hết chính": "ép chín",
        "hết chín": "ép chín",
        "ép dính": "ép chín",
        "ba x mười một": "xê mười một",
        "x mười một": "xê mười một",
        "giữa lỗi một": "sửa lỗi một",
        "giữa lỗi": "sửa lỗi",
        "bác": "pass",
        "đạt loài": "đạt lại",
        "đàn": "đạt",
        "tệt": "đạt",
        "ông kê": "ô kê",
        "okê": "ô kê",
        # Các cụm nhầm âm thực tế trích xuất từ log thực chiến
        "bẩy": "bảy",
        "người bảy": "mười bảy",
        "người bẩy": "mười bảy",
        "mười lắm": "mười lăm",
        "bùi lắm": "mười lăm",
        "de mùi": "đê mười",
        "đê mùi": "đê mười",
        "e bùi": "e mười",
        "xe bố": "xê bốn",
        "he he bốn": "e bốn",
        "he he bố": "e bốn",
        "em mười ba": "e mười ba",
        "em mười bốn": "e mười bốn",
        "em mười lăm": "e mười lăm",
        "he mười bốn": "e mười bốn",
        "hee tám": "e tám",
        "dăm he": "năm e",
        "giám the": "năm e",
        "mười bố mẹ": "mười bốn e",
        "bùi lắm he": "mười lăm e",
        "buổi sáu que": "mười sáu e",
        "ser mi h": "xê mười hai",
        # Biến âm phương ngữ Nam Bộ thực tế
        "mọp": "một",
        "mọt": "một",
        "người mọc bè": "mười một bê",
        "người một": "mười một",
        "mười một ba": "mười một bê",
        "xửa mọp": "sửa một",
        "xử mọp": "sửa một",
        "xửa hè": "sửa e",
        # ===== Nhóm lỗi nhầm âm thực tế trích xuất từ test run =====
        # 1. B (Bê): "bốn bê" hay bị Whisper nhận thành "bố mẹ", "bốn bề", "mười bốn ba"
        "bố mẹ": "bốn bê",
        "bồ mẹ": "bốn bê",
        "bố mê": "bốn bê",
        "bốn bề": "bốn bê",
        "bề năm": "bê năm",
        "sáu về": "sáu bê",
        "chín bả": "chín bê",
        "chín bế": "chín bê",
        "mười ba bả": "mười ba bê",
        "mười lăm bế": "mười lăm bê",
        "mười bảy bảy": "mười bảy bê",
        # Chuẩn hóa 'em <số>' thành 'e <số>' để không cần gán 'em' thành vị trí E đơn lẻ
        "em một": "e một",
        "em hai": "e hai",
        "em ba": "e ba",
        "em bốn": "e bốn",
        "em năm": "e năm",
        "em sáu": "e sáu",
        "em bảy": "e bảy",
        "em tám": "e tám",
        "em chín": "e chín",
        "em chính": "ép chín",
        "em mười": "e mười",
        # 2. C (Xê): các biến âm sơi, sười, rơi, sề, sư, xưa, sệt, sáy, giây
        "sơi một": "xê một",
        "một giây": "một xê",
        "hai sệt": "hai xê",
        "bốn sề": "bốn xê",
        "bốn sệt": "bốn xê",
        "sười năm": "xê năm",
        "sáu sệt": "sáu xê",
        "sề tám": "xê tám",
        "xưa tám": "xê tám",
        "sư chín": "xê chín",
        "sơi mười": "xê mười",
        "rơi mười": "xê mười",
        "rơi mười hai": "xê mười hai",
        "sơi mười sáu": "xê mười sáu",
        "sơi mười bảy": "xê mười bảy",
        "mười bảy sáy": "mười bảy xê",
        "xưa mới chín": "xê mười chín",
        # 3. D (Đê): các biến âm đến, đấy, đêm
        "mười đến": "mười đê",
        "mười sáu đến": "mười sáu đê",
        "vừa ba đấy": "mười ba đê",
        "rồi đây": "mười đê",
        "mười hai đêm": "mười hai đê",
        # 4. E / Ê: biến âm hè, yé, lên
        "sáu hè": "sáu e",
        "mười sáu hè": "mười sáu e",
        "và yé": "ba e",
        "ba lên": "ba e",
        # 5. F (Ép): biến âm ế pa, ếp một, mét, với hai ép
        "ế pa": "ép ba",
        "ếp một": "ép một",
        "mười bảy mét": "mười bảy ép",
        "với hai ép": "mười hai ép",
        # 6. A / K: trên na -> chín a, trên ca -> chín ca
        "trên na": "chín a",
        "trên ca": "chín ca",
        "chim ca": "chín ca",
        # 7. G (Gờ / Giờ): các biến thể nhận nhầm âm gờ -> giờ/nặng
        "một giờ": "một gờ",
        "hai giờ": "hai gờ",
        "mười bảy giờ": "mười bảy gờ",
        "gờ nặng": "gờ năm",
        "gờ mọc": "gờ một",
        # 8. Các biến thể mới phát hiện từ đợt test lại:
        "xưa mười bảy": "xê mười bảy",
        "bồn rơi": "bốn xê",
        "sau giây": "sáu xê",
        "sề năm": "xê năm",
        "sể nam": "xê năm",
        "một sệt": "một xê",
        "hai giây": "hai xê",
        "một đi": "một đê",
        "ai đê": "hai đê",
        "chiến bề": "chín bê",
        "chiến bê": "chín bê",
        "năm nơi": "năm đê",
        "sáu bể": "sáu bê",
        "mọi bài bề": "mười bảy bê",
        "mồi sau e": "sáu e",
        "mỗi chín bê": "mười chín bê",
        # 9. Bổ sung các biến âm thực tế từ shadow audit:
        "am mười": "a mười",
        "am một": "a một",
        "áp một": "a một",
        "áp hai": "a hai",
        "áp ba": "a ba",
        "áp bốn": "a bốn",
        "áp năm": "a năm",
        "ác một": "a một",
        "ác hai": "a hai",
        "át một": "a một",
        "át mốt": "a một",
        "bố mẹ nuôi": "bốn bê",
        "xít thai": "xê hai",
        "sợi hai": "xê hai",
        "suỡ một": "sửa một",
        "sua một": "sửa một",
    }
    for k, v in _QUIRKS.items():
        pattern = r"(?<!\w)" + re.escape(k) + r"(?!\w)"
        result = re.sub(pattern, v, result)

    return result


if __name__ == "__main__":
    test_cases = [
        "A1.",
        "a 1",
        "Một A.",
        "21",
        "Pass.",
        "Đạt!",
        "b2",
        "d15",
        "e4.",
        "sửa đạt!",
    ]
    print("=== KIỂM THỬ WHISPER NORMALIZER ===")
    for tc in test_cases:
        norm = normalize_whisper_text(tc)
        print(f"'{tc}' -> '{norm}'")

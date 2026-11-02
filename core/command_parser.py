import re
from difflib import get_close_matches

# Chỉ còn 3 loại từ khoá: tên vị trí chuẩn, số (đếm lỗi), và đạt/sửa.
# Đã bỏ hẳn: mode (chế độ on/óp), "đã biết", chọn mẫu, tên lỗi bằng chữ.

_VI_NUM = {
    "một": 1,  "mốt": 1,  "mốc": 1,  "hai": 2,  "ba": 3,   "bốn": 4,  "tư": 4,  "năm": 5,  "lăm": 5,
    "sáu": 6,  "bảy": 7,  "bẩy": 7,  "tám": 8,  "chín": 9,  "mười": 10,

    "mười một": 11, "mười hai": 12, "mười ba": 13, "mười bốn": 14,
    "mười lăm": 15, "mười năm": 15, "mười sáu": 16, "mười bảy": 17, "mười bẩy": 17,
    # Chuyền P211: Danh mục chỉ gồm 17 lỗi (1-17), loại bỏ số > 17 để tránh nhầm lẫn cặp số
    "bống": 4, "táng": 8, "chíng": 9, "chính": 9,
    "mot": 1, "bon": 4, "nam": 5, "lam": 5,
    "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10,
    "muoi mot": 11, "muoi hai": 12, "muoi ba": 13, "muoi bon": 14, "muoi tu": 14,
    "muoi lam": 15, "muoi nam": 15, "muoi sau": 16, "muoi bay": 17,
}

_POSITION_NAMES: dict[str, int] = {
    # ===== TÊN VỊ TRÍ TIẾNG VIỆT =====
    "mũi": 1, "mũi giày": 1,
    "hông ngoài": 2,
    "hông trong": 3,
    "lưỡi gà": 4,
    "gót": 5, "gót giày": 5,
    "đế": 6, "đế giày": 6,

    # ===== 1: A / K (Ca) =====
    "A": 1, "Á": 1, "À": 1, "Ả": 1, "Ã": 1, "Ạ": 1,
    "a": 1, "á": 1, "à": 1, "ả": 1, "ã": 1, "ạ": 1,
    "AA": 1, "ÀA": 1, "ÁA": 1,
    "K": 1, "k": 1, "CA": 1, "Ca": 1, "ca": 1, "CÁ": 1, "cá": 1, "CÀ": 1, "cà": 1,

    # ===== 2: Bê / Pê =====
    "B": 2, "b": 2, "BÊ": 2, "bê": 2,
    "Bè": 2, "bè": 2, "Bẻ": 2, "bẻ": 2, "Bẽ": 2, "bẽ": 2, "Bẹ": 2, "bẹ": 2, "Bé": 2, "bé": 2,
    "Bề": 2, "bề": 2, "Bể": 2, "bể": 2, "Bễ": 2, "bễ": 2, "Bệ": 2, "bệ": 2, "Bế": 2, "bế": 2,
    "bờ": 2, "BỜ": 2,
    "BE": 2, "be": 2,
    "P": 2, "p": 2, "PÊ": 2, "Pè": 2, "Pẻ": 2, "Pẽ": 2, "Pẹ": 2,
    "pê": 2, "pè": 2, "pẻ": 2, "pẽ": 2, "pẹ": 2,
    "PE": 2, "pe": 2,
    "BÊÊ": 2, "PÊÊ": 2,

    # ===== 5: Xê / Cê =====
    "C": 5, "c": 5, "CÊ": 5, "Cè": 5, "Cẻ": 5, "Cẽ": 5, "Cẹ": 5,
    "cê": 5, "cè": 5, "cẻ": 5, "cẽ": 5, "cẹ": 5,
    "cờ": 5, "CỜ": 5,
    "CE": 5, "ce": 5,
    "X": 5, "x": 5, "XÊ": 5, "Xè": 5, "Xẻ": 5, "Xẽ": 5, "Xẹ": 5,
    "xê": 5, "xè": 5, "xẻ": 5, "xẽ": 5, "xẹ": 5,
    "XE": 5, "xe": 5,
    "SÊ": 5, "sê": 5,          # người hay đọc nhầm C/X thành S
    "SE": 5, "se": 5,
    "SAY": 5, "say": 5,

    # ===== 3: Đê =====
    "D": 3, "d": 3, "Đ": 3, "đ": 3, "ĐÊ": 3, "Đè": 3, "Đẻ": 3, "Đẽ": 3, "Đẹ": 3,
    "đê": 3, "đè": 3, "đẻ": 3, "đẽ": 3, "đẹ": 3,
    "đờ": 3, "ĐỜ": 3, "dờ": 3, "DỜ": 3,
    "DE": 3, "de": 3, "ĐE": 3, "đe": 3,
    "DÊ": 3, "dê": 3,            # hay bỏ dấu đ
    "ĐÊÊ": 3,
    "đêm": 3, "đen": 3, "đây": 3, "đi": 3, "đến": 3,

    # ===== 4: Ép / Ét =====
    "F": 4, "f": 4, "ÉP": 4, "ép": 4,
    "EP": 4, "ep": 4,
    "ÉT": 4, "ét": 4,
    "ET": 4, "et": 4,
    "ÉF": 4, "éf": 4,            # hay viết nhầm p thành f
    "EF": 4, "ef": 4,

    # ===== 6: E / EE / G (Gờ) / H (Hát) =====
    "E": 6, "É": 6, "È": 6, "Ẻ": 6, "Ẽ": 6, "Ẹ": 6,
    "e": 6, "é": 6, "è": 6, "ẻ": 6, "ẽ": 6, "ẹ": 6,
    "EE": 6, "ee": 6, "ÊÊ": 6, "êê": 6,
    "Ê": 6, "ê": 6, "he": 6, "hee": 6, "que": 6,
    "G": 6, "g": 6, "GỜ": 6, "Gờ": 6, "gờ": 6,
    "rờ": 6, "RỜ": 6,
    "H": 6, "h": 6, "HÁT": 6, "Hát": 6, "hát": 6, "HẮT": 6, "hắt": 6,
}

_PASS_WORDS = {"pass", "pas", "pat", "pát", "bas", "đạt", "qua", "ok", "ô kê", "oke", "được", "đúng"}

_EXACT_CORRECTIONS: dict[str, str] = {
    # ===== Vị trí 1: A / K (Ca) =====
    "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
    "aa": "a", "àa": "a", "áa": "a",
    "k": "ca", "cá": "ca", "cà": "ca",

    # ===== Vị trí 2: Bê / Pê =====
    "bê": "bê", "bè": "bê", "bẻ": "bê", "bẽ": "bê", "bẹ": "bê",
    "bề": "bê", "bể": "bê", "bễ": "bê", "bệ": "bê", "bế": "bê",
    "be": "bê", "bờ": "bê",
    "pê": "pê", "pè": "pê", "pẻ": "pê", "pẽ": "pê", "pẹ": "pê",
    "pe": "pê",
    "bêê": "bê", "pêê": "pê",

    # ===== Vị trí 5: Xê / Cê =====
    "cê": "cê", "cè": "cê", "cẻ": "cê", "cẽ": "cê", "cẹ": "cê",
    "ce": "cê", "cờ": "cê",
    "xê": "xê", "xè": "xê", "xẻ": "xê", "xẽ": "xê", "xẹ": "xê",
    "xe": "xê",
    "sê": "xê", "se": "xê", "say": "xê",     # hay đọc/nhận nhầm C/X → S/say

    # ===== Vị trí 3: Đê =====
    "đê": "đê", "đè": "đê", "đẻ": "đê", "đẽ": "đê", "đẹ": "đê",
    "đe": "đê", "de": "đê", "dê": "đê",
    "đờ": "đê", "dờ": "đê",
    "đề": "đê", "đé": "đê", "đệ": "đê", "độ": "đê",

    # ===== Vị trí 4: Ép / Ét =====
    "ép": "ép", "èp": "ép", "ẹp": "ép", "ẻp": "ép", "ẽp": "ép",
    "ep": "ép",
    "ét": "ét", "èt": "ét", "ẹt": "ét", "ẻt": "ét", "ẽt": "ét",
    "et": "ét",
    "éf": "ép", "ef": "ép",

    # ===== Vị trí 6: E / EE / G (Gờ) / H (Hát) =====
    "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "êê": "ee", "ee": "ee",
    "g": "gờ", "rờ": "gờ",
    "h": "hát", "hắt": "hát",

    # ===== Biến âm số =====
    "bống": "bốn", "táng": "tám", "chíng": "chín", "chính": "chín",

    # ===== Pass words =====
    "bas": "đạt", "pat": "đạt", "pát": "đạt", "bát": "đạt", "đẻ": "đạt",

    # ===== Bê bị nhận nhầm thành Ba khi đi kèm số lỗi (công nhân phát âm nhanh) =====
    "chín bả": "chín bê", "chín bế": "chín bê",

    # ===== Cụm lệch âm âm học do mic vỡ hạt =====
    "qua è": "đê", "bè cờ": "bê bốn", "đè ẹp": "ép", "ẹp bát": "ẹp ba",
    "đạt sáu": "ép sáu", "mười ham": "mười lăm",
    "bát mốt": "bê một", "bát một": "bê một", "bát hai": "bê hai", "bát ba": "bê ba",
    "bát bốn": "bê bốn", "bát năm": "bê năm", "bát lăm": "bê lăm", "bát sáu": "bê sáu",
    "tư bẻ": "bê bốn", "bê bờ": "bê", "ê tư": "e bốn",

    # ===== Ánh xạ nối âm thực tế (Whisper / Vosk) =====
    "bố ma": "bốn a",
    "sexy": "xê hai",
    "mười lăm he": "mười lăm e",
    "mười lăm è": "mười lăm e",
    "hết chính": "ép chín",
    "hết chín": "ép chín",
}




_ALL_KNOWN = (
    list(_POSITION_NAMES.keys())
    + list(_VI_NUM.keys())
    + list(_PASS_WORDS)
    + ["sửa", "mươi", "chấm", "phẩy"]
)

# Chỉ dùng cho bước so khớp CỤM 2 TỪ — phải là phrase thật sự (có khoảng
# trắng, vd "mười một", "úp bơ"). Nếu dùng chung _ALL_KNOWN (có cả từ đơn
# như "upper"), difflib sẽ so "upper 2" với "upper" và thấy giống ~83%
# rồi nuốt mất số đứng sau — đây chính là bug khiến số bị mất khi đứng
# ngay sau tên vị trí.
_KNOWN_PHRASES = [k for k in _ALL_KNOWN if " " in k]


def _fuzzy_correct(text: str) -> str:
    # Bước 0: Exact match nguyên cả câu nếu có trong từ điển
    if text in _EXACT_CORRECTIONS:
        return _EXACT_CORRECTIONS[text]

    # Bước 1: exact map -- 4-gram -- trigram -- bigram -- unigram
    words  = text.split()
    result = []
    i = 0
    while i < len(words):
        if i + 3 < len(words):
            fourgram = words[i] + " " + words[i + 1] + " " + words[i + 2] + " " + words[i + 3]
            if fourgram in _EXACT_CORRECTIONS:
                result.append(_EXACT_CORRECTIONS[fourgram])
                i += 4
                continue
        if i + 2 < len(words):
            trigram = words[i] + " " + words[i + 1] + " " + words[i + 2]
            if trigram in _EXACT_CORRECTIONS:
                result.append(_EXACT_CORRECTIONS[trigram])
                i += 3
                continue
        if i + 1 < len(words):
            bigram = words[i] + " " + words[i + 1]
            if bigram in _EXACT_CORRECTIONS:
                result.append(_EXACT_CORRECTIONS[bigram])
                i += 2
                continue
        w = words[i]
        result.append(_EXACT_CORRECTIONS.get(w, w))
        i += 1
    text = " ".join(result)


    # Bước 2: difflib bigram
    words  = text.split()
    result = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            # Nếu words[i] là vị trí số 1..6 và words[i+1] là "mười" khi có từ tiếp theo (vd: "hai mười tám"):
            # Đây là Vị trí 1..6 + Lỗi 11..19, TUYỆT ĐỐI KHÔNG ghép difflib thành "hai mươi"!
            if words[i] in ("một", "hai", "ba", "bốn", "tư", "năm", "lăm", "sáu") and words[i + 1] in ("mười", "mười một", "mười hai", "mười ba", "mười bốn", "mười lăm", "mười sáu", "mười bảy", "mười tám", "mười chín") and i + 2 < len(words):
                result.append(words[i])
                i += 1
                continue

            # Nếu từ hiện tại HOẶC từ kế tiếp ĐÃ LÀ TÊN VỊ TRÍ CHUẨN (a, b, c, d, e, f, bê, xê...) thì KHÔNG ghép bigram!
            # Tránh lỗi: "hai à" bị difflib ép thành "hai ba", "a bốn" bị ép thành "hai bốn".
            if words[i] not in _POSITION_NAMES and words[i + 1] not in _POSITION_NAMES:
                bigram = words[i] + " " + words[i + 1]
                matches = get_close_matches(bigram, _KNOWN_PHRASES, n=1, cutoff=0.86)
                if matches:
                    result.append(matches[0])
                    i += 2
                    continue

        # Bước 3: difflib unigram — áp dụng cho từ > 2 ký tự
        w = words[i]
        if w in ("mươi", "chấm", "phẩy", "mốt"):
            result.append(w)
        elif len(w) > 2:
            matches = get_close_matches(w, _ALL_KNOWN, n=1, cutoff=0.80)
            result.append(matches[0] if matches else w)
        else:
            result.append(w)
        i += 1

    return " ".join(result)


def _is_pass(text: str) -> bool:
    t = text.strip()
    if t in _PASS_WORDS:
        return True
    return bool(re.fullmatch(r"(?:cho\s+)?(đạt|pass|pas|pát|qua|bát|ok|ô kê|oke|được)", t))



def _to_int(token: str) -> int | None:
    token = token.strip()
    if token in _VI_NUM:
        return _VI_NUM[token]
    try:
        return int(token)
    except (ValueError, TypeError):
        return None


_POS_ALT = "(?:" + "|".join(re.escape(k) for k in sorted(_POSITION_NAMES, key=len, reverse=True)) + r")"
_NUM_ALT = "(?:" + "|".join(re.escape(k) for k in sorted(_VI_NUM, key=len, reverse=True)) + r"|\d+)"
_PASS_SUFFIX = "(?:" + "|".join(re.escape(w) for w in sorted(_PASS_WORDS, key=len, reverse=True)) + ")"

_REINS_PASS_WORDS = ["sửa", "xữa", "sữa", "xửa"]

# "ba" bị Vosk hay nhận nhầm từ "pass" — cho phép dùng "ba" thay "đạt",
# NHƯNG chỉ trong cụm 2+ TỪ có ngữ cảnh rõ ràng ngay trong câu nói (vd
# "sửa ba" = sửa đạt). KHÔNG gộp "ba" vào _PASS_WORDS chung ở trên, vì
# "ba" đứng MỘT MÌNH còn là số 3 dùng để chọn lỗi trong flow 2 bước
# (nói vị trí xong, nói riêng "ba" để chọn lỗi số 3) — nghĩa đó phải do
# command_dispatcher quyết định dựa theo trạng thái đang chờ gì (xem
# intent "ba_or_pass" ở parse_command() và CommandDispatcher.dispatch()).
_REINS_FAIL_STANDALONE = set(_REINS_PASS_WORDS) | {
    "sửa lại", "sửa lỗi", "sửa hàng", "tái kiểm", "reins", "re-ins"
}
_PASS_WORDS_FOR_REINS = _PASS_WORDS | {"ba", "tốt", "được", "xong", "ok", "ô kê", "oke"}
_REINS_PASS_PATTERN = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in _REINS_PASS_WORDS) + r")"
    r"\s+(?:" + "|".join(re.escape(w) for w in _PASS_WORDS_FOR_REINS) + r")\s*$"
)

def _is_reins_pass(text: str) -> bool:
    t = text.strip()
    if _REINS_PASS_PATTERN.search(t):
        return True
    if re.fullmatch(r"(?:cho\s+)?(đạt|pass|pas|pát|qua|bát)\s+(?:lại|nữa)", t):
        return True
    if re.fullmatch(r"(?:sửa|xữa|sữa|xửa)\s+(?:đạt|pass|tốt|được|qua|xong|ok|ô kê|oke)", t):
        return True
    return False

# Câu 1 hơi kiểu cũ: <vị trí> <số> [sửa] [đạt] — nhưng vì Vosk có thể gộp
# cả cụm "vị trí + sửa + số" (thứ tự flow 2 bước) thành MỘT utterance
# duy nhất, không thể chỉ dựa vào 1 regex cố định thứ tự. Thay vào đó,
# quét từng token/cụm bất kể thứ tự đứng trước/sau nhau, và dùng chung
# _REINS_PASS_WORDS (đủ biến thể chính tả ASR: sửa/xữa/sữa/xửa) thay vì
# chỉ hard-code đúng chữ "sửa" như trước — đây là 2 nguyên nhân chính
# khiến câu 1 hơi bị bỏ qua (parse_command trả None, không dispatch gì).
_COMBINED_TOKEN = re.compile(
    r"(?:(?<=\s)|^)(?:"
    r"(?P<pos>" + _POS_ALT + r")"
    r"|(?P<num>" + _NUM_ALT + r")"
    r"|(?P<sua>" + "|".join(re.escape(w) for w in _REINS_PASS_WORDS) + r")"
    r"|(?P<tot>" + _PASS_SUFFIX + r")"
    r")(?:(?=\s)|$)"
)


def _parse_number_pair(text: str) -> dict | None:
    has_sua = any(w in text.split() for w in _REINS_PASS_WORDS) or any(k in text for k in ("sửa lại", "sửa lỗi", "tái kiểm"))
    has_tot = any(w in text.split() for w in _PASS_WORDS) or any(k in text for k in ("đạt lại", "sửa đạt", "sửa tốt"))

    clean = text
    words_to_remove = sorted(list(_REINS_PASS_WORDS) + ["sửa lại", "sửa lỗi", "tái kiểm", "đạt lại", "sửa đạt", "sửa tốt", "lại", "nữa"], key=len, reverse=True)
    for w in words_to_remove:
        clean = re.sub(r"\b" + re.escape(w) + r"\b", " ", clean)
    for w in _PASS_WORDS:
        clean = re.sub(r"\b" + re.escape(w) + r"\b", " ", clean)
    clean = re.sub(r"\bvị trí\b|\blỗi\b", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Nếu toàn bộ chuỗi đã là 1 số đơn lẻ hợp lệ (ví dụ "mười hai" = 12, "hai mươi ba" = 23):
    # Không tách thành cặp số, để rơi xuống xử lý bare_number!
    if re.search(r"\bchấm\b|\bphẩy\b|[.,]", clean) is None and _to_int(clean) is not None:
        return None

    pos = dfct = None

    # TRƯỜNG HỢP 1: Có từ phân cách rõ ràng (chấm, phẩy, .)
    # Ví dụ: "một chấm hai", "hai chấm ba", "hai chấm hai mươi mốt", "mười sáu chấm hai"
    sep_match = re.search(r"\bchấm\b|\bphẩy\b|[.,]", clean)
    if sep_match:
        left_str = clean[:sep_match.start()].strip()
        right_str = clean[sep_match.end():].strip()

        n1 = _to_int(left_str)
        n2 = _to_int(right_str)

        if n1 is not None and n2 is not None:
            # Quy tắc P211: Số đầu tiên LUÔN là Vị trí (1..6), Số thứ hai là Mã lỗi (1..17)
            if 1 <= n1 <= 6 and 1 <= n2 <= 17:
                pos, dfct = n1, n2

    # TRƯỜNG HỢP 2: Đọc liền không có từ nối (ví dụ: "một một", "ba mười ba", "bốn mười")
    if pos is None or dfct is None:
        words = clean.split()
        if len(words) >= 2:
            for k in range(1, len(words)):
                s1 = " ".join(words[:k])
                s2 = " ".join(words[k:])

                n1 = _to_int(s1)
                n2 = _to_int(s2)

                if n1 is not None and n2 is not None:
                    # Quy tắc P211: Số đầu tiên LUÔN là Vị trí (1..6), Số thứ hai là Mã lỗi (1..17)
                    if 1 <= n1 <= 6 and 1 <= n2 <= 17:
                        pos, dfct = n1, n2
                        break

    if pos is not None and dfct is not None:
        if len(text.split()) > 5 and not any(w in text for w in ("chấm", "phẩy", "sửa", "lỗi", "vị trí")):
            return None
        return _build_inspection(pos, dfct, has_sua, has_tot)

    return None


from .whisper_normalizer import normalize_whisper_text

_CANCEL_WORDS = {
    "hủy", "huỷ", "bỏ", "xóa", "xoá", "hủy lệnh", "huỷ lệnh",
    "quay lại", "hủy bỏ", "huỷ bỏ", "cancel", "clear"
}

def parse_command(text: str) -> dict | None:
    if not text:
        return None

    # Áp dụng chuẩn hoá chuỗi Whisper: tách chữ số dính nhau (a1 -> a 1), đổi 1-25 thành chữ
    text = normalize_whisper_text(text)

    # Lệnh QA công nghiệp tối đa 8 từ (vd: "một chấm hai mươi bốn sửa lại").
    # Các câu dài hơn chắc chắn là nói chuyện tự do hoặc ảo tưởng Whisper -> Bỏ qua ngay
    if len(text.split()) > 8:
        return None

    # 1. Kiểm tra lệnh HỦY / QUAY LẠI (ưu tiên cao nhất)
    if text in _CANCEL_WORDS:
        return {"intent": "cancel"}

    # 1b. Nhận diện cặp số: [VỊ TRÍ (1..6)] + [MÃ LỖI (1..24)] (có hoặc không có từ "chấm", "phẩy")
    # Kiểm tra NGAY trên chuỗi text chuẩn để tránh difflib làm biến dạng các từ số
    num_pair_cmd = _parse_number_pair(text)
    if num_pair_cmd is not None:
        return num_pair_cmd

    text = _fuzzy_correct(text)

    # Thử lại nhận diện cặp số sau khi difflib đã sửa các từ lệch âm
    num_pair_cmd = _parse_number_pair(text)
    if num_pair_cmd is not None:
        return num_pair_cmd

    if text in _CANCEL_WORDS:
        return {"intent": "cancel"}

    # Re-ins pass đơn lẻ ("sửa đạt", "đạt lại") — PHẢI kiểm tra TRƯỚC pass đơn lẻ
    if _is_reins_pass(text):
        return {"intent": "reins_pass"}

    # Pass đơn lẻ ("đạt" / "pass" / "cho pass")
    if _is_pass(text):
        return {"intent": "pass"}

    # "sửa" / "sửa lại" đơn lẻ (bước xác nhận trong flow 2 bước)
    if text in _REINS_FAIL_STANDALONE:
        return {"intent": "sua"}

    # "ba" ĐỨNG MỘT MÌNH: Vosk hay nhận nhầm "pass" → "ba", nhưng "ba"
    # cũng là số 3 dùng chọn lỗi trong flow 2 bước (nói vị trí xong nói
    # riêng "ba"). Ở TẦNG PARSER NÀY không biết được lúc này dispatcher
    # có đang chờ số hay không (đó là state riêng của CommandDispatcher),
    # nên KHÔNG tự quyết nghĩa ở đây — trả về 1 intent trung gian
    # "ba_or_pass" mang theo cả 2 khả năng, để command_dispatcher tự
    # chọn đúng theo trạng thái hiện tại của nó.
    if text == "ba":
        return {"intent": "ba_or_pass", "index": 3}

    # Vị trí dạng "vị trí [tên/số]" hoặc "vùng [tên/số]"
    pos_match = re.search(r"^(?:vị\s+trí|vùng)\s+(.+)$", text)
    if pos_match:
        pos_target = pos_match.group(1).strip()
        pos_val = _POSITION_NAMES.get(pos_target) or _to_int(pos_target)
        if pos_val and 1 <= pos_val <= 6:
            return {"intent": "position", "position": pos_val}

    # Vị trí đơn lẻ (bước 1 trong flow 2 bước — chỉ nói "đế"/"gót"/"a"/"bê"...)
    if text in _POSITION_NAMES:
        return {"intent": "position", "position": _POSITION_NAMES[text]}

    # Số đơn lẻ hoặc "lỗi [số]" — bước 2 trong flow 2 bước
    bare_clean = re.sub(r"^(?:mã\s+)?lỗi(?:\s+số)?\s+", "", text).strip()
    bare_clean = re.sub(r"^số\s+", "", bare_clean).strip()
    bare_idx = _to_int(bare_clean) or _to_int(text)
    if bare_idx is not None and 1 <= bare_idx <= 17:
        return {"intent": "bare_number", "index": bare_idx}

    # Câu ghép 1 hơi: <vị trí> <số> [sửa] [đạt]
    # Quét danh sách token: ưu tiên ghép cặp vị trí + số đứng ngay sau vị trí
    tokens = list(_COMBINED_TOKEN.finditer(text))
    pos = dfct = None
    has_sua = has_tot = False
    pos_idx = -1

    for idx, m in enumerate(tokens):
        if m.group("pos") and pos is None:
            pos = _POSITION_NAMES.get(m.group("pos"))
            pos_idx = idx
            break

    if pos is not None:
        # 1. Tìm số đứng sau vị trí: <vị trí> <số> (VD: "a một", "bê hai")
        for idx in range(pos_idx + 1, len(tokens)):
            if tokens[idx].group("num") and dfct is None:
                dfct = _to_int(tokens[idx].group("num"))
                break
        # 2. Nếu chưa có, tìm số đứng trước vị trí: <số> <vị trí> (VD: "một a", "hai bê")
        if dfct is None:
            for idx in range(0, pos_idx):
                if tokens[idx].group("num") and dfct is None:
                    dfct = _to_int(tokens[idx].group("num"))
                    break

    for m in tokens:
        if m.group("sua"):
            has_sua = True
        elif m.group("tot"):
            has_tot = True

    if pos is not None and dfct is not None:
        if len(text.split()) > 5 and not any(w in text for w in ("chấm", "phẩy", "sửa", "lỗi", "vị trí")):
            return None
        return _build_inspection(pos, dfct, has_sua, has_tot)

    if pos is not None and dfct is None:
        # Nếu câu quá dài (> 3 từ) mà không có số lỗi, đây là câu nói chuyện tự do hoặc
        # ảo tưởng từ Whisper chứa từ như "em", "a", "be" -> Không kích hoạt chọn vị trí
        if len(text.split()) > 3:
            return None
        if has_sua:
            return {"intent": "sua"}
        return {"intent": "position", "position": pos}

    if pos is None and dfct is None:
        for m in tokens:
            if m.group("num"):
                dfct = _to_int(m.group("num"))
                break
        if dfct is not None and has_sua:
            return {"intent": "reins_fail_number", "defect": dfct}

    return None




def _build_inspection(pos: int, dfct: int, has_sua: bool, has_tot: bool) -> dict:
    if has_sua and has_tot:
        return {"intent": "reins_pass", "position": pos, "defect": dfct}
    if has_sua:
        return {"intent": "reins_fail", "position": pos, "defect": dfct}
    if has_tot:
        return {"intent": "inspection", "position": pos, "defect": dfct, "result": "pass"}
    return {"intent": "inspection", "position": pos, "defect": dfct, "result": "fail"}
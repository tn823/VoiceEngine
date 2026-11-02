import re
from difflib import get_close_matches

# Bảng quy đổi từ số tiếng Việt sang số nguyên (1..24)
_VI_NUM = {
    "một": 1,  "mốt": 1,  "mốc": 1,  "hai": 2,  "ba": 3,   "bốn": 4,  "tư": 4,  "năm": 5,  "lăm": 5,
    "sáu": 6,  "bảy": 7,  "bẩy": 7,  "tám": 8,  "chín": 9,  "mười": 10,

    "mười một": 11, "mười hai": 12, "mười ba": 13, "mười bốn": 14, "mười tư": 14,
    "mười lăm": 15, "mười năm": 15, "mười sáu": 16, "mười bảy": 17, "mười bẩy": 17,
    "mười tám": 18, "mười chín": 19, "hai mươi": 20, "hai chục": 20,
    "hai mươi mốt": 21, "hai mươi hai": 22,
    "hai mươi ba": 23, "hai mươi bốn": 24, "hai mươi tư": 24,

    # Tiếng lóng / âm lệch
    "bống": 4, "táng": 8, "chíng": 9, "chính": 9,

    # Không dấu
    "mot": 1, "bon": 4, "nam": 5, "lam": 5,
    "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10,
    "muoi mot": 11, "muoi hai": 12, "muoi ba": 13, "muoi bon": 14, "muoi tu": 14,
    "muoi lam": 15, "muoi nam": 15, "muoi sau": 16, "muoi bay": 17, "muoi tam": 18, "muoi chin": 19,
    "hai muoi": 20, "hai muoi mot": 21, "hai mot": 21, "hai muoi hai": 22, "hai muoi ba": 23,
    "hai muoi bon": 24, "hai muoi tu": 24, "hai tu": 24,
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
    "SÊ": 5, "sê": 5,
    "SE": 5, "se": 5,
    "SAY": 5, "say": 5,

    # ===== 3: Đê =====
    "D": 3, "d": 3, "Đ": 3, "đ": 3, "ĐÊ": 3, "Đè": 3, "Đẻ": 3, "Đẽ": 3, "Đẹ": 3,
    "đê": 3, "đè": 3, "đẻ": 3, "đẽ": 3, "đẹ": 3,
    "đờ": 3, "ĐỜ": 3, "dờ": 3, "DỜ": 3,
    "DE": 3, "de": 3, "ĐE": 3, "đe": 3,
    "DÊ": 3, "dê": 3,
    "ĐÊÊ": 3,
    "đêm": 3, "đen": 3, "đây": 3, "đi": 3, "đến": 3,

    # ===== 4: Ép / Ét =====
    "F": 4, "f": 4, "ÉP": 4, "ép": 4,
    "EP": 4, "ep": 4,
    "ÉT": 4, "ét": 4,
    "ET": 4, "et": 4,
    "ÉF": 4, "éf": 4,
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
    "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
    "aa": "a", "àa": "a", "áa": "a",
    "k": "ca", "cá": "ca", "cà": "ca",
    "bê": "bê", "bè": "bê", "bẻ": "bê", "bẽ": "bê", "bẹ": "bê",
    "bề": "bê", "bể": "bê", "bễ": "bê", "bệ": "bê", "bế": "bê",
    "be": "bê", "bờ": "bê",
    "pê": "pê", "pè": "pê", "pẻ": "pê", "pẽ": "pê", "pẹ": "pê",
    "pe": "pê",
    "bêê": "bê", "pêê": "pê",
    "xê": "xê", "xè": "xê", "xẻ": "xê", "xẽ": "xê", "xẹ": "xê",
    "xe": "xê", "sê": "xê", "se": "xê", "say": "xê",
    "cê": "xê", "cè": "xê", "cẻ": "xê", "cẽ": "xê", "cẹ": "xê",
    "ce": "xê", "cờ": "xê",
    "đê": "đê", "đè": "đê", "đẻ": "đê", "đẽ": "đê", "đẹ": "đê",
    "de": "đê", "đe": "đê", "dê": "đê", "đờ": "đê", "dờ": "đê",
    "đêm": "đê", "đen": "đê", "đây": "đê", "đi": "đê", "đến": "đê",
    "đêê": "đê",
    "ép": "ép", "ep": "ép", "ét": "ép", "et": "ép", "éf": "ép", "ef": "ép",
    "f": "ép",
    "e": "e", "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "ee": "e", "êê": "e", "he": "e", "hee": "e", "que": "e",
    "g": "gờ", "gờ": "gờ", "rờ": "gờ",
    "h": "hát", "hát": "hát", "hắt": "hát",
}

_LOOKUP_WORDS = list(_POSITION_NAMES.keys()) + list(_VI_NUM.keys()) + list(_PASS_WORDS)


def _fuzzy_correct(text: str) -> str:
    tokens = text.split()
    corrected = []
    i = 0
    n = len(tokens)
    while i < n:
        # Ưu tiên khớp 3 từ
        if i + 3 <= n:
            trigram = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
            if trigram in _VI_NUM or trigram in _POSITION_NAMES:
                corrected.append(trigram)
                i += 3
                continue

        # Thử ghép 2 từ
        if i + 1 < n:
            bigram = f"{tokens[i]} {tokens[i+1]}"
            if bigram in _EXACT_CORRECTIONS:
                corrected.append(_EXACT_CORRECTIONS[bigram])
                i += 2
                continue
            if bigram in _POSITION_NAMES or bigram in _VI_NUM:
                corrected.append(bigram)
                i += 2
                continue

        t = tokens[i]
        if t in _EXACT_CORRECTIONS:
            corrected.append(_EXACT_CORRECTIONS[t])
            i += 1
            continue
        if t in _POSITION_NAMES or t in _VI_NUM or t in _PASS_WORDS:
            corrected.append(t)
            i += 1
            continue

        matches = get_close_matches(t, _LOOKUP_WORDS, n=1, cutoff=0.80)
        corrected.append(matches[0] if matches else t)
        i += 1

    return " ".join(corrected)


def _is_pass(text: str) -> bool:
    t = text.strip().lower()
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


_REINS_PASS_WORDS = ["sửa", "xữa", "sữa", "xửa"]
_REINS_FAIL_STANDALONE = set(_REINS_PASS_WORDS) | {
    "sửa lại", "sửa lỗi", "sửa hàng", "tái kiểm", "reins", "re-ins"
}
_PASS_WORDS_FOR_REINS = _PASS_WORDS | {"ba", "tốt", "được", "xong", "ok", "ô kê", "oke"}
_REINS_PASS_PATTERN = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in _REINS_PASS_WORDS) + r")"
    r"\s+(?:" + "|".join(re.escape(w) for w in _PASS_WORDS_FOR_REINS) + r")\s*$"
)


def _is_reins_pass(text: str) -> bool:
    t = text.strip().lower()
    if t in ("sửa đạt", "sửa tốt", "sửa ok", "sửa được", "sửa xong", "sửa ba", "đạt lại", "tốt lại", "reins pass"):
        return True
    return bool(_REINS_PASS_PATTERN.match(t))


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

    if re.search(r"\bchấm\b|\bphẩy\b|[.,]", clean) is None and _to_int(clean) is not None:
        return None

    pos = dfct = None

    # TRƯỜNG HỢP 1: Có từ phân cách rõ ràng (chấm, phẩy, .)
    sep_match = re.search(r"\bchấm\b|\bphẩy\b|[.,]", clean)
    if sep_match:
        left_str = clean[:sep_match.start()].strip()
        right_str = clean[sep_match.end():].strip()

        n1 = _to_int(left_str)
        n2 = _to_int(right_str)

        if n1 is not None and n2 is not None:
            if 1 <= n1 <= 6 and 1 <= n2 <= 24:
                pos, dfct = n1, n2

    # TRƯỜNG HỢP 2: Đọc liền không có từ nối (ví dụ: "một một", "hai mười tám", "ba chín")
    if pos is None or dfct is None:
        words = clean.split()
        if len(words) >= 2:
            for k in range(1, len(words)):
                s1 = " ".join(words[:k])
                s2 = " ".join(words[k:])

                n1 = _to_int(s1)
                n2 = _to_int(s2)

                if n1 is not None and n2 is not None:
                    if 1 <= n1 <= 6 and 1 <= n2 <= 24:
                        pos, dfct = n1, n2
                        break

    if pos is not None and dfct is not None:
        if len(text.split()) > 6 and not any(w in text for w in ("chấm", "phẩy", "sửa", "lỗi", "vị trí")):
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

    text = normalize_whisper_text(text)

    if len(text.split()) > 8:
        return None

    # 1. Lệnh HỦY / QUAY LẠI
    if text in _CANCEL_WORDS:
        return {"intent": "cancel"}

    # 2. Cặp số: [VỊ TRÍ (1..6)] + [MÃ LỖI (1..24)]
    num_pair_cmd = _parse_number_pair(text)
    if num_pair_cmd is not None:
        return num_pair_cmd

    text = _fuzzy_correct(text)

    num_pair_cmd = _parse_number_pair(text)
    if num_pair_cmd is not None:
        return num_pair_cmd

    if text in _CANCEL_WORDS:
        return {"intent": "cancel"}

    # Re-ins pass ("sửa đạt", "đạt lại")
    if _is_reins_pass(text):
        return {"intent": "reins_pass"}

    # Pass đơn lẻ ("đạt" / "pass")
    if _is_pass(text):
        return {"intent": "pass"}

    # "sửa" / "sửa lại" đơn lẻ
    if text in _REINS_FAIL_STANDALONE:
        return {"intent": "sua"}

    if text == "ba":
        return {"intent": "ba_or_pass", "index": 3}

    # Vị trí dạng "vị trí [tên/số]" hoặc "vùng [tên/số]"
    pos_match = re.search(r"^(?:vị\s+trí|vùng)\s+(.+)$", text)
    if pos_match:
        pos_target = pos_match.group(1).strip()
        pos_val = _POSITION_NAMES.get(pos_target) or _to_int(pos_target)
        if pos_val and 1 <= pos_val <= 6:
            return {"intent": "position", "position": pos_val}

    # Vị trí đơn lẻ ("mũi", "đế", "gót", "a", "bê"...)
    if text in _POSITION_NAMES:
        return {"intent": "position", "position": _POSITION_NAMES[text]}

    # Số đơn lẻ hoặc "lỗi [số]" (1..24)
    bare_clean = re.sub(r"^(?:mã\s+)?lỗi(?:\s+số)?\s+", "", text).strip()
    bare_clean = re.sub(r"^số\s+", "", bare_clean).strip()
    bare_idx = _to_int(bare_clean) or _to_int(text)
    if bare_idx is not None and 1 <= bare_idx <= 24:
        return {"intent": "bare_number", "index": bare_idx}

    # Ghép 1 hơi: <vị trí> + <mã lỗi> [sửa] [đạt]
    # Sắp xếp các token vị trí và số dài trước
    _POS_LIST = sorted(_POSITION_NAMES.keys(), key=len, reverse=True)
    _NUM_LIST = sorted(_VI_NUM.keys(), key=len, reverse=True)

    pos = None
    dfct = None
    has_sua = any(w in text.split() for w in _REINS_PASS_WORDS) or any(k in text for k in ("sửa lại", "sửa lỗi", "tái kiểm"))
    has_tot = any(w in text.split() for w in _PASS_WORDS) or any(k in text for k in ("đạt lại", "sửa đạt", "sửa tốt"))

    # Tìm vị trí trước
    text_clean_pos = text
    for p_name in _POS_LIST:
        p_pattern = r"\b" + re.escape(p_name) + r"\b"
        if re.search(p_pattern, text_clean_pos):
            pos = _POSITION_NAMES[p_name]
            text_clean_pos = re.sub(p_pattern, " ", text_clean_pos, count=1)
            break

    # Sau đó tìm mã lỗi trong phần còn lại
    if pos is not None:
        text_clean_pos = re.sub(r"\bvị trí\b|\blỗi\b|\bsố\b|\bchấm\b|\bphẩy\b|\bsửa\b|\bđạt\b|\blại\b", " ", text_clean_pos)
        text_clean_pos = re.sub(r"\s+", " ", text_clean_pos).strip()

        # Kiểm tra cụm số đầy đủ
        for num_word in _NUM_LIST:
            num_pattern = r"\b" + re.escape(num_word) + r"\b"
            if re.search(num_pattern, text_clean_pos):
                dfct = _VI_NUM[num_word]
                break

        if dfct is None:
            # Thử parse int trực tiếp
            for token in text_clean_pos.split():
                val = _to_int(token)
                if val is not None and 1 <= val <= 24:
                    dfct = val
                    break

    if pos is not None and dfct is not None:
        return _build_inspection(pos, dfct, has_sua, has_tot)

    if pos is not None and dfct is None:
        if len(text.split()) > 3:
            return None
        if has_sua:
            return {"intent": "sua"}
        return {"intent": "position", "position": pos}

    if pos is None and dfct is not None:
        if has_sua:
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

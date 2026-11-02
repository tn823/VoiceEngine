# -*- coding: utf-8 -*-
"""
Command Parser cho VoiceEngine (Phiên bản chuyên biệt: Số-Số, Đạt, Đạt lại, Lỗi, Lỗi lại)
Chỉ nhận diện đúng 5 nhóm lệnh nghiệp vụ QA:
1. Số - Số ([Vị trí 1..6] + [Mã lỗi 1..24]) -> {"intent": "inspection", "position": P, "defect": D, "result": "fail"}
2. Đạt (Pass)                               -> {"intent": "pass"}
3. Đạt lại / Sửa đạt (Re-Pass)              -> {"intent": "reins_pass"}
4. Lỗi (Fail đơn lẻ hoặc kèm Số - Số)       -> {"intent": "fail"} hoặc {"intent": "inspection", ...}
5. Lỗi lại / Sửa lại (Re-Fail)              -> {"intent": "reins_fail", "position": P, "defect": D} hoặc {"intent": "sua"}
(Kèm lệnh phụ Hủy / Quay lại -> {"intent": "cancel"})
"""

import re
from .whisper_normalizer import normalize_whisper_text

# Bảng quy đổi từ số tiếng Việt sang số nguyên (1..24)
_VI_NUM = {
    "một": 1,  "mốt": 1,  "mốc": 1,  "hai": 2,  "ba": 3,   "bốn": 4,  "tư": 4,  "năm": 5,  "lăm": 5,
    "sáu": 6,  "bảy": 7,  "bẩy": 7,  "tám": 8,  "chín": 9,  "mười": 10,

    "mười một": 11, "mười hai": 12, "mười ba": 13, "mười bốn": 14, "mười tư": 14,
    "mười lăm": 15, "mười năm": 15, "mười lam": 15, "mười sáu": 16, "mười bảy": 17, "mười bẩy": 17,
    "mười tám": 18, "mười chín": 19, "hai mươi": 20, "hai mười": 20, "hai chục": 20,
    "hai mươi mốt": 21, "hai mươi một": 21, "hai mười một": 21, "hai mười mốt": 21, "hai mốt": 21,
    "hai mươi hai": 22, "hai mười hai": 22, "hai hai": 22,
    "hai mươi ba": 23, "hai mười ba": 23, "hai ba": 23,
    "hai mươi bốn": 24, "hai mươi tư": 24, "hai mười bốn": 24, "hai mười tư": 24, "hai tư": 24, "hai bốn": 24,

    # Biến âm số
    "bống": 4, "táng": 8, "chíng": 9, "chính": 9,

    # Không dấu
    "mot": 1, "bon": 4, "nam": 5, "lam": 5,
    "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10,
    "muoi mot": 11, "muoi hai": 12, "muoi ba": 13, "muoi bon": 14, "muoi tu": 14,
    "muoi lam": 15, "muoi nam": 15, "muoi sau": 16, "muoi bay": 17, "muoi tam": 18, "muoi chin": 19,
    "hai muoi": 20, "hai muoi mot": 21, "hai mot": 21, "hai muoi hai": 22, "hai muoi ba": 23,
    "hai muoi bon": 24, "hai muoi tu": 24, "hai tu": 24,
}

_PASS_WORDS = {
    "pass", "pas", "pat", "pát", "bas", "bát", "bác",
    "đạt", "đạc", "đặt", "qua", "ok", "ô kê", "oke", "được", "đúng",
    "cho pass", "cho đạt"
}

_REINS_PASS_EXACT = {
    "đạt lại", "đại lại", "sửa đạt", "sửa tốt", "sửa ok", "sửa ô kê",
    "sửa oke", "sửa được", "sửa xong", "tốt lại", "ok lại", "ô kê lại", "reins pass"
}

_FAIL_STANDALONE = {
    "lỗi", "lổi", "nỗi", "báo lỗi", "hàng lỗi", "fail"
}

_REINS_FAIL_STANDALONE = {
    "lỗi lại", "lổi lại", "nỗi lại", "báo lỗi lại",
    "sửa", "sữa", "xửa", "xữa",
    "sửa lại", "sửa lỗi", "sửa hàng", "tái kiểm", "reins", "re-ins"
}

_CANCEL_WORDS = {
    "hủy", "huỷ", "bỏ", "xóa", "xoá", "hủy lệnh", "huỷ lệnh",
    "quay lại", "hủy bỏ", "huỷ bỏ", "cancel", "clear"
}


def _to_int(token: str) -> int | None:
    token = token.strip()
    if token in _VI_NUM:
        return _VI_NUM[token]
    try:
        return int(token)
    except (ValueError, TypeError):
        return None


def _is_pass(text: str) -> bool:
    t = text.strip().lower()
    if t in _PASS_WORDS:
        return True
    return bool(re.fullmatch(r"(?:cho\s+)?(đạt|đạc|pass|pas|pát|qua|bát|ok|ô kê|oke|được)", t))


def _is_reins_pass(text: str) -> bool:
    t = text.strip().lower()
    return t in _REINS_PASS_EXACT


def _parse_number_pair(text: str) -> dict | None:
    """
    Phân tích cặp Số - Số: [Vị trí (1..6)] + [Mã lỗi (1..24)]
    Hỗ trợ đi kèm từ khóa 'lỗi', 'lỗi lại', 'sửa', 'sửa lại', 'đạt lại', 'sửa đạt'.
    """
    has_reins_pass = any(k in text for k in ("đạt lại", "đại lại", "sửa đạt", "sửa tốt", "sửa ok", "sửa ô kê", "sửa xong", "tốt lại"))
    has_sua = (not has_reins_pass) and (
        any(k in text for k in ("lỗi lại", "sửa lại", "sửa lỗi", "tái kiểm"))
        or any(w in text.split() for w in ("sửa", "sữa", "xửa", "xữa"))
    )
    has_tot = (not has_reins_pass) and any(w in text.split() for w in ("đạt", "pass", "ok", "tốt"))

    clean = text
    # Loại bỏ các cụm từ khóa nghiệp vụ để lấy phần số thuần túy
    phrases_to_strip = [
        "lỗi lại", "lổi lại", "nỗi lại", "sửa lại", "sửa lỗi", "tái kiểm",
        "đạt lại", "đại lại", "sửa đạt", "sửa tốt", "sửa ô kê", "sửa ok",
        "vị trí", "mã lỗi", "báo lỗi", "hàng lỗi", "ô kê",
        "sửa", "sữa", "xửa", "xữa", "lỗi", "số", "lại", "nữa",
        "đạt", "pass", "ok", "tốt"
    ]
    for p in phrases_to_strip:
        clean = re.sub(r"\b" + re.escape(p) + r"\b", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean:
        return None

    pos = dfct = None

    # TRƯỜNG HỢP 1: Có từ phân cách rõ ràng ("chấm", "phẩy")
    sep_match = re.search(r"\b(?:chấm|phẩy)\b", clean)
    if sep_match:
        left_str = clean[:sep_match.start()].strip()
        right_str = clean[sep_match.end():].strip()

        n1 = _to_int(left_str)
        n2 = _to_int(right_str)

        if n1 is not None and n2 is not None and 1 <= n1 <= 6 and 1 <= n2 <= 24:
            pos, dfct = n1, n2
        else:
            return None

    # TRƯỜNG HỢP 2: Đọc liền Số - Số (VD: "một một", "hai mười tám", "ba mười bảy", "năm hai mươi mốt")
    # Vì Vị trí 1..6 trong tiếng Việt ("một", "hai", "ba", "bốn", "năm", "sáu") LUÔN là 1 từ đơn:
    # Từ đầu tiên (words[0]) bắt buộc là Vị trí (1..6), phần còn lại (words[1:]) bắt buộc là Mã lỗi (1..24).
    if pos is None or dfct is None:
        words = clean.split()
        if len(words) >= 2:
            s1 = words[0]
            s2 = " ".join(words[1:])

            n1 = _to_int(s1)
            n2 = _to_int(s2)

            if n1 is not None and n2 is not None and 1 <= n1 <= 6 and 1 <= n2 <= 24:
                pos, dfct = n1, n2

    if pos is not None and dfct is not None:
        if has_reins_pass or (has_sua and has_tot):
            return {"intent": "reins_pass", "position": pos, "defect": dfct}
        if has_sua:
            return {"intent": "reins_fail", "position": pos, "defect": dfct}
        if has_tot:
            return {"intent": "inspection", "position": pos, "defect": dfct, "result": "pass"}
        return {"intent": "inspection", "position": pos, "defect": dfct, "result": "fail"}

    return None


def parse_command(text: str) -> dict | None:
    if not text:
        return None

    text = normalize_whisper_text(text)
    if not text:
        return None

    if len(text.split()) > 8:
        return None

    # 1. Lệnh HỦY / QUAY LẠI
    if text in _CANCEL_WORDS:
        return {"intent": "cancel"}

    # 2. Lệnh ĐẠT LẠI / SỬA ĐẠT đơn lẻ
    if _is_reins_pass(text):
        return {"intent": "reins_pass"}

    # 3. Lệnh ĐẠT (PASS) đơn lẻ
    if _is_pass(text):
        return {"intent": "pass"}

    # 4. Lệnh LỖI đơn lẻ ("lỗi", "báo lỗi")
    if text in _FAIL_STANDALONE:
        return {"intent": "fail"}

    # 5. Lệnh LỖI LẠI / SỬA LẠI đơn lẻ ("lỗi lại", "sửa lại", "sửa")
    if text in _REINS_FAIL_STANDALONE:
        return {"intent": "sua"}

    # 6. Cặp SỐ - SỐ: [Vị trí (1..6)] + [Mã lỗi (1..24)] (kèm hoặc không kèm "lỗi" / "lỗi lại" / "sửa")
    num_pair_cmd = _parse_number_pair(text)
    if num_pair_cmd is not None:
        return num_pair_cmd

    return None

# -*- coding: utf-8 -*-
import json
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.whisper_normalizer import normalize_whisper_text
from core.command_parser import parse_command

lines = open('logs/shadow_audit.jsonl', encoding='utf-8').readlines()
today = [json.loads(l) for l in lines if '2026-11-03' in l]

print(f"Tổng số lượt ghi âm hôm nay: {len(today)}")
runtime_val = [x for x in today if x.get('status') == 'VALID_COMMAND']
runtime_unm = [x for x in today if x.get('status') != 'VALID_COMMAND']
print(f"Runtime lúc chạy: Khớp {len(runtime_val)}, Không khớp {len(runtime_unm)}")

# Replay đối chiếu với parser hiện tại (sau khi có bóc tách đuôi và từ dẫn)
replayed_valid = []
replayed_unmatched = []

for e in today:
    raw = e.get('raw_whisper', '')
    norm = normalize_whisper_text(raw)
    cmd = parse_command(norm)
    if cmd:
        replayed_valid.append((e, cmd, norm))
    else:
        replayed_unmatched.append((e, norm))

print(f"\nSau bản vá mới nhất (Replay): Khớp {len(replayed_valid)} (+{len(replayed_valid) - len(runtime_val)} ca cứu được)")

# Phân loại intent của các câu hợp lệ
intent_counts = Counter(cmd['intent'] for _, cmd, _ in replayed_valid)
print("\n--- PHÂN BỐ CÁC LỆNH HỢP LỆ ---")
for k, v in intent_counts.items():
    print(f"  • {k}: {v} lượt")

# Danh sách các câu được cứu sau bản vá
newly_saved = [(e, c) for e, c, _ in replayed_valid if e.get('status') != 'VALID_COMMAND']
print(f"\n--- CÁC CÂU RUNTIME BỊ MISS NHƯNG HIỆN TẠI ĐÃ ĐƯỢC CỨU ({len(newly_saved)} câu) ---")
for e, c in newly_saved:
    print(f"  • Raw: \"{e['raw_whisper']}\" -> Cmd: {c}")

# Phân tích 400+ câu Unmatched còn lại:
# Tìm xem trong 400+ câu unmatched có câu nào chứa số hoặc từ khóa QA không (tiềm năng là lệnh bị nói méo)
potential_commands = []
casual_chat = []

for e, norm in replayed_unmatched:
    raw = e.get('raw_whisper', '')
    # Check if raw or norm contains digits or QA words
    has_num_or_qa = any(k in norm for k in [
        'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín', 'mười',
        'đạt', 'pass', 'ok', 'sửa', 'lỗi', 'qua', 'bát', 'bác', 'bột'
    ])
    if has_num_or_qa:
        potential_commands.append((e, norm))
    else:
        casual_chat.append((e, norm))

print(f"\n--- PHÂN TÍCH {len(replayed_unmatched)} CÂU CHƯA KHỚP LỆNH ---")
print(f"  • Trò chuyện ngoài lề / Tạp âm môi trường thuần túy: {len(casual_chat)} câu (Lọc bỏ thành công, không nhận bậy)")
print(f"  • Có chứa từ khóa số hoặc nghiệp vụ (Tiềm năng cần tối ưu): {len(potential_commands)} câu")

print(f"\n--- CHI TIẾT CÁC CÂU CHỨA TỪ KHÓA SỐ/NGHIỆP VỤ BỊ UNMATCHED ({len(potential_commands)} câu) ---")
for e, norm in potential_commands:
    print(f"  [Dòng {e.get('time_str')}] raw: \"{e.get('raw_whisper')}\" | norm: \"{norm}\" | conf: {e.get('conf')}")


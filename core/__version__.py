# -*- coding: utf-8 -*-
"""
VoiceEngine Version Specification
Tuân thủ chuẩn Semantic Versioning (SemVer 2.0.0): MAJOR.MINOR.PATCH
- MAJOR: Thay đổi phá vỡ tương thích (đổi IPC format, kiến trúc giao tiếp).
- MINOR: Bổ sung tính năng, lệnh mới, chế độ mới (tương thích ngược).
- PATCH: Vá lỗi, cải thiện từ điển chuẩn hóa, tinh chỉnh âm thanh DSP.
"""

VERSION_INFO = (1, 2, 0)
__version__ = ".".join(map(str, VERSION_INFO))
__author__ = "VoiceEngine QA Team"

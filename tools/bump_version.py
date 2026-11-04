# -*- coding: utf-8 -*-
"""
VoiceEngine Automated Version Management Tool (SemVer 2.0)
Tự động hóa toàn bộ quy trình nâng cấp phiên bản cho VoiceEngine:
1. Kiểm tra bộ test suite (đảm bảo không release code lỗi).
2. Tính toán phiên bản mới theo Semantic Versioning (patch, minor, major, hoặc set cụ thể).
3. Cập nhật core/__version__.py.
4. Tự động ghi nhật ký vào CHANGELOG.md.
5. Tự động tái biên dịch tài liệu PDF hướng dẫn (đồng bộ phiên bản trên PDF).
6. Tự động tạo Git Commit và Git Tag chuẩn hóa.
"""

import os
import sys
import re
import datetime
import subprocess
import argparse

# Cấu hình UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VERSION_FILE = os.path.join(PROJECT_ROOT, "core", "__version__.py")
CHANGELOG_FILE = os.path.join(PROJECT_ROOT, "CHANGELOG.md")
PDF_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "generate_pdf_guide.py")
TEST_SCRIPT = os.path.join(PROJECT_ROOT, "tests", "test_all_cases.py")


def get_current_version():
    if not os.path.exists(VERSION_FILE):
        return (1, 0, 0)
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"VERSION_INFO\s*=\s*\((\d+),\s*(\d+),\s*(\d+)\)", content)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    match_str = re.search(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if match_str:
        return (int(match_str.group(1)), int(match_str.group(2)), int(match_str.group(3)))
    return (1, 0, 0)


def format_version(ver_tuple):
    return f"{ver_tuple[0]}.{ver_tuple[1]}.{ver_tuple[2]}"


def bump_tuple(current_ver, bump_type):
    major, minor, patch = current_ver
    if bump_type == "patch":
        return (major, minor, patch + 1)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "major":
        return (major + 1, 0, 0)
    else:
        # Nếu nhập dạng chuỗi x.y.z
        parts = bump_type.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        raise ValueError(f"Loại bump không hợp lệ: '{bump_type}'. Hãy chọn: patch, minor, major, hoặc cú pháp 'x.y.z'")


def update_version_file(new_ver, dry_run=False):
    ver_str = format_version(new_ver)
    content = f'''# -*- coding: utf-8 -*-
"""
VoiceEngine Version Specification
Tuân thủ chuẩn Semantic Versioning (SemVer 2.0.0): MAJOR.MINOR.PATCH
- MAJOR: Thay đổi phá vỡ tương thích (đổi IPC format, kiến trúc giao tiếp).
- MINOR: Bổ sung tính năng, lệnh mới, chế độ mới (tương thích ngược).
- PATCH: Vá lỗi, cải thiện từ điển chuẩn hóa, tinh chỉnh âm thanh DSP.
"""

VERSION_INFO = ({new_ver[0]}, {new_ver[1]}, {new_ver[2]})
__version__ = ".".join(map(str, VERSION_INFO))
__author__ = "VoiceEngine QA Team"
'''
    if dry_run:
        print(f"[DRY-RUN] Cập nhật {VERSION_FILE} -> v{ver_str}")
        return
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✔ Đã cập nhật {VERSION_FILE} -> v{ver_str}")


def update_changelog(new_ver, message=None, dry_run=False):
    ver_str = format_version(new_ver)
    today = datetime.date.today().isoformat()
    header = f"## [{ver_str}] - {today}\n"
    
    note_line = f"- {message.strip()}\n" if message else "- Cập nhật và bảo trì định kỳ VoiceEngine.\n"
    entry = f"{header}\n### Changed\n{note_line}\n"

    if not os.path.exists(CHANGELOG_FILE):
        full_content = f"# Nhật Ký Thay Đổi (Changelog)\n\n{entry}"
    else:
        with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
            old_content = f.read()
        
        # Chèn ngay dưới tiêu đề chính hoặc trước version đầu tiên
        match = re.search(r"(##\s*\[\d+\.\d+\.\d+\])", old_content)
        if match:
            idx = match.start()
            full_content = old_content[:idx] + entry + "\n" + old_content[idx:]
        else:
            full_content = old_content + "\n" + entry

    if dry_run:
        print(f"[DRY-RUN] Cập nhật {CHANGELOG_FILE} với mục [{ver_str}]")
        return

    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        f.write(full_content)
    print(f"✔ Đã thêm mục v{ver_str} vào {CHANGELOG_FILE}")


def run_tests():
    if not os.path.exists(TEST_SCRIPT):
        return True
    print("\n⏳ [1/4] Đang kiểm tra bộ test suite (tests/test_all_cases.py)...")
    res = subprocess.run([sys.executable, TEST_SCRIPT], cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print("\n❌ KIỂM THỬ THẤT BẠI! Hãy sửa lỗi trước khi phát hành phiên bản mới.")
        return False
    print("✔ Toàn bộ test suite ĐẠT 100%!")
    return True


def rebuild_pdf(dry_run=False):
    if not os.path.exists(PDF_SCRIPT):
        return
    print("\n⏳ [3/4] Đang tái tạo tài liệu PDF hướng dẫn theo phiên bản mới...")
    if dry_run:
        print(f"[DRY-RUN] Chạy {PDF_SCRIPT}")
        return
    res = subprocess.run([sys.executable, PDF_SCRIPT], cwd=PROJECT_ROOT)
    if res.returncode == 0:
        print("✔ Đồng bộ tài liệu PDF thành công!")
    else:
        print("⚠️ Có cảnh báo khi tạo PDF, vui lòng kiểm tra lại ReportLab.")


def git_release(new_ver, message=None, dry_run=False):
    ver_str = format_version(new_ver)
    tag_name = f"v{ver_str}"
    commit_msg = f"chore(release): {tag_name}"
    if message:
        commit_msg += f" - {message}"

    print(f"\n⏳ [4/4] Đang thực hiện Git Commit & Tag ({tag_name})...")
    if dry_run:
        print(f"[DRY-RUN] git add -A")
        print(f"[DRY-RUN] git commit -m \"{commit_msg}\"")
        print(f"[DRY-RUN] git tag -a {tag_name} -m \"Release {tag_name}\"")
        return

    # Git add
    subprocess.run(["git", "add", "-A"], cwd=PROJECT_ROOT, check=True)
    
    # Check if there's anything to commit
    status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if status.stdout.strip():
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, check=True)
        print(f"✔ Đã tạo Git Commit: '{commit_msg}'")
    else:
        print("ℹ Không có thay đổi file cần commit.")

    # Git tag
    # Xóa tag nếu đã tồn tại cục bộ
    subprocess.run(["git", "tag", "-d", tag_name], cwd=PROJECT_ROOT, capture_output=True)
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}: {message or 'New release'}"], cwd=PROJECT_ROOT, check=True)
    print(f"✔ Đã gắn Git Tag: {tag_name}")


def main():
    parser = argparse.ArgumentParser(
        description="VoiceEngine Automated SemVer & Release Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python tools/bump_version.py --current               # Xem phiên bản hiện tại
  python tools/bump_version.py patch -m "Sửa lỗi DSP"  # Nâng patch: 1.2.0 -> 1.2.1
  python tools/bump_version.py minor -m "Thêm lệnh mới"# Nâng minor: 1.2.0 -> 1.3.0
  python tools/bump_version.py major -m "Đổi giao thức"# Nâng major: 1.2.0 -> 2.0.0
  python tools/bump_version.py 1.2.5 -m "Bản hotfix"   # Chỉ định số cụ thể
        """
    )
    parser.add_argument(
        "action",
        nargs="?",
        default=None,
        help="Loại nâng version: 'patch', 'minor', 'major', hoặc chuỗi số 'x.y.z'"
    )
    parser.add_argument("-m", "--message", type=str, default=None, help="Ghi chú mô tả thay đổi cho release")
    parser.add_argument("--current", action="store_true", help="Chỉ xem phiên bản hiện tại rồi thoát")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm không ghi file và không tạo git tag")
    parser.add_argument("--no-test", action="store_true", help="Bỏ qua bước chạy kiểm thử tự động")
    parser.add_argument("--no-git", action="store_true", help="Không tự động thực hiện git commit và git tag")

    args = parser.parse_args()

    curr_ver = get_current_version()
    curr_str = format_version(curr_ver)

    if args.current or not args.action:
        print(f"📌 Phiên bản hiện tại của VoiceEngine: v{curr_str}")
        if not args.action:
            print("💡 Hãy truyền loại bump (patch / minor / major) để nâng version. Dùng --help để xem chi tiết.")
        return

    try:
        new_ver = bump_tuple(curr_ver, args.action)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    new_str = format_version(new_ver)
    print("=" * 60)
    print(f"🚀 NÂNG CẤP PHIÊN BẢN VOICEENGINE: v{curr_str} ➔ v{new_str}")
    print("=" * 60)

    # 1. Chạy test
    if not args.no_test:
        if not run_tests():
            sys.exit(1)

    # 2. Cập nhật version file & changelog
    print(f"\n⏳ [2/4] Đang cập nhật tệp tin mã nguồn và nhật ký thay đổi...")
    update_version_file(new_ver, dry_run=args.dry_run)
    update_changelog(new_ver, message=args.message, dry_run=args.dry_run)

    # 3. Tái tạo tài liệu PDF
    rebuild_pdf(dry_run=args.dry_run)

    # 4. Git release
    if not args.no_git:
        git_release(new_ver, message=args.message, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print(f"🎉 PHÁT HÀNH THÀNH CÔNG: VoiceEngine v{new_str}")
    print("=" * 60)
    if not args.no_git and not args.dry_run:
        print("💡 Để đẩy phiên bản và thẻ tag mới lên kho lưu trữ từ xa (GitHub/GitLab), hãy chạy:")
        print(f"   git push origin main --tags\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Tạo file PDF Bảng Khẩu Lệnh VoiceEngine QA siêu tinh gọn, trực quan (1 trang A4).
Cấu trúc 3 cột:
- Cột 1: Nghiệp Vụ
- Cột 2: Cấu Trúc Khẩu Lệnh (ngắn gọn, không giải thích)
- Cột 3: Khẩu Lệnh Đọc Vào Mic (các câu đọc mẫu thực tế)
"""
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. Đăng ký Font Unicode tiếng Việt Arial từ Windows
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_ITALIC = "C:/Windows/Fonts/ariali.ttf"

pdfmetrics.registerFont(TTFont("Arial", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_BOLD))
pdfmetrics.registerFont(TTFont("Arial-Italic", FONT_ITALIC))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from core.__version__ import __version__
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

OUTPUT_PDF = os.path.join(DOCS_DIR, "VoiceEngine_QA_Voice_Command_Guide.pdf")
OUTPUT_PDF_ROOT = os.path.join(PROJECT_ROOT, "VoiceEngine_QA_Voice_Command_Guide.pdf")


def build_pdf():
    # Khổ A4 đứng, lề 1.5cm rộng rãi
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "DocTitle",
        fontName="Arial-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#0F172A"),
        alignment=1, # Center
        spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        "DocSubTitle",
        fontName="Arial",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceAfter=14,
    )
    style_table_header = ParagraphStyle(
        "TableHeader",
        fontName="Arial-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.white,
        alignment=1, # Center
    )
    style_col1 = ParagraphStyle(
        "Col1",
        fontName="Arial-Bold",
        fontSize=11.5,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        alignment=1, # Center
    )
    style_col2 = ParagraphStyle(
        "Col2",
        fontName="Arial-Bold",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
    )
    style_col3 = ParagraphStyle(
        "Col3",
        fontName="Arial",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
    )
    style_note = ParagraphStyle(
        "DocNote",
        fontName="Arial-Italic",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    story = []

    # 1. TIÊU ĐỀ
    story.append(Paragraph("VOICE ENGINE QA — BẢNG KHẨU LỆNH KIỂM THỬ", style_title))
    story.append(Paragraph(f"Tài liệu tra cứu nhanh khẩu lệnh giọng nói dành cho quản lý & kiểm thử viên • Phiên bản v{__version__}", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceBefore=0, spaceAfter=14))

    # 2. BẢNG 3 CỘT: [Nghiệp Vụ] - [Cấu Trúc Khẩu Lệnh] - [Khẩu Lệnh Đọc Vào Mic]
    headers = [
        Paragraph("Nghiệp Vụ", style_table_header),
        Paragraph("Cấu Trúc Khẩu Lệnh", style_table_header),
        Paragraph("Khẩu Lệnh Đọc Vào Mic (Ví Dụ Thực Tế)", style_table_header),
    ]

    table_data = [headers]

    # Hàng 1: Part
    table_data.append([
        Paragraph("<b>Part</b><br/><font color='#64748B' size='9'>(Vị trí)</font>", style_col1),
        Paragraph("<b>1, 2, 3, 4, 5, 6</b>", style_col2),
        Paragraph("<b>Một</b>, <b>Hai</b>, <b>Ba</b>, <b>Bốn</b>, <b>Năm</b>, <b>Sáu</b>", style_col3),
    ])

    # Hàng 2: Reason
    table_data.append([
        Paragraph("<b>Reason</b><br/><font color='#64748B' size='9'>(Mã lỗi)</font>", style_col1),
        Paragraph("<b>1, 2, 3 ... 17</b>", style_col2),
        Paragraph("<b>Một</b>, <b>Hai</b>, <b>Ba</b> ... <b>Mười bảy</b>", style_col3),
    ])

    # Hàng 3: Pass
    table_data.append([
        Paragraph("<font color='#059669'><b>Pass</b></font><br/><font color='#64748B' size='9'>(Đạt)</font>", style_col1),
        Paragraph("<b>Đạt, Pass, OK, Ô kê</b>", style_col2),
        Paragraph("• <b>'Đạt'</b>, <b>'Pass'</b>, <b>'Qua'</b><br/>• <b>'OK'</b>, <b>'Ô kê'</b>, <b>'Cho pass'</b>", style_col3),
    ])

    # Hàng 4: Re-Pass
    table_data.append([
        Paragraph("<font color='#0284C7'><b>Re-Pass</b></font><br/><font color='#64748B' size='9'>(Tái kiểm đạt)</font>", style_col1),
        Paragraph("<b>Đạt lại, OK lại</b><br/><b>re pass / re-ins pass</b> <i>('rì bát')</i><br/><i>(hoặc Sửa đạt, Sửa rồi)</i>", style_col2),
        Paragraph(
            "• <b>'Đạt lại'</b>, <b>'OK lại'</b>, <b>'re pass'</b>, <b>'re-ins pass'</b>, <b>'rì bát'</b><br/>"
            "• <b>'Pass lại'</b>, <b>'Sửa đạt'</b>, <b>'Sửa OK'</b>, <b>'Sửa rồi'</b><br/>"
            "• <b>'Đạt sửa'</b>, <b>'OK sửa'</b>",
            style_col3
        ),
    ])

    # Hàng 5: Fail
    table_data.append([
        Paragraph("<font color='#DC2626'><b>Fail</b></font><br/><font color='#64748B' size='9'>(Chấm lỗi)</font>", style_col1),
        Paragraph("<b>Số - Số</b><br/><i>(part reason)</i>", style_col2),
        Paragraph(
            "• <b>'Một một'</b>, <b>'Một hai'</b>, <b>'Một mười bảy'</b><br/>"
            "• <b>'Hai mười hai'</b>, <b>'Hai mười tám'</b><br/>"
            "• <b>'Ba mười bảy'</b>, <b>'Lỗi một mười bảy'</b>",
            style_col3
        ),
    ])

    # Hàng 6: Re-Fail
    table_data.append([
        Paragraph("<font color='#D97706'><b>Re-Fail</b></font><br/><font color='#64748B' size='9'>(Tái kiểm lỗi)</font>", style_col1),
        Paragraph("• <b>Số - Số + sửa</b><br/>• <b>Số - Số + lại</b>", style_col2),
        Paragraph(
            "• <b>'Một một sửa'</b>, <b>'Một một lại'</b><br/>"
            "• <b>'Hai mười hai sửa'</b>, <b>'Hai mười hai lại'</b><br/>"
            "• <b>'Ba mười bảy sửa'</b>, <b>'Ba mười bảy lại'</b><br/>"
            "• <i>Nói đơn lẻ:</i> <b>'Sửa lại'</b>, <b>'Lỗi lại'</b>, <b>'Sửa'</b>",
            style_col3
        ),
    ])

    col_widths = [3.5 * cm, 5.5 * cm, 9.0 * cm]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        # Màu nền xen kẽ nhẹ nhàng, dễ đọc
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#F8FAFC")),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#F0FDF4")), # Pass xanh lá nhẹ
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#F0F9FF")), # Re-pass xanh biển nhẹ
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#FEF2F2")), # Fail đỏ nhẹ
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor("#FFFBEB")), # Re-fail vàng nhẹ
    ]))

    story.append(t)
    story.append(Spacer(1, 16))

    # 3. GHI CHÚ NGẮN GỌN DƯỚI BẢNG
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#E2E8F0"), spaceBefore=0, spaceAfter=8))
    note_text = (
        "💡 <b>Mẹo đọc chuẩn:</b> Nói tự nhiên, mic cách miệng 3 - 5 cm. "
        "Với lệnh <b>Số - Số</b> (Fail & Re-Fail), đọc <b>liền mạch trong 1 hơi thở</b> "
        "<i>(Ví dụ: 'Một một', 'Ba mười bảy sửa')</i>."
    )
    story.append(Paragraph(note_text, style_note))

    # Biên dịch PDF
    doc.build(story)
    import shutil
    shutil.copy2(OUTPUT_PDF, OUTPUT_PDF_ROOT)
    print(f"XUẤT FILE PDF THÀNH CÔNG: {OUTPUT_PDF}")
    print(f"BẢN SAO TẠI GỐC: {OUTPUT_PDF_ROOT}")


if __name__ == "__main__":
    build_pdf()

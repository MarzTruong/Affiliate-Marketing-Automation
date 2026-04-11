"""Generate Vietnamese PDF guide for platform connections."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "HUONG_DAN_KET_NOI.pdf"

# Colors
BLUE = HexColor("#1e40af")
DARK = HexColor("#1e293b")
GRAY = HexColor("#64748b")
LIGHT_BG = HexColor("#f1f5f9")
WHITE = HexColor("#ffffff")
GREEN = HexColor("#16a34a")
RED = HexColor("#dc2626")

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle(
    "DocTitle", parent=styles["Title"], fontSize=24, textColor=BLUE,
    spaceAfter=6, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "DocSubtitle", parent=styles["Normal"], fontSize=12, textColor=GRAY,
    spaceAfter=20, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "SectionTitle", parent=styles["Heading1"], fontSize=18, textColor=BLUE,
    spaceBefore=20, spaceAfter=10, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "SubSection", parent=styles["Heading2"], fontSize=14, textColor=DARK,
    spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "StepTitle", parent=styles["Heading3"], fontSize=12, textColor=DARK,
    spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "Body", parent=styles["Normal"], fontSize=11, textColor=DARK,
    spaceAfter=6, leading=16,
))
styles.add(ParagraphStyle(
    "BodyBold", parent=styles["Normal"], fontSize=11, textColor=DARK,
    spaceAfter=6, leading=16, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "CodeBlock", parent=styles["Normal"], fontSize=10, textColor=HexColor("#334155"),
    fontName="Courier", backColor=LIGHT_BG, spaceAfter=6, leading=14,
    leftIndent=20, rightIndent=20, spaceBefore=4,
))
styles.add(ParagraphStyle(
    "Warning", parent=styles["Normal"], fontSize=10, textColor=RED,
    spaceAfter=8, leading=14, fontName="Helvetica-Bold",
    leftIndent=10,
))
styles.add(ParagraphStyle(
    "Tip", parent=styles["Normal"], fontSize=10, textColor=GREEN,
    spaceAfter=8, leading=14, fontName="Helvetica-Bold",
    leftIndent=10,
))
styles.add(ParagraphStyle(
    "BulletItem", parent=styles["Normal"], fontSize=11, textColor=DARK,
    spaceAfter=4, leading=16, leftIndent=20, bulletIndent=10,
))


def hr():
    return HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0"), spaceAfter=10, spaceBefore=10)


def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", styles["BulletItem"])


def numbered(num, text):
    return Paragraph(f"<b>{num}.</b> {text}", styles["Body"])


def code(text):
    return Paragraph(text, styles["CodeBlock"])


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    story = []

    # ── COVER ──────────────────────────────────────────────
    story.append(Spacer(1, 60))
    story.append(Paragraph("HUONG DAN KET NOI NEN TANG", styles["DocTitle"]))
    story.append(Paragraph("Affiliate Marketing Automation System", styles["DocSubtitle"]))
    story.append(hr())
    story.append(Paragraph(
        "Tai lieu huong dan chi tiet cach lay API key va cau hinh "
        "ket noi cho TikTok Shop, Facebook va Telegram.",
        styles["Body"],
    ))
    story.append(Spacer(1, 20))

    # Table of contents
    toc_data = [
        ["Phan", "Noi dung", "Trang"],
        ["1", "TikTok Shop - Lay API Key", "2"],
        ["2", "Facebook - Cau hinh dang bai tu dong", "5"],
        ["3", "Telegram - Cau hinh bot dang bai", "8"],
        ["4", "Kiem tra ket noi", "10"],
    ]
    toc_table = Table(toc_data, colWidths=[2*cm, 10*cm, 3*cm])
    toc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(toc_table)

    # ══════════════════════════════════════════════════════════
    # PHAN 1: TIKTOK SHOP
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("PHAN 1: TIKTOK SHOP - LAY API KEY", styles["SectionTitle"]))
    story.append(hr())

    story.append(Paragraph("Tong quan", styles["SubSection"]))
    story.append(Paragraph(
        "TikTok Shop cho phep ban ket noi qua API de tim san pham, "
        "tao lien ket tiep thi (affiliate link) va theo doi don hang. "
        "Ban can dang ky lam <b>Affiliate Creator</b> hoac <b>Developer</b> tren TikTok Shop.",
        styles["Body"],
    ))

    story.append(Paragraph("Buoc 1: Dang ky tai khoan TikTok Shop Seller/Creator", styles["StepTitle"]))
    story.append(numbered(1, "Mo trinh duyet, vao dia chi: <b>seller-vn.tiktok.com</b>"))
    story.append(numbered(2, "Dang nhap bang tai khoan TikTok cua ban"))
    story.append(numbered(3, "Neu chua co shop, chon <b>\"Bat dau ban hang\"</b> va lam theo huong dan"))
    story.append(numbered(4, "Hoan thanh xac minh tai khoan (CMND/CCCD + dia chi)"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "* Luu y: Qua trinh xac minh co the mat 1-3 ngay lam viec.",
        styles["Warning"],
    ))

    story.append(Paragraph("Buoc 2: Tao ung dung Developer", styles["StepTitle"]))
    story.append(numbered(1, "Vao: <b>partner.tiktokshop.com</b>"))
    story.append(numbered(2, "Dang nhap cung tai khoan TikTok Shop"))
    story.append(numbered(3, "Vao menu <b>\"My Apps\"</b> (Ung dung cua toi)"))
    story.append(numbered(4, "Nhan <b>\"Create App\"</b> (Tao ung dung moi)"))
    story.append(numbered(5, "Dien thong tin:"))
    story.append(Spacer(1, 4))

    app_info = [
        ["Truong", "Dien gi"],
        ["App Name", "Affiliate Marketing Tool (hoac ten bat ky)"],
        ["App Type", "Chon \"Private App\""],
        ["Category", "Chon \"Affiliate\""],
    ]
    t = Table(app_info, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(numbered(6, "Nhan <b>\"Submit\"</b> va doi TikTok duyet (thuong 1-2 ngay)"))

    story.append(Paragraph("Buoc 3: Lay API Key", styles["StepTitle"]))
    story.append(numbered(1, "Sau khi app duoc duyet, vao lai <b>\"My Apps\"</b>"))
    story.append(numbered(2, "Click vao ten app ban vua tao"))
    story.append(numbered(3, "Tim muc <b>\"App Key\"</b> va <b>\"App Secret\"</b>"))
    story.append(numbered(4, "Sao chep (copy) ca hai gia tri nay"))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Buoc 4: Lay Access Token", styles["StepTitle"]))
    story.append(numbered(1, "Trong trang app, tim muc <b>\"Authorization\"</b>"))
    story.append(numbered(2, "Nhan <b>\"Generate Token\"</b>"))
    story.append(numbered(3, "Chon shop cua ban va cap quyen (Affiliate, Product, Order)"))
    story.append(numbered(4, "Copy <b>Access Token</b> duoc tao ra"))

    story.append(Paragraph("Buoc 5: Dien vao file .env", styles["StepTitle"]))
    story.append(Paragraph("Mo file <b>.env</b> (hoac <b>.env.prod</b>) va dien:", styles["Body"]))
    story.append(code("TIKTOK_APP_KEY=app_key_cua_ban_o_day"))
    story.append(code("TIKTOK_APP_SECRET=app_secret_cua_ban_o_day"))
    story.append(code("TIKTOK_ACCESS_TOKEN=access_token_cua_ban_o_day"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "* Meo: Access Token co han su dung. Khi het han, vao lai trang app de tao moi.",
        styles["Tip"],
    ))

    # Permissions table
    story.append(Paragraph("Quyen can cap (Permissions)", styles["SubSection"]))
    perms = [
        ["Quyen", "Mo ta", "Bat buoc?"],
        ["Product Read", "Doc thong tin san pham", "Co"],
        ["Affiliate Read", "Doc lien ket tiep thi", "Co"],
        ["Affiliate Write", "Tao lien ket tiep thi moi", "Co"],
        ["Order Read", "Doc thong tin don hang", "Nen co"],
    ]
    pt = Table(perms, colWidths=[5*cm, 7*cm, 3*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pt)

    # ══════════════════════════════════════════════════════════
    # PHAN 2: FACEBOOK
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("PHAN 2: FACEBOOK - CAU HINH DANG BAI TU DONG", styles["SectionTitle"]))
    story.append(hr())

    story.append(Paragraph("Tong quan", styles["SubSection"]))
    story.append(Paragraph(
        "He thong su dung <b>Facebook Graph API</b> de tu dong dang bai len <b>Facebook Page</b> "
        "(trang doanh nghiep). Ban can: mot Facebook Page va mot Facebook App.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "* Luu y: Chi hoat dong voi Facebook Page (trang), KHONG phai profile ca nhan.",
        styles["Warning"],
    ))

    story.append(Paragraph("Buoc 1: Tao Facebook Page (neu chua co)", styles["StepTitle"]))
    story.append(numbered(1, "Dang nhap Facebook"))
    story.append(numbered(2, "Tren trinh duyet, vao: <b>facebook.com/pages/create</b>"))
    story.append(numbered(3, "Chon loai: <b>\"Doanh nghiep hoac Thuong hieu\"</b>"))
    story.append(numbered(4, "Dat ten trang, chon danh muc (vi du: \"Mua sam\")"))
    story.append(numbered(5, "Nhan <b>\"Tao Trang\"</b>"))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "* Ghi lai ten Page. Ban se can Page ID o buoc sau.",
        styles["Tip"],
    ))

    story.append(Paragraph("Buoc 2: Tao Facebook App", styles["StepTitle"]))
    story.append(numbered(1, "Vao: <b>developers.facebook.com</b>"))
    story.append(numbered(2, "Dang nhap bang tai khoan Facebook cua ban"))
    story.append(numbered(3, "Nhan <b>\"My Apps\"</b> (goc tren phai) -> <b>\"Create App\"</b>"))
    story.append(numbered(4, "Chon <b>\"Business\"</b> lam loai app"))
    story.append(numbered(5, "Dat ten app, vi du: \"Affiliate Auto Post\""))
    story.append(numbered(6, "Nhan <b>\"Create App\"</b>"))

    story.append(Paragraph("Buoc 3: Them quyen Pages", styles["StepTitle"]))
    story.append(numbered(1, "Trong Dashboard cua app, tim muc <b>\"Add Products\"</b>"))
    story.append(numbered(2, "Tim <b>\"Facebook Login\"</b> va nhan <b>\"Set Up\"</b>"))
    story.append(numbered(3, "Vao <b>Settings -> Basic</b>, ghi lai <b>App ID</b> va <b>App Secret</b>"))

    story.append(Paragraph("Buoc 4: Lay Page Access Token", styles["StepTitle"]))
    story.append(Paragraph("Day la buoc quan trong nhat:", styles["BodyBold"]))
    story.append(numbered(1, "Vao: <b>developers.facebook.com/tools/explorer</b>"))
    story.append(numbered(2, "O goc phai, chon app ban vua tao"))
    story.append(numbered(3, "Nhan <b>\"Generate Access Token\"</b>"))
    story.append(numbered(4, "Tick chon cac quyen sau:"))
    story.append(Spacer(1, 4))

    perms_fb = [
        ["Quyen", "Chuc nang"],
        ["pages_show_list", "Hien thi danh sach Page"],
        ["pages_read_engagement", "Doc tuong tac tren Page"],
        ["pages_manage_posts", "Dang va quan ly bai viet"],
        ["pages_read_user_content", "Doc noi dung nguoi dung"],
    ]
    fbt = Table(perms_fb, colWidths=[6*cm, 9*cm])
    fbt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(fbt)
    story.append(Spacer(1, 8))

    story.append(numbered(5, "Nhan <b>\"Generate Access Token\"</b> va cho phep"))
    story.append(numbered(6, "Copy token nay (day la <b>User Access Token</b>)"))

    story.append(Paragraph("Buoc 5: Chuyen sang Page Token (dai han)", styles["StepTitle"]))
    story.append(Paragraph(
        "User Token chi ton tai 1 gio. De co token vinh vien, lam them buoc nay:",
        styles["Body"],
    ))
    story.append(numbered(1, "Van o Graph API Explorer, o o <b>\"GET\"</b>, go: <b>me/accounts</b>"))
    story.append(numbered(2, "Nhan <b>\"Submit\"</b>"))
    story.append(numbered(3, "Ket qua tra ve danh sach Page. Tim Page cua ban"))
    story.append(numbered(4, "Copy gia tri <b>\"access_token\"</b> va <b>\"id\"</b> (day la Page ID)"))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "* Meo: De co token VINH VIEN, vao: developers.facebook.com/tools/debug "
        "-> dan token -> nhan \"Extend Access Token\".",
        styles["Tip"],
    ))

    story.append(Paragraph("Buoc 6: Dien vao file .env", styles["StepTitle"]))
    story.append(code("FACEBOOK_PAGE_ID=page_id_cua_ban"))
    story.append(code("FACEBOOK_ACCESS_TOKEN=page_access_token_dai_han"))

    # ══════════════════════════════════════════════════════════
    # PHAN 3: TELEGRAM
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("PHAN 3: TELEGRAM - CAU HINH BOT DANG BAI", styles["SectionTitle"]))
    story.append(hr())

    story.append(Paragraph("Tong quan", styles["SubSection"]))
    story.append(Paragraph(
        "Telegram la kenh de cau hinh nhat. Ban chi can tao mot <b>Bot</b> "
        "va mot <b>Channel</b> (kenh), roi cho bot quyen dang bai vao kenh.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "* Hoan toan MIEN PHI, khong gioi han bai dang.",
        styles["Tip"],
    ))

    story.append(Paragraph("Buoc 1: Tao Bot tren Telegram", styles["StepTitle"]))
    story.append(numbered(1, "Mo app Telegram (dien thoai hoac may tinh)"))
    story.append(numbered(2, "Tim kiem <b>@BotFather</b> (co dau tich xanh)"))
    story.append(numbered(3, "Nhan <b>Start</b> hoac go <b>/start</b>"))
    story.append(numbered(4, "Go lenh: <b>/newbot</b>"))
    story.append(numbered(5, "BotFather se hoi ten bot -> Go ten, vi du: <b>Affiliate Post Bot</b>"))
    story.append(numbered(6, "BotFather hoi username -> Go, vi du: <b>affiliate_post_bot</b> (phai ket thuc bang \"bot\")"))
    story.append(numbered(7, "BotFather se gui cho ban mot <b>Token</b> dang:"))
    story.append(code("1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"))
    story.append(Paragraph("<b>Copy token nay lai.</b>", styles["BodyBold"]))

    story.append(Paragraph("Buoc 2: Tao Channel (Kenh)", styles["StepTitle"]))
    story.append(numbered(1, "Trong Telegram, nhan bieu tuong <b>viet moi</b> (goc tren)"))
    story.append(numbered(2, "Chon <b>\"New Channel\"</b> (Kenh moi)"))
    story.append(numbered(3, "Dat ten kenh, vi du: <b>Deal Hot Moi Ngay</b>"))
    story.append(numbered(4, "Chon <b>Public</b> (cong khai) va dat link, vi du: <b>@deal_hot_moi_ngay</b>"))
    story.append(numbered(5, "Nhan <b>Done</b> (Xong)"))

    story.append(Paragraph("Buoc 3: Them Bot vao Channel", styles["StepTitle"]))
    story.append(numbered(1, "Mo kenh vua tao"))
    story.append(numbered(2, "Nhan ten kenh o tren cung de mo thong tin"))
    story.append(numbered(3, "Nhan <b>\"Administrators\"</b> (Quan tri vien)"))
    story.append(numbered(4, "Nhan <b>\"Add Admin\"</b> (Them quan tri)"))
    story.append(numbered(5, "Tim bot cua ban bang username (vi du: <b>@affiliate_post_bot</b>)"))
    story.append(numbered(6, "Cap quyen: <b>Post Messages</b> (Dang tin nhan) -> Nhan <b>Done</b>"))

    story.append(Paragraph("Buoc 4: Lay Channel ID", styles["StepTitle"]))
    story.append(Paragraph("Neu kenh la Public, Channel ID chinh la <b>@ten_kenh</b>:", styles["Body"]))
    story.append(code("Vi du: @deal_hot_moi_ngay"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Neu kenh la Private, ban can lay ID so:", styles["Body"]))
    story.append(numbered(1, "Gui mot tin nhan bat ky vao kenh"))
    story.append(numbered(2, "Mo trinh duyet, vao:"))
    story.append(code("https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates"))
    story.append(numbered(3, "(Thay &lt;TOKEN&gt; bang token o Buoc 1)"))
    story.append(numbered(4, "Tim gia tri <b>\"chat\":{\"id\":-100...}</b> -> Do la Channel ID"))

    story.append(Paragraph("Buoc 5: Dien vao file .env", styles["StepTitle"]))
    story.append(code("TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"))
    story.append(code("TELEGRAM_CHANNEL_ID=@deal_hot_moi_ngay"))

    # ══════════════════════════════════════════════════════════
    # PHAN 4: KIEM TRA KET NOI
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("PHAN 4: KIEM TRA KET NOI", styles["SectionTitle"]))
    story.append(hr())

    story.append(Paragraph(
        "Sau khi dien day du API key vao file .env, ban co the kiem tra ket noi "
        "bang cach sau:",
        styles["Body"],
    ))

    story.append(Paragraph("Cach 1: Dung giao dien web", styles["SubSection"]))
    story.append(numbered(1, "Khoi dong he thong (backend + frontend)"))
    story.append(numbered(2, "Vao trang <b>\"Cai dat\"</b> tren giao dien"))
    story.append(numbered(3, "Xem trang thai cac nen tang da ket noi"))

    story.append(Paragraph("Cach 2: Dung API truc tiep", styles["SubSection"]))
    story.append(Paragraph("Mo trinh duyet va vao:", styles["Body"]))
    story.append(code("http://localhost:8000/docs"))
    story.append(Paragraph(
        "Day la trang Swagger UI - cho phep ban test tung API ma khong can viet code.",
        styles["Body"],
    ))
    story.append(Spacer(1, 8))

    # API test table
    test_apis = [
        ["Nen tang", "API de test", "Ket qua mong doi"],
        ["Facebook", "GET /api/v1/publisher/channels", "Danh sach co \"facebook\""],
        ["Telegram", "GET /api/v1/publisher/channels", "Danh sach co \"telegram\""],
        ["TikTok Shop", "GET /api/v1/platforms", "Hien thi tai khoan TikTok"],
        ["He thong", "GET /api/v1/system/health", "Status: healthy"],
    ]
    tt = Table(test_apis, colWidths=[3.5*cm, 6*cm, 5.5*cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tt)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Cach 3: Test dang bai thu", styles["SubSection"]))
    story.append(numbered(1, "Vao trang <b>\"Noi dung\"</b> -> Tao mot noi dung mau"))
    story.append(numbered(2, "Vao trang <b>\"Dang bai\"</b>"))
    story.append(numbered(3, "Chon noi dung vua tao"))
    story.append(numbered(4, "Chon kenh (Facebook hoac Telegram)"))
    story.append(numbered(5, "Nhan <b>\"Dang ngay\"</b>"))
    story.append(numbered(6, "Kiem tra tren Facebook Page / Telegram Channel xem bai da len chua"))

    story.append(Spacer(1, 20))
    story.append(hr())
    story.append(Paragraph(
        "Neu gap van de, xem file <b>HUONG_DAN_SU_DUNG.md</b> muc \"Xu ly su co\" "
        "hoac lien he ho tro.",
        styles["Body"],
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Phien ban: v0.2.0 | Ngay tao: 2026-04-06",
        styles["DocSubtitle"],
    ))

    doc.build(story)
    print(f"Da tao file: {OUTPUT}")


if __name__ == "__main__":
    build()

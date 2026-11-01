import datetime
import io
import math
import os
import uuid
import urllib.request
from enum import Enum
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import psycopg2
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
)
import streamlit as st

st.set_page_config(
    page_title="Technická čistota - VDA 19.1",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.cdnfonts.com/css/computer-modern-serif');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');

    p, h1, h2, h3, h4, h5, h6, li, label, input, textarea, select, table, th, td {
        font-family: 'Computer Modern Serif', serif !important;
    }
    
    .stButton button p {
        font-family: 'Computer Modern Serif', serif !important;
    }

    .material-symbols-rounded {
        font-family: 'Material Symbols Rounded' !important;
        vertical-align: middle;
        margin-right: 6px;
        color: #4b5563;
    }
    
    button[kind="secondary"]:has(div:contains("Nové vyhodnocení")),
    button[kind="secondary"]:has(div:contains("New Inspection")),
    div.stButton > button:has(div:contains("Nové vyhodnocení")),
    div.stButton > button:has(div:contains("New Inspection")) {
        background-color: #991b1b !important;
        color: white !important;
        border-color: #991b1b !important;
    }
    div.stButton > button:has(div:contains("Nové vyhodnocení")):hover,
    div.stButton > button:has(div:contains("New Inspection")):hover {
        background-color: #7f1d1d !important;
        border-color: #7f1d1d !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

translations = {
    "cs": {
        "title": "Systém vyhodnocení čistoty dle reportů (VDA 19.1)",
        "db_header": "Připojení k databázi",
        "db_pass": "Heslo k databázi",
        "db_connected": "Připojeno k Supabase",
        "db_error": "Chyba připojení k databázi:",
        "nav": ["Zápis a vyhodnocení z reportu", "Správa norem (Limity)", "Přehled historie měření", "Manažerský Dashboard"],
        "sec_ident": "Obecné informace a identifikace dílu",
        "sec_prep": "Parametry extrakce a filtrace",
        "sec_grav": "Gravimetrická analýza (Zbytková hmotnost)",
        "sec_opt": "Optická analýza částic (Matice B až N)",
        "sec_qual": "Validační brány a doplňkové parametry",
        "sec_adv": "Pokročilé metriky",
        "sec_hard": "Hard-Stop parametry a poznámka",
        "order_no": "Order no. (Číslo zakázky)",
        "rep_no": "Report no. (Číslo protokolu)",
        "cust": "Customer (Zákazník)",
        "contact": "Contact person (Kontaktní osoba)",
        "insp_name": "Jméno technika / Inspector",
        "test_ordered": "Test ordered (Typ zkoušky)",
        "reason_test": "Reason for test (Důvod zkoušky)",
        "filt_no": "Číslo filtru / Filter number",
        "filt_lot": "Šarže filtru / Batch number",
        "designation": "Designation (Označení dílu)",
        "part_no": "Part number (Číslo dílu)",
        "batch_no": "Batch number (Šarže)",
        "cond_delivery": "Condition on delivery (Stav při dodání)",
        "lot_size": "Inspection lot size (Velikost dávky)",
        "control_area": "Control area Ac [cm²]",
        "wetted_vol": "Wetted volume Vc [cm³]",
        "ext_method": "Extraction method (Metoda extrakce)",
        "dissolving_fluid": "Dissolving fluid (Rozpouštěcí médium)",
        "filt_mat": "Filter material (Materiál filtru)",
        "filt_pore": "Pore size (Velikost pórů µm)",
        "resid_mass": "Zbytková hmotnost M z protokolu vah [mg]",
        "scale_readable": "Scale readable to (Přesnost vah)",
        "blank_val": "Slepá hodnota [% z limitu]",
        "decl_test": "Klesající zkouška / Recovery [%]",
        "filt_occ": "Pokrytí filtru [%]",
        "pixel_res": "Pixelové rozlišení splněno (min 5-10 px)",
        "inc_unc": "Započítat modul nejistoty měření v protokolu",
        "note": "Poznámka k měření",
        "submit_eval": "Porovnat s normou a uložit do databáze",
        "l_max": "Maximální rozměr částice (L_max / Feret Max) [µm]",
        "aspect_ratio": "Prahová hodnota poměru stran (b/L)",
        "metallic_ratio": "Podíl kovových částic [%]",
        "cleanliness_class": "Kód čistoty (ISO 16232 / CCC kód)",
        "specific_surface": "Plošná hustota kontaminace [mg/m²]",
        "recovery_rate": "Účinnost extrakce (Recovery %)",
        "res_title": "Výsledek porovnání s podnikovou normou",
        "download_pdf": "Stáhnout souhrnný protokol (PDF)",
        "new_insp": "Nové zadání z reportu",
        "history_title": "Historie vyhodnocených měření",
        "standards_title": "Správa zákaznických a podnikových norem",
    },
    "en": {
        "title": "Technical Cleanliness Report Evaluation System (VDA 19.1)",
        "db_header": "Database Connection",
        "db_pass": "Database Password",
        "db_connected": "Connected to Supabase",
        "db_error": "Database connection error:",
        "nav": ["Report Evaluation & Entry", "Standards & Limits Management", "Inspection History", "Management Dashboard"],
        "sec_ident": "General Information & Inspected Object",
        "sec_prep": "Extraction & Filtration Parameters",
        "sec_grav": "Gravimetric Analysis",
        "sec_opt": "Optical Particle Analysis (Matrix B to N)",
        "sec_qual": "Validation Gates & Additional Parameters",
        "sec_adv": "Advanced Evaluation Parameters",
        "sec_hard": "Hard-Stop Parameters",
        "order_no": "Order no.",
        "rep_no": "Report no.",
        "cust": "Customer",
        "contact": "Contact person",
        "insp_name": "Inspector Name",
        "test_ordered": "Test ordered",
        "reason_test": "Reason for test",
        "filt_no": "Filter Number",
        "filt_lot": "Filter Lot / Batch",
        "designation": "Designation",
        "part_no": "Part number",
        "batch_no": "Batch number",
        "cond_delivery": "Condition on delivery",
        "lot_size": "Inspection lot size",
        "control_area": "Control area Ac [cm²]",
        "wetted_vol": "Wetted volume Vc [cm³]",
        "ext_method": "Extraction method",
        "dissolving_fluid": "Dissolving fluid",
        "filt_mat": "Filter material",
        "filt_pore": "Pore size [µm]",
        "resid_mass": "Residual Mass M from Scale [mg]",
        "scale_readable": "Scale readable to",
        "blank_val": "Blank Value [% of limit]",
        "decl_test": "Declining Test / Recovery [%]",
        "filt_occ": "Filter Occupancy [%]",
        "pixel_res": "Pixel Resolution Satisfied (min 5-10 px)",
        "inc_unc": "Include Measurement Uncertainty Module in Report",
        "note": "Inspection Note",
        "submit_eval": "Compare with Standard & Save to Database",
        "l_max": "Maximum Particle Dimension (L_max / Feret Max) [µm]",
        "aspect_ratio": "Aspect Ratio Threshold (b/L)",
        "metallic_ratio": "Metallic Particles Share [%]",
        "cleanliness_class": "Cleanliness Class (ISO 16232 / CCC Code)",
        "specific_surface": "Specific Surface Contamination [mg/m²]",
        "recovery_rate": "Extraction Efficiency (Recovery %)",
        "res_title": "Evaluation Result vs. Corporate Standard",
        "download_pdf": "Download Summary Report (PDF)",
        "new_insp": "New Report Entry",
        "history_title": "Inspection History",
        "standards_title": "Customer & Corporate Standards Management",
    }
}

st.sidebar.markdown("---")
lang_choice = st.sidebar.selectbox("Language / Jazyk", options=["cs", "en"], format_func=lambda x: "Čeština" if x == "cs" else "English")
t = translations[lang_choice]

st.sidebar.header(t["db_header"])
DB_PASSWORD = st.sidebar.text_input(t["db_pass"], type="password")


def get_db_connection():
    if not DB_PASSWORD:
        return None
    try:
        conn = psycopg2.connect(
            host="aws-0-eu-west-1.pooler.supabase.com",
            database="postgres",
            user="postgres.ywyicopmesmwtkjewbfk",
            password=DB_PASSWORD,
            port="6543",
            sslmode="require",
            connect_timeout=10,
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"{t['db_error']} {e}")
        return None


# --- CACHED DATA FUNCTIONS (Optimalizace rychlosti) ---
@st.cache_data(ttl=300)
def cached_fetch_components(pwd):
    try:
        conn = psycopg2.connect(
            host="aws-0-eu-west-1.pooler.supabase.com", database="postgres",
            user="postgres.ywyicopmesmwtkjewbfk", password=pwd, port="6543",
            sslmode="require", connect_timeout=10,
        )
        df = pd.read_sql("SELECT id, part_number, name FROM components", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()


class ProfileType(str, Enum):
    VDA_19_1 = "VDA 19.1"
    INTERNAL_CUSTOM = "Interní norma (Custom)"


# --- OFICIÁLNÍ TABULKA KÓDOVÝCH ÚROVNÍ VDA 19.1 (Tabulka 9-21) ---
VDA_CONTAMINATION_LEVELS = {
    '00': 0, '0': 1, '1': 2, '2': 4, '3': 8, '4': 16, '5': 32, '6': 64, '7': 130,
    '8': 250, '9': 500, '10': 1000, '11': 2000, '12': 4000, '13': 8000,
    '14': 16000, '15': 32000, '16': 64000, '17': 130000, '18': 250000,
    '19': 500000, '20': 1000000
}

def calculate_vda_code_level(particle_count, wetted_area):
    if particle_count <= 0:
        return '00'
    norm_count = particle_count * (1000.0 / wetted_area) if wetted_area > 0 else particle_count
    sorted_levels = sorted(VDA_CONTAMINATION_LEVELS.items(), key=lambda x: x[1])
    for code, limit in sorted_levels:
        if norm_count <= limit:
            return code
    return '20'

def generate_ccc_string(code_dict, ref_unit="A"):
    classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
    mapped_codes = []
    for cls in classes:
        lvl = code_dict.get(cls, '00')
        mapped_codes.append((cls, str(lvl).zfill(2) if len(str(lvl)) == 1 and str(lvl) != '00' else str(lvl)))
        
    i = 0
    grouped_parts = []
    while i < len(mapped_codes):
        cls_group = mapped_codes[i][0]
        lvl_group = mapped_codes[i][1]
        
        j = i + 1
        while j < len(mapped_codes) and mapped_codes[j][1] == lvl_group:
            cls_group += mapped_codes[j][0]
            j += 1
            
        grouped_parts.append(f"{cls_group}{lvl_group}")
        i = j
        
    inner_str = "/".join(grouped_parts)
    return f"{ref_unit}({inner_str})"

def calculate_measurement_uncertainty():
    u_microscope = 0.05
    u_recovery = 0.10
    u_declining = 0.10
    u_blank = 0.10
    k = 2.0
    u_combined = math.sqrt(u_microscope**2 + u_recovery**2 + u_declining**2 + u_blank**2)
    U_expanded = k * u_combined
    return {
        "combined_pct": round(u_combined * 100, 2),
        "expanded_pct": round(U_expanded * 100, 2),
    }

def generate_pdf_chart_image(report_df):
    fig, ax = plt.subplots(figsize=(7, 2.8))
    classes = report_df["Velikostní třída"].tolist()
    measured = pd.to_numeric(report_df["Naměřená úroveň"], errors="coerce").fillna(0).tolist()
    limits = pd.to_numeric(report_df["Povolený limit"], errors="coerce").fillna(0).tolist()
    
    x = np.arange(len(classes))
    width = 0.38
    
    ax.bar(x - width/2, measured, width, label='Vypočtená kódová úroveň CCC', color='#3b82f6')
    ax.bar(x + width/2, limits, width, label='Limit normy', color='#94a3b8', alpha=0.6)
    
    ax.set_ylabel('Kódová úroveň', fontsize=8)
    ax.set_xlabel('Velikostní třída (VDA 19.1)', fontsize=8)
    ax.set_title('Porovnání kódových úrovní CCC s limity normy', fontsize=9, fontweight='bold', pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(classes, fontsize=7)
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def ensure_pdf_fonts():
    font_dir = "fonts"
    os.makedirs(font_dir, exist_ok=True)
    
    reg_path = os.path.join(font_dir, "Roboto-Regular.ttf")
    bold_path = os.path.join(font_dir, "Roboto-Bold.ttf")
    
    if not os.path.exists(reg_path):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", reg_path)
    if not os.path.exists(bold_path):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", bold_path)
        
    try:
        pdfmetrics.registerFont(TTFont('Roboto', reg_path))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', bold_path))
        return "Roboto", "Roboto-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"

def create_pdf_report(meta_info, report_df, conformity_text, failed, note, grav_data, uncertainty_info=None, advanced_data=None, optical_meta=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )

    font_name, font_name_bold = ensure_pdf_fonts()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", fontName=font_name_bold, fontSize=11, leading=14, textColor=colors.HexColor("#111827"), alignment=1, spaceAfter=2)
    subtitle_style = ParagraphStyle("DocSubtitle", fontName=font_name, fontSize=7.5, leading=9, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=6)
    cell_style = ParagraphStyle("TableCell", fontName=font_name, fontSize=7, leading=9, textColor=colors.HexColor("#1f2937"))
    cell_bold = ParagraphStyle("TableCellBold", fontName=font_name_bold, fontSize=7, leading=9, textColor=colors.HexColor("#111827"))
    cell_header = ParagraphStyle("TableHeader", fontName=font_name_bold, fontSize=7, leading=9, textColor=colors.whitesmoke)
    ccc_style = ParagraphStyle("CCCStyle", fontName=font_name_bold, fontSize=8.5, leading=11, textColor=colors.HexColor("#1e3a8a"), alignment=1)

    elements = [
        Paragraph("INSPECTION REPORT: CLEANLINESS INSPECTION AS PER VDA 19.1", title_style),
        Paragraph("Souhrnný protokol technické čistoty dle podnikové normy", subtitle_style),
    ]

    current_date = datetime.date.today().strftime("%d.%m.%Y")
    
    meta_data = [
        [Paragraph("<b>Order no.:</b>", cell_style), Paragraph(meta_info.get('order_no', '-'), cell_style), Paragraph("<b>Customer:</b>", cell_style), Paragraph(meta_info.get('customer', '-'), cell_style)],
        [Paragraph("<b>Report no.:</b>", cell_style), Paragraph(meta_info.get('report_no', '-'), cell_style), Paragraph("<b>Contact person:</b>", cell_style), Paragraph(meta_info.get('contact', '-'), cell_style)],
        [Paragraph("<b>Test ordered:</b>", cell_style), Paragraph(meta_info.get('test_ordered', '-'), cell_style), Paragraph("<b>Reason for test:</b>", cell_style), Paragraph(meta_info.get('reason_test', '-'), cell_style)],
        [Paragraph("<b>Designation / Part:</b>", cell_style), Paragraph(meta_info.get('comp_name', '-'), cell_style), Paragraph("<b>Norma / Standard:</b>", cell_style), Paragraph(meta_info.get('std_name', '-'), cell_style)],
        [Paragraph("<b>Batch number:</b>", cell_style), Paragraph(meta_info.get('filter_lot', '-'), cell_style), Paragraph("<b>Filter number:</b>", cell_style), Paragraph(meta_info.get('filter_no', '-'), cell_style)],
        [Paragraph("<b>Control area (Ac):</b>", cell_style), Paragraph(f"{meta_info.get('wetted_area', 1000)} cm²", cell_style), Paragraph("<b>Extraction method:</b>", cell_style), Paragraph(meta_info.get('ext_method', '-'), cell_style)],
        [Paragraph("<b>Filter material / pore:</b>", cell_style), Paragraph(f"{meta_info.get('filt_mat', '-')}, {meta_info.get('filt_pore', '-')} µm", cell_style), Paragraph("<b>Dissolving fluid:</b>", cell_style), Paragraph(meta_info.get('dissolving_fluid', '-'), cell_style)],
        [Paragraph("<b>Datum vyhodnocení:</b>", cell_style), Paragraph(current_date, cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
    ]

    if optical_meta:
        meta_data.append([Paragraph("<b>Optické zařízení:</b>", cell_style), Paragraph(f"{optical_meta.get('manufacturer', '-')}, {optical_meta.get('model', '-')}", cell_style), Paragraph("<b>Zvětšení / Průměr:</b>", cell_style), Paragraph(f"{optical_meta.get('scale', '-')} | {optical_meta.get('eval_diameter', '-')} mm", cell_style)])
        meta_data.append([Paragraph("<b>Typ analýzy / Jas:</b>", cell_style), Paragraph(f"{optical_meta.get('scan_type', '-')} | Prah: {optical_meta.get('brightness_thresh', '-')}", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)])

    meta_table = Table(meta_data, colWidths=[110, 165, 100, 179])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 4))

    ccc_string = meta_info.get('ccc_string', 'CCC neuveden')
    ccc_table = Table([[Paragraph(f"<b>CCC kód (Component Cleanliness Code):</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]], colWidths=[554], rowHeights=[20])
    ccc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ])
    )
    elements.append(ccc_table)
    elements.append(Spacer(1, 4))

    if failed:
        res_color = colors.HexColor("#fee2e2")
        res_text_color = colors.HexColor("#991b1b")
    else:
        res_color = colors.HexColor("#d1fae5")
        res_text_color = colors.HexColor("#065f46")

    res_style = ParagraphStyle("ResText", fontName=font_name_bold, fontSize=8, leading=10, textColor=res_text_color, alignment=1)
    res_table = Table([[Paragraph(f"<b>VÝSLEDEK POSOUZENÍ / EVALUATION RESULT: {conformity_text.upper()}</b>", res_style)]], colWidths=[554], rowHeights=[18])
    res_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), res_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, res_text_color),
        ])
    )
    elements.append(res_table)
    elements.append(Spacer(1, 4))

    if uncertainty_info:
        unc_text = Paragraph(f"<b>Nejistota měření (k=2, 95%):</b> Kombinovaná: {uncertainty_info['combined_pct']}% | Rozšířená: {uncertainty_info['expanded_pct']}%", cell_style)
        elements.append(unc_text)
        elements.append(Spacer(1, 4))

    res_mass_val = grav_data.get('residual_mass', 0.0) if grav_data else 0.0
    grav_limit_val = grav_data.get('gravimetry_limit', 0.50) if grav_data else 0.50
    scale_readable_val = grav_data.get('scale_readable', '±0.01 mg') if grav_data else '±0.01 mg'
    grav_status = "specifikace nesplněna" if res_mass_val > grav_limit_val else "specifikace splněna"
    grav_status_html = '<font color="#991b1b"><b>specifikace nesplněna</b></font>' if grav_status == "specifikace nesplněna" else '<font color="#065f46"><b>specifikace splněna</b></font>'

    grav_table_data = [
        [Paragraph("<b>Gravimetrická analýza (Zbytková hmotnost M)</b>", cell_header), Paragraph("<b>Limit / Hodnota</b>", cell_header), Paragraph("<b>Stav / Status</b>", cell_header)],
        [Paragraph(f"Zbytková hmotnost M z protokolu vah (Scale readable: {scale_readable_val})", cell_style), Paragraph(f"{res_mass_val:.4f} mg", cell_style), Paragraph("-", cell_style)],
        [Paragraph("Max. povolená zbytková hmotnost (Limit normy)", cell_style), Paragraph(f"{grav_limit_val:.4f} mg", cell_style), Paragraph(grav_status_html, cell_style)],
    ]
    grav_table = Table(grav_table_data, colWidths=[254, 150, 150])
    grav_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(grav_table)
    elements.append(Spacer(1, 4))

    table_data = [[
        Paragraph("<b>Třída</b>", cell_header),
        Paragraph("<b>Rozsah</b>", cell_header),
        Paragraph("<b>Kov</b>", cell_header),
        Paragraph("<b>Nekov</b>", cell_header),
        Paragraph("<b>Vlákna</b>", cell_header),
        Paragraph("<b>Celkem (ks)</b>", cell_header),
        Paragraph("<b>Limit CCC</b>", cell_header),
        Paragraph("<b>Naměř. CCC</b>", cell_header),
        Paragraph("<b>Stav</b>", cell_header),
    ]]

    size_ranges = {
        "B": "5 µm - 15 µm", "C": "15 µm - 25 µm", "D": "25 µm - 50 µm",
        "E": "50 µm - 100 µm", "F": "100 µm - 150 µm", "G": "150 µm - 200 µm",
        "H": "200 µm - 400 µm", "I": "400 µm - 600 µm", "J": "600 µm - 1000 µm",
        "K": "1000 µm - 1500 µm", "L": "1500 µm - 2000 µm", "M": "2000 µm - 3000 µm",
        "N": "> 3000 µm",
    }

    if not report_df.empty:
        for _, row in report_df.iterrows():
            s_class = str(row["Velikostní třída"])
            s_range = size_ranges.get(s_class, "-")
            status = str(row["Stav"])
            status_html = (
                '<font color="#065f46"><b>OK</b></font>' if status in ["specifikace splněna", "OK"] else
                ('<font color="#991b1b"><b>NOK</b></font>' if status in ["specifikace nesplněna", "NOK"] else '<font color="#b45309"><b>VAR</b></font>')
            )

            table_data.append([
                Paragraph(s_class, cell_bold), 
                Paragraph(s_range, cell_style),
                Paragraph(str(row["Kovové"]), cell_style),
                Paragraph(str(row["Nekovové"]), cell_style),
                Paragraph(str(row["Vlákna"]), cell_style),
                Paragraph(str(row["Počet částic"]), cell_style),
                Paragraph(str(row["Povolený limit"]), cell_style),
                Paragraph(str(row["Naměřená úroveň"]), cell_style),
                Paragraph(status_html, cell_style),
            ])

        t = Table(table_data, colWidths=[35, 95, 45, 45, 45, 55, 65, 65, 50])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        elements.append(t)
        elements.append(Spacer(1, 4))

        try:
            chart_img_buf = generate_pdf_chart_image(report_df)
            elements.append(Paragraph("<b>Grafické porovnání kódových úrovní CCC:</b>", cell_bold))
            elements.append(Spacer(1, 2))
            elements.append(RLImage(chart_img_buf, width=500, height=180))
            elements.append(Spacer(1, 4))
        except Exception:
            pass

    if advanced_data:
        adv_data = [
            [Paragraph("<b>Doplňkové a pokročilé parametry</b>", cell_header), Paragraph("<b>Hodnota</b>", cell_header)],
            [Paragraph("Max. rozměr částice (L_max / Feret Max)", cell_style), Paragraph(f"{advanced_data.get('l_max', 0)} µm", cell_style)],
            [Paragraph("Poměr stran (b/L threshold)", cell_style), Paragraph(str(advanced_data.get('aspect_ratio', '-')), cell_style)],
            [Paragraph("Plošná hustota kontaminace (Specific Surface)", cell_style), Paragraph(f"{advanced_data.get('specific_surface', 0)} mg/m²", cell_style)],
            [Paragraph("Účinnost extrakce z protokolu (Recovery rate)", cell_style), Paragraph(f"{advanced_data.get('recovery_rate', 0)} %", cell_style)],
        ]
        adv_table = Table(adv_data, colWidths=[354, 200])
        adv_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        elements.append(adv_table)

    if note:
        elements.append(Spacer(1, 4))
        note_table = Table([[Paragraph("<b>Poznámka k záznamu:</b>", cell_bold)], [Paragraph(note, cell_style)]], colWidths=[554])
        elements.append(note_table)

    elements.append(Spacer(1, 6))
    sig_table = Table([[Paragraph(f"<b>Záznam zapsal / ověřil (technik):</b> {meta_info.get('inspector_name', 'Jan Novák')}", cell_style)]], colWidths=[554])
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    return buffer.getvalue()


def show_home_screen():
    st.write("Vítejte v systému vyhodnocení technické čistoty dle VDA 19.1. Vyberte požadovanou sekci:")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### <span class='material-symbols-rounded'>description</span> Zápis", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 60px;'>Zadání dat z reportu a generování PDF.</div>", unsafe_allow_html=True)
        if st.button("Vyhodnocení", use_container_width=True, type="primary"):
            st.session_state.active_tab = t["nav"][0]
            st.rerun()
            
    with col2:
        st.markdown("### <span class='material-symbols-rounded'>tune</span> Normy", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 60px;'>Nastavení podnikových limitů.</div>", unsafe_allow_html=True)
        if st.button("Správa norem", use_container_width=True):
            st.session_state.active_tab = t["nav"][1]
            st.rerun()
            
    with col3:
        st.markdown("### <span class='material-symbols-rounded'>history</span> Historie", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 60px;'>Přehled uložených protokolů.</div>", unsafe_allow_html=True)
        if st.button("Zobrazit historii", use_container_width=True):
            st.session_state.active_tab = t["nav"][2]
            st.rerun()

    with col4:
        st.markdown("### <span class='material-symbols-rounded'>analytics</span> Dashboard", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 60px;'>Manažerské trendy a analýzy.</div>", unsafe_allow_html=True)
        if st.button("Otevřít dashboard", use_container_width=True):
            st.session_state.active_tab = t["nav"][3]
            st.rerun()


def show_standards_management(conn):
    st.markdown(f"### <span class='material-symbols-rounded'>tune</span> {t['nav'][1]}", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Přidat novou podnikovou normu", "Editovat / Smazat stávající normu"])
    
    vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
    size_ranges_desc = {
        "B": "5 µm - 15 µm", "C": "15 µm - 25 µm", "D": "25 µm - 50 µm",
        "E": "50 µm - 100 µm", "F": "100 µm - 150 µm", "G": "150 µm - 200 µm",
        "H": "200 µm - 400 µm", "I": "400 µm - 600 µm", "J": "600 µm - 1000 µm",
        "K": "1000 µm - 1500 µm", "L": "1500 µm - 2000 µm", "M": "2000 µm - 3000 µm",
        "N": "> 3000 µm",
    }
    
    with tab1:
        components_df = cached_fetch_components(DB_PASSWORD)
        if components_df.empty:
            try:
                components_df = pd.read_sql("SELECT id, part_number, name FROM components", conn)
            except Exception:
                st.error("Chyba při načítání dílů.")
                return

        with st.form("add_standard_form"):
            col1, col2 = st.columns(2)
            with col1:
                selected_comp_id = st.selectbox(
                    "Přiřadit k dílu",
                    options=components_df['id'].tolist(),
                    format_func=lambda x: f"{components_df[components_df['id'] == x]['part_number'].values[0]} - {components_df[components_df['id'] == x]['name'].values[0]}"
                )
            with col2:
                norm_name = st.text_input("Název podnikové/zákaznické normy", value="testovacifirmaA")

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                limit_basis = st.selectbox("Základ limitu (Vztaženo na)", ["Vztaženo na plochu (1000 cm²)", "Vztaženo na celý díl"], key="add_limit_basis")
            with col_s2:
                gravimetry_limit_input = st.number_input("Max. povolená zbytková hmotnost (mg)", min_value=0.0, value=0.50, step=0.1)

            st.markdown("---")
            st.markdown("### Nastavení limitů kódových úrovní pro velikostní frakce a druhy částic")
            
            default_test_limits = {"B": "5", "C": "4", "D": "3", "E": "2", "F": "1", "G": "0", "H": "0", "I": "0", "J": "0", "K": "0", "L": "0", "M": "0", "N": "0"}
            
            add_inputs = {}
            h_c1, h_c2, h_c3, h_c4, h_c5 = st.columns([1, 2, 2, 2, 2])
            h_c1.markdown("**Třída**")
            h_c2.markdown("**Rozsah**")
            h_c3.markdown("**Kovové**")
            h_c4.markdown("**Nekovové**")
            h_c5.markdown("**Vlákna**")

            for s_class in vda_classes:
                c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 2])
                with c1:
                    st.markdown(f"**{s_class}**")
                with c2:
                    st.caption(size_ranges_desc.get(s_class, ''))
                with c3:
                    kov_v = st.text_input(f"Kov {s_class}", value=default_test_limits.get(s_class, "0"), key=f"add_kov_{s_class}", label_visibility="collapsed")
                with c4:
                    nekov_v = st.text_input(f"Nekov {s_class}", value="", placeholder="0", key=f"add_nekov_{s_class}", label_visibility="collapsed")
                with c5:
                    fib_v = st.text_input(f"Fib {s_class}", value="", placeholder="0", key=f"add_fib_{s_class}", label_visibility="collapsed")
                
                add_inputs[s_class] = {"kov": kov_v, "nekov": nekov_v, "fib": fib_v}

            std_note = st.text_area("Poznámka k normě", value="Testovací norma A s limity kódových úrovní")
            submit_new_std = st.form_submit_button("Vytvořit a uložit normu", type="primary")

            if submit_new_std:
                if not norm_name:
                    st.error("Název normy je povinný.")
                else:
                    try:
                        cur = conn.cursor()
                        inserted_any = False
                        full_note = f"[ZÁKLAD: {limit_basis}] {std_note}"
                        
                        for s_class, vals in add_inputs.items():
                            for p_type, val_str in [("kov", vals["kov"]), ("nekov", vals["nekov"]), ("fib", vals["fib"])]:
                                if val_str.strip() and val_str.strip() != "-":
                                    new_row_id = str(uuid.uuid4())
                                    db_class_key = f"{s_class}_{p_type}"
                                    cur.execute(
                                        "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (new_row_id, selected_comp_id, norm_name, db_class_key, float(val_str), full_note, gravimetry_limit_input if gravimetry_limit_input > 0 else None)
                                    )
                                    inserted_any = True
                                    
                        if inserted_any:
                            conn.commit()
                            st.success(f"Norma '{norm_name}' byla úspěšně uložena.")
                        else:
                            st.warning("Nevyplnili jste žádné limity.")
                            conn.rollback()
                        cur.close()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Chyba při ukládání: {e}")

    with tab2:
        try:
            all_standards_df = pd.read_sql(
                "SELECT DISTINCT cs.id, cs.norm_name, c.part_number, c.name as comp_name FROM customer_standards cs JOIN components c ON cs.component_id = c.id", conn
            )
        except Exception as e:
            st.error("Nelze načíst existující normy.")
            all_standards_df = pd.DataFrame()

        if not all_standards_df.empty:
            edit_std_id = st.selectbox(
                "Vyberte normu k editaci",
                options=all_standards_df['id'].tolist(),
                format_func=lambda x: f"{all_standards_df[all_standards_df['id'] == x]['norm_name'].values[0]} (Díl: {all_standards_df[all_standards_df['id'] == x]['part_number'].values[0]})"
            )

            if edit_std_id:
                existing_limits_df = pd.read_sql(f"SELECT size_class, max_allowed_level, note, gravimetry_limit_mg, component_id, norm_name FROM customer_standards WHERE id = '{edit_std_id}'", conn)
                
                curr_note_raw = existing_limits_df['note'].iloc[0] if not existing_limits_df.empty and existing_limits_df['note'].notna().any() else ""
                
                curr_basis = "Vztaženo na plochu (1000 cm²)"
                curr_clean_note = curr_note_raw
                if "[ZÁKLAD: Vztaženo na celý díl]" in curr_note_raw:
                    curr_basis = "Vztaženo na celý díl"
                    curr_clean_note = curr_note_raw.replace("[ZÁKLAD: Vztaženo na celý díl]", "").strip()
                elif "[ZÁKLAD: Vztaženo na plochu (1000 cm²)]" in curr_note_raw:
                    curr_basis = "Vztaženo na plochu (1000 cm²)"
                    curr_clean_note = curr_note_raw.replace("[ZÁKLAD: Vztaženo na plochu (1000 cm²)]", "").strip()

                curr_grav = existing_limits_df['gravimetry_limit_mg'].iloc[0] if not existing_limits_df.empty and existing_limits_df['gravimetry_limit_mg'].notna().any() else 0.0
                curr_norm_name = existing_limits_df['norm_name'].iloc[0]
                curr_comp_id = existing_limits_df['component_id'].iloc[0]

                current_class_limits = {}
                for _, row in existing_limits_df.iterrows():
                    sc = str(row['size_class']).strip()
                    val = row['max_allowed_level']
                    val_str = str(int(val)) if val.is_integer() else str(val)
                    
                    if sc.endswith("_kov"):
                        base = sc[:-4]
                        current_class_limits.setdefault(base, {})['kov'] = val_str
                    elif sc.endswith("_nekov"):
                        base = sc[:-6]
                        current_class_limits.setdefault(base, {})['nekov'] = val_str
                    elif sc.endswith("_fib"):
                        base = sc[:-4]
                        current_class_limits.setdefault(base, {})['fib'] = val_str
                    else:
                        current_class_limits.setdefault(sc, {})['kov'] = val_str

                st.markdown(f"**Upravit parametry normy**")
                with st.form("edit_standard_form"):
                    edit_norm_name = st.text_input("Název normy", value=curr_norm_name)
                    
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_basis = st.selectbox(
                            "Základ limitu (Vztaženo na)",
                            ["Vztaženo na plochu (1000 cm²)", "Vztaženo na celý díl"],
                            index=0 if curr_basis == "Vztaženo na plochu (1000 cm²)" else 1,
                            key="edit_limit_basis"
                        )
                    with col_e2:
                        edit_gravimetry = st.number_input("Max. povolená hmotnost gravimetrie (mg)", min_value=0.0, value=float(curr_grav), step=0.1)
                    
                    st.markdown("---")
                    st.markdown("### Úprava limitů kódových úrovní pro velikostní frakce a druhy částic")

                    edit_inputs = {}
                    h_e1, h_e2, h_e3, h_e4, h_e5 = st.columns([1, 2, 2, 2, 2])
                    h_e1.markdown("**Třída**")
                    h_e2.markdown("**Rozsah**")
                    h_e3.markdown("**Kovové**")
                    h_e4.markdown("**Nekovové**")
                    h_e5.markdown("**Vlákna**")

                    for s_class in vda_classes:
                        cls_data = current_class_limits.get(s_class, {})
                        c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 2])
                        with c1:
                            st.markdown(f"**{s_class}**")
                        with c2:
                            st.caption(size_ranges_desc.get(s_class, ''))
                        with c3:
                            kov_v = st.text_input(f"Edit Kov {s_class}", value=cls_data.get('kov', ''), key=f"edit_kov_{s_class}", label_visibility="collapsed")
                        with c4:
                            nekov_v = st.text_input(f"Edit Nekov {s_class}", value=cls_data.get('nekov', ''), key=f"edit_nekov_{s_class}", label_visibility="collapsed")
                        with c5:
                            fib_v = st.text_input(f"Edit Fib {s_class}", value=cls_data.get('fib', ''), key=f"edit_fib_{s_class}", label_visibility="collapsed")
                        
                        edit_inputs[s_class] = {"kov": kov_v, "nekov": nekov_v, "fib": fib_v}

                    edit_note = st.text_area("Poznámka", value=curr_clean_note)
                    
                    col_save, col_del = st.columns([1, 4])
                    with col_save:
                        submit_edit = st.form_submit_button("Uložit úpravy", type="primary")
                    with col_del:
                        submit_delete = st.form_submit_button("Odstranit normu")

                    if submit_edit:
                        try:
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM customer_standards WHERE norm_name = '{curr_norm_name}'")
                            full_edit_note = f"[ZÁKLAD: {edit_basis}] {edit_note}"
                            
                            for s_class, vals in edit_inputs.items():
                                for p_type, val_str in [("kov", vals["kov"]), ("nekov", vals["nekov"]), ("fib", vals["fib"])]:
                                    if val_str.strip() and val_str.strip() != "-":
                                        new_row_id = str(uuid.uuid4())
                                        db_class_key = f"{s_class}_{p_type}"
                                        cur.execute(
                                            "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                            (new_row_id, curr_comp_id, edit_norm_name, db_class_key, float(val_str), full_edit_note, edit_gravimetry if edit_gravimetry > 0 else None)
                                        )
                            conn.commit()
                            st.success("Změny byly úspěšně uloženy.")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Chyba při ukládání úprav: {e}")
                            
                    if submit_delete:
                        try:
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM customer_standards WHERE norm_name = '{curr_norm_name}'")
                            conn.commit()
                            st.warning("Norma byla kompletně smazána.")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Chyba při mazání: {e}")


def show_evaluation_form(conn):
    st.markdown(f"### <span class='material-symbols-rounded'>description</span> {t['nav'][0]}", unsafe_allow_html=True)
    
    if "eval_success" not in st.session_state:
        st.session_state.eval_success = False

    if st.session_state.eval_success:
        st.subheader(t["res_title"])
        st.info(f"**CCC kód (Component Cleanliness Code):** {st.session_state.generated_ccc}")
        if st.session_state.eval_failed:
            st.error(f"Posouzení: **{st.session_state.eval_message.upper()}**")
        else:
            st.success(f"Posouzení: **{st.session_state.eval_message.upper()}**")
        
        if not st.session_state.eval_report_df.empty:
            st.dataframe(st.session_state.eval_report_df, use_container_width=True)
            
            st.markdown("#### 📈 Grafické porovnání kódových úrovní CCC s limity normy")
            chart_df = st.session_state.eval_report_df.copy()
            chart_df["Povolený limit"] = pd.to_numeric(chart_df["Povolený limit"], errors="coerce").fillna(0)
            chart_df["Naměřená úroveň"] = pd.to_numeric(chart_df["Naměřená úroveň"], errors="coerce").fillna(0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=chart_df["Velikostní třída"],
                y=chart_df["Naměřená úroveň"],
                name="Vypočtená kódová úroveň CCC",
                marker_color=["#ef4444" if row["Stav"] in ["specifikace nesplněna", "NOK"] else "#3b82f6" for _, row in chart_df.iterrows()]
            ))
            fig.add_trace(go.Scatter(
                x=chart_df["Velikostní třída"],
                y=chart_df["Povolený limit"],
                name="Limit normy",
                mode="lines+markers",
                line=dict(color="#0f172a", width=2, dash="dash")
            ))
            fig.update_layout(
                xaxis_title="Velikostní třída (VDA 19.1)",
                yaxis_title="Kódová úroveň",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=20),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.download_button(
                t["download_pdf"],
                st.session_state.generated_pdf,
                file_name=f"porovnani_norma_{st.session_state.filt_no_for_pdf}.pdf",
                mime="application/pdf",
            )
        with btn_col2:
            if st.button(t["new_insp"]):
                st.session_state.eval_success = False
                st.rerun()
        return

    components_df = cached_fetch_components(DB_PASSWORD)
    if components_df.empty:
        try:
            components_df = pd.read_sql("SELECT id, part_number, name FROM components", conn)
        except Exception as err:
            components_df = pd.DataFrame()
            st.error(f"Chyba při načítání dílů: {err}")

    if not components_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            selected_comp_idx = st.selectbox(
                "Výběr dílu / Component Selection",
                options=components_df.index,
                format_func=lambda x: f"{components_df.loc[x, 'part_number']} - {components_df.loc[x, 'name']}",
            )
            c_id = components_df.loc[selected_comp_idx, "id"]
            c_pn = components_df.loc[selected_comp_idx, "part_number"]
            c_nm = components_df.loc[selected_comp_idx, "name"]
            comp_name = f"{c_pn} ({c_nm})"

        with col2:
            standards_df = pd.read_sql(f"SELECT DISTINCT id, norm_name FROM customer_standards WHERE component_id = '{c_id}'", conn)
            if not standards_df.empty:
                selected_std_idx = st.selectbox(
                    "Výběr podnikové / zákaznické normy pro porovnání",
                    options=standards_df.index,
                    format_func=lambda x: standards_df.loc[x, "norm_name"],
                )
                std_id = standards_df.loc[selected_std_idx, "id"]
                std_name = standards_df.loc[selected_std_idx, "norm_name"]
                
                gravimetry_limit_db = 0.50
                try:
                    grav_df = pd.read_sql(f"SELECT gravimetry_limit_mg FROM customer_standards WHERE id = '{std_id}' LIMIT 1", conn)
                    if not grav_df.empty and pd.notna(grav_df.iloc[0]['gravimetry_limit_mg']):
                        gravimetry_limit_db = float(grav_df.iloc[0]['gravimetry_limit_mg'])
                except:
                    pass
            else:
                std_id, std_name, gravimetry_limit_db = None, "testovacifirmaA", 0.50

        db_limits_dict = {}
        if std_id:
            try:
                lim_fetch = pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id = '{std_id}' OR norm_name = '{std_name}'", conn)
                for _, row in lim_fetch.iterrows():
                    sc = str(row['size_class']).strip()
                    val = row['max_allowed_level']
                    db_limits_dict[sc] = int(val)
            except Exception as e:
                pass

        fallback_test_limits = {"B": 5, "C": 4, "D": 3, "E": 2, "F": 1, "G": 0, "H": 0, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0}

        st.markdown("---")

        st.subheader(t["sec_ident"])
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            order_number = st.text_input(t["order_no"], value="ORD-2026-001")
            report_number = st.text_input(t["rep_no"], value="REP-VDA-042")
            customer = st.text_input(t["cust"], value="Testovací Zákazník s.r.o.")
            contact_person = st.text_input(t["contact"], value="Ing. Petr Novotný")
        with col_b:
            insp_name = st.text_input(t["insp_name"], value="Jan Novák")
            test_ordered = st.selectbox(t["test_ordered"], ["Routine inspection", "Double inspection", "Qualification test"])
            reason_test = st.selectbox(t["reason_test"], ["Initial assessment", "Process monitoring", "Modifications, design"])
            filt_no = st.text_input(t["filt_no"], value="F-1024")
        with col_c:
            filt_lot = st.text_input(t["filt_lot"], value="sdvsdv")
            profile_type = st.selectbox("Profil vyhodnocení", [ProfileType.VDA_19_1, ProfileType.INTERNAL_CUSTOM])
            cond_delivery = st.text_input(t["cond_delivery"], value="Sériový díl čistý")
            lot_size = st.number_input(t["lot_size"], min_value=1, value=1, step=1)

        st.markdown("---")
        
        st.subheader(t["sec_prep"])
        col_d, col_e, col_f = st.columns(3)
        with col_d:
            wetted_area = st.number_input(t["control_area"], min_value=0.0, value=1000.0)
            extraction_method = st.selectbox(t["ext_method"], ["Pressure-rinsing", "Ultrasonics", "Internal rinsing", "Agitation"])
        with col_e:
            wetted_volume = st.number_input(t["wetted_vol"], min_value=0.0, value=0.0)
            extraction_medium = st.selectbox(
                t["dissolving_fluid"],
                ["Testovací benzín (Petroether)", "Izopropanol (IPA)", "Aceton", "Demineralizovaná voda", "Ethanol"]
            )
        with col_f:
            filter_material = st.selectbox(
                t["filt_mat"],
                ["PET (polyester)", "PTFE (polytetrafluorethylen)", "Cellulose nitrate", "Nylon / PA", "Glass fiber"]
            )
            filter_pore_size = st.number_input(t["filt_pore"], min_value=0.1, value=5.0)

        st.markdown("---")

        st.subheader(t["sec_grav"])
        if gravimetry_limit_db:
            st.info(f"Očekávaný limit normy pro gravimetrii: **{gravimetry_limit_db} mg**")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            residual_mass = st.number_input(t["resid_mass"], min_value=0.0, value=0.4200, format="%.4f", step=0.1)
        with col_g2:
            scale_readable_choice = st.selectbox(t["scale_readable"], ["±0.01 mg", "±0.1 mg", "0.001 mg"], index=0)

        st.markdown("---")

        st.subheader(t["sec_opt"])
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            micro_manuf = st.text_input("Výrobce mikroskopu (Manufacturer)", value="Leica Microsystems")
            eval_diameter = st.number_input("Vyhodnocovací průměr [mm] (Evaluation diameter)", min_value=0.0, value=50.0, step=1.0)
        with col_m2:
            micro_model = st.text_input("Model (Model)", value="DM6 M Cleanliness")
            scan_type = st.selectbox("Typ analýzy (Scan type)", ["Standard", "Free"])
        with col_m3:
            micro_scale = st.text_input("Zvětšení / Měřítko (Scale / Magnification)", value="5.0x")
            brightness_thresh = st.number_input("Prahová hodnota jasu (Brightness threshold)", min_value=0, max_value=255, value=128)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Matice počtů částic podle velikostních tříd a typů (zadáte počty, systém automaticky spočte kódové úrovně CCC):**")
        
        vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
        size_ranges_desc = {
            "B": "5 µm - 15 µm", "C": "15 µm - 25 µm", "D": "25 µm - 50 µm",
            "E": "50 µm - 100 µm", "F": "100 µm - 150 µm", "G": "150 µm - 200 µm",
            "H": "200 µm - 400 µm", "I": "400 µm - 600 µm", "J": "600 µm - 1000 µm",
            "K": "1000 µm - 1500 µm", "L": "1500 µm - 2000 µm", "M": "2000 µm - 3000 µm",
            "N": "> 3000 µm",
        }
        
        matrix_inputs = {}
        
        h_c1, h_c2, h_c3, h_c4, h_c5 = st.columns([1, 2, 2, 2, 2])
        h_c1.markdown("**Třída**")
        h_c2.markdown("**Rozsah**")
        h_c3.markdown("**Kovové**")
        h_c4.markdown("**Nekovové**")
        h_c5.markdown("**Vlákna**")
        
        for s_class in vda_classes:
            limit_val = db_limits_dict.get(s_class, db_limits_dict.get(f"{s_class}_kov", fallback_test_limits.get(s_class, 0)))
            c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 2])
            with c1:
                st.markdown(f"**{s_class}**")
            with c2:
                st.caption(f"{size_ranges_desc.get(s_class, '')} (Limit: {limit_val})")
            with c3:
                met_val = st.text_input(f"Kov {s_class}", value="", placeholder="0", key=f"mat_kov_{s_class}", label_visibility="collapsed")
            with c4:
                nonmet_val = st.text_input(f"Nekov {s_class}", value="", placeholder="0", key=f"mat_nekov_{s_class}", label_visibility="collapsed")
            with c5:
                fib_val = st.text_input(f"Fib {s_class}", value="", placeholder="0", key=f"mat_fib_{s_class}", label_visibility="collapsed")
                
            matrix_inputs[s_class] = {
                "metallic": met_val,
                "non_metallic": nonmet_val,
                "fibers": fib_val
            }

        st.markdown("---")

        st.subheader(t["sec_qual"])
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            blank_value_pct = st.number_input(t["blank_val"], min_value=0.0, value=2.0, step=0.1)
        with col_q2:
            declining_test_pct = st.number_input(t["decl_test"], min_value=0.0, value=5.0, step=0.5)
        with col_q3:
            filter_occupancy_pct = st.number_input(t["filt_occ"], min_value=0.0, value=3.0, step=0.5)

        st.markdown("---")

        st.subheader(t["sec_adv"])
        col_ad1, col_ad2, col_ad3 = st.columns(3)
        with col_ad1:
            l_max_val = st.number_input(t["l_max"], min_value=0.0, value=450.0, step=10.0)
            aspect_ratio_val = st.number_input(t["aspect_ratio"], min_value=0.0, max_value=10.0, value=0.1, step=0.01)
        with col_ad2:
            metallic_percentage = st.number_input(t["metallic_ratio"], min_value=0.0, max_value=100.0, value=2.5, step=0.1)
            recovery_rate_val = st.number_input(t["recovery_rate"], min_value=0.0, max_value=100.0, value=92.5, step=0.5)
        with col_ad3:
            specific_surface_val = st.number_input(t["specific_surface"], min_value=0.0, value=round(residual_mass / (wetted_area / 10000.0) if wetted_area > 0 else 0.0, 2), step=0.1)
            cleanliness_class_code = st.text_input("Vlastní CCC kód (při prázdném poli se vygeneruje automaticky, např. A(B20/CD16))", value="")

        st.markdown("---")
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            pixel_resolution_ok = st.checkbox(t["pixel_res"], value=True)
        with col_x2:
            include_uncertainty = st.checkbox(t["inc_unc"], value=True)

        hard_stop_feret_max = 0.0
        has_v3 = False
        max_feret_measured = 0.0
        if profile_type == ProfileType.INTERNAL_CUSTOM:
            st.markdown("---")
            st.subheader(t["sec_hard"])
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                hard_stop_feret_max = st.number_input("Max. povolený Feret_max [µm] (Hard-stop)", min_value=0.0, value=1500.0)
            with col_h2:
                has_v3 = st.checkbox("Detekovány zakázané částice V3 (>1000 HV)", value=False)
            max_feret_measured = st.number_input("Naměřená největší částice Feret_max [µm]", min_value=0.0, value=250.0)

        note = st.text_area(t["note"])
        
        sub_btn = st.button(t["submit_eval"], type="primary", use_container_width=True)

        if sub_btn:
            if not filt_no:
                st.error("Vyplňte číslo filtru.")
            else:
                gating_errors = []
                if blank_value_pct > 10.0:
                    gating_errors.append(f"Slepá hodnota ({blank_value_pct}%) překračuje max. povolenou (10%).")
                if filter_occupancy_pct > 10.0:
                    gating_errors.append(f"Pokrytí filtru ({filter_occupancy_pct}%) překračuje max. povolené (10%).")
                if declining_test_pct > 10.0:
                    gating_errors.append(f"Klesající zkouška ({declining_test_pct}%) překračuje limit (10%).")
                if not pixel_resolution_ok:
                    gating_errors.append("Pixelové rozlišení neodpovídá požadavkům.")

                if gating_errors:
                    st.error("TEST JE NEPLATNÝ (Chyba validačních bran):")
                    for err in gating_errors:
                        st.error(f"- {err}")
                else:
                    ref_unit_char = "A"
                    if std_id:
                        try:
                            note_check = pd.read_sql(f"SELECT note FROM customer_standards WHERE id = '{std_id}' LIMIT 1", conn)
                            if not note_check.empty and note_check.iloc[0]['note'] and "celý díl" in str(note_check.iloc[0]['note'] ):
                                ref_unit_char = "N"
                        except:
                            pass

                    report = []
                    failed = False
                    warning_triggered = False

                    if gravimetry_limit_db and residual_mass > gravimetry_limit_db:
                        failed = True
                        st.error(f"Gravimetrie překročena: Naměřená zbytková hmotnost {residual_mass:.4f} mg (Limit normy: {gravimetry_limit_db} mg)")

                    valid_matrix_totals = {}
                    codes_for_ccc = {}
                    
                    for s_class in vda_classes:
                        vals = matrix_inputs[s_class]
                        
                        def parse_int(v):
                            try:
                                return int(v.strip()) if v.strip() and v.strip() != "-" else 0
                            except:
                                return 0

                        kov_count = parse_int(vals["metallic"])
                        nekov_count = parse_int(vals["non_metallic"])
                        fib_count = parse_int(vals["fibers"])
                        
                        total_particles = kov_count + nekov_count + fib_count
                        calc_code_level = calculate_vda_code_level(total_particles, wetted_area)
                        
                        valid_matrix_totals[s_class] = int(calc_code_level)
                        codes_for_ccc[s_class] = calc_code_level

                        max_alw = int(db_limits_dict.get(s_class, db_limits_dict.get(f"{s_class}_kov", fallback_test_limits.get(s_class, 0))))
                        
                        if profile_type == ProfileType.VDA_19_1:
                            num_calc = int(calc_code_level) if calc_code_level != '00' else 0
                            status = "specifikace nesplněna" if num_calc > max_alw else "specifikace splněna"
                            if status == "specifikace nesplněna":
                                failed = True
                            else:
                                if max_alw > 0 and num_calc >= max_alw:
                                    status = "VAROVÁNÍ"
                                    warning_triggered = True
                                else:
                                    status = "specifikace splněna"

                        report.append({
                            "Velikostní třída": s_class,
                            "Kovové": kov_count,
                            "Nekovové": nekov_count,
                            "Vlákna": fib_count,
                            "Počet částic": total_particles,
                            "Povolený limit": str(max_alw),
                            "Kódová úroveň (Naměřeno)": calc_code_level,
                            "Stav": status,
                        })

                    auto_ccc = generate_ccc_string(codes_for_ccc, ref_unit_char)
                    generated_ccc_string = cleanliness_class_code if cleanliness_class_code.strip() else auto_ccc

                    hard_stop_failed = False
                    if profile_type == ProfileType.INTERNAL_CUSTOM:
                        if hard_stop_feret_max > 0 and max_feret_measured > hard_stop_feret_max:
                            hard_stop_failed = True
                            failed = True
                            st.error("Překročen Hard-Stop limit pro největší částici (Feret max).")
                        if has_v3:
                            hard_stop_failed = True
                            failed = True
                            st.error("Detekovány zakázané částice V3 (>1000 HV).")

                    report_df = pd.DataFrame(report)
                    report_df = report_df.rename(columns={"Kódová úroveň (Naměřeno)": "Naměřená úroveň"})

                    if profile_type == ProfileType.VDA_19_1:
                        conformity_text = "specifikace nesplněna" if failed else "specifikace splněna"
                    else:
                        if failed or hard_stop_failed:
                            conformity_text = "specifikace nesplněna"
                        elif warning_triggered:
                            conformity_text = "VAROVÁNÍ"
                        else:
                            conformity_text = "specifikace splněna"

                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO inspections (component_id, standard_id, inspector_name, filter_number, filter_lot_number, entered_ccc_string, evaluation_result, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                        (c_id, std_id if std_id else None, insp_name, filt_no, filt_lot, generated_ccc_string, conformity_text, note),
                    )
                    ins_id = cur.fetchone()[0]
                    for s_class, code_lvl in valid_matrix_totals.items():
                        cur.execute(
                            "INSERT INTO inspection_details (inspection_id, size_class, cleanliness_level) VALUES (%s, %s, %s);",
                            (ins_id, s_class, code_lvl),
                        )
                    conn.commit()
                    cur.close()

                    meta_info_dict = {
                        "order_no": order_number, "report_no": report_number, "customer": customer,
                        "contact": contact_person, "test_ordered": test_ordered, "reason_test": reason_test,
                        "comp_name": comp_name, "std_name": std_name, "filter_no": filt_no, "filter_lot": filt_lot,
                        "wetted_area": wetted_area, "ext_method": extraction_method, "dissolving_fluid": extraction_medium,
                        "filt_mat": filter_material, "filt_pore": filter_pore_size, "inspector_name": insp_name, "ccc_string": generated_ccc_string
                    }
                    grav_data_dict = {"residual_mass": residual_mass, "gravimetry_limit": gravimetry_limit_db, "scale_readable": scale_readable_choice}
                    uncertainty_dict = calculate_measurement_uncertainty() if include_uncertainty else None
                    advanced_dict = {
                        "l_max": l_max_val, "aspect_ratio": aspect_ratio_val, "metallic_percentage": metallic_percentage,
                        "specific_surface": specific_surface_val, "recovery_rate": recovery_rate_val
                    }
                    optical_meta_dict = {
                        "manufacturer": micro_manuf, "model": micro_model, "scale": micro_scale,
                        "eval_diameter": eval_diameter, "scan_type": scan_type, "brightness_thresh": brightness_thresh
                    }

                    pdf_data = create_pdf_report(
                        meta_info_dict, report_df, conformity_text, failed, note,
                        grav_data_dict, uncertainty_dict, advanced_dict, optical_meta_dict
                    )
                    
                    st.session_state.eval_success = True
                    st.session_state.generated_pdf = pdf_data
                    st.session_state.eval_message = conformity_text
                    st.session_state.generated_ccc = generated_ccc_string
                    st.session_state.eval_failed = failed
                    st.session_state.eval_report_df = report_df
                    st.session_state.filt_no_for_pdf = filt_no
                    
                    st.rerun()


def show_history(conn):
    st.markdown(f"### <span class='material-symbols-rounded'>history</span> {t['history_title']}", unsafe_allow_html=True)
    try:
        history_df = pd.read_sql(
            '''
            SELECT 
                i.inspection_date AS "Datum", 
                c.part_number AS "Číslo dílu", 
                c.name AS "Název dílu",
                COALESCE(cs.norm_name, '-') AS "Norma",
                i.inspector_name AS "Technik", 
                i.filter_number AS "Filtr", 
                i.filter_lot_number AS "Šarže filtru",
                i.entered_ccc_string AS "CCC kód", 
                i.evaluation_result AS "Výsledek",
                COALESCE(i.note, '-') AS "Poznámka"
            FROM inspections i 
            JOIN components c ON i.component_id = c.id 
            LEFT JOIN customer_standards cs ON i.standard_id = cs.id
            ORDER BY i.inspection_date DESC;
            ''',
            conn,
        )
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
            st.info("Zatím nejsou uložena žádná vyhodnocení.")
    except Exception as err:
        st.error(f"Chyba načítání historie: {err}")


def show_dashboard(conn):
    st.markdown(f"### <span class='material-symbols-rounded'>analytics</span> Manažerský Dashboard & Trendy", unsafe_allow_html=True)
    try:
        df = pd.read_sql(
            '''
            SELECT 
                i.inspection_date, 
                c.part_number, 
                c.name AS comp_name,
                i.inspector_name, 
                i.evaluation_result
            FROM inspections i 
            JOIN components c ON i.component_id = c.id
            ''',
            conn
        )
        if df.empty:
            st.info("Zatím nejsou k dispozici žádná data pro analýzu. Proveďte nejprve nějaká měření.")
            return

        total_insp = len(df)
        ok_count = len(df[df['evaluation_result'].str.lower().str.contains("splněna")])
        nok_count = len(df[df['evaluation_result'].str.lower().str.contains("nesplněna")])
        warn_count = len(df[df['evaluation_result'].str.lower().str.contains("varování")])
        success_rate = (ok_count / total_insp * 100) if total_insp > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Celkem měření", total_insp)
        col2.metric("Úspěšná (OK)", ok_count, f"{success_rate:.1f}%")
        col3.metric("Neúspěšná (NOK)", nok_count)
        col4.metric("Varování", warn_count)

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Výsledky posouzení (Podíl)")
            res_counts = df['evaluation_result'].value_counts().reset_index()
            res_counts.columns = ['Výsledek', 'Počet']
            fig_pie = px.pie(res_counts, names='Výsledek', values='Počet', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            st.markdown("#### Počet měření podle dílů")
            part_counts = df['part_number'].value_counts().reset_index()
            part_counts.columns = ['Díl', 'Počet měření']
            fig_bar = px.bar(part_counts, x='Díl', y='Počet měření', color='Díl', color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_bar.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=300, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### Vývoj počtu měření v čase")
        df['date_only'] = pd.to_datetime(df['inspection_date']).dt.date
        time_counts = df.groupby('date_only').size().reset_index(name='Počet')
        fig_time = px.line(time_counts, x='date_only', y='Počet', markers=True, line_shape='spline', color_discrete_sequence=['#2563eb'])
        fig_time.update_layout(xaxis_title="Datum", yaxis_title="Počet měření", margin=dict(l=20, r=20, t=30, b=20), height=320)
        st.plotly_chart(fig_time, use_container_width=True)

    except Exception as e:
        st.error(f"Chyba při načítání dat pro dashboard: {e}")


if DB_PASSWORD:
    conn = get_db_connection()
    if conn:
        st.sidebar.success(t["db_connected"])
        
        st.markdown(f"## {t['title']}")

        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Home"

        if st.session_state.active_tab != "Home":
            col_home, col_info = st.columns([1, 5])
            with col_home:
                if st.button("Zpět na menu", use_container_width=True):
                    st.session_state.active_tab = "Home"
                    st.rerun()
            with col_info:
                st.markdown(f"Aktivní sekce: **{st.session_state.active_tab}**")
            st.markdown("---")

        if st.session_state.active_tab == "Home":
            show_home_screen()
        elif st.session_state.active_tab == t["nav"][0]:
            show_evaluation_form(conn)
        elif st.session_state.active_tab == t["nav"][1]:
            show_standards_management(conn)
        elif st.session_state.active_tab == t["nav"][2]:
            show_history(conn)
        elif st.session_state.active_tab == t["nav"][3]:
            show_dashboard(conn)

        conn.close()
else:
    st.info("Zadejte heslo k databázi v levém panelu. / Enter the database password in the sidebar.")

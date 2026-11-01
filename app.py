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

# =====================================================================
# VZHLEDOVÝ MODUL (THEME) A KOMPONENTY
# =====================================================================

NAVY = "#0f172a"
SLATE = "#475569"
BORDER = "#e2e8f0"
BG = "#f6f8fb"
CARD = "#ffffff"
ACCENT = "#2563eb"
OK = "#059669"
OK_BG = "#d1fae5"
NOK = "#dc2626"
NOK_BG = "#fee2e2"
WARN = "#d97706"
WARN_BG = "#fef3c7"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"], .stApp, input, textarea, select, button {{
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded {{
    font-family: 'Material Symbols Rounded' !important;
}}

.stApp {{ background: {BG}; }}
.block-container {{ padding-top: 2rem; padding-bottom: 4rem; max-width: 1280px; }}
#MainMenu, footer {{ visibility: hidden; }}

h1, h2, h3, h4 {{ color: {NAVY}; letter-spacing: -0.01em; font-weight: 650; }}
h3 {{ font-size: 1.25rem; }}
hr {{ border: none; border-top: 1px solid {BORDER}; margin: 1.5rem 0; }}

/* ---------- Postranní panel ---------- */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY} 0%, #1e293b 100%);
}}
[data-testid="stSidebar"] * {{ color: #e2e8f0; }}
[data-testid="stSidebar"] hr {{ border-top: 1px solid rgba(255,255,255,.12); }}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background: rgba(255,255,255,.07) !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    color: #fff !important;
}}

/* ---------- Vstupy ---------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="select"] > div {{
    border-radius: 10px !important;
    border: 1px solid {BORDER} !important;
    background: {CARD} !important;
    transition: border-color .15s, box-shadow .15s;
}}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.15) !important;
}}
label, [data-testid="stWidgetLabel"] p {{
    font-size: .82rem; font-weight: 500; color: {SLATE};
}}

/* ---------- Tlačítka ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
    border-radius: 10px; font-weight: 600; padding: .55rem 1.1rem;
    border: 1px solid {BORDER}; transition: all .15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: {ACCENT}; color: {ACCENT}; transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15,23,42,.08);
}}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {{
    background: linear-gradient(135deg, {ACCENT}, #1d4ed8); color: #fff; border: none;
}}
.stButton > button[kind="primary"]:hover {{ color: #fff; box-shadow: 0 6px 16px rgba(37,99,235,.35); }}

/* ---------- Karty a Expandery ---------- */
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {{
    background: {CARD}; border: 1px solid {BORDER} !important;
    border-radius: 14px; box-shadow: 0 1px 2px rgba(15,23,42,.04);
}}
[data-testid="stExpander"] {{
    background: {CARD}; border: 1px solid {BORDER} !important;
    border-radius: 10px; margin-bottom: 1rem;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden;
}}
[data-testid="stPlotlyChart"] {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; padding: .5rem;
}}

/* ---------- Vlastní komponenty ---------- */
.page-header {{
    background: linear-gradient(135deg, {NAVY} 0%, #1e3a8a 100%);
    color: #fff; border-radius: 16px; padding: 1.6rem 2rem; margin-bottom: 1.5rem;
    box-shadow: 0 8px 24px rgba(15,23,42,.15);
}}
.page-header h1 {{ color: #fff !important; font-size: 1.55rem; margin: 0 0 .25rem 0; font-family: 'Inter', sans-serif !important; }}
.page-header p {{ color: #cbd5e1 !important; margin: 0; font-size: .92rem; font-family: 'Inter', sans-serif !important; }}

.section-title {{
    display: flex; align-items: center; gap: .6rem;
    font-size: 1.05rem; font-weight: 650; color: {NAVY};
    margin: 1.4rem 0 .8rem 0; padding-bottom: .5rem; border-bottom: 2px solid {BORDER};
}}
.section-title .bar {{ width: 4px; height: 1.1rem; background: {ACCENT}; border-radius: 2px; }}

.result-banner {{
    border-radius: 14px; padding: 1.1rem 1.4rem; font-weight: 600; font-size: 1.05rem;
    display: flex; align-items: center; gap: .8rem; margin: .5rem 0 1rem 0;
}}
.result-banner.ok   {{ background: {OK_BG};  color: #065f46; border: 1px solid {OK}; }}
.result-banner.nok  {{ background: {NOK_BG}; color: #991b1b; border: 1px solid {NOK}; }}
.result-banner.warn {{ background: {WARN_BG}; color: #92400e; border: 1px solid {WARN}; }}

.ccc-chip {{
    font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace;
    background: #eff6ff; color: #1e3a8a; border: 1px solid #bfdbfe;
    padding: .5rem 1rem; border-radius: 10px; font-weight: 600; display: inline-block;
}}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="page-header"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

def section(title: str) -> None:
    st.markdown(f'<div class="section-title"><span class="bar"></span>{title}</div>', unsafe_allow_html=True)

def result_banner(text: str, failed: bool, warning: bool = False) -> None:
    cls = "nok" if failed else ("warn" if warning else "ok")
    icon = "✕" if failed else ("!" if warning else "✓")
    st.markdown(f'<div class="result-banner {cls}"><span style="font-size:1.4rem">{icon}</span><span>Posouzení: {text.upper()}</span></div>', unsafe_allow_html=True)

def ccc_chip(code: str) -> None:
    st.markdown(f'<div style="margin-bottom:1rem"><div style="font-size:.75rem;color:{SLATE};text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem">CCC kód (Component Cleanliness Code)</div><span class="ccc-chip">{code}</span></div>', unsafe_allow_html=True)

def style_fig(fig, height: int = 360):
    fig.update_layout(template="plotly_white", height=height, font=dict(family="Inter, sans-serif", size=12, color=NAVY), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), bargap=0.35)
    fig.update_xaxes(showgrid=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor="#eef2f7", zeroline=False)
    return fig

def status_table_style(df, status_col: str = "Stav"):
    def _row(row):
        s = str(row[status_col]).lower()
        if "nesplněna" in s or s == "nok":
            bg = NOK_BG
        elif "var" in s:
            bg = WARN_BG
        else:
            return [""] * len(row)
        return [f"background-color: {bg}"] * len(row)
    return df.style.apply(_row, axis=1)

# =====================================================================
# PŘEKLADY A LOGIKA APLIKACE
# =====================================================================

translations = {
    "cs": {
        "title": "Systém vyhodnocení čistoty (VDA 19.1)",
        "subtitle": "Komplexní analýza a generování CCC kódů",
        "db_header": "Připojení k databázi",
        "db_pass": "Heslo k databázi",
        "db_connected": "Připojeno k Supabase",
        "db_error": "Chyba připojení k databázi:",
        "nav": ["Zápis a vyhodnocení", "Správa norem (Limity)", "Přehled historie"],
        "sec_ident": "Obecné informace a identifikace dílu",
        "sec_prep": "Parametry extrakce a filtrace",
        "sec_grav": "Gravimetrická analýza",
        "sec_opt": "Optická analýza částic (Matice B až N)",
        "sec_qual": "Validační brány",
        "sec_adv": "Pokročilé metriky a nastavení",
        "sec_hard": "Hard-Stop parametry",
    },
    "en": {
        "title": "Cleanliness Evaluation System (VDA 19.1)",
        "subtitle": "Comprehensive analysis and CCC code generation",
        "db_header": "Database Connection",
        "db_pass": "Database Password",
        "db_connected": "Connected to Supabase",
        "db_error": "Database connection error:",
        "nav": ["Report Evaluation", "Standards Management", "Inspection History"],
        "sec_ident": "General Information",
        "sec_prep": "Extraction & Filtration",
        "sec_grav": "Gravimetric Analysis",
        "sec_opt": "Optical Particle Analysis",
        "sec_qual": "Validation Gates",
        "sec_adv": "Advanced Metrics",
        "sec_hard": "Hard-Stop Parameters",
    }
}

st.sidebar.markdown("---")
lang_choice = st.sidebar.selectbox("Language / Jazyk", options=["cs", "en"], format_func=lambda x: "Čeština" if x == "cs" else "English")
t = translations[lang_choice]

st.sidebar.header(t["db_header"])
DB_PASSWORD = st.sidebar.text_input(t["db_pass"], type="password")

def get_db_connection():
    if not DB_PASSWORD: return None
    try:
        conn = psycopg2.connect(
            host="aws-0-eu-west-1.pooler.supabase.com", database="postgres",
            user="postgres.ywyicopmesmwtkjewbfk", password=DB_PASSWORD, port="6543",
            sslmode="require", connect_timeout=10,
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"{t['db_error']} {e}")
        return None

class ProfileType(str, Enum):
    VDA_19_1 = "VDA 19.1"
    INTERNAL_CUSTOM = "Interní norma (Custom)"

VDA_CONTAMINATION_LEVELS = {
    '00': 0, '0': 1, '1': 2, '2': 4, '3': 8, '4': 16, '5': 32, '6': 64, '7': 130,
    '8': 250, '9': 500, '10': 1000, '11': 2000, '12': 4000, '13': 8000,
    '14': 16000, '15': 32000, '16': 64000, '17': 130000, '18': 250000,
    '19': 500000, '20': 1000000
}

def calculate_vda_code_level(particle_count, wetted_area):
    if particle_count <= 0: return '00'
    norm_count = particle_count * (1000.0 / wetted_area) if wetted_area > 0 else particle_count
    sorted_levels = sorted(VDA_CONTAMINATION_LEVELS.items(), key=lambda x: x[1])
    for code, limit in sorted_levels:
        if norm_count <= limit: return code
    return '20'

def generate_ccc_string(code_dict, ref_unit="A"):
    classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
    mapped_codes = [(cls, str(code_dict.get(cls, '00')).zfill(2) if len(str(code_dict.get(cls, '00'))) == 1 and str(code_dict.get(cls, '00')) != '00' else str(code_dict.get(cls, '00'))) for cls in classes]
    i = 0
    grouped_parts = []
    while i < len(mapped_codes):
        cls_group, lvl_group = mapped_codes[i]
        j = i + 1
        while j < len(mapped_codes) and mapped_codes[j][1] == lvl_group:
            cls_group += mapped_codes[j][0]
            j += 1
        grouped_parts.append(f"{cls_group}{lvl_group}")
        i = j
    return f"{ref_unit}({'/'.join(grouped_parts)})"

def calculate_measurement_uncertainty():
    u_combined = math.sqrt(0.05**2 + 0.10**2 + 0.10**2 + 0.10**2)
    return {"combined_pct": round(u_combined * 100, 2), "expanded_pct": round(2.0 * u_combined * 100, 2)}

def generate_pdf_chart_image(report_df):
    fig, ax = plt.subplots(figsize=(7, 2.8))
    classes = report_df["Velikostní třída"].tolist()
    measured = pd.to_numeric(report_df["Naměřená úroveň"], errors="coerce").fillna(0).tolist()
    limits = pd.to_numeric(report_df["Povolený limit"], errors="coerce").fillna(0).tolist()
    x = np.arange(len(classes))
    width = 0.38
    ax.bar(x - width/2, measured, width, label='CCC', color='#3b82f6')
    ax.bar(x + width/2, limits, width, label='Limit', color='#94a3b8', alpha=0.6)
    ax.set_ylabel('Kódová úroveň', fontsize=8)
    ax.set_xlabel('Velikostní třída', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(classes, fontsize=7)
    ax.legend(fontsize=7)
    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def ensure_pdf_fonts():
    font_dir = "fonts"
    os.makedirs(font_dir, exist_ok=True)
    reg_path, bold_path = os.path.join(font_dir, "Roboto-Regular.ttf"), os.path.join(font_dir, "Roboto-Bold.ttf")
    if not os.path.exists(reg_path): urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", reg_path)
    if not os.path.exists(bold_path): urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", bold_path)
    try:
        pdfmetrics.registerFont(TTFont('Roboto', reg_path))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', bold_path))
        return "Roboto", "Roboto-Bold"
    except:
        return "Helvetica", "Helvetica-Bold"

def create_pdf_report(meta_info, report_df, conformity_text, failed, note, grav_data, uncertainty_info=None, advanced_data=None, optical_meta=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    font_name, font_name_bold = ensure_pdf_fonts()
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
    meta_data = [
        [Paragraph("<b>Order no.:</b>", cell_style), Paragraph(meta_info.get('order_no', '-'), cell_style), Paragraph("<b>Customer:</b>", cell_style), Paragraph(meta_info.get('customer', '-'), cell_style)],
        [Paragraph("<b>Report no.:</b>", cell_style), Paragraph(meta_info.get('report_no', '-'), cell_style), Paragraph("<b>Contact person:</b>", cell_style), Paragraph(meta_info.get('contact', '-'), cell_style)],
        [Paragraph("<b>Designation / Part:</b>", cell_style), Paragraph(meta_info.get('comp_name', '-'), cell_style), Paragraph("<b>Norma / Standard:</b>", cell_style), Paragraph(meta_info.get('std_name', '-'), cell_style)],
        [Paragraph("<b>Control area (Ac):</b>", cell_style), Paragraph(f"{meta_info.get('wetted_area', 1000)} cm²", cell_style), Paragraph("<b>Extraction method:</b>", cell_style), Paragraph(meta_info.get('ext_method', '-'), cell_style)],
    ]
    meta_table = Table(meta_data, colWidths=[110, 165, 100, 179])
    meta_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0"))]))
    elements.extend([meta_table, Spacer(1, 4)])

    ccc_table = Table([[Paragraph(f"<b>CCC kód:</b> &nbsp;&nbsp; {meta_info.get('ccc_string', 'CCC neuveden')}", ccc_style)]], colWidths=[554], rowHeights=[20])
    ccc_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6"))]))
    elements.extend([ccc_table, Spacer(1, 4)])

    res_color, res_text_color = (colors.HexColor("#fee2e2"), colors.HexColor("#991b1b")) if failed else (colors.HexColor("#d1fae5"), colors.HexColor("#065f46"))
    res_style = ParagraphStyle("ResText", fontName=font_name_bold, fontSize=8, leading=10, textColor=res_text_color, alignment=1)
    res_table = Table([[Paragraph(f"<b>VÝSLEDEK POSOUZENÍ: {conformity_text.upper()}</b>", res_style)]], colWidths=[554], rowHeights=[18])
    res_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), res_color), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 1, res_text_color)]))
    elements.extend([res_table, Spacer(1, 4)])

    # Tabulka částic s přidaným sloupcem Celkem (ks)
    table_data = [[Paragraph("<b>Třída</b>", cell_header), Paragraph("<b>Rozsah</b>", cell_header), Paragraph("<b>Kov</b>", cell_header), Paragraph("<b>Nekov</b>", cell_header), Paragraph("<b>Vlákna</b>", cell_header), Paragraph("<b>Celkem (ks)</b>", cell_header), Paragraph("<b>Limit</b>", cell_header), Paragraph("<b>Naměř. CCC</b>", cell_header), Paragraph("<b>Stav</b>", cell_header)]]
    for _, row in report_df.iterrows():
        s = str(row["Stav"])
        status_html = '<font color="#065f46"><b>OK</b></font>' if s in ["specifikace splněna", "OK"] else ('<font color="#991b1b"><b>NOK</b></font>' if s in ["specifikace nesplněna", "NOK"] else '<font color="#b45309"><b>VAR</b></font>')
        table_data.append([Paragraph(str(row["Velikostní třída"]), cell_bold), Paragraph("-", cell_style), Paragraph(str(row["Kovové"]), cell_style), Paragraph(str(row["Nekovové"]), cell_style), Paragraph(str(row["Vlákna"]), cell_style), Paragraph(str(row["Počet částic"]), cell_style), Paragraph(str(row["Povolený limit"]), cell_style), Paragraph(str(row["Naměřená úroveň"]), cell_style), Paragraph(status_html, cell_style)])
    
    t_obj = Table(table_data, colWidths=[35, 95, 45, 45, 45, 55, 65, 65, 50])
    t_obj.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1"))]))
    elements.extend([t_obj, Spacer(1, 4)])
    
    doc.build(elements)
    return buffer.getvalue()


def show_evaluation_form(conn):
    section(t["nav"][0])
    
    if "eval_success" not in st.session_state:
        st.session_state.eval_success = False

    if st.session_state.eval_success:
        result_banner(st.session_state.eval_message, st.session_state.eval_failed)
        ccc_chip(st.session_state.generated_ccc)
        
        if not st.session_state.eval_report_df.empty:
            st.dataframe(status_table_style(st.session_state.eval_report_df), use_container_width=True)
            
            st.markdown("#### 📈 Porovnání kódových úrovní")
            chart_df = st.session_state.eval_report_df.copy()
            chart_df["Povolený limit"] = pd.to_numeric(chart_df["Povolený limit"], errors="coerce").fillna(0)
            chart_df["Naměřená úroveň"] = pd.to_numeric(chart_df["Naměřená úroveň"], errors="coerce").fillna(0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_df["Velikostní třída"], y=chart_df["Naměřená úroveň"], name="Vypočtená úroveň CCC", marker_color=["#ef4444" if row["Stav"] in ["specifikace nesplněna", "NOK"] else "#3b82f6" for _, row in chart_df.iterrows()]))
            fig.add_trace(go.Scatter(x=chart_df["Velikostní třída"], y=chart_df["Povolený limit"], name="Limit normy", mode="lines+markers", line=dict(color="#0f172a", width=2, dash="dash")))
            st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.download_button(t["download_pdf"], st.session_state.generated_pdf, file_name=f"protokol_{st.session_state.filt_no_for_pdf}.pdf", mime="application/pdf")
        with btn_col2:
            if st.button("Nové vyhodnocení"):
                st.session_state.eval_success = False
                st.rerun()
        return

    try:
        components_df = pd.read_sql("SELECT id, part_number, name FROM components", conn)
    except Exception:
        components_df = pd.DataFrame()

    if not components_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            selected_comp_idx = st.selectbox("Výběr dílu", options=components_df.index, format_func=lambda x: f"{components_df.loc[x, 'part_number']} - {components_df.loc[x, 'name']}")
            c_id = components_df.loc[selected_comp_idx, "id"]
            comp_name = f"{components_df.loc[selected_comp_idx, 'part_number']} ({components_df.loc[selected_comp_idx, 'name']})"
        with col2:
            standards_df = pd.read_sql(f"SELECT DISTINCT id, norm_name FROM customer_standards WHERE component_id = '{c_id}'", conn)
            if not standards_df.empty:
                selected_std_idx = st.selectbox("Norma pro porovnání", options=standards_df.index, format_func=lambda x: standards_df.loc[x, "norm_name"])
                std_id, std_name = standards_df.loc[selected_std_idx, "id"], standards_df.loc[selected_std_idx, "norm_name"]
                try:
                    grav_df = pd.read_sql(f"SELECT gravimetry_limit_mg FROM customer_standards WHERE id = '{std_id}' LIMIT 1", conn)
                    gravimetry_limit_db = float(grav_df.iloc[0]['gravimetry_limit_mg']) if not grav_df.empty else 0.50
                except:
                    gravimetry_limit_db = 0.50
            else:
                std_id, std_name, gravimetry_limit_db = None, "Výchozí", 0.50

        db_limits_dict = {}
        if std_id:
            try:
                lim_fetch = pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id = '{std_id}' OR norm_name = '{std_name}'", conn)
                for _, row in lim_fetch.iterrows():
                    db_limits_dict[str(row['size_class']).strip()] = int(row['max_allowed_level'])
            except: pass
        fallback_test_limits = {"B": 5, "C": 4, "D": 3, "E": 2, "F": 1, "G": 0, "H": 0, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0}

        with st.expander(t["sec_ident"], expanded=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                order_number = st.text_input(t["order_no"], value="ORD-2026-001")
                report_number = st.text_input(t["rep_no"], value="REP-VDA-042")
            with col_b:
                insp_name = st.text_input(t["insp_name"], value="Jan Novák")
                filt_no = st.text_input(t["filt_no"], value="F-1024")
            with col_c:
                filt_lot = st.text_input(t["filt_lot"], value="BAT-999")
                profile_type = st.selectbox("Profil vyhodnocení", [ProfileType.VDA_19_1, ProfileType.INTERNAL_CUSTOM])

        with st.expander(t["sec_prep"], expanded=False):
            col_d, col_e = st.columns(2)
            with col_d:
                wetted_area = st.number_input(t["control_area"], min_value=0.0, value=1000.0)
                extraction_method = st.selectbox(t["ext_method"], ["Pressure-rinsing", "Ultrasonics", "Internal rinsing"])
            with col_e:
                wetted_volume = st.number_input(t["wetted_vol"], min_value=0.0, value=0.0)
                extraction_medium = st.selectbox(t["dissolving_fluid"], ["Testovací benzín", "Izopropanol (IPA)"])

        with st.expander(t["sec_grav"], expanded=False):
            col_g1, col_g2 = st.columns(2)
            with col_g1: residual_mass = st.number_input(t["resid_mass"], min_value=0.0, value=0.4200, format="%.4f")
            with col_g2: scale_readable_choice = st.selectbox(t["scale_readable"], ["±0.01 mg", "±0.1 mg"])

        with st.expander("Optická analýza částic a pokročilé parametry", expanded=False):
            st.caption("Detaily optického skeneru a validační brány (Slepá hodnota, Pokrytí filtru)")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1: blank_value_pct = st.number_input(t["blank_val"], value=2.0)
            with col_q2: declining_test_pct = st.number_input(t["decl_test"], value=5.0)
            with col_q3: filter_occupancy_pct = st.number_input(t["filt_occ"], value=3.0)
            pixel_resolution_ok = st.checkbox(t["pixel_res"], value=True)

        st.markdown(f"**Matice počtů částic podle velikostních tříd a typů**")
        vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
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
            with c1: st.markdown(f"**{s_class}**")
            with c2: st.caption(f"(Limit: {limit_val})")
            with c3: met_val = st.text_input(f"Kov {s_class}", value="", placeholder="0", label_visibility="collapsed")
            with c4: nonmet_val = st.text_input(f"Nekov {s_class}", value="", placeholder="0", label_visibility="collapsed")
            with c5: fib_val = st.text_input(f"Fib {s_class}", value="", placeholder="0", label_visibility="collapsed")
            matrix_inputs[s_class] = {"metallic": met_val, "non_metallic": nonmet_val, "fibers": fib_val}

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t["submit_eval"], type="primary", use_container_width=True):
            with st.spinner("Zpracovávám data a generuji protokol..."):
                report = []
                failed, warning_triggered = False, False
                if gravimetry_limit_db and residual_mass > gravimetry_limit_db:
                    failed = True
                    st.toast(f"Varování: Gravimetrie překročena ({residual_mass} > {gravimetry_limit_db})", icon="⚠️")

                valid_matrix_totals, codes_for_ccc = {}, {}
                for s_class in vda_classes:
                    vals = matrix_inputs[s_class]
                    kov_count = int(vals["metallic"]) if vals["metallic"].strip() else 0
                    nekov_count = int(vals["non_metallic"]) if vals["non_metallic"].strip() else 0
                    fib_count = int(vals["fibers"]) if vals["fibers"].strip() else 0
                    
                    total_particles = kov_count + nekov_count + fib_count
                    calc_code_level = calculate_vda_code_level(total_particles, wetted_area)
                    
                    valid_matrix_totals[s_class] = int(calc_code_level)
                    codes_for_ccc[s_class] = calc_code_level
                    max_alw = int(db_limits_dict.get(s_class, db_limits_dict.get(f"{s_class}_kov", fallback_test_limits.get(s_class, 0))))
                    
                    if profile_type == ProfileType.VDA_19_1:
                        num_calc = int(calc_code_level) if calc_code_level != '00' else 0
                        status = "specifikace nesplněna" if num_calc > max_alw else "specifikace splněna"
                        if status == "specifikace nesplněna": failed = True
                        elif max_alw > 0 and num_calc >= max_alw: warning_triggered = True; status = "VAROVÁNÍ"

                    report.append({
                        "Velikostní třída": s_class, "Kovové": kov_count, "Nekovové": nekov_count,
                        "Vlákna": fib_count, "Počet částic": total_particles,
                        "Povolený limit": str(max_alw), "Naměřená úroveň": calc_code_level, "Stav": status,
                    })

                ref_unit_char = "A"
                auto_ccc = generate_ccc_string(codes_for_ccc, ref_unit_char)
                conformity_text = "specifikace nesplněna" if failed else ("VAROVÁNÍ" if warning_triggered else "specifikace splněna")

                report_df = pd.DataFrame(report)

                # Uložení do DB
                cur = conn.cursor()
                cur.execute("INSERT INTO inspections (component_id, standard_id, inspector_name, filter_number, filter_lot_number, entered_ccc_string, evaluation_result, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;", (c_id, std_id, insp_name, filt_no, filt_lot, auto_ccc, conformity_text, ""))
                ins_id = cur.fetchone()[0]
                for s_class, code_lvl in valid_matrix_totals.items():
                    cur.execute("INSERT INTO inspection_details (inspection_id, size_class, cleanliness_level) VALUES (%s, %s, %s);", (ins_id, s_class, code_lvl))
                conn.commit()
                cur.close()

                meta_info_dict = {
                    "order_no": order_number, "report_no": report_number, "customer": "-", "contact": "-", 
                    "test_ordered": "-", "reason_test": "-", "comp_name": comp_name, "std_name": std_name, 
                    "filter_no": filt_no, "filter_lot": filt_lot, "wetted_area": wetted_area, 
                    "ext_method": extraction_method, "dissolving_fluid": extraction_medium, 
                    "filt_mat": "-", "filt_pore": "-", "inspector_name": insp_name, "ccc_string": auto_ccc
                }
                
                pdf_data = create_pdf_report(meta_info_dict, report_df, conformity_text, failed, "", {"residual_mass": residual_mass, "gravimetry_limit": gravimetry_limit_db, "scale_readable": scale_readable_choice})
                
                st.session_state.eval_success = True
                st.session_state.generated_pdf = pdf_data
                st.session_state.eval_message = conformity_text
                st.session_state.generated_ccc = auto_ccc
                st.session_state.eval_failed = failed
                st.session_state.eval_report_df = report_df
                st.session_state.filt_no_for_pdf = filt_no
                st.rerun()

def show_history(conn):
    section(t["nav"][2])
    try:
        history_df = pd.read_sql('''
            SELECT i.inspection_date AS "Datum", c.part_number AS "Číslo dílu", c.name AS "Název dílu",
                COALESCE(cs.norm_name, '-') AS "Norma", i.inspector_name AS "Technik", i.filter_number AS "Filtr", 
                i.entered_ccc_string AS "CCC kód", i.evaluation_result AS "Výsledek"
            FROM inspections i JOIN components c ON i.component_id = c.id 
            LEFT JOIN customer_standards cs ON i.standard_id = cs.id ORDER BY i.inspection_date DESC;
        ''', conn)
        if not history_df.empty:
            st.dataframe(status_table_style(history_df, status_col="Výsledek"), use_container_width=True, hide_index=True)
        else:
            st.info("Zatím nejsou uložena žádná vyhodnocení.")
    except Exception as err:
        st.error(f"Chyba načítání historie: {err}")

if DB_PASSWORD:
    conn = get_db_connection()
    if conn:
        page_header(t["title"], t.get("subtitle", "Komplexní analýza čistoty a CCC kódování"))
        
        if "active_tab" not in st.session_state: st.session_state.active_tab = "Home"

        if st.session_state.active_tab != "Home":
            if st.button("← Zpět na hlavní menu"):
                st.session_state.active_tab = "Home"
                st.rerun()

        if st.session_state.active_tab == "Home":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### Zápis z reportu")
                st.caption("Zadání dat z reportu, porovnání s normou a generování PDF.")
                if st.button("Přejít na vyhodnocení", use_container_width=True, type="primary"):
                    st.session_state.active_tab = t["nav"][0]; st.rerun()
            with col2:
                st.markdown("### Správa norem")
                st.caption("Nastavení podnikových a zákaznických limitů.")
                if st.button("Přejít na normy", use_container_width=True):
                    st.session_state.active_tab = t["nav"][1]; st.rerun()
            with col3:
                st.markdown("### Historie měření")
                st.caption("Přehled uložených protokolů z databáze.")
                if st.button("Přejít na historii", use_container_width=True):
                    st.session_state.active_tab = t["nav"][2]; st.rerun()
        elif st.session_state.active_tab == t["nav"][0]:
            show_evaluation_form(conn)
        elif st.session_state.active_tab == t["nav"][2]:
            show_history(conn)
        conn.close()
else:
    st.info("Zadejte heslo k databázi v levém panelu.")

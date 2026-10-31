import datetime
import io
import math
import os
import uuid
from enum import Enum
import pandas as pd
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
        "nav": ["Zápis a vyhodnocení z reportu", "Správa norem (Limity)", "Přehled historie měření"],
        "sec_ident": "1. General Information & Inspected Object (VDA 19.1)",
        "sec_prep": "2. Preparatory steps & Extraction",
        "sec_filt": "3. Filtration & Drying",
        "sec_grav": "4. Gravimetrická analýza – Zbytková hmotnost M",
        "sec_opt": "5. Light-optical analysis & Particle size distribution (B až N)",
        "sec_qual": "6. Kvalitativní charakteristiky a Validační brány",
        "sec_adv": "7. Pokročilé vyhodnotitelné parametry",
        "sec_hard": "8. Hard-Stop parametry (Interní norma)",
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
        "date_removed": "Date removed (Datum odběru)",
        "time_removed": "Time removed (Čas odběru)",
        "removed_from": "Removed from (Odebráno z)",
        "cond_delivery": "Condition on delivery (Stav při dodání)",
        "lot_size": "Inspection lot size (Velikost dávky)",
        "control_area": "Control area Ac [cm²]",
        "wetted_vol": "Wetted volume Vc [cm³]",
        "prep_steps": "Preparatory steps (Přípravné kroky)",
        "ext_scope": "Scope of extraction (Rozsah extrakce)",
        "test_env": "Test environment (Zkušební prostředí)",
        "ext_method": "Extraction method (Metoda extrakce)",
        "dissolving_fluid": "Dissolving fluid (Rozpouštěcí médium)",
        "filt_manuf": "Filter Manufacturer",
        "filt_type": "Filter Type",
        "filt_mat": "Filter material (Materiál filtru)",
        "filt_pore": "Pore size (Velikost pórů µm)",
        "drying_params": "Drying Manufacturer / Model / Temp",
        "resid_mass": "Zbytková hmotnost M z protokolu vah [mg]",
        "fibers": "Vlákna (Fibers)",
        "blank_val": "Slepá hodnota [% z limitu]",
        "met_ref": "Kovové lesklé částice",
        "decl_test": "Klesající zkouška / Recovery [%]",
        "met_nonref": "Kovové nelesklé částice",
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
        "nav": ["Report Evaluation & Entry", "Standards & Limits Management", "Inspection History"],
        "sec_ident": "1. General Information & Inspected Object (VDA 19.1)",
        "sec_prep": "2. Preparatory steps & Extraction",
        "sec_filt": "3. Filtration & Drying",
        "sec_grav": "4. Gravimetric Analysis – Residual Mass M",
        "sec_opt": "5. Light-optical analysis & Particle size distribution (B to N)",
        "sec_qual": "6. Qualitative Characteristics & Validation Gates",
        "sec_adv": "7. Advanced Evaluation Parameters",
        "sec_hard": "8. Hard-Stop Parameters (Internal Standard)",
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
        "date_removed": "Date removed",
        "time_removed": "Time removed",
        "removed_from": "Removed from",
        "cond_delivery": "Condition on delivery",
        "lot_size": "Inspection lot size",
        "control_area": "Control area Ac [cm²]",
        "wetted_vol": "Wetted volume Vc [cm³]",
        "prep_steps": "Preparatory steps",
        "ext_scope": "Scope of extraction",
        "test_env": "Test environment",
        "ext_method": "Extraction method",
        "dissolving_fluid": "Dissolving fluid",
        "filt_manuf": "Filter Manufacturer",
        "filt_type": "Filter Type",
        "filt_mat": "Filter material",
        "filt_pore": "Pore size [µm]",
        "drying_params": "Drying Manufacturer / Model / Temp",
        "resid_mass": "Residual Mass M from Scale [mg]",
        "fibers": "Fibers",
        "blank_val": "Blank Value [% of limit]",
        "met_ref": "Metallic Reflective Particles",
        "decl_test": "Declining Test / Recovery [%]",
        "met_nonref": "Metallic Non-Reflective / Other Particles",
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


class ProfileType(str, Enum):
    VDA_19_1 = "VDA 19.1"
    INTERNAL_CUSTOM = "Interní norma (Custom)"


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


def create_pdf_report(
    meta_info, report_df, conformity_text, failed, note, fibers_count,
    metallic_ref_count, metallic_nonref_count, grav_data, uncertainty_info=None,
    advanced_data=None
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )

    font_name = "Times-Roman"
    font_name_bold = "Times-Bold"
    try:
        if os.path.exists("cmr10.ttf"):
            pdfmetrics.registerFont(TTFont('ComputerModern', 'cmr10.ttf'))
            pdfmetrics.registerFont(TTFont('ComputerModern-Bold', 'cmbx10.ttf' if os.path.exists('cmbx10.ttf') else 'cmr10.ttf'))
            font_name = "ComputerModern"
            font_name_bold = "ComputerModern-Bold"
    except:
        pass

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", fontName=font_name_bold, fontSize=12, leading=15, textColor=colors.HexColor("#111827"), alignment=1, spaceAfter=3)
    subtitle_style = ParagraphStyle("DocSubtitle", fontName=font_name, fontSize=8, leading=10, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=8)
    cell_style = ParagraphStyle("TableCell", fontName=font_name, fontSize=7.5, leading=10, textColor=colors.HexColor("#1f2937"))
    cell_bold = ParagraphStyle("TableCellBold", fontName=font_name_bold, fontSize=7.5, leading=10, textColor=colors.HexColor("#111827"))
    cell_header = ParagraphStyle("TableHeader", fontName=font_name_bold, fontSize=7.5, leading=10, textColor=colors.whitesmoke)
    ccc_style = ParagraphStyle("CCCStyle", fontName=font_name_bold, fontSize=9, leading=12, textColor=colors.HexColor("#1e3a8a"), alignment=1)

    elements = [
        Paragraph("INSPECTION REPORT: CLEANLINESS INSPECTION AS PER VDA 19.1 (2025)", title_style),
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
        [Paragraph("<b>Filter material / pore:</b>", cell_style), Paragraph(f"{meta_info.get('filt_mat', '-')}, {meta_info.get('filt_pore', '-')} µm", cell_style), Paragraph("<b>Datum vyhodnoceni:</b>", cell_style), Paragraph(current_date, cell_style)],
    ]

    meta_table = Table(meta_data, colWidths=[110, 165, 100, 179])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 6))

    ccc_string = meta_info.get('ccc_string', 'CCC neuveden')
    ccc_table = Table([[Paragraph(f"<b>CCC kód:</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]], colWidths=[554], rowHeights=[22])
    ccc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ])
    )
    elements.append(ccc_table)
    elements.append(Spacer(1, 6))

    if failed:
        res_color = colors.HexColor("#fee2e2")
        res_text_color = colors.HexColor("#991b1b")
    else:
        res_color = colors.HexColor("#d1fae5")
        res_text_color = colors.HexColor("#065f46")

    res_style = ParagraphStyle("ResText", fontName=font_name_bold, fontSize=8.5, leading=11, textColor=res_text_color, alignment=1)
    res_table = Table([[Paragraph(f"<b>VYSLEDEK POSOUZENI / EVALUATION RESULT: {conformity_text.upper()}</b>", res_style)]], colWidths=[554], rowHeights=[20])
    res_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), res_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, res_text_color),
        ])
    )
    elements.append(res_table)
    elements.append(Spacer(1, 6))

    if uncertainty_info:
        unc_text = Paragraph(f"<b>Nejistota mereni (k=2, 95%):</b> Kombinovana: {uncertainty_info['combined_pct']}% | Rozsirena: {uncertainty_info['expanded_pct']}%", cell_style)
        elements.append(unc_text)
        elements.append(Spacer(1, 5))

    # --- GRAVIMETRIE ---
    res_mass_val = grav_data.get('residual_mass', 0.0) if grav_data else 0.0
    grav_limit_val = grav_data.get('gravimetry_limit', 0.50) if grav_data else 0.50
    grav_status = "specifikace nesplněna" if res_mass_val > grav_limit_val else "specifikace splněna"
    grav_status_html = '<font color="#991b1b"><b>specifikace nesplněna</b></font>' if grav_status == "specifikace nesplněna" else '<font color="#065f46"><b>specifikace splněna</b></font>'

    grav_table_data = [
        [Paragraph("<b>Gravimetrická analýza (Zbytková hmotnost M)</b>", cell_header), Paragraph("<b>Limit / Hodnota</b>", cell_header), Paragraph("<b>Stav / Status</b>", cell_header)],
        [Paragraph("Zbytková hmotnost M z protokolu vah", cell_style), Paragraph(f"{res_mass_val:.4f} mg", cell_style), Paragraph("-", cell_style)],
        [Paragraph("Max. povolená zbytková hmotnost (Limit normy)", cell_style), Paragraph(f"{grav_limit_val:.4f} mg", cell_style), Paragraph(grav_status_html, cell_style)],
    ]
    grav_table = Table(grav_table_data, colWidths=[254, 150, 150])
    grav_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(grav_table)
    elements.append(Spacer(1, 6))

    # --- OPTICKÁ ANALÝZA ---
    table_data = [[
        Paragraph("<b>Velikostni trida</b>", cell_header),
        Paragraph("<b>Rozsah velikosti</b>", cell_header),
        Paragraph("<b>Max. povoleny limit</b>", cell_header),
        Paragraph("<b>Namereno z reportu</b>", cell_header),
        Paragraph("<b>Stav / Status</b>", cell_header),
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
                '<font color="#065f46"><b>specifikace splněna</b></font>' if status in ["specifikace splněna", "OK"] else
                ('<font color="#991b1b"><b>specifikace nesplněna</b></font>' if status in ["specifikace nesplněna", "NOK"] else '<font color="#b45309"><b>VAROVÁNÍ</b></font>')
            )

            table_data.append([
                Paragraph(s_class, cell_bold), Paragraph(s_range, cell_style),
                Paragraph(str(row["Povolený limit"]), cell_style), Paragraph(str(row["Naměřená úroveň"]), cell_style),
                Paragraph(status_html, cell_style),
            ])

        t = Table(table_data, colWidths=[90, 134, 130, 100, 100])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ])
        )
        elements.append(t)
        elements.append(Spacer(1, 6))

    qual_data = [
        [Paragraph("<b>Kvalitativni charakteristiky z reportu (VDA 19.1)</b>", cell_header), Paragraph("<b>Zjistena hodnota</b>", cell_header)],
        [Paragraph("Vlakna (Fibers)", cell_style), Paragraph(str(fibers_count), cell_style)],
        [Paragraph("Kovove leskle castice (Metallic reflective)", cell_style), Paragraph(str(metallic_ref_count), cell_style)],
        [Paragraph("Kovove neleskle / ostatni castice (Non-reflective)", cell_style), Paragraph(str(metallic_nonref_count), cell_style)],
    ]

    if advanced_data:
        qual_data.append([Paragraph("Max. rozmer castice z reportu (L_max / Feret Max)", cell_style), Paragraph(f"{advanced_data.get('l_max', 0)} µm")])
        qual_data.append([Paragraph("Pomer stran (b/L threshold)", cell_style), Paragraph(str(advanced_data.get('aspect_ratio', '-')))])
        qual_data.append([Paragraph("Plosna hustota kontaminace (Specific Surface)", cell_style), Paragraph(f"{advanced_data.get('specific_surface', 0)} mg/m²")])
        qual_data.append([Paragraph("Ucinnost extrakce z protokolu (Recovery rate)", cell_style), Paragraph(f"{advanced_data.get('recovery_rate', 0)} %")])

    qual_table = Table(qual_data, colWidths=[354, 200])
    qual_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ])
    )
    elements.append(qual_table)

    if note:
        elements.append(Spacer(1, 6))
        note_table = Table([[Paragraph("<b>Poznamka k zaznamu:</b>", cell_bold)], [Paragraph(note, cell_style)]], colWidths=[554])
        elements.append(note_table)

    elements.append(Spacer(1, 8))
    sig_table = Table([[Paragraph(f"<b>Zaznam zapsal / overil (technik):</b> {meta_info.get('inspector_name', 'Jan Novák')}", cell_style)]], colWidths=[554])
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    # Vrátíme ihned byte strukturu pro bezpečné stahování
    return buffer.getvalue()


def show_home_screen():
    st.write("Vítejte v systému vyhodnocení technické čistoty dle VDA 19.1. Vyberte požadovanou sekci:")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### <span class='material-symbols-rounded'>description</span> Zápis z reportu", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 75px;'>Zadání dat z reportu, porovnání s normou a generování PDF protokolu.</div>", unsafe_allow_html=True)
        if st.button("Přejít na vyhodnocení", use_container_width=True, type="primary"):
            st.session_state.active_tab = t["nav"][0]
            st.rerun()
            
    with col2:
        st.markdown("### <span class='material-symbols-rounded'>tune</span> Správa norem", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 75px;'>Nastavení a úprava podnikových a zákaznických limitů pro jednotlivé díly.</div>", unsafe_allow_html=True)
        if st.button("Přejít na normy", use_container_width=True):
            st.session_state.active_tab = t["nav"][1]
            st.rerun()
            
    with col3:
        st.markdown("### <span class='material-symbols-rounded'>history</span> Historie měření", unsafe_allow_html=True)
        st.markdown("<div style='min-height: 75px;'>Přehled všech uložených vyhodnocení a protokolů z databáze.</div>", unsafe_allow_html=True)
        if st.button("Přejít na historii", use_container_width=True):
            st.session_state.active_tab = t["nav"][2]
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
        try:
            components_df = pd.read_sql("SELECT id, part_number, name FROM components", conn)
        except Exception as e:
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

            st.markdown("**1. Gravimetrický limit**")
            gravimetry_limit_input = st.number_input("Max. povolená zbytková hmotnost (mg)", min_value=0.0, value=0.50, step=0.1)

            st.markdown("---")
            st.markdown("### 2. Nastavení kvalitativních a pokročilých limitů (nepovinné)")
            st.caption("Zadejte maximální povolené limity pro jednotlivé parametry:")

            adv_limit_definitions = [
                ("FIBERS", "Max. počet vláken (Fibers)", ""),
                ("METALLIC", "Max. kovových částic (Metallic)", ""),
                ("L_MAX", "Max. rozměr částice L_max [µm]", ""),
                ("B_L_RATIO", "Limitní poměr b/L", ""),
                ("SPEC_SURFACE", "Max. plošná hustota kontaminace [mg/m²]", "")
            ]

            adv_limit_inputs = {}
            for key, label_text, default_val in adv_limit_definitions:
                col_a1, col_a2, col_a3 = st.columns([1, 3, 3])
                with col_a1:
                    st.markdown(f"**{key}**")
                with col_a2:
                    st.caption(label_text)
                with col_a3:
                    adv_limit_inputs[key] = st.text_input(
                        f"Limit {key}",
                        value=default_val,
                        key=f"add_adv_{key}",
                        label_visibility="collapsed",
                        placeholder="Zadejte limit..."
                    )

            st.markdown("---")
            st.markdown("### 3. Nastavení limitů pro velikostní frakce (CCC kódové úrovně)")
            st.caption("Do políček níže zadejte povolený **limit** (max. úroveň) pro každou velikostní třídu:")
            
            default_test_limits = {"B": "15", "C": "12", "D": "10", "E": "8", "F": "5", "G": "3", "H": "2", "I": "1", "J": "0", "K": "0", "L": "0", "M": "0", "N": "0"}
            
            limit_inputs = {}
            for s_class in vda_classes:
                col_c1, col_c2, col_c3 = st.columns([1, 3, 3])
                with col_c1:
                    st.markdown(f"**Třída {s_class}**")
                with col_c2:
                    st.caption(f"Rozsah: {size_ranges_desc.get(s_class, '')}")
                with col_c3:
                    limit_inputs[s_class] = st.text_input(
                        f"Limit {s_class}",
                        value=default_test_limits.get(s_class, ""),
                        key=f"add_{s_class}",
                        label_visibility="collapsed",
                        placeholder="Zadejte limit..."
                    )

            std_note = st.text_area("Poznámka k normě", value="Testovací norma A s výchozími limity")
            submit_new_std = st.form_submit_button("Vytvořit a uložit normu", type="primary")

            if submit_new_std:
                if not norm_name:
                    st.error("Název normy je povinný.")
                else:
                    try:
                        cur = conn.cursor()
                        inserted_any = False
                        
                        all_limits_to_save = limit_inputs.copy()
                        for k, val_str in adv_limit_inputs.items():
                            if val_str.strip():
                                all_limits_to_save[k] = val_str

                        for s_class, limit_val in all_limits_to_save.items():
                            if limit_val.strip() and limit_val.strip() != "-":
                                new_row_id = str(uuid.uuid4())
                                cur.execute(
                                    "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    (new_row_id, selected_comp_id, norm_name, s_class, float(limit_val), std_note, gravimetry_limit_input if gravimetry_limit_input > 0 else None)
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
                
                curr_note = existing_limits_df['note'].iloc[0] if not existing_limits_df.empty and existing_limits_df['note'].notna().any() else ""
                curr_grav = existing_limits_df['gravimetry_limit_mg'].iloc[0] if not existing_limits_df.empty and existing_limits_df['gravimetry_limit_mg'].notna().any() else 0.0
                curr_norm_name = existing_limits_df['norm_name'].iloc[0]
                curr_comp_id = existing_limits_df['component_id'].iloc[0]

                current_class_limits = {}
                for _, row in existing_limits_df.iterrows():
                    val = row['max_allowed_level']
                    current_class_limits[row['size_class']] = str(int(val)) if val.is_integer() else str(val)

                st.markdown(f"**Upravit parametry normy**")
                with st.form("edit_standard_form"):
                    edit_norm_name = st.text_input("Název normy", value=curr_norm_name)
                    
                    st.markdown("**1. Gravimetrický limit**")
                    edit_gravimetry = st.number_input("Max. povolená hmotnost gravimetrie (mg)", min_value=0.0, value=float(curr_grav), step=0.1)
                    
                    st.markdown("---")
                    st.markdown("### 2. Úprava kvalitativních a pokročilých limitů (nepovinné)")
                    st.caption("Upravte maximální povolené limity pro jednotlivé parametry:")

                    adv_limit_definitions = [
                        ("FIBERS", "Max. počet vláken (Fibers)", ""),
                        ("METALLIC", "Max. kovových částic (Metallic)", ""),
                        ("L_MAX", "Max. rozměr částice L_max [µm]", ""),
                        ("B_L_RATIO", "Limitní poměr b/L", ""),
                        ("SPEC_SURFACE", "Max. plošná hustota kontaminace [mg/m²]", "")
                    ]

                    edit_adv_inputs = {}
                    for key, label_text, _ in adv_limit_definitions:
                        col_e1, col_e2, col_e3 = st.columns([1, 3, 3])
                        with col_e1:
                            st.markdown(f"**{key}**")
                        with col_e2:
                            st.caption(label_text)
                        with col_e3:
                            edit_adv_inputs[key] = st.text_input(
                                f"Edit Limit {key}",
                                value=current_class_limits.get(key, ""),
                                key=f"edit_adv_{key}",
                                label_visibility="collapsed",
                                placeholder="Zadejte limit..."
                            )

                    st.markdown("---")
                    st.markdown("### 3. Úprava limitů pro velikostní frakce (CCC kódové úrovně)")
                    st.caption("Do políček níže zadejte povolený **limit** (max. úroveň) pro každou velikostní třídu:")

                    edit_inputs = {}
                    for s_class in vda_classes:
                        col_c1, col_c2, col_c3 = st.columns([1, 3, 3])
                        with col_c1:
                            st.markdown(f"**Třída {s_class}**")
                        with col_c2:
                            st.caption(f"Rozsah: {size_ranges_desc.get(s_class, '')}")
                        with col_c3:
                            edit_inputs[s_class] = st.text_input(
                                f"Edit Limit {s_class}",
                                value=current_class_limits.get(s_class, ""),
                                key=f"edit_{s_class}",
                                label_visibility="collapsed",
                                placeholder="Zadejte limit..."
                            )

                    edit_note = st.text_area("Poznámka", value=curr_note)
                    
                    col_save, col_del = st.columns([1, 4])
                    with col_save:
                        submit_edit = st.form_submit_button("Uložit úpravy", type="primary")
                    with col_del:
                        submit_delete = st.form_submit_button("Odstranit normu")

                    if submit_edit:
                        try:
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM customer_standards WHERE norm_name = '{curr_norm_name}'")
                            
                            all_edit_limits = edit_inputs.copy()
                            for k, val_str in edit_adv_inputs.items():
                                if val_str.strip():
                                    all_edit_limits[k] = val_str

                            for s_class, limit_val in all_edit_limits.items():
                                if limit_val.strip() and limit_val.strip() != "-":
                                    new_row_id = str(uuid.uuid4())
                                    cur.execute(
                                        "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (new_row_id, curr_comp_id, edit_norm_name, s_class, float(limit_val), edit_note, edit_gravimetry if edit_gravimetry > 0 else None)
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
    
    # Inicializace stavu pro řízení zobrazení (přechod formulář -> hotové PDF)
    if "eval_success" not in st.session_state:
        st.session_state.eval_success = False

    if st.session_state.eval_success:
        # POKUD BYLO VYHODNOCENÍ ÚSPĚŠNÉ, ZOBRAZÍME ROVNOU VÝSLEDKY A PDF BEZ FORMULÁŘE
        st.subheader(t["res_title"])
        st.info(f"**CCC kód:** {st.session_state.generated_ccc}")
        if st.session_state.eval_failed:
            st.error(f"Posouzení: **{st.session_state.eval_message.upper()}**")
        else:
            st.success(f"Posouzení: **{st.session_state.eval_message.upper()}**")
        
        if not st.session_state.eval_report_df.empty:
            st.dataframe(st.session_state.eval_report_df, use_container_width=True)

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
        # Ukončíme funkci tady, aby se samotný formulář nevykresloval
        return

    # ------------------ ZAČÁTEK FORMULÁŘE (Interaktivní) ------------------
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
                    val = row['max_allowed_level']
                    if str(row['size_class']).strip() in ["FIBERS", "METALLIC", "L_MAX", "B_L_RATIO", "SPEC_SURFACE"]:
                        db_limits_dict[str(row['size_class']).strip()] = float(val)
                    else:
                        db_limits_dict[str(row['size_class']).strip()] = int(val)
            except Exception as e:
                pass

        limit_fibers = db_limits_dict.get('FIBERS', None)
        limit_metallic = db_limits_dict.get('METALLIC', None)
        limit_lmax = db_limits_dict.get('L_MAX', None)
        limit_bl = db_limits_dict.get('B_L_RATIO', None)
        limit_surface = db_limits_dict.get('SPEC_SURFACE', None)

        fallback_test_limits = {"B": 15, "C": 12, "D": 10, "E": 8, "F": 5, "G": 3, "H": 2, "I": 1, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0}
        for k, v in fallback_test_limits.items():
            if k not in db_limits_dict:
                db_limits_dict[k] = v

        st.markdown("---")

        # --- SEKCE 1: General Information ---
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
        
        # --- SEKCE 2 & 3: Preparatory steps ---
        col_h1, col_h2 = st.columns([5, 1])
        with col_h1:
            st.subheader(t["sec_prep"])
        with col_h2:
            enable_part_ext = st.toggle("Aktivní sekce", value=True, key="chk_p2")

        col_d, col_e, col_f = st.columns(3)
        with col_d:
            wetted_area = st.number_input(t["control_area"], min_value=0.0, value=1000.0, disabled=not enable_part_ext)
            extraction_method = st.selectbox(t["ext_method"], ["Pressure-rinsing", "Ultrasonics", "Internal rinsing", "Agitation"], disabled=not enable_part_ext)
        with col_e:
            wetted_volume = st.number_input(t["wetted_vol"], min_value=0.0, value=0.0, disabled=not enable_part_ext)
            extraction_medium = st.text_input(t["dissolving_fluid"], value="Testovací benzín", disabled=not enable_part_ext)
        with col_f:
            filter_material = st.text_input(t["filt_mat"], value="PET (polyester)", disabled=not enable_part_ext)
            filter_pore_size = st.number_input(t["filt_pore"], min_value=0.1, value=5.0, disabled=not enable_part_ext)

        st.markdown("---")

        # --- SEKCE 4: Gravimetrická analýza ---
        col_h3, col_h4 = st.columns([5, 1])
        with col_h3:
            st.subheader(t["sec_grav"])
        with col_h4:
            enable_grav = st.toggle("Aktivní sekce", value=True, key="chk_p3")

        if gravimetry_limit_db and enable_grav:
            st.info(f"Očekávaný limit normy pro gravimetrii: **{gravimetry_limit_db} mg**")
        
        col_g, _ = st.columns([1, 2])
        with col_g:
            residual_mass = st.number_input(t["resid_mass"], min_value=0.0, value=0.4200, format="%.4f", step=0.1, disabled=not enable_grav)

        st.markdown("---")

        # --- SEKCE 5: Optická analýza (B až N pod sebou) ---
        col_h5, col_h6 = st.columns([5, 1])
        with col_h5:
            st.subheader(t["sec_opt"])
        with col_h6:
            enable_opt = st.toggle("Aktivní sekce", value=True, key="chk_p4")

        vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
        size_ranges_desc = {
            "B": "5 µm - 15 µm", "C": "15 µm - 25 µm", "D": "25 µm - 50 µm",
            "E": "50 µm - 100 µm", "F": "100 µm - 150 µm", "G": "150 µm - 200 µm",
            "H": "200 µm - 400 µm", "I": "400 µm - 600 µm", "J": "600 µm - 1000 µm",
            "K": "1000 µm - 1500 µm", "L": "1500 µm - 2000 µm", "M": "2000 µm - 3000 µm",
            "N": "> 3000 µm",
        }
        entered_levels = {}

        for s_class in vda_classes:
            limit_val = db_limits_dict.get(s_class, 0)
            col_c1, col_c2, col_c3 = st.columns([1, 3, 3])
            with col_c1:
                st.markdown(f"**Třída {s_class}**")
            with col_c2:
                st.caption(f"Rozsah: {size_ranges_desc.get(s_class, '')} | Limit: {limit_val}")
            with col_c3:
                raw_input = st.text_input(f"Úroveň {s_class}", value="", placeholder="-", key=f"cls_{s_class}", label_visibility="collapsed", disabled=not enable_opt)
                entered_levels[s_class] = raw_input
            
            # LIVE validace přímo během psaní (funguje díky odstranění st.form)
            if enable_opt and raw_input.strip() and raw_input.strip() != "-":
                try:
                    val_num = int(raw_input.strip())
                    if val_num > limit_val:
                        st.markdown(f"<p style='color:red; font-size:11px; margin-top:-10px;'>Limit překročen! (Max: {limit_val})</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:green; font-size:11px; margin-top:-10px;'>V toleranci (Max: {limit_val})</p>", unsafe_allow_html=True)
                except ValueError:
                    pass

        st.markdown("---")

        # --- SEKCE 6: Kvalitativní charakteristiky ---
        st.subheader(t["sec_qual"])
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            fibers_count = st.number_input(t["fibers"], min_value=0, value=9, step=1, help=f"Limit z normy: {limit_fibers}" if limit_fibers is not None else None)
            blank_value_pct = st.number_input(t["blank_val"], min_value=0.0, value=2.0, step=0.1)
        with col_q2:
            metallic_ref_count = st.number_input(t["met_ref"], min_value=0, value=19, step=1, help=f"Limit z normy: {limit_metallic}" if limit_metallic is not None else None)
            declining_test_pct = st.number_input(t["decl_test"], min_value=0.0, value=5.0, step=0.5)
        with col_q3:
            metallic_nonref_count = st.number_input(t["met_nonref"], min_value=0, value=24, step=1)
            filter_occupancy_pct = st.number_input(t["filt_occ"], min_value=0.0, value=3.0, step=0.5)

        st.markdown("---")

        # --- SEKCE 7: Pokročilé metriky ---
        col_h7, col_h8 = st.columns([5, 1])
        with col_h7:
            st.subheader(t["sec_adv"])
        with col_h8:
            enable_adv = st.toggle("Aktivní sekce", value=True, key="chk_p6")
        
        l_max_val, aspect_ratio_val, metallic_percentage, recovery_rate_val, specific_surface_val, cleanliness_class_code = 450.0, 0.1, 2.5, 92.5, 0.0, ""
        col_ad1, col_ad2, col_ad3 = st.columns(3)
        with col_ad1:
            l_max_val = st.number_input(t["l_max"], min_value=0.0, value=450.0, step=10.0, disabled=not enable_adv, help=f"Limit z normy: {limit_lmax} µm" if limit_lmax is not None else None)
            aspect_ratio_val = st.number_input(t["aspect_ratio"], min_value=0.0, max_value=10.0, value=0.1, step=0.01, disabled=not enable_adv, help=f"Limit z normy: {limit_bl}" if limit_bl is not None else None)
        with col_ad2:
            metallic_percentage = st.number_input(t["metallic_ratio"], min_value=0.0, max_value=100.0, value=2.5, step=0.1, disabled=not enable_adv)
            recovery_rate_val = st.number_input(t["recovery_rate"], min_value=0.0, max_value=100.0, value=92.5, step=0.5, disabled=not enable_adv)
        with col_ad3:
            specific_surface_val = st.number_input(t["specific_surface"], min_value=0.0, value=round(residual_mass / (wetted_area / 10000.0) if wetted_area > 0 else 0.0, 2), step=0.1, disabled=not enable_adv, help=f"Limit z normy: {limit_surface} mg/m²" if limit_surface is not None else None)
            cleanliness_class_code = st.text_input("CCC Code string", value="CCC A(B 00/C 12/D15/E3/G34)", disabled=not enable_adv)

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
        
        # Běžné interaktivní tlačítko místo form_submit
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
                    ccc_parts, valid_levels = [], {}
                    if enable_opt:
                        for s_class in vda_classes:
                            a_level_str = str(entered_levels.get(s_class, "")).strip()
                            if a_level_str and a_level_str != "-":
                                val_int = int(a_level_str)
                                ccc_parts.append(f"{s_class} {a_level_str}")
                                valid_levels[s_class] = val_int

                    generated_ccc_string = cleanliness_class_code if cleanliness_class_code else (f"CCC {ref_unit_char}({' / '.join(ccc_parts)})" if valid_levels else "CCC neuveden")

                    failed, report = False, []
                    warning_triggered = False
                    
                    if enable_grav and gravimetry_limit_db and residual_mass > gravimetry_limit_db:
                        failed = True
                        st.error(f"Gravimetrie překročena: Naměřená zbytková hmotnost {residual_mass:.4f} mg (Limit normy: {gravimetry_limit_db} mg)")

                    if limit_fibers is not None and fibers_count > limit_fibers:
                        failed = True
                        st.error(f"Překročen limit pro Vlákna: naměřeno {fibers_count} (Limit normy: {limit_fibers})")
                        
                    if limit_metallic is not None and metallic_ref_count > limit_metallic:
                        failed = True
                        st.error(f"Překročen limit pro Kovové částice: naměřeno {metallic_ref_count} (Limit normy: {limit_metallic})")
                        
                    if enable_adv:
                        if limit_lmax is not None and l_max_val > limit_lmax:
                            failed = True
                            st.error(f"Překročen limit pro L_max: naměřeno {l_max_val} µm (Limit normy: {limit_lmax} µm)")
                        
                        if limit_bl is not None and aspect_ratio_val > limit_bl:
                            failed = True
                            st.error(f"Překročen limit pro poměr b/L: naměřeno {aspect_ratio_val} (Limit normy: {limit_bl})")
                            
                        if limit_surface is not None and specific_surface_val > limit_surface:
                            failed = True
                            st.error(f"Překročen limit pro plošnou hustotu kontaminace: naměřeno {specific_surface_val} mg/m² (Limit normy: {limit_surface} mg/m²)")

                    if enable_opt:
                        for s_class in vda_classes:
                            actual_val = valid_levels.get(s_class, 0)
                            max_alw = int(db_limits_dict.get(s_class, 0))
                            
                            if profile_type == ProfileType.VDA_19_1:
                                status = "specifikace nesplněna" if actual_val > max_alw else "specifikace splněna"
                                if status == "specifikace nesplněna":
                                    failed = True
                                else:
                                    if max_alw > 0 and actual_val >= max_alw * 0.8:
                                        status = "VAROVÁNÍ"
                                        warning_triggered = True
                                    else:
                                        status = "specifikace splněna"

                            report.append({
                                "Velikostní třída": s_class,
                                "Povolený limit": str(max_alw),
                                "Naměřená úroveň": actual_val,
                                "Stav": status,
                            })

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
                    if enable_opt:
                        for s_class, a_level in valid_levels.items():
                            cur.execute(
                                "INSERT INTO inspection_details (inspection_id, size_class, cleanliness_level) VALUES (%s, %s, %s);",
                                (ins_id, s_class, a_level),
                            )
                    conn.commit()
                    cur.close()

                    meta_info_dict = {
                        "order_no": order_number, "report_no": report_number, "customer": customer,
                        "contact": contact_person, "test_ordered": test_ordered, "reason_test": reason_test,
                        "comp_name": comp_name, "std_name": std_name, "filter_no": filt_no, "filter_lot": filt_lot,
                        "wetted_area": wetted_area, "ext_method": extraction_method, "filt_mat": filter_material,
                        "filt_pore": filter_pore_size, "inspector_name": insp_name, "ccc_string": generated_ccc_string
                    }
                    grav_data_dict = {"residual_mass": residual_mass, "gravimetry_limit": gravimetry_limit_db} if enable_grav else {"residual_mass": 0, "gravimetry_limit": None}
                    uncertainty_dict = calculate_measurement_uncertainty() if include_uncertainty else None
                    advanced_dict = {
                        "l_max": l_max_val, "aspect_ratio": aspect_ratio_val, "metallic_percentage": metallic_percentage,
                        "specific_surface": specific_surface_val, "recovery_rate": recovery_rate_val
                    } if enable_adv else None

                    pdf_data = create_pdf_report(
                        meta_info_dict, report_df, conformity_text, failed, note,
                        fibers_count, metallic_ref_count, metallic_nonref_count,
                        grav_data_dict, uncertainty_dict, advanced_dict
                    )
                    
                    # Uložení výsledků do session_state pro okamžité přepnutí pohledu
                    st.session_state.eval_success = True
                    st.session_state.generated_pdf = pdf_data
                    st.session_state.eval_message = conformity_text
                    st.session_state.generated_ccc = generated_ccc_string
                    st.session_state.eval_failed = failed
                    st.session_state.eval_report_df = report_df
                    st.session_state.filt_no_for_pdf = filt_no
                    
                    st.rerun() # Okamžitý refresh, ukáže se jen vyhodnocení


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

        conn.close()
else:
    st.info("Zadejte heslo k databázi v levém panelu. / Enter the database password in the sidebar.")

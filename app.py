import datetime
import io
import math
import uuid
from enum import Enum
import pandas as pd
import psycopg2
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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
    button[kind="secondary"]:has(div:contains("Nové vyhodnocení")),
    button[kind="secondary"]:has(div:contains("New Inspection")),
    div.stButton > button:has(div:contains("Nové vyhodnocení")),
    div.stButton > button:has(div:contains("New Inspection")) {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    div.stButton > button:has(div:contains("Nové vyhodnocení")):hover,
    div.stButton > button:has(div:contains("New Inspection")):hover {
        background-color: #b91c1c !important;
        border-color: #b91c1c !important;
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
        "sec_ident": "1. Identifikace reportu a zkušební podmínky",
        "sec_part": "2. Parametry dílu a extrakce (z protokolu)",
        "sec_grav": "3. Gravimetrická analýza – Zbytková hmotnost M (z protokolu vah)",
        "sec_opt": "4. Optická analýza – Naměřené třídy z optického reportu (B až N)",
        "sec_qual": "5. Kvalitativní charakteristiky a Validační brány z reportu",
        "sec_adv": "6. Pokročilé vyhodnotitelné parametry z reportu (VDA 19.1)",
        "sec_hard": "7. Hard-Stop parametry (Interní norma)",
        "order_no": "Číslo zakázky",
        "rep_no": "Číslo laboratorní zprávy / protokolu",
        "insp_name": "Jméno technika",
        "insp_type": "Typ zkoušky",
        "filt_no": "Číslo filtru",
        "filt_lot": "Šarže filtru",
        "profile": "Vyhodnocovací profil",
        "supply_cond": "Stav při dodání",
        "sample_size": "Kontrolní dávka (n)",
        "ref_unit": "Referenční jednotka",
        "wetted_area": "Smáčená plocha AC [cm²]",
        "ext_method": "Metoda extrakce",
        "wetted_vol": "Smáčený objem VC [cm³]",
        "ext_medium": "Extrakční médium",
        "filt_mat": "Materiál filtru",
        "filt_pore": "Velikost pórů [µm]",
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
        "l_max_desc": "Maximální délka největší detekované částice z reportu.",
        "aspect_ratio": "Prahová hodnota poměru stran (b/L)",
        "aspect_ratio_desc": "Poměr šířky a délky pro detekci třísek.",
        "metallic_ratio": "Podíl kovových částic [%]",
        "cleanliness_class": "Kód čistoty (ISO 16232 / CCC kód)",
        "specific_surface": "Plošná hustota kontaminace [mg/m²]",
        "recovery_rate": "Účinnost extrakce (Deklinační faktor / Recovery %)",
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
        "sec_ident": "1. Report Identification & Inspection Conditions",
        "sec_part": "2. Component & Extraction Parameters (from Protocol)",
        "sec_grav": "3. Gravimetric Analysis – Residual Mass M (from Scale Protocol)",
        "sec_opt": "4. Optical Analysis – Measured Classes from Optical Report (B to N)",
        "sec_qual": "5. Qualitative Characteristics & Validation Gates from Report",
        "sec_adv": "6. Advanced Evaluation Parameters from Report (VDA 19.1)",
        "sec_hard": "7. Hard-Stop Parameters (Internal Standard)",
        "order_no": "Order Number",
        "rep_no": "Report Number",
        "insp_name": "Inspector Name",
        "insp_type": "Inspection Type",
        "filt_no": "Filter Number",
        "filt_lot": "Filter Lot / Batch",
        "profile": "Evaluation Profile",
        "supply_cond": "Supply Condition",
        "sample_size": "Sample Size (n)",
        "ref_unit": "Reference Unit",
        "wetted_area": "Wetted Area AC [cm²]",
        "ext_method": "Extraction Method",
        "wetted_vol": "Wetted Volume VC [cm³]",
        "ext_medium": "Extraction Medium",
        "filt_mat": "Filter Material",
        "filt_pore": "Pore Size [µm]",
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
        "l_max_desc": "Maximum length of the largest detected particle from report.",
        "aspect_ratio": "Aspect Ratio Threshold (b/L)",
        "aspect_ratio_desc": "Width-to-length ratio.",
        "metallic_ratio": "Metallic Particles Share [%]",
        "cleanliness_class": "Cleanliness Class (ISO 16232 / CCC Code)",
        "specific_surface": "Specific Surface Contamination [mg/m²]",
        "recovery_rate": "Extraction Efficiency / Decline Factor (Recovery %)",
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


class ReferenceType(str, Enum):
    A = "A"
    V = "V"
    N = "N"


class ProfileType(str, Enum):
    VDA_19_1 = "VDA 19.1"
    INTERNAL_CUSTOM = "Interní norma (Custom)"


def count_to_ccc_level(count: float) -> int:
    if count <= 0:
        return 0
    if count <= 1:
        return 0
    level = math.ceil(math.log2(count))
    return min(max(level, 1), 24)


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
    comp_name, std_name, filter_no, filter_lot, inspector_name, ref_unit,
    ccc_string, report_df, conformity_text, failed, note, fibers_count,
    metallic_ref_count, metallic_nonref_count, grav_data, uncertainty_info=None,
    advanced_data=None
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )

    font_name = "Helvetica"
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", fontName=font_name, fontSize=13, leading=16, textColor=colors.HexColor("#111827"), alignment=1, spaceAfter=4)
    subtitle_style = ParagraphStyle("DocSubtitle", fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=10)
    cell_style = ParagraphStyle("TableCell", fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#1f2937"))
    cell_bold = ParagraphStyle("TableCellBold", fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#111827"))
    cell_header = ParagraphStyle("TableHeader", fontName=font_name, fontSize=8, leading=11, textColor=colors.whitesmoke)
    ccc_style = ParagraphStyle("CCCStyle", fontName=font_name, fontSize=9.5, leading=13, textColor=colors.HexColor("#1e3a8a"), alignment=1)

    elements = [
        Paragraph("SOUHRNNY PROTOKOL KONTROLY CISTOTY / CLEANLINESS REPORT EVALUATION", title_style),
        Paragraph("Porovnani namerenych hodnot z reportu s podnikovou normou (VDA 19.1 / ISO 16232)", subtitle_style),
    ]

    current_date = datetime.date.today().strftime("%d.%m.%Y")
    
    meta_data = [
        [Paragraph("<b>Oznaceni dilu:</b>", cell_style), Paragraph(comp_name, cell_style), Paragraph("<b>Datum vyhodnoceni:</b>", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("<b>Podnikova norma:</b>", cell_style), Paragraph(std_name, cell_style), Paragraph("<b>Zadal z reportu:</b>", cell_style), Paragraph(inspector_name, cell_style)],
        [Paragraph("<b>Cislo filtru:</b>", cell_style), Paragraph(filter_no, cell_style), Paragraph("<b>Sarze filtru:</b>", cell_style), Paragraph(filter_lot if filter_lot else "-", cell_style)],
        [Paragraph("<b>Referencni jednotka:</b>", cell_style), Paragraph(ref_unit, cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
    ]

    meta_table = Table(meta_data, colWidths=[110, 160, 100, 184])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    ccc_table = Table([[Paragraph(f"<b>CCC kod:</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]], colWidths=[554], rowHeights=[24])
    ccc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ])
    )
    elements.append(ccc_table)
    elements.append(Spacer(1, 8))

    if failed:
        res_color = colors.HexColor("#fee2e2")
        res_text_color = colors.HexColor("#991b1b")
    else:
        res_color = colors.HexColor("#d1fae5")
        res_text_color = colors.HexColor("#065f46")

    res_style = ParagraphStyle("ResText", fontName=font_name, fontSize=9, leading=12, textColor=res_text_color, alignment=1)
    res_table = Table([[Paragraph(f"<b>VYSLEDEK POSOUZENI / EVALUATION RESULT: {conformity_text.upper()}</b>", res_style)]], colWidths=[554], rowHeights=[22])
    res_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), res_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, res_text_color),
        ])
    )
    elements.append(res_table)
    elements.append(Spacer(1, 8))

    if uncertainty_info:
        unc_text = Paragraph(f"<b>Nejistota mereni (k=2, 95%):</b> Kombinovana: {uncertainty_info['combined_pct']}% | Rozsirena: {uncertainty_info['expanded_pct']}%", cell_style)
        elements.append(unc_text)
        elements.append(Spacer(1, 6))

    # --- SEKCE 3: GRAVIMETRICKÁ ANALÝZA ---
    res_mass_val = grav_data.get('residual_mass', 0.0) if grav_data else 0.0
    grav_limit_val = grav_data.get('gravimetry_limit', 0.50) if grav_data else 0.50
    grav_status = "NOK" if res_mass_val > grav_limit_val else "OK"
    grav_status_html = '<font color="#991b1b"><b>NOK</b></font>' if grav_status == "NOK" else '<font color="#065f46"><b>OK</b></font>'

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
    elements.append(Spacer(1, 8))

    # --- SEKCE 4: OPTICKÁ ANALÝZA ---
    table_data = [[
        Paragraph("<b>Velikostni trida</b>", cell_header),
        Paragraph("<b>Rozsah velikosti</b>", cell_header),
        Paragraph("<b>Max. povoleny limit</b>", cell_header),
        Paragraph("<b>Namereno z reportu</b>", cell_header),
        Paragraph("<b>Stav / Status</b>", cell_header),
    ]]

    size_ranges = {
        "B": "5 um - 15 um", "C": "15 um - 25 um", "D": "25 um - 50 um",
        "E": "50 um - 100 um", "F": "100 um - 150 um", "G": "150 um - 200 um",
        "H": "200 um - 400 um", "I": "400 um - 600 um", "J": "600 um - 1000 um",
        "K": "1000 um - 1500 um", "L": "1500 um - 2000 um", "M": "2000 um - 3000 um",
        "N": "> 3000 um",
    }

    if not report_df.empty:
        for _, row in report_df.iterrows():
            s_class = str(row["Velikostní třída"])
            s_range = size_ranges.get(s_class, "-")
            status = str(row["Stav"])
            status_html = (
                '<font color="#065f46"><b>OK</b></font>' if status in ["OK", "specifikace splněna"] else
                ('<font color="#991b1b"><b>NOK</b></font>' if status in ["NOK", "specifikace nesplněna"] else '<font color="#b45309"><b>VAROVANI</b></font>')
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
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        elements.append(t)
        elements.append(Spacer(1, 8))

    qual_data = [
        [Paragraph("<b>Kvalitativni charakteristiky z reportu (VDA 19.1)</b>", cell_header), Paragraph("<b>Zjistena hodnota</b>", cell_header)],
        [Paragraph("Vlakna (Fibers)", cell_style), Paragraph(str(fibers_count), cell_style)],
        [Paragraph("Kovove leskle castice (Metallic reflective)", cell_style), Paragraph(str(metallic_ref_count), cell_style)],
        [Paragraph("Kovove neleskle / ostatni castice (Non-reflective)", cell_style), Paragraph(str(metallic_nonref_count), cell_style)],
    ]

    if advanced_data:
        qual_data.append([Paragraph("Max. rozmer castice z reportu (L_max / Feret Max)", cell_style), Paragraph(f"{advanced_data.get('l_max', 0)} um")])
        qual_data.append([Paragraph("Pomer stran (b/L threshold)", cell_style), Paragraph(str(advanced_data.get('aspect_ratio', '-')))])
        qual_data.append([Paragraph("Plosna hustota kontaminace (Specific Surface)", cell_style), Paragraph(f"{advanced_data.get('specific_surface', 0)} mg/m^2")])
        qual_data.append([Paragraph("Ucinnost extrakce z protokolu (Recovery rate)", cell_style), Paragraph(f"{advanced_data.get('recovery_rate', 0)} %")])

    qual_table = Table(qual_data, colWidths=[354, 200])
    qual_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    elements.append(qual_table)

    if note:
        elements.append(Spacer(1, 8))
        note_table = Table([[Paragraph("<b>Poznamka k zaznamu:</b>", cell_bold)], [Paragraph(note, cell_style)]], colWidths=[554])
        elements.append(note_table)

    elements.append(Spacer(1, 10))
    sig_table = Table([[Paragraph(f"<b>Zaznam zapsal / overil (technik):</b> {inspector_name}", cell_style)]], colWidths=[554])
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def show_standards_management(conn):
    st.subheader(t["standards_title"])
    tab1, tab2 = st.tabs(["➕ Přidat novou podnikovou normu", "✏️ Editovat / Smazat stávající normu"])
    
    vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
    
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

            st.markdown("**Gravimetrický limit pro hmotnost zbytků**")
            gravimetry_limit_input = st.number_input("Max. povolená zbytková hmotnost (mg)", min_value=0.0, value=0.50, step=0.1)

            st.markdown("**Maximální povolené limity frakcí z normy (kódové úrovně 0-24)**")
            default_test_limits = {"B": "15", "C": "12", "D": "10", "E": "8", "F": "5", "G": "3", "H": "2", "I": "1", "J": "0", "K": "0", "L": "0", "M": "0", "N": "0"}
            
            limit_inputs = {}
            cols_r1 = st.columns(7)
            for i in range(7):
                cls = vda_classes[i]
                limit_inputs[cls] = cols_r1[i].text_input(cls, value=default_test_limits.get(cls, ""), key=f"add_{cls}")
            
            cols_r2 = st.columns(6)
            for i in range(7, 13):
                cls = vda_classes[i]
                limit_inputs[cls] = cols_r2[i - 7].text_input(cls, value=default_test_limits.get(cls, ""), key=f"add_{cls}")

            std_note = st.text_area("Poznámka k normě", value="Testovací norma A s výchozími limity")
            submit_new_std = st.form_submit_button("Vytvořit a uložit normu", type="primary")

            if submit_new_std:
                if not norm_name:
                    st.error("Název normy je povinný.")
                else:
                    try:
                        cur = conn.cursor()
                        inserted_any = False
                        for s_class, limit_val in limit_inputs.items():
                            if limit_val.strip() and limit_val.strip() != "-":
                                new_row_id = str(uuid.uuid4())
                                cur.execute(
                                    "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    (new_row_id, selected_comp_id, norm_name, s_class, int(limit_val), std_note, gravimetry_limit_input if gravimetry_limit_input > 0 else None)
                                )
                                inserted_any = True
                                
                        if inserted_any:
                            conn.commit()
                            st.success(f"Norma '{norm_name}' byla úspěšně uložena.")
                        else:
                            st.warning("Nevyplnili jste žádné limity pro velikostní třídy.")
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
                    current_class_limits[row['size_class']] = str(int(row['max_allowed_level']))

                st.markdown(f"**Upravit parametry normy**")
                with st.form("edit_standard_form"):
                    edit_norm_name = st.text_input("Název normy", value=curr_norm_name)
                    edit_gravimetry = st.number_input("Max. povolená hmotnost gravimetrie (mg)", min_value=0.0, value=float(curr_grav), step=0.1)
                    
                    st.markdown("**Limity frakcí (kódové úrovně 0-24)**")
                    edit_inputs = {}
                    cols_e1 = st.columns(7)
                    for i in range(7):
                        cls = vda_classes[i]
                        edit_inputs[cls] = cols_e1[i].text_input(cls, value=current_class_limits.get(cls, ""), key=f"edit_{cls}")
                    
                    cols_e2 = st.columns(6)
                    for i in range(7, 13):
                        cls = vda_classes[i]
                        edit_inputs[cls] = cols_e2[i - 7].text_input(cls, value=current_class_limits.get(cls, ""), key=f"edit_{cls}")

                    edit_note = st.text_area("Poznámka", value=curr_note)
                    
                    col_save, col_del = st.columns([1, 4])
                    with col_save:
                        submit_edit = st.form_submit_button("Uložit úpravy", type="primary")
                    with col_del:
                        submit_delete = st.form_submit_button("🗑️ Smazat normu")

                    if submit_edit:
                        try:
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM customer_standards WHERE norm_name = '{curr_norm_name}'")
                            
                            for s_class, limit_val in edit_inputs.items():
                                if limit_val.strip() and limit_val.strip() != "-":
                                    new_row_id = str(uuid.uuid4())
                                    cur.execute(
                                        "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (new_row_id, curr_comp_id, edit_norm_name, s_class, int(limit_val), edit_note, edit_gravimetry if edit_gravimetry > 0 else None)
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
                    db_limits_dict[str(row['size_class']).strip()] = int(row['max_allowed_level'])
            except Exception as e:
                pass

        fallback_test_limits = {"B": 15, "C": 12, "D": 10, "E": 8, "F": 5, "G": 3, "H": 2, "I": 1, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0}
        for k, v in fallback_test_limits.items():
            if k not in db_limits_dict:
                db_limits_dict[k] = v

        st.markdown("---")

        st.subheader("Volitelné bloky pro přepis z reportu")
        col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
        with col_opt1:
            enable_part_ext = st.checkbox("2. Parametry dílu", value=True, key="chk_p2")
        with col_opt2:
            enable_grav = st.checkbox("3. Gravimetrie", value=True, key="chk_p3")
        with col_opt3:
            enable_opt = st.checkbox("4. Optická analýza", value=True, key="chk_p4")
        with col_opt4:
            # ZMĚNA: Blok 6 (pokročilé metriky) je nyní automaticky zaškrtnutý
            enable_adv = st.checkbox("6. Pokročilé metriky", value=True, key="chk_p6")

        st.markdown("---")

        with st.form("inspection_form"):
            st.subheader(t["sec_ident"])
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                order_number = st.text_input(t["order_no"])
                report_number = st.text_input(t["rep_no"])
                insp_name = st.text_input(t["insp_name"], value="Jan Novák")
            with col_b:
                inspection_type = st.selectbox(t["insp_type"], ["Rutinní kontrola", "Kvalifikační zkouška", "Dvojitá inspekce"])
                filt_no = st.text_input(t["filt_no"])
                filt_lot = st.text_input(t["filt_lot"])
            with col_c:
                profile_type = st.selectbox(t["profile"], [ProfileType.VDA_19_1, ProfileType.INTERNAL_CUSTOM])
                supply_condition = st.text_input(t["supply_cond"], value="Sériový díl")
                sample_size = st.number_input(t["sample_size"], min_value=1, value=1, step=1)
                ref_unit = st.selectbox(t["ref_unit"], ["A (1000 cm²)", "V (100 cm³)", "N (kus)"])

            st.markdown("---")
            
            wetted_area, extraction_method, wetted_volume, extraction_medium, filter_material, filter_pore_size = 1000.0, "Tlakový oplach", 0.0, "Testovací benzín", "PET", 5.0
            
            st.markdown(f"**{t['sec_part']}**")
            col_d, col_e, col_f = st.columns(3)
            with col_d:
                wetted_area = st.number_input(t["wetted_area"], min_value=0.0, value=1000.0, disabled=not enable_part_ext)
                extraction_method = st.selectbox(t["ext_method"], ["Tlakový oplach", "Ultrazvuk", "Vnitřní oplach", "Agitace"], disabled=not enable_part_ext)
            with col_e:
                wetted_volume = st.number_input(t["wetted_vol"], min_value=0.0, value=0.0, disabled=not enable_part_ext)
                extraction_medium = st.text_input(t["ext_medium"], value="Testovací benzín", disabled=not enable_part_ext)
            with col_f:
                filter_material_select = st.selectbox(
                    t["filt_mat"], 
                    ["PET (polyester)", "PA (polyamid)", "PTFE (teflon)", "Nitrocelulóza", "Kovové sítko", "Jiný"],
                    disabled=not enable_part_ext
                )
                filter_material = st.text_input("Zadejte vlastní materiál filtru", disabled=not enable_part_ext) if filter_material_select == "Jiný" else filter_material_select
                filter_pore_size = st.number_input(t["filt_pore"], min_value=0.1, value=5.0, disabled=not enable_part_ext)

            st.markdown("---")

            if gravimetry_limit_db and enable_grav:
                st.info(f"Očekávaný limit normy pro gravimetrii: **{gravimetry_limit_db} mg**")
            
            st.markdown(f"**{t['sec_grav']}**")
            col_g, _ = st.columns([1, 2])
            with col_g:
                residual_mass = st.number_input(t["resid_mass"], min_value=0.0, value=0.4200, format="%.4f", step=0.1, disabled=not enable_grav)

            st.markdown("---")

            st.markdown(f"**{t['sec_opt']}**")
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

            st.markdown(f"**{t['sec_qual']}**")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                fibers_count = st.number_input(t["fibers"], min_value=0, value=0, step=1)
                blank_value_pct = st.number_input(t["blank_val"], min_value=0.0, value=2.0, step=0.1)
            with col_q2:
                metallic_ref_count = st.number_input(t["met_ref"], min_value=0, value=0, step=1)
                declining_test_pct = st.number_input(t["decl_test"], min_value=0.0, value=5.0, step=0.5)
            with col_q3:
                metallic_nonref_count = st.number_input(t["met_nonref"], min_value=0, value=0, step=1)
                filter_occupancy_pct = st.number_input(t["filt_occ"], min_value=0.0, value=3.0, step=0.5)

            st.markdown("---")
            st.markdown(f"**{t['sec_adv']}**")
            
            l_max_val, aspect_ratio_val, metallic_percentage, recovery_rate_val, specific_surface_val, cleanliness_class_code = 0.0, 0.1, 0.0, 92.5, 0.0, ""
            col_ad1, col_ad2, col_ad3 = st.columns(3)
            with col_ad1:
                l_max_val = st.number_input(t["l_max"], min_value=0.0, value=450.0, step=10.0, help=t["l_max_desc"], disabled=not enable_adv)
                aspect_ratio_val = st.number_input(t["aspect_ratio"], min_value=0.0, max_value=1.0, value=0.1, step=0.01, help=t["aspect_ratio_desc"], disabled=not enable_adv)
            with col_ad2:
                metallic_percentage = st.number_input(t["metallic_ratio"], min_value=0.0, max_value=100.0, value=2.5, step=0.1, disabled=not enable_adv)
                recovery_rate_val = st.number_input(t["recovery_rate"], min_value=0.0, max_value=100.0, value=92.5, step=0.5, disabled=not enable_adv)
            with col_ad3:
                specific_surface_val = st.number_input(t["specific_surface"], min_value=0.0, value=round(residual_mass / (wetted_area / 10000.0) if wetted_area > 0 else 0.0, 2), step=0.1, disabled=not enable_adv)
                cleanliness_class_code = st.text_input(t["cleanliness_class"], value="CCC Code: E / 12 / 3", disabled=not enable_adv)

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
            sub_btn = st.form_submit_button(t["submit_eval"], type="primary")

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
                    ref_unit_char = ref_unit[0]
                    ccc_parts, valid_levels = [], {}
                    if enable_opt:
                        for s_class in vda_classes:
                            a_level_str = str(entered_levels.get(s_class, "")).strip()
                            if a_level_str and a_level_str != "-":
                                val_int = int(a_level_str)
                                ccc_parts.append(f"{s_class} {a_level_str}")
                                valid_levels[s_class] = val_int

                    generated_ccc_string = f"CCC {ref_unit_char}({' / '.join(ccc_parts)})" if valid_levels else "CCC neuveden"

                    failed, report = False, []
                    warning_triggered = False
                    
                    if enable_grav and gravimetry_limit_db and residual_mass > gravimetry_limit_db:
                        failed = True
                        st.error(f"Gravimetrie překročena: Naměřená zbytková hmotnost {residual_mass:.4f} mg (Limit normy: {gravimetry_limit_db} mg)")

                    if enable_opt:
                        for s_class in vda_classes:
                            actual_val = valid_levels.get(s_class, 0)
                            max_alw = int(db_limits_dict.get(s_class, 0))
                            
                            if profile_type == ProfileType.VDA_19_1:
                                status = "NOK" if actual_val > max_alw else "OK"
                                if status == "NOK":
                                    failed = True
                                else:
                                    if max_alw > 0 and actual_val >= max_alw * 0.8:
                                        status = "VAROVÁNÍ"
                                        warning_triggered = True
                                    else:
                                        status = "OK"

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
                            conformity_text = "NOK"
                        elif warning_triggered:
                            conformity_text = "VAROVÁNÍ"
                        else:
                            conformity_text = "OK"

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

                    st.subheader(t["res_title"])
                    st.info(f"**CCC kód:** {generated_ccc_string}")
                    if failed:
                        st.error(f"Posouzení: **{conformity_text.upper()}**")
                    else:
                        st.success(f"Posouzení: **{conformity_text.upper()}**")
                    
                    if not report_df.empty:
                        st.dataframe(report_df, use_container_width=True)

                    grav_data_dict = {"residual_mass": residual_mass, "gravimetry_limit": gravimetry_limit_db} if enable_grav else {"residual_mass": 0, "gravimetry_limit": None}
                    uncertainty_dict = calculate_measurement_uncertainty() if include_uncertainty else None
                    advanced_dict = {
                        "l_max": l_max_val,
                        "aspect_ratio": aspect_ratio_val,
                        "metallic_percentage": metallic_percentage,
                        "specific_surface": specific_surface_val,
                        "recovery_rate": recovery_rate_val,
                        "cleanliness_class": cleanliness_class_code
                    } if enable_adv else None

                    pdf_data = create_pdf_report(
                        comp_name, std_name, filt_no, filt_lot, insp_name, ref_unit,
                        generated_ccc_string, report_df, conformity_text, failed, note,
                        fibers_count, metallic_ref_count, metallic_nonref_count,
                        grav_data_dict, uncertainty_dict, advanced_dict
                    )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        st.download_button(
                            t["download_pdf"],
                            pdf_data,
                            file_name=f"porovnani_norma_{filt_no}.pdf",
                            mime="application/pdf",
                        )
                    with btn_col2:
                        if st.button(t["new_insp"]):
                            st.rerun()


def show_history(conn):
    st.subheader(t["history_title"])
    try:
        history_df = pd.read_sql(
            'SELECT i.inspection_date AS "Datum", c.part_number AS "Číslo dílu", i.filter_number AS "Filtr", i.entered_ccc_string AS "CCC kód", i.evaluation_result AS "Výsledek" FROM inspections i JOIN components c ON i.component_id = c.id ORDER BY i.inspection_date DESC;',
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
        st.title(t["title"])

        menu_choice = st.radio(
            "Navigace",
            t["nav"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown("---")

        if menu_choice == t["nav"][0]:
            show_evaluation_form(conn)
        elif menu_choice == t["nav"][1]:
            show_standards_management(conn)
        elif menu_choice == t["nav"][2]:
            show_history(conn)

        conn.close()
else:
    st.info("Zadejte heslo k databázi v levém panelu. / Enter the database password in the sidebar.")

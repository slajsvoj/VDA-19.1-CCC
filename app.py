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
        "title": "Systém vyhodnocení čistoty (VDA 19.1)",
        "db_header": "Připojení k databázi",
        "db_pass": "Heslo k databázi",
        "db_connected": "Připojeno k Supabase",
        "db_error": "Chyba připojení k databázi:",
        "nav": ["Vyhodnocení měření", "Správa norem (Limity)", "Přehled historie měření"],
        "sec_ident": "1. Identifikace a zkušební podmínky",
        "sec_part": "2. Parametry dílu a extrakce",
        "sec_grav": "3. Gravimetrická analýza (Zbytková hmotnost)",
        "sec_opt": "4. Optická analýza – Velikostní třídy částic (B až N)",
        "sec_qual": "5. Kvalitativní charakteristiky a Validační brány (VDA 19.1)",
        "sec_adv": "6. Pokročilé vyhodnotitelné parametry (VDA 19.1)",
        "sec_hard": "7. Hard-Stop parametry (Interní norma)",
        "order_no": "Číslo zakázky",
        "rep_no": "Číslo zprávy / protokolu",
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
        "mass_b": "Hmotnost před filtrací M1 [mg]",
        "mass_a": "Hmotnost po filtraci M2 [mg]",
        "resid_mass": "Zbytková hmotnost (M = M2 - M1)",
        "fibers": "Vlákna (Fibers)",
        "blank_val": "Slepá hodnota [% z limitu]",
        "met_ref": "Kovové lesklé částice",
        "decl_test": "Klesající zkouška / Recovery [%]",
        "met_nonref": "Kovové nelesklé částice",
        "filt_occ": "Pokrytí filtru [%]",
        "pixel_res": "Pixelové rozlišení splněno (min 5-10 px)",
        "inc_unc": "Započítat modul nejistoty měření v protokolu",
        "note": "Poznámka k měření",
        "submit_eval": "Vyhodnotit a uložit do databáze",
        "l_max": "Maximální rozměr částice (L_max / Feret Max) [µm]",
        "l_max_desc": "Maximální délka největší detekované částice.",
        "aspect_ratio": "Prahová hodnota poměru stran (b/L)",
        "aspect_ratio_desc": "Poměr šířky a délky pro detekci třísek.",
        "metallic_ratio": "Podíl kovových částic [%]",
        "cleanliness_class": "Kód čistoty (ISO 16232 / CCC kód)",
        "specific_surface": "Plošná hustota kontaminace [mg/m²]",
        "recovery_rate": "Účinnost extrakce (Deklinační faktor / Recovery %)",
        "res_title": "Výsledek vyhodnocení",
        "download_pdf": "Stáhnout protokol (PDF)",
        "new_insp": "Nové vyhodnocení",
        "history_title": "Historie provedených měření",
        "standards_title": "Správa zákaznických a podnikových norem",
    },
    "en": {
        "title": "Technical Cleanliness Analysis System (VDA 19.1)",
        "db_header": "Database Connection",
        "db_pass": "Database Password",
        "db_connected": "Connected to Supabase",
        "db_error": "Database connection error:",
        "nav": ["Inspection Evaluation", "Standards & Limits Management", "Inspection History"],
        "sec_ident": "1. Identification & Inspection Conditions",
        "sec_part": "2. Component & Extraction Parameters",
        "sec_grav": "3. Gravimetric Analysis (Residual Mass)",
        "sec_opt": "4. Optical Analysis – Particle Size Classes (B to N)",
        "sec_qual": "5. Qualitative Characteristics & Validation Gates (VDA 19.1)",
        "sec_adv": "6. Advanced Evaluation Parameters (VDA 19.1)",
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
        "mass_b": "Mass Before Filtration M1 [mg]",
        "mass_a": "Mass After Filtration M2 [mg]",
        "resid_mass": "Residual Mass (M = M2 - M1)",
        "fibers": "Fibers",
        "blank_val": "Blank Value [% of limit]",
        "met_ref": "Metallic Reflective Particles",
        "decl_test": "Declining Test / Recovery [%]",
        "met_nonref": "Metallic Non-Reflective / Other Particles",
        "filt_occ": "Filter Occupancy [%]",
        "pixel_res": "Pixel Resolution Satisfied (min 5-10 px)",
        "inc_unc": "Include Measurement Uncertainty Module in Report",
        "note": "Inspection Note",
        "submit_eval": "Evaluate and Save to Database",
        "l_max": "Maximum Particle Dimension (L_max / Feret Max) [µm]",
        "l_max_desc": "Maximum length of the largest detected particle.",
        "aspect_ratio": "Aspect Ratio Threshold (b/L)",
        "aspect_ratio_desc": "Width-to-length ratio.",
        "metallic_ratio": "Metallic Particles Share [%]",
        "cleanliness_class": "Cleanliness Class (ISO 16232 / CCC Code)",
        "specific_surface": "Specific Surface Contamination [mg/m²]",
        "recovery_rate": "Extraction Efficiency / Decline Factor (Recovery %)",
        "res_title": "Evaluation Result",
        "download_pdf": "Download Report (PDF)",
        "new_insp": "New Inspection",
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
        buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )

    font_name = "Helvetica"
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", fontName=font_name, fontSize=15, leading=18, textColor=colors.HexColor("#111827"), alignment=1, spaceAfter=4)
    subtitle_style = ParagraphStyle("DocSubtitle", fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=14)
    cell_style = ParagraphStyle("TableCell", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#1f2937"))
    cell_bold = ParagraphStyle("TableCellBold", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#111827"))
    cell_header = ParagraphStyle("TableHeader", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.whitesmoke)
    ccc_style = ParagraphStyle("CCCStyle", fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor("#1e3a8a"), alignment=1)

    elements = [
        Paragraph("LABORATORNÍ PROTOKOL TECHNICKÉ ČISTOTY / TECHNICAL CLEANLINESS REPORT", title_style),
        Paragraph("Vyhodnocení dle normy VDA 19.1 / ISO 16232", subtitle_style),
    ]

    current_date = datetime.date.today().strftime("%d.%m.%Y")
    meta_data = [
        [Paragraph("<b>Označení dílu:</b>", cell_style), Paragraph(comp_name, cell_style), Paragraph("<b>Datum měření:</b>", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("<b>Zákaznická norma:</b>", cell_style), Paragraph(std_name, cell_style), Paragraph("<b>Jméno technika:</b>", cell_style), Paragraph(inspector_name, cell_style)],
        [Paragraph("<b>Číslo filtru:</b>", cell_style), Paragraph(filter_no, cell_style), Paragraph("<b>Šarže filtru:</b>", cell_style), Paragraph(filter_lot if filter_lot else "-", cell_style)],
        [Paragraph("<b>Referenční jednotka:</b>", cell_style), Paragraph(ref_unit, cell_style), Paragraph("<b>Zbytková hmotnost (M):</b>", cell_style), Paragraph(f"{grav_data.get('residual_mass', 0):.4f} mg", cell_style)],
    ]
    
    if grav_data.get('gravimetry_limit'):
        meta_data.append([Paragraph("<b>Limit gravimetrie:</b>", cell_style), Paragraph(f"{grav_data.get('gravimetry_limit'):.4f} mg", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)])

    meta_table = Table(meta_data, colWidths=[110, 160, 100, 170])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    ccc_table = Table([[Paragraph(f"<b>CCC kód:</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]], colWidths=[540], rowHeights=[28])
    ccc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ])
    )
    elements.append(ccc_table)
    elements.append(Spacer(1, 10))

    if failed:
        res_color = colors.HexColor("#fee2e2")
        res_text_color = colors.HexColor("#991b1b")
    else:
        res_color = colors.HexColor("#d1fae5")
        res_text_color = colors.HexColor("#065f46")

    res_style = ParagraphStyle("ResText", fontName=font_name, fontSize=10, leading=14, textColor=res_text_color, alignment=1)
    res_table = Table([[Paragraph(f"<b>VÝSLEDEK POSOUZENÍ / EVALUATION RESULT: {conformity_text.upper()}</b>", res_style)]], colWidths=[540], rowHeights=[26])
    res_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), res_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, res_text_color),
        ])
    )
    elements.append(res_table)
    elements.append(Spacer(1, 12))

    if uncertainty_info:
        unc_text = Paragraph(f"<b>Nejistota měření (k=2, 95%):</b> Kombinovaná: {uncertainty_info['combined_pct']}% | Rozšířená: {uncertainty_info['expanded_pct']}%", cell_style)
        elements.append(unc_text)
        elements.append(Spacer(1, 8))

    table_data = [[
        Paragraph("<b>Velikostní třída / Size Class</b>", cell_header),
        Paragraph("<b>Rozsah velikosti / Range</b>", cell_header),
        Paragraph("<b>Max. povolená úroveň / Limit</b>", cell_header),
        Paragraph("<b>Naměřená úroveň / Measured</b>", cell_header),
        Paragraph("<b>Stav / Status</b>", cell_header),
    ]]

    size_ranges = {
        "B": "5 µm – 15 µm", "C": "15 µm – 25 µm", "D": "25 µm – 50 µm",
        "E": "50 µm – 100 µm", "F": "100 µm – 150 µm", "G": "150 µm – 200 µm",
        "H": "200 µm – 400 µm", "I": "400 µm – 600 µm", "J": "600 µm – 1000 µm",
        "K": "1000 µm – 1500 µm", "L": "1500 µm – 2000 µm", "M": "2000 µm – 3000 µm",
        "N": "> 3000 µm",
    }

    if not report_df.empty:
        for _, row in report_df.iterrows():
            s_class = str(row["Velikostní třída"])
            s_range = size_ranges.get(s_class, "-")
            status = str(row["Stav"])
            status_html = (
                '<font color="#065f46"><b>OK</b></font>' if status in ["OK", "specifikace splněna"] else
                ('<font color="#991b1b"><b>NOK</b></font>' if status in ["NOK", "specifikace nesplněna"] else '<font color="#b45309"><b>VAROVÁNÍ</b></font>')
            )

            table_data.append([
                Paragraph(s_class, cell_bold), Paragraph(s_range, cell_style),
                Paragraph(str(row["Povolený limit"]), cell_style), Paragraph(str(row["Naměřená úroveň"]), cell_style),
                Paragraph(status_html, cell_style),
            ])

        t = Table(table_data, colWidths=[90, 130, 130, 95, 95])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ])
        )
        elements.append(t)
        elements.append(Spacer(1, 12))

    qual_data = [
        [Paragraph("<b>Kvalitativní charakteristika částic (VDA 19.1)</b>", cell_header), Paragraph("<b>Zjištěný počet / podíl</b>", cell_header)],
        [Paragraph("Vlákna (Fibers)", cell_style), Paragraph(str(fibers_count), cell_style)],
        [Paragraph("Kovové lesklé částice (Metallic reflective)", cell_style), Paragraph(str(metallic_ref_count), cell_style)],
        [Paragraph("Kovové nelesklé / ostatní částice (Non-reflective)", cell_style), Paragraph(str(metallic_nonref_count), cell_style)],
    ]

    if advanced_data:
        qual_data.append([Paragraph("Max. rozměr částice (L_max / Feret Max)", cell_style), Paragraph(f"{advanced_data.get('l_max', 0)} µm", cell_style)])
        qual_data.append([Paragraph("Poměr stran (b/L threshold)", cell_style), Paragraph(str(advanced_data.get('aspect_ratio', '-')), cell_style)])
        qual_data.append([Paragraph("Plošná hustota kontaminace (Specific Surface)", cell_style), Paragraph(f"{advanced_data.get('specific_surface', 0)} mg/m²", cell_style)])
        qual_data.append([Paragraph("Účinnost extrakce (Recovery / Decline rate)", cell_style), Paragraph(f"{advanced_data.get('recovery_rate', 0)} %", cell_style)])

    qual_table = Table(qual_data, colWidths=[340, 200])
    qual_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ])
    )
    elements.append(qual_table)

    if note:
        elements.append(Spacer(1, 10))
        note_table = Table([[Paragraph("<b>Poznámka k měření:</b>", cell_bold)], [Paragraph(note, cell_style)]], colWidths=[540])
        elements.append(note_table)

    elements.append(Spacer(1, 20))
    sig_table = Table([[Paragraph(f"<b>Protokol vytvořil (technik) / Inspector:</b> {inspector_name}", cell_style)]], colWidths=[540])
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def show_standards_management(conn):
    st.subheader(t["standards_title"])
    tab1, tab2 = st.tabs(["➕ Přidat novou normu", "✏️ Editovat / Smazat stávající normu"])
    
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
                norm_name = st.text_input("Název normy (např. VDA 19.1 - Zpřísněná)", placeholder="Zadejte název...")

            st.markdown("**Gravimetrie (Limit hmotnosti zbytků)**")
            gravimetry_limit_input = st.number_input("Max. povolená hmotnost (mg)", min_value=0.0, value=0.0, step=0.1, help="Pokud se gravimetrie nesleduje, nechte 0.")

            st.markdown("**Maximální povolené limity frakcí (kódové úrovně 0-24)**")
            limit_inputs = {}
            cols_r1 = st.columns(7)
            for i in range(7):
                limit_inputs[vda_classes[i]] = cols_r1[i].text_input(vda_classes[i], key=f"add_{vda_classes[i]}")
            
            cols_r2 = st.columns(6)
            for i in range(7, 13):
                limit_inputs[vda_classes[i]] = cols_r2[i - 7].text_input(vda_classes[i], key=f"add_{vda_classes[i]}")

            std_note = st.text_area("Poznámka k normě (např. interní požadavky na Feret_max)")
            submit_new_std = st.form_submit_button("Vytvořit a uložit normu", type="primary")

            if submit_new_std:
                if not norm_name:
                    st.error("Název normy je povinný.")
                else:
                    try:
                        cur = conn.cursor()
                        new_std_id = str(uuid.uuid4()) 
                        inserted_any = False
                        for s_class, limit_val in limit_inputs.items():
                            if limit_val.strip() and limit_val.strip() != "-":
                                cur.execute(
                                    "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    (new_std_id, selected_comp_id, norm_name, s_class, int(limit_val), std_note, gravimetry_limit_input if gravimetry_limit_input > 0 else None)
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
                            cur.execute(f"DELETE FROM customer_standards WHERE id = '{edit_std_id}'")
                            
                            for s_class, limit_val in edit_inputs.items():
                                if limit_val.strip() and limit_val.strip() != "-":
                                    cur.execute(
                                        "INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, note, gravimetry_limit_mg) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (edit_std_id, curr_comp_id, edit_norm_name, s_class, int(limit_val), edit_note, edit_gravimetry if edit_gravimetry > 0 else None)
                                    )
                            conn.commit()
                            st.success("Změny byly úspěšně uloženy.")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Chyba při ukládání úprav: {e}")
                            
                    if submit_delete:
                        try:
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM customer_standards WHERE id = '{edit_std_id}'")
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
                    "Zákaznický limit / norma / Cleanliness Standard",
                    options=standards_df.index,
                    format_func=lambda x: standards_df.loc[x, "norm_name"],
                )
                std_id = standards_df.loc[selected_std_idx, "id"]
                std_name = standards_df.loc[selected_std_idx, "norm_name"]
                
                gravimetry_limit_db = None
                try:
                    grav_df = pd.read_sql(f"SELECT gravimetry_limit_mg FROM customer_standards WHERE id = '{std_id}' LIMIT 1", conn)
                    if not grav_df.empty and pd.notna(grav_df.iloc[0]['gravimetry_limit_mg']):
                        gravimetry_limit_db = float(grav_df.iloc[0]['gravimetry_limit_mg'])
                except:
                    pass
            else:
                st.warning("Pro tento díl není definován limit v DB.")
                std_id, std_name, gravimetry_limit_db = None, "Neznámá norma", None

        db_limits_dict = {}
        if std_id:
            try:
                lim_fetch = pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id = '{std_id}'", conn)
                for _, row in lim_fetch.iterrows():
                    db_limits_dict[row['size_class']] = int(row['max_allowed_level'])
            except:
                pass

        st.markdown("---")

        # --- PŘEPÍNAČE PRO VOLITELNOST SEKCÍ (MIMO FORMULAR PRO OKAMŽITOU REAKCI) ---
        st.subheader("Konfigurace volitelných bloků měření")
        col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
        with col_opt1:
            enable_part_ext = st.checkbox("2. Parametry dílu", value=True, key="chk_p2")
        with col_opt2:
            enable_grav = st.checkbox("3. Gravimetrie", value=True, key="chk_p3")
        with col_opt3:
            enable_opt = st.checkbox("4. Optická analýza", value=True, key="chk_p4")
        with col_opt4:
            enable_adv = st.checkbox("6. Pokročilé metriky", value=False, key="chk_p6")

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
            
            # --- SEKCE 2: Parametry dílu a extrakce ---
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

            # --- SEKCE 3: Gravimetrická analýza ---
            residual_mass = 0.0
            if gravimetry_limit_db and enable_grav:
                st.info(f"Očekávaný limit normy pro gravimetrii: **{gravimetry_limit_db} mg**")
            
            st.markdown(f"**{t['sec_grav']}**")
            col_g, col_h, col_i = st.columns(3)
            with col_g:
                mass_before = st.number_input(t["mass_b"], min_value=0.0, value=45.1200, format="%.4f", disabled=not enable_grav)
            with col_h:
                mass_after = st.number_input(t["mass_a"], min_value=0.0, value=45.5400, format="%.4f", disabled=not enable_grav)
            with col_i:
                residual_mass = max(0.0, mass_after - mass_before)
                st.metric(label=t["resid_mass"], value=f"{residual_mass:.4f} mg")

            st.markdown("---")

            # --- SEKCE 4: Optická analýza ---
            st.markdown(f"**{t['sec_opt']}**")
            vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
            entered_levels = {}

            cols_row1 = st.columns(7)
            for i in range(7):
                s_class = vda_classes[i]
                limit_val = db_limits_dict.get(s_class, None)
                
                raw_input = cols_row1[i].text_input(s_class, value="", placeholder="-", key=f"cls_{s_class}", disabled=not enable_opt)
                entered_levels[s_class] = raw_input
                
                if enable_opt and raw_input.strip() and raw_input.strip() != "-":
                    try:
                        val_num = int(raw_input.strip())
                        if limit_val is not None:
                            if val_num > limit_val:
                                cols_row1[i].markdown(f"<p style='color:red; font-size:11px; margin:0;'>Limit překročen! (Max: {limit_val})</p>", unsafe_allow_html=True)
                            else:
                                cols_row1[i].markdown(f"<p style='color:green; font-size:11px; margin:0;'>V toleranci (Max: {limit_val})</p>", unsafe_allow_html=True)
                    except ValueError:
                        pass

            cols_row2 = st.columns(6)
            for i in range(7, 13):
                s_class = vda_classes[i]
                limit_val = db_limits_dict.get(s_class, None)
                
                raw_input = cols_row2[i - 7].text_input(s_class, value="", placeholder="-", key=f"cls_{s_class}", disabled=not enable_opt)
                entered_levels[s_class] = raw_input
                
                if enable_opt and raw_input.strip() and raw_input.strip() != "-":
                    try:
                        val_num = int(raw_input.strip())
                        if limit_val is not None:
                            if val_num > limit_val:
                                cols_row2[i - 7].markdown(f"<p style='color:red; font-size:11px; margin:0;'>Limit překročen! (Max: {limit_val})</p>", unsafe_allow_html=True)
                            else:
                                cols_row2[i - 7].markdown(f"<p style='color:green; font-size:11px; margin:0;'>V toleranci (Max: {limit_val})</p>", unsafe_allow_html=True)
                    except ValueError:
                        pass

            st.markdown("---")

            # --- SEKCE 5: Kvalitativní charakteristiky ---
            st.markdown(f"**{t['sec_qual']}**")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                fibers_count = st.number_input(t["fibers"], min_value=0, value=0, step=1)
                blank_value_pct = st.number_input(t["blank_val"], min_value=0.0, value=2.0)
            with col_q2:
                metallic_ref_count = st.number_input(t["met_ref"], min_value=0, value=0, step=1)
                declining_test_pct = st.number_input(t["decl_test"], min_value=0.0, value=5.0)
            with col_q3:
                metallic_nonref_count = st.number_input(t["met_nonref"], min_value=0, value=0, step=1)
                filter_occupancy_pct = st.number_input(t["filt_occ"], min_value=0.0, value=3.0)

            # --- SEKCE 6: Pokročilé vyhodnotitelné parametry (PŘEDĚLANO NA ČÍSELNÁ OKNA) ---
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
            if not filt_no or not std_id:
                st.error("Vyplňte číslo filtru a vyberte normu.")
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
                        for s_class, a_level_str in entered_levels.items():
                            a_level_str = a_level_str.strip()
                            if a_level_str and a_level_str != "-":
                                val_int = int(a_level_str)
                                ccc_parts.append(f"{s_class} {a_level_str}")
                                valid_levels[s_class] = val_int

                    generated_ccc_string = f"CCC {ref_unit_char}({' / '.join(ccc_parts)})" if valid_levels else "CCC neuveden"
                    
                    limits_df = pd.DataFrame()
                    if enable_opt and std_id:
                        limits_df = pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id = '{std_id}'", conn)

                    failed, report = False, []
                    warning_triggered = False
                    
                    if enable_grav and gravimetry_limit_db and residual_mass > gravimetry_limit_db:
                        failed = True
                        st.error(f"Gravimetrie překročena: Naměřeno {residual_mass:.4f} mg (Limit normy: {gravimetry_limit_db} mg)")

                    if enable_opt:
                        for s_class, actual_val in valid_levels.items():
                            lim_row = limits_df[limits_df["size_class"] == s_class] if not limits_df.empty else pd.DataFrame()
                            max_alw = int(lim_row.iloc[0]["max_allowed_level"]) if not lim_row.empty else 0
                            
                            if profile_type == ProfileType.VDA_19_1:
                                status = "NOK" if not lim_row.empty and actual_val > max_alw else "OK"
                                if status == "NOK":
                                    failed = True
                                else:
                                    if not lim_row.empty and actual_val >= max_alw * 0.8:
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
                        (c_id, std_id, insp_name, filt_no, filt_lot, generated_ccc_string, conformity_text, note),
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
                            file_name=f"protokol_{filt_no}.pdf",
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
            st.info("Zatím nejsou uložena žádná měření.")
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

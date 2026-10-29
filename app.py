import datetime
import io
import math
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
    div.stButton > button:has(div:contains("Nové vyhodnocení")) {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    div.stButton > button:has(div:contains("Nové vyhodnocení")):hover {
        background-color: #b91c1c !important;
        border-color: #b91c1c !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Zadání hesla v levém panelu
st.sidebar.header("Připojení k databázi")
DB_PASSWORD = st.sidebar.text_input("Heslo k databázi", type="password")


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
        st.sidebar.error(f"Chyba připojení k databázi: {e}")
        return None


# --- VYHODNOCOVACÍ LOGIKA A MODELY ---

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
    comp_name,
    std_name,
    filter_no,
    filter_lot,
    inspector_name,
    ref_unit,
    ccc_string,
    report_df,
    conformity_text,
    failed,
    note,
    fibers_count,
    metallic_ref_count,
    metallic_nonref_count,
    grav_data,
    uncertainty_info=None,
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )

    font_name = "Helvetica"
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle", fontName=font_name, fontSize=15, leading=18, textColor=colors.HexColor("#111827"), alignment=1, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle", fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=14
    )
    cell_style = ParagraphStyle(
        "TableCell", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#1f2937")
    )
    cell_bold = ParagraphStyle(
        "TableCellBold", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#111827")
    )
    cell_header = ParagraphStyle(
        "TableHeader", fontName=font_name, fontSize=8.5, leading=12, textColor=colors.whitesmoke
    )
    ccc_style = ParagraphStyle(
        "CCCStyle", fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor("#1e3a8a"), alignment=1
    )

    elements = [
        Paragraph("LABORATORNÍ PROTOKOL TECHNICKÉ ČISTOTY", title_style),
        Paragraph("Vyhodnocení dle normy VDA 19.1 / ISO 16232", subtitle_style),
    ]

    current_date = datetime.date.today().strftime("%d.%m.%Y")
    meta_data = [
        [Paragraph("<b>Označení dílu:</b>", cell_style), Paragraph(comp_name, cell_style), Paragraph("<b>Datum měření:</b>", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("<b>Zákaznická norma:</b>", cell_style), Paragraph(std_name, cell_style), Paragraph("<b>Jméno technika:</b>", cell_style), Paragraph(inspector_name, cell_style)],
        [Paragraph("<b>Číslo filtru:</b>", cell_style), Paragraph(filter_no, cell_style), Paragraph("<b>Šarže filtru:</b>", cell_style), Paragraph(filter_lot if filter_lot else "-", cell_style)],
        [Paragraph("<b>Referenční jednotka:</b>", cell_style), Paragraph(ref_unit, cell_style), Paragraph("<b>Zbytková hmotnost (M):</b>", cell_style), Paragraph(f"{grav_data.get('residual_mass', 0):.4f} mg", cell_style)],
    ]

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
    res_table = Table([[Paragraph(f"<b>VÝSLEDEK POSOUZENÍ: {conformity_text.upper()}</b>", res_style)]], colWidths=[540], rowHeights=[26])
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
        Paragraph("<b>Velikostní třída</b>", cell_header),
        Paragraph("<b>Rozsah velikosti</b>", cell_header),
        Paragraph("<b>Max. povolená úroveň</b>", cell_header),
        Paragraph("<b>Naměřená úroveň</b>", cell_header),
        Paragraph("<b>Stav</b>", cell_header),
    ]]

    size_ranges = {
        "B": "5 µm – 15 µm", "C": "15 µm – 25 µm", "D": "25 µm – 50 µm",
        "E": "50 µm – 100 µm", "F": "100 µm – 150 µm", "G": "150 µm – 200 µm",
        "H": "200 µm – 400 µm", "I": "400 µm – 600 µm", "J": "600 µm – 1000 µm",
        "K": "1000 µm – 1500 µm", "L": "1500 µm – 2000 µm", "M": "2000 µm – 3000 µm",
        "N": "> 3000 µm",
    }

    for _, row in report_df.iterrows():
        s_class = str(row["Velikostní třída"])
        s_range = size_ranges.get(s_class, "-")
        status = str(row["Stav"])
        status_html = (
            '<font color="#065f46"><b>OK</b></font>' if status in ["OK", "specifikace splněna"] else
            ('<font color="#991b1b"><b>NOK</b></font>' if status in ["NOK", "specifikace nesplněna"] else '<font color="#b45309"><b>VAROVÁNÍ</b></font>')
        )

        table_data.append([
            Paragraph(s_class, cell_bold),
            Paragraph(s_range, cell_style),
            Paragraph(str(row["Povolený limit"]), cell_style),
            Paragraph(str(row["Naměřená úroveň"]), cell_style),
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
    sig_table = Table([[Paragraph(f"<b>Protokol vytvořil (technik):</b> {inspector_name}", cell_style)]], colWidths=[540])
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    buffer.seek(0)
    return buffer


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
                "Výběr dílu",
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
                    "Zákaznický limit / norma",
                    options=standards_df.index,
                    format_func=lambda x: standards_df.loc[x, "norm_name"],
                )
                std_id = standards_df.loc[selected_std_idx, "id"]
                std_name = standards_df.loc[selected_std_idx, "norm_name"]
            else:
                st.warning("Pro tento díl není definován limit v DB.")
                std_id, std_name = None, "Neznámá norma"

        st.markdown("---")

        with st.form("inspection_form"):
            st.subheader("1. Identifikace a zkušební podmínky")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                order_number = st.text_input("Číslo zakázky")
                report_number = st.text_input("Číslo zprávy / protokolu")
                insp_name = st.text_input("Jméno technika", value="Jan Novák")
            with col_b:
                inspection_type = st.selectbox("Typ zkoušky", ["Rutinní kontrola", "Kvalifikační zkouška", "Dvojitá inspekce"])
                filt_no = st.text_input("Číslo filtru")
                filt_lot = st.text_input("Šarže filtru")
            with col_c:
                profile_type = st.selectbox("Vyhodnocovací profil", [ProfileType.VDA_19_1, ProfileType.INTERNAL_CUSTOM])
                supply_condition = st.text_input("Stav při dodání", value="Sériový díl")
                sample_size = st.number_input("Kontrolní dávka (n)", min_value=1, value=1, step=1)
                ref_unit = st.selectbox("Referenční jednotka", ["A (1000 cm²)", "V (100 cm³)", "N (kus)"])

            st.markdown("---")
            st.subheader("2. Parametry dílu a extrakce")
            col_d, col_e, col_f = st.columns(3)
            with col_d:
                wetted_area = st.number_input("Smáčená plocha AC [cm²]", min_value=0.0, value=1000.0)
                extraction_method = st.selectbox("Metoda extrakce", ["Tlakový oplach", "Ultrazvuk", "Vnitřní oplach", "Agitace"])
            with col_e:
                wetted_volume = st.number_input("Smáčený objem VC [cm³]", min_value=0.0, value=0.0)
                extraction_medium = st.text_input("Extrakční médium", value="Testovací benzín")
            with col_f:
                filter_material = st.text_input("Materiál filtru", value="PET (polyester)")
                filter_pore_size = st.number_input("Velikost pórů [µm]", min_value=0.1, value=5.0)

            st.markdown("---")
            st.subheader("3. Gravimetrická analýza (Zbytková hmotnost)")
            col_g, col_h, col_i = st.columns(3)
            with col_g:
                mass_before = st.number_input("Hmotnost před filtrací M1 [mg]", min_value=0.0, value=45.1200, format="%.4f")
            with col_h:
                mass_after = st.number_input("Hmotnost po filtraci M2 [mg]", min_value=0.0, value=45.5400, format="%.4f")
            with col_i:
                residual_mass = max(0.0, mass_after - mass_before)
                st.metric(label="Zbytková hmotnost (M = M2 - M1)", value=f"{residual_mass:.4f} mg")

            st.markdown("---")
            st.subheader("4. Optická analýza – Velikostní třídy částic (B až N)")
            vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
            entered_levels = {}

            cols_row1 = st.columns(7)
            for i in range(7):
                s_class = vda_classes[i]
                entered_levels[s_class] = cols_row1[i].text_input(s_class, value="", placeholder="-", key=f"cls_{s_class}")

            cols_row2 = st.columns(6)
            for i in range(7, 13):
                s_class = vda_classes[i]
                entered_levels[s_class] = cols_row2[i - 7].text_input(s_class, value="", placeholder="-", key=f"cls_{s_class}")

            st.markdown("---")
            st.subheader("5. Kvalitativní charakteristiky a Validační brány (VDA 19.1)")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                fibers_count = st.number_input("Vlákna (Fibers)", min_value=0, value=0, step=1)
                blank_value_pct = st.number_input("Slepá hodnota [% z limitu]", min_value=0.0, value=2.0)
            with col_q2:
                metallic_ref_count = st.number_input("Kovové lesklé částice", min_value=0, value=0, step=1)
                declining_test_pct = st.number_input("Klesající zkouška [%]", min_value=0.0, value=5.0)
            with col_q3:
                metallic_nonref_count = st.number_input("Kovové nelesklé částice", min_value=0, value=0, step=1)
                filter_occupancy_pct = st.number_input("Pokrytí filtru [%]", min_value=0.0, value=3.0)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                pixel_resolution_ok = st.checkbox("Pixelové rozlišení splněno (min 5-10 px)", value=True)
            with col_x2:
                include_uncertainty = st.checkbox("Započítat modul nejistoty měření v protokolu", value=True)

            hard_stop_feret_max = 0.0
            has_v3 = False
            max_feret_measured = 0.0
            if profile_type == ProfileType.INTERNAL_CUSTOM:
                st.markdown("---")
                st.subheader("6. Hard-Stop parametry (Interní norma)")
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hard_stop_feret_max = st.number_input("Max. povolený Feret_max [µm] (Hard-stop)", min_value=0.0, value=1500.0)
                with col_h2:
                    has_v3 = st.checkbox("Detekovány zakázané částice V3 (>1000 HV)", value=False)
                max_feret_measured = st.number_input("Naměřená největší částice Feret_max [µm]", min_value=0.0, value=250.0)

            note = st.text_area("Poznámka k měření")
            sub_btn = st.form_submit_button("Vyhodnotit a uložit do databáze", type="primary")

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
                    for s_class, a_level_str in entered_levels.items():
                        a_level_str = a_level_str.strip()
                        if a_level_str and a_level_str != "-":
                            val_int = int(a_level_str)
                            ccc_parts.append(f"{s_class} {a_level_str}")
                            valid_levels[s_class] = val_int

                    if not valid_levels:
                        st.error("Vyplňte hodnotu alespoň pro jednu velikostní třídu.")
                    else:
                        generated_ccc_string = f"CCC {ref_unit_char}({' / '.join(ccc_parts)})"
                        limits_df = pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id = '{std_id}'", conn)

                        failed, report = False, []
                        warning_triggered = False
                        for s_class, actual_val in valid_levels.items():
                            lim_row = limits_df[limits_df["size_class"] == s_class]
                            max_alw = int(lim_row.iloc[0]["max_allowed_level"]) if not lim_row.empty else 0
                            
                            if profile_type == ProfileType.VDA_19_1:
                                status = "NOK" if not lim_row.empty and actual_val > max_alw else "OK"
                                if status == "NOK":
                                    failed = True
                            else:
                                if not lim_row.empty and actual_val > max_alw:
                                    status = "NOK"
                                    failed = True
                                elif not lim_row.empty and actual_val >= max_alw * 0.8:
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
                            if has_v3:
                                hard_stop_failed = True
                                failed = True

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
                        for s_class, a_level in valid_levels.items():
                            cur.execute(
                                "INSERT INTO inspection_details (inspection_id, size_class, cleanliness_level) VALUES (%s, %s, %s);",
                                (ins_id, s_class, a_level),
                            )
                        conn.commit()
                        cur.close()

                        st.subheader("Výsledek vyhodnocení")
                        st.info(f"**CCC kód:** {generated_ccc_string}")
                        if failed:
                            st.error(f"Posouzení: **{conformity_text.upper()}**")
                        else:
                            st.success(f"Posouzení: **{conformity_text.upper()}**")
                        
                        st.dataframe(report_df, use_container_width=True)

                        grav_data_dict = {"residual_mass": residual_mass}
                        uncertainty_dict = calculate_measurement_uncertainty() if include_uncertainty else None

                        pdf_data = create_pdf_report(
                            comp_name, std_name, filt_no, filt_lot, insp_name, ref_unit,
                            generated_ccc_string, report_df, conformity_text, failed, note,
                            fibers_count, metallic_ref_count, metallic_nonref_count,
                            grav_data_dict, uncertainty_dict
                        )

                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            st.download_button(
                                "Stáhnout protokol (PDF)",
                                pdf_data,
                                file_name=f"protokol_{filt_no}.pdf",
                                mime="application/pdf",
                            )
                        with btn_col2:
                            if st.button("Nové vyhodnocení"):
                                st.rerun()


def show_history(conn):
    st.subheader("Historie provedených měření")
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


# HLAVNÍ BĚH APLIKACE
if DB_PASSWORD:
    conn = get_db_connection()
    if conn:
        st.sidebar.success("Připojeno k Supabase")
        st.title("Systém vyhodnocení čistoty (VDA 19.1)")

        menu_choice = st.radio(
            "Navigace",
            ["Vyhodnocení měření", "Přehled historie měření"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown("---")

        if menu_choice == "Vyhodnocení měření":
            show_evaluation_form(conn)
        elif menu_choice == "Přehled historie měření":
            show_history(conn)

        conn.close()
else:
    st.info("Zadejte heslo k databázi v levém panelu.")

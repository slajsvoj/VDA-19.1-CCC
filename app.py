import datetime
import io
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


def get_db_connection():
  try:
    conn = psycopg2.connect(
        host="aws-0-eu-west-1.pooler.supabase.com",
        database="postgres",
        user="postgres.ywyicopmesmwtkjewbfk",
        password="X-rb42&e4$uJ%rJ",
        port="6543",
        sslmode="require",
        connect_timeout=10,
    )
    return conn
  except Exception as e:
    st.error(f"Chyba připojení k databázi: {e}")
    return None


def create_pdf_report(
    comp_name,
    std_name,
    filter_no,
    filter_lot,
    inspector_name,
    ref_unit,
    ccc_string,
    report_df,
    failed,
    note,
    fibers_count,
    metallic_ref_count,
    metallic_nonref_count,
):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
  )

  font_name = "Helvetica"

  styles = getSampleStyleSheet()

  title_style = ParagraphStyle(
      "DocTitle",
      fontName=font_name,
      fontSize=15,
      leading=18,
      textColor=colors.HexColor("#111827"),
      alignment=1,
      spaceAfter=4,
  )
  subtitle_style = ParagraphStyle(
      "DocSubtitle",
      fontName=font_name,
      fontSize=9,
      leading=13,
      textColor=colors.HexColor("#4b5563"),
      alignment=1,
      spaceAfter=14,
  )
  cell_style = ParagraphStyle(
      "TableCell",
      fontName=font_name,
      fontSize=9,
      leading=13,
      textColor=colors.HexColor("#1f2937"),
  )
  cell_bold = ParagraphStyle(
      "TableCellBold",
      fontName=font_name,
      fontSize=9,
      leading=13,
      textColor=colors.HexColor("#111827"),
  )
  cell_header = ParagraphStyle(
      "TableHeader",
      fontName=font_name,
      fontSize=9,
      leading=13,
      textColor=colors.whitesmoke,
  )
  ccc_style = ParagraphStyle(
      "CCCStyle",
      fontName=font_name,
      fontSize=11,
      leading=15,
      textColor=colors.HexColor("#1e3a8a"),
      alignment=1,
  )

  elements = [
      Paragraph("LABORATORNI PROTOKOL TECHNICKE CISTOTY", title_style),
      Paragraph("Vyhodnoceni dle normy VDA 19.1 / ISO 16232", subtitle_style),
  ]

  current_date = datetime.date.today().strftime("%d.%m.%Y")
  meta_data = [
      [
          Paragraph("<b>Oznaceni dilu:</b>", cell_style),
          Paragraph(comp_name, cell_style),
          Paragraph("<b>Datum mereni:</b>", cell_style),
          Paragraph(current_date, cell_style),
      ],
      [
          Paragraph("<b>Zakaznicka norma:</b>", cell_style),
          Paragraph(std_name, cell_style),
          Paragraph("<b>Jmeno technika:</b>", cell_style),
          Paragraph(inspector_name, cell_style),
      ],
      [
          Paragraph("<b>Cislo filtru:</b>", cell_style),
          Paragraph(filter_no, cell_style),
          Paragraph("<b>Sarze filtru:</b>", cell_style),
          Paragraph(filter_lot if filter_lot else "-", cell_style),
      ],
      [
          Paragraph("<b>Referencni jednotka:</b>", cell_style),
          Paragraph(ref_unit, cell_style),
          Paragraph("<b>Laboratorni stav:</b>", cell_style),
          Paragraph("Kompletni analyza", cell_style),
      ],
  ]

  meta_table = Table(meta_data, colWidths=[110, 160, 100, 170])
  meta_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
          ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
          ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
          ("TOPPADDING", (0, 0), (-1, -1), 6),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
          ("LEFTPADDING", (0, 0), (-1, -1), 8),
          ("RIGHTPADDING", (0, 0), (-1, -1), 8),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
      ])
  )
  elements.append(meta_table)
  elements.append(Spacer(1, 10))

  ccc_table = Table(
      [[Paragraph(f"<b>CCC kod:</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]],
      colWidths=[540],
      rowHeights=[28],
  )
  ccc_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
      ])
  )
  elements.append(ccc_table)
  elements.append(Spacer(1, 12))

  if failed:
    res_text = "CELKOVY VYSLEDEK: NEVYHOVUJE (NOT MET)"
    res_color = colors.HexColor("#fee2e2")
    res_text_color = colors.HexColor("#991b1b")
  else:
    res_text = "CELKOVY VYSLEDEK: SPLNENO (MET)"
    res_color = colors.HexColor("#d1fae5")
    res_text_color = colors.HexColor("#065f46")

  res_style = ParagraphStyle(
      "ResText",
      fontName=font_name,
      fontSize=10,
      leading=14,
      textColor=res_text_color,
      alignment=1,
  )
  res_table = Table(
      [[Paragraph(f"<b>{res_text}</b>", res_style)]],
      colWidths=[540],
      rowHeights=[26],
  )
  res_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), res_color),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BOX", (0, 0), (-1, -1), 1, res_text_color),
      ])
  )
  elements.append(res_table)
  elements.append(Spacer(1, 14))

  table_data = [[
      Paragraph("<b>Velikostni trida</b>", cell_header),
      Paragraph("<b>Rozsah velikosti</b>", cell_header),
      Paragraph("<b>Max. povolena uroveň</b>", cell_header),
      Paragraph("<b>Namerena uroveň</b>", cell_header),
      Paragraph("<b>Stav</b>", cell_header),
  ]]

  size_ranges = {
      "B": "5 um – 15 um",
      "C": "15 um – 25 um",
      "D": "25 um – 50 um",
      "E": "50 um – 100 um",
      "F": "100 um – 150 um",
      "G": "150 um – 200 um",
      "H": "200 um – 400 um",
      "I": "400 um – 600 um",
      "J": "600 um – 1000 um",
      "K": "> 1000 um",
  }

  for _, row in report_df.iterrows():
    s_class = str(row["Velikostní třída"])
    s_range = size_ranges.get(s_class, "-")
    status = str(row["Stav"])
    status_html = (
        '<font color="#065f46"><b>OK</b></font>'
        if status == "OK"
        else (
            '<font color="#991b1b"><b>NOK</b></font>'
            if status == "NOK"
            else '<font color="#4b5563">N/A</font>'
        )
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
      [
          Paragraph("<b>Kvalitativni charakteristika castic (VDA 19.1)</b>", cell_header),
          Paragraph("<b>Zjisteny pocet / podil</b>", cell_header),
      ],
      [
          Paragraph("Vlakna (Fibers)", cell_style),
          Paragraph(str(fibers_count), cell_style),
      ],
      [
          Paragraph("Kovove leskle castice (Metallic reflective)", cell_style),
          Paragraph(str(metallic_ref_count), cell_style),
      ],
      [
          Paragraph(
              "Kovove neleskle / ostatni castice (Non-reflective)", cell_style
          ),
          Paragraph(str(metallic_nonref_count), cell_style),
      ],
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
    note_table = Table(
        [[Paragraph("<b>Poznamka k mereni:</b>", cell_bold)], [Paragraph(note, cell_style)]],
        colWidths=[540],
    )
    elements.append(note_table)

  elements.append(Spacer(1, 20))
  sig_table = Table(
      [[Paragraph(f"<b>Protokol vytvoril (technik):</b> {inspector_name}", cell_style)]],
      colWidths=[540],
  )
  elements.append(KeepTogether(sig_table))

  doc.build(elements)
  buffer.seek(0)
  return buffer


def show_evaluation_form(conn):
  try:
    components_df = pd.read_sql(
        "SELECT id, part_number, name FROM components", conn
    )
  except Exception as err:
    components_df = pd.DataFrame()
    st.error(f"Chyba při načítání dílů: {err}")

  if not components_df.empty:
    col1, col2 = st.columns(2)
    with col1:
      selected_comp_idx = st.selectbox(
          "Výběr dílu",
          options=components_df.index,
          format_func=lambda x: (
              f"{components_df.loc[x, 'part_number']} -"
              f" {components_df.loc[x, 'name']}"
          ),
      )
      c_id = components_df.loc[selected_comp_idx, "id"]
      c_pn = components_df.loc[selected_comp_idx, "part_number"]
      c_nm = components_df.loc[selected_comp_idx, "name"]
      comp_name = f"{c_pn} ({c_nm})"

    with col2:
      standards_df = pd.read_sql(
          "SELECT DISTINCT id, norm_name FROM customer_standards WHERE"
          f" component_id = '{c_id}'",
          conn,
      )
      if not standards_df.empty:
        selected_std_idx = st.selectbox(
            "Zákaznický limit / norma",
            options=standards_df.index,
            format_func=lambda x: standards_df.loc[x, "norm_name"],
        )
        std_id = standards_df.loc[selected_std_idx, "id"]
        std_name = standards_df.loc[selected_std_idx, "norm_name"]
      else:
        st.warning("Pro tento díl není definován limit.")
        std_id, std_name = None, "Neznámá norma"

    st.markdown("---")

    with st.form("inspection_form"):
      col_a, col_b = st.columns(2)
      with col_a:
        insp_name = st.text_input("Jméno technika", value="Jan Novák")
        filt_no = st.text_input("Číslo filtru")
      with col_b:
        filt_lot = st.text_input("Šarže filtru")
        ref_unit = st.selectbox(
            "Referenční jednotka (A=plocha, V=objem, N=kus)", ["A", "V", "N"]
        )

      vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
      entered_levels = {}
      class_cols = st.columns(len(vda_classes))
      for i, s_class in enumerate(vda_classes):
        entered_levels[s_class] = class_cols[i].text_input(
            s_class, value="", placeholder="-", key=f"cls_{s_class}"
        )

      col_q1, col_q2, col_q3 = st.columns(3)
      with col_q1:
        fibers_count = st.number_input(
            "Vlákna (Fibers)", min_value=0, value=0, step=1
        )
      with col_q2:
        metallic_ref_count = st.number_input(
            "Kovové lesklé částice", min_value=0, value=0, step=1
        )
      with col_q3:
        metallic_nonref_count = st.number_input(
            "Kovové nelesklé částice", min_value=0, value=0, step=1
        )

      note = st.text_area("Poznámka k měření")
      sub_btn = st.form_submit_button(
          "Vyhodnotit a uložit do databáze", type="primary"
      )

    if sub_btn:
      if not filt_no or not std_id:
        st.error("Vyplňte číslo filtru a vyberte normu.")
      else:
        ccc_parts, valid_levels = [], {}
        for s_class, a_level_str in entered_levels

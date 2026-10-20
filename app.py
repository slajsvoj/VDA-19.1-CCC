import datetime
import io
import socket
import urllib.parse
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

# CSS pro obarvení tlačítka "Nové vyhodnocení" na červeno
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

# Supabase Connection Pooler (port 6543)
DB_HOST = "db.ywyicopmesmwtkjewbfk.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PORT = "6543"

st.sidebar.header("Připojení k databázi")
DB_PASSWORD = st.sidebar.text_input("Heslo k databázi", type="password")


def get_db_connection():
  try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require",
        connect_timeout=10,
    )
    return conn
  except Exception as e:
    try:
      ipv4_addr = socket.getaddrinfo(
          DB_HOST, int(DB_PORT), socket.AF_INET
      )[0][4][0]
      conn = psycopg2.connect(
          host=ipv4_addr,
          database=DB_NAME,
          user=DB_USER,
          password=DB_PASSWORD,
          port=DB_PORT,
          sslmode="require",
          connect_timeout=10,
      )
      return conn
    except Exception as inner_e:
      st.sidebar.error(
          "Chyba připojení k Supabase přes port 6543. Zkontroluj heslo nebo"
          f" síťové připojení. Detail: {e}"
      )
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

  try:
    pdfmetrics.registerFont(TTFont("Arial", "/Library/Fonts/Arial.ttf"))
    font_name = "Arial"
  except:
    try:
      path = "/System/Library/Fonts/Supplemental/Arial.ttf"
      pdfmetrics.registerFont(TTFont("Arial", path))
      font_name = "Arial"
    except:
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

  elements = []

  elements.append(
      Paragraph("LABORATORNÍ PROTOKOL TECHNICKÉ ČISTOTY", title_style)
  )
  elements.append(
      Paragraph("Vyhodnocení dle normy VDA 19.1 / ISO 16232", subtitle_style)
  )

  current_date = datetime.date.today().strftime("%d.%m.%Y")
  meta_data = [
      [
          Paragraph("<b>Označení dílu:</b>", cell_style),
          Paragraph(comp_name, cell_style),
          Paragraph("<b>Datum měření:</b>", cell_style),
          Paragraph(current_date, cell_style),
      ],
      [
          Paragraph("<b>Zákaznická norma:</b>", cell_style),
          Paragraph(std_name, cell_style),
          Paragraph("<b>Jméno technika:</b>", cell_style),
          Paragraph(inspector_name, cell_style),
      ],
      [
          Paragraph("<b>Číslo filtru:</b>", cell_style),
          Paragraph(filter_no, cell_style),
          Paragraph("<b>Šarže filtru:</b>", cell_style),
          Paragraph(filter_lot if filter_lot else "-", cell_style),
      ],
      [
          Paragraph("<b>Referenční jednotka:</b>", cell_style),
          Paragraph(ref_unit, cell_style),
          Paragraph("<b>Laboratorní stav:</b>", cell_style),
          Paragraph("Kompletní analýza", cell_style),
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
      [[Paragraph(f"<b>CCC kód:</b> &nbsp;&nbsp; {ccc_string}", ccc_style)]],
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
    res_text = "CELKOVÝ VÝSLEDEK: NEVYHOVUJE (NOT MET)"
    res_color = colors.HexColor("#fee2e2")
    res_text_color = colors.HexColor("#991b1b")
  else:
    res_text = "CELKOVÝ VÝSLEDEK: SPLNĚNO (MET)"
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
      Paragraph("<b>Velikostní třída</b>", cell_header),
      Paragraph("<b>Rozsah velikosti</b>", cell_header),
      Paragraph("<b>Max. povolená úroveň</b>", cell_header),
      Paragraph("<b>Naměřená úroveň</b>", cell_header),
      Paragraph("<b>Stav</b>", cell_header),
  ]]

  size_ranges = {
      "B": "5 µm – 15 µm",
      "C": "15 µm – 25 µm",
      "D": "25 µm – 50 µm",
      "E": "50 µm – 100 µm",
      "F": "100 µm – 150 µm",
      "G": "150 µm – 200 µm",
      "H": "200 µm – 400 µm",
      "I": "400 µm – 600 µm",
      "J": "600 µm – 1000 µm",
      "K": "> 1000 µm",
  }

  for _, row in report_df.iterrows():
    s_class = str(row["Velikostní třída"])
    s_range = size_ranges.get(s_class, "-")
    status = str(row["Stav"])

    if status == "OK":
      status_html = '<font color="#065f46"><b>OK</b></font>'
    elif status == "NOK":
      status_html = '<font color="#991b1b"><b>NOK</b></font>'
    else:
      status_html = '<font color="#4b5563">N/A</font>'

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
          ("FONTNAME", (0, 0), (-1, -1), font_name),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 6),
          ("LEFTPADDING", (0, 0), (-1, -1), 8),
          ("RIGHTPADDING", (0, 0), (-1, -1), 8),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          (
              "ROWBACKGROUNDS",
              (0, 1),
              (-1, -1),
              [colors.white, colors.HexColor("#f8fafc")],
          ),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
      ])
  )

  elements.append(t)
  elements.append(Spacer(1, 12))

  qual_data = [
      [
          Paragraph("<b>Kvalitativní charakteristika částic (VDA 19.1)</b>", cell_header),
          Paragraph("<b>Zjištěný počet / podíl</b>", cell_header),
      ],
      [
          Paragraph("Vlákna (Fibers)", cell_style),
          Paragraph(str(fibers_count), cell_style),
      ],
      [
          Paragraph("Kovové lesklé částice (Metallic reflective)", cell_style),
          Paragraph(str(metallic_ref_count), cell_style),
      ],
      [
          Paragraph(
              "Kovové nelesklé / ostatní částice (Non-reflective)", cell_style
          ),
          Paragraph(str(metallic_nonref_count), cell_style),
      ],
  ]

  qual_table = Table(qual_data, colWidths=[340, 200])
  qual_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
          ("FONTNAME", (0, 0), (-1, -1), font_name),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (0, 0), (-1, -1), 8),
          ("RIGHTPADDING", (0, 0), (-1, -1), 8),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
          (
              "ROWBACKGROUNDS",
              (0, 1),
              (-1, -1),
              [colors.white, colors.HexColor("#f8fafc")],
          ),
      ])
  )
  elements.append(qual_table)

  if note:
    elements.append(Spacer(1, 10))
    note_data = [
        [Paragraph("<b>Poznámka k měření:</b>", cell_bold)],
        [Paragraph(note, cell_style)],
    ]
    note_table = Table(note_data, colWidths=[540])
    note_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(note_table)

  elements.append(Spacer(1, 20))

  sig_data = [[
      Paragraph(
          f"<b>Protokol vytvořil (technik):</b> {inspector_name}", cell_style
      )
  ]]
  sig_table = Table(sig_data, colWidths=[540])
  sig_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
          ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
          ("TOPPADDING", (0, 0), (-1, -1), 8),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
          ("LEFTPADDING", (0, 0), (-1, -1), 10),
      ])
  )

  elements.append(KeepTogether(sig_table))

  doc.build(elements)
  buffer.seek(0)
  return buffer


if DB_PASSWORD:
  conn = get_db_connection()
  if conn:
    st.sidebar.success("Připojeno k Supabase (Pooler)")
    st.title("Systém vyhodnocení čistoty (VDA 19.1)")

    menu_choice = st.radio(
        "Navigace",
        ["Vyhodnocení měření", "Přehled historie měření"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown("---")

    if menu_choice == "Vyhodnocení měření":
      st.subheader("Zápis měření do formuláře")
      st.write("Vyberte díl a vepište naměřené stupně pro jednotlivé třídy.")

      try:
        comp_q = "SELECT id, part_number, name FROM components"
        components_df = pd.read_sql(comp_q, conn)

        if components_df.empty:
          st.warning("V databázi nejsou uloženy žádné díly.")
        else:
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
            std_q = (
                "SELECT DISTINCT id, norm_name FROM customer_standards WHERE"
                f" component_id = '{c_id}'"
            )
            standards_df = pd.read_sql(std_q, conn)

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
              std_id = None
              std_name = "Neznámá norma"

          st.markdown("---")

          with st.form("inspection_form"):
            st.markdown("**1. Obecné údaje o měření**")
            col_a, col_b = st.columns(2)
            with col_a:
              insp_name = st.text_input("Jméno technika", value="Jan Novák")
              filt_no = st.text_input("Číslo filtru")
            with col_b:
              filt_lot = st.text_input("Šarže filtru")
              ref_unit = st.selectbox(
                  "Referenční jednotka (A=plocha, V=objem, N=kus)",
                  ["A", "V", "N"],
              )

            st.markdown("---")

            st.markdown(
                "**2. Hodnoty naměřených tříd (tvorba CCC kódu) – vepište"
                " stupně**"
            )

            with st.expander("ℹ️ Zobrazit rozsahy velikostí tříd (VDA 19.1)"):
              st.markdown("""
                            - **B:** 5 µm – 15 µm
                            - **C:** 15 µm – 25 µm
                            - **D:** 25 µm – 50 µm
                            - **E:** 50 µm – 100 µm
                            - **F:** 100 µm – 150 µm
                            - **G:** 150 µm – 200 µm
                            - **H:** 200 µm – 400 µm
                            - **I:** 400 µm – 600 µm
                            - **J:** 600 µm – 1000 µm
                            - **K:** > 1000 µm
                            """)

            st.caption(
                "Napište naměřený stupeň (např. 0, 5, 12, 00). Neměřené třídy"
                " nechávejte prázdné."
            )

            vda_classes = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
            entered_levels = {}

            class_cols = st.columns

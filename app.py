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

# Sidebar pro nastavení připojení k databázi
st.sidebar.header("Nastavení databáze")
DB_HOST = st.sidebar.text_input(
    "Database Host", value="db.ywyicopmesmwtkjewbfk.supabase.co"
)
DB_PORT = st.sidebar.text_input(
    "Database Port", value="5432"
)  # Případně 6543 pro pooler
DB_NAME = st.sidebar.text_input("Database Name", value="postgres")
DB_USER = st.sidebar.text_input("Database User", value="postgres")
DB_PASSWORD = st.sidebar.text_input("Heslo k databázi", type="password")


def get_db_connection():
  if not DB_PASSWORD:
    return None
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
          f"Chyba připojení k Supabase ({DB_PORT}): {e}. Zkontroluj hostitele a"
          " heslo."
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
    st.sidebar.success(f"Připojeno k Supabase ({DB_PORT})")
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
      except Exception as err:
        components_df = pd.DataFrame()
        st.error(f"Chyba načítání dílů z databáze: {err}")

      if components_df.empty:
        st.warning(
            "V databázi nejsou uloženy žádné díly nebo došlo k chybě načtení."
        )
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
          try:
            std_q = (
                "SELECT DISTINCT id, norm_name FROM customer_standards WHERE"
                f" component_id = '{c_id}'"
            )
            standards_df = pd.read_sql(std_q, conn)
          except Exception as err:
            standards_df = pd.DataFrame()
            st.error(f"Chyba načítání norem: {err}")

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

          class_cols = st.columns(len(vda_classes))
          for i, s_class in enumerate(vda_classes):
            val = class_cols[i].text_input(
                s_class, value="", placeholder="-", key=f"cls_{s_class}"
            )
            entered_levels[s_class] = val

          st.markdown("---")
          st.markdown("**3. Kvalitativní analýza částic (VDA 19.1)**")
          st.caption(
              "Zadejte zjištěné počty pro jednotlivé druhy částic na filtru."
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

          st.markdown("---")
          note = st.text_area("Poznámka k měření")

          sub_btn = st.form_submit_button(
              "Vyhodnotit a uložit do databáze", type="primary"
          )

        if sub_btn:
          if not filt_no:
            st.error("Vyplňte prosím číslo filtru.")
          elif not std_id:
            st.error("Nelze vyhodnotit - chybí přiřazená norma.")
          else:
            ccc_parts = []
            valid_levels = {}

            for s_class, a_level_str in entered_levels.items():
              a_level_str = a_level_str.strip()
              if a_level_str and a_level_str != "-":
                try:
                  val_int = int(a_level_str)
                  ccc_parts.append(f"{s_class} {a_level_str}")
                  valid_levels[s_class] = val_int
                except ValueError:
                  st.error(
                      f"Neplatná hodnota '{a_level_str}' ve třídě {s_class}."
                      " Zadejte celé číslo."
                  )
                  st.stop()

            if not ccc_parts:
              st.error(
                  "Musíte vyplnit hodnotu alespoň pro jednu velikostní třídu."
              )
            else:
              joined_parts = " / ".join(ccc_parts)
              generated_ccc_string = f"CCC {ref_unit}({joined_parts})"

              try:
                lim_q = (
                    "SELECT size_class, max_allowed_level FROM"
                    f" customer_standards WHERE id = '{std_id}'"
                )
                limits_df = pd.read_sql(lim_q, conn)
              except Exception as err:
                limits_df = pd.DataFrame()
                st.error(f"Chyba při načítání limitů: {err}")

              failed = False
              report = []

              for s_class, actual_val in valid_levels.items():
                lim_row = limits_df[limits_df["size_class"] == s_class]

                if not lim_row.empty:
                  max_alw = int(lim_row.iloc[0]["max_allowed_level"])
                  status = "OK"
                  if actual_val > max_alw:
                    status = "NOK"
                    failed = True

                  report.append({
                      "Velikostní třída": s_class,
                      "Povolený limit": str(max_alw),
                      "Naměřená úroveň": actual_val,
                      "Stav": status,
                  })
                else:
                  report.append({
                      "Velikostní třída": s_class,
                      "Povolený limit": "-",
                      "Naměřená úroveň": actual_val,
                      "Stav": "N/A (Není limit)",
                  })

              report_df = pd.DataFrame(report)
              eval_res = "NOT_MET" if failed else "MET"

              try:
                cur = conn.cursor()
                ins_q = (
                    "INSERT INTO inspections (component_id, standard_id,"
                    " inspector_name, filter_number, filter_lot_number,"
                    " entered_ccc_string, evaluation_result, note) VALUES (%s,"
                    " %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                )

                cur.execute(
                    ins_q,
                    (
                        c_id,
                        std_id,
                        insp_name,
                        filt_no,
                        filt_lot,
                        generated_ccc_string,
                        eval_res,
                        note,
                    ),
                )
                ins_id = cur.fetchone()[0]

                for s_class, a_level in valid_levels.items():
                  det_q = (
                      "INSERT INTO inspection_details (inspection_id,"
                      " size_class, cleanliness_level) VALUES (%s, %s, %s);"
                  )
                  cur.execute(det_q, (ins_id, s_class, a_level))

                conn.commit()
                cur.close()
              except Exception as err:
                st.error(f"Chyba při ukládání do databáze: {err}")

              st.markdown("---")
              st.subheader("Výsledek vyhodnocení")
              st.info(f"**CCC kód:** {generated_ccc_string}")

              if failed:
                st.error("NEVYHOVUJE - Limity čistoty byly překročeny!")
              else:
                st.success("SPLNĚNO - Všechny kontrolované třídy jsou v limitu.")

              st.dataframe(report_df, use_container_width=True)

              pdf_data = create_pdf_report(
                  comp_name,
                  std_name,
                  filt_no,
                  filt_lot,
                  insp_name,
                  ref_unit,
                  generated_ccc_string,
                  report_df,
                  failed,
                  note,
                  fibers_count,
                  metallic_ref_count,
                  metallic_nonref_count,
              )

              btn_col1, btn_col2 = st.columns(2)
              with btn_col1:
                st.download_button(
                    label="Stáhnout protokol (PDF)",
                    data=pdf_data,
                    file_name=f"protokol_cistoty_{filt_no}.pdf",
                    mime="application/pdf",
                )
              with btn_col2:
                if st.button("Nové vyhodnocení"):
                  st.rerun()

    elif menu_choice == "Přehled historie měření":
      st.subheader("Historie provedených měření")

      try:
        hist_q = (
            'SELECT i.inspection_date AS "Datum", c.part_number AS "Číslo'
            ' dílu", i.filter_number AS "Filtr", i.entered_ccc_string AS "CCC'
            ' kód", i.evaluation_result AS "Výsledek" FROM inspections i JOIN'
            " components c ON i.component_id = c.id ORDER BY i.inspection_date"
            " DESC;"
        )
        history_df = pd.read_sql(hist_q, conn)

        if not history_df.empty:
          st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
          st.info("Zatím nejsou uložena žádná měření.")
      except Exception as err:
        st.error(f"Chyba načítání historie: {err}")

    conn.close()
else:
  st.info("Zadejte heslo k databázi v levém panelu.")

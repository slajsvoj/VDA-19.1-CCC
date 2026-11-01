import datetime, io, math, os, uuid, urllib.request
from enum import Enum
import pandas as pd, numpy as np, plotly.graph_objects as go, matplotlib.pyplot as plt, psycopg2
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image as RLImage
import streamlit as st

st.set_page_config(page_title="VDA 19.1 - Technická čistota", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# BEZPEČNÉ CSS (Nerozbije ikony ani postranní panel)
# =====================================================================
st.markdown("""
<style>
    .res-ok { background-color: #d1fae5; color: #065f46; padding: 1rem; border-radius: 8px; font-weight: bold; border: 1px solid #059669; margin-bottom: 1rem; }
    .res-nok { background-color: #fee2e2; color: #991b1b; padding: 1rem; border-radius: 8px; font-weight: bold; border: 1px solid #dc2626; margin-bottom: 1rem; }
    .res-warn { background-color: #fef3c7; color: #92400e; padding: 1rem; border-radius: 8px; font-weight: bold; border: 1px solid #d97706; margin-bottom: 1rem; }
    .ccc-chip { background-color: #eff6ff; color: #1e3a8a; border: 1px solid #bfdbfe; padding: 0.5rem 1rem; border-radius: 6px; font-weight: bold; font-family: monospace; font-size: 1.1rem; display: inline-block; margin-bottom: 1rem;}
    /* Bezpečná modrá pro primární tlačítka */
    button[kind="primary"] { background-color: #2563eb !important; color: white !important; border: none !important; }
    button[kind="primary"]:hover { background-color: #1d4ed8 !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# LOGIKA A VÝPOČTY VDA
# =====================================================================
VDA_CLASSES = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
VDA_LEVELS = {'00':0, '0':1, '1':2, '2':4, '3':8, '4':16, '5':32, '6':64, '7':130, '8':250, '9':500, '10':1000, '11':2000, '12':4000, '13':8000, '14':16000, '15':32000, '16':64000, '17':130000, '18':250000, '19':500000, '20':1000000}

def get_db(pwd):
    if not pwd: return None
    try: return psycopg2.connect(host="aws-0-eu-west-1.pooler.supabase.com", database="postgres", user="postgres.ywyicopmesmwtkjewbfk", password=pwd, port="6543", sslmode="require")
    except: return None

def calc_lvl(cnt, area):
    if cnt <= 0: return '00'
    norm = cnt * (1000.0 / area) if area > 0 else cnt
    for c, l in sorted(VDA_LEVELS.items(), key=lambda x: x[1]):
        if norm <= l: return c
    return '20'

def gen_ccc(codes, ref="A"):
    mc = [(c, str(codes.get(c,'00')).zfill(2) if len(str(codes.get(c,'00')))==1 and str(codes.get(c,'00'))!='00' else str(codes.get(c,'00'))) for c in VDA_CLASSES]
    res, i = [], 0
    while i < len(mc):
        cg, lg = mc[i]
        j = i + 1
        while j < len(mc) and mc[j][1] == lg:
            cg += mc[j][0]; j += 1
        res.append(f"{cg}{lg}"); i = j
    return f"{ref}({'/'.join(res)})"

def make_pdf(meta, df, res_txt, failed, warn, grav, db_grav):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Fonty pro češtinu
    f_dir = "fonts"
    os.makedirs(f_dir, exist_ok=True)
    r_reg, r_bld = os.path.join(f_dir, "R.ttf"), os.path.join(f_dir, "RB.ttf")
    if not os.path.exists(r_reg): urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", r_reg)
    if not os.path.exists(r_bld): urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", r_bld)
    try: pdfmetrics.registerFont(TTFont('Rob', r_reg)); pdfmetrics.registerFont(TTFont('RobB', r_bld)); fn, fnb = 'Rob', 'RobB'
    except: fn, fnb = 'Helvetica', 'Helvetica-Bold'
    
    def P(txt, b=False, s=8, c="#1f2937", a=0): return Paragraph(txt, ParagraphStyle("", fontName=fnb if b else fn, fontSize=s, textColor=colors.HexColor(c), alignment=a))
    def T(data, cw, bg, grid=0.5): 
        t = Table(data, colWidths=cw)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(bg)), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), grid, colors.HexColor("#cbd5e1"))]))
        return t

    ele = [P("INSPECTION REPORT: VDA 19.1", True, 11, "#111827", 1), Spacer(1,10)]
    md = [
        [P("Číslo zakázky:", True), P(meta.get('ord','-')), P("Zákazník:", True), P(meta.get('cust','-'))],
        [P("Protokol č.:", True), P(meta.get('rep','-')), P("Kontakt:", True), P(meta.get('cont','-'))],
        [P("Díl:", True), P(meta.get('part','-')), P("Norma:", True), P(meta.get('std','-'))],
        [P("Plocha Ac:", True), P(f"{meta.get('area',1000)} cm²"), P("Filtr:", True), P(meta.get('filt','-'))]
    ]
    mt = Table(md, colWidths=[100, 160, 100, 180])
    mt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8fafc")), ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1"))]))
    ele.extend([mt, Spacer(1, 8), P(f"CCC Kód: {meta.get('ccc','')}", True, 9, "#1e3a8a"), Spacer(1, 8)])
    
    # Gravimetrie
    gd = [[P("Gravimetrie",True,7,"#fff"), P("Naměřeno",True,7,"#fff"), P("Limit",True,7,"#fff"), P("Stav",True,7,"#fff")]]
    g_st = '<font color="#991b1b"><b>NOK</b></font>' if grav > db_grav else '<font color="#065f46"><b>OK</b></font>'
    gd.append([P("Zbytková hmotnost"), P(f"{grav} mg"), P(f"{db_grav} mg"), P(g_st)])
    ele.extend([T(gd, [250, 100, 100, 90], "#334155"), Spacer(1, 8)])

    ele.append(P(f"VÝSLEDEK: {res_txt.upper()}", True, 10, "#991b1b" if failed else ("#92400e" if warn else "#065f46"), 1))
    ele.append(Spacer(1, 10))

    td = [[P("Třída",True,7,"#fff"), P("Kov",True,7,"#fff"), P("Nekov",True,7,"#fff"), P("Vlákna",True,7,"#fff"), P("Celkem",True,7,"#fff"), P("Limit",True,7,"#fff"), P("CCC",True,7,"#fff"), P("Stav",True,7,"#fff")]]
    for _, r in df.iterrows():
        s = str(r["Stav"])
        st_txt = '<font color="#065f46"><b>OK</b></font>' if s in ["splněno", "OK"] else ('<font color="#991b1b"><b>NOK</b></font>' if s=="NOK" else '<font color="#b45309"><b>VAR</b></font>')
        td.append([P(r["Třída"],True), P(str(r["Kov"])), P(str(r["Nekov"])), P(str(r["Vlákna"])), P(str(r["Celkem"])), P(str(r["Limit"])), P(str(r["CCC"])), P(st_txt)])
    
    ele.extend([T(td, [40, 50, 50, 50, 60, 60, 60, 60], "#1e293b"), Spacer(1, 10)])
    doc.build(ele)
    return buf.getvalue()

# =====================================================================
# UI APLIKACE
# =====================================================================
st.sidebar.title("Připojení k DB")
pwd = st.sidebar.text_input("Zadejte heslo", type="password")
conn = get_db(pwd)

if conn:
    st.sidebar.success("Připojeno k DB")
    if "tab" not in st.session_state: st.session_state.tab = "Menu"
    if st.session_state.tab != "Menu" and st.sidebar.button("← Zpět do menu"):
        st.session_state.tab = "Menu"; st.rerun()

    if st.session_state.tab == "Menu":
        st.title("Technická čistota (VDA 19.1)")
        c1, c2, c3 = st.columns(3)
        if c1.button("Zápis z reportu", use_container_width=True): st.session_state.tab = "Eval"; st.rerun()
        if c2.button("Správa norem", use_container_width=True): st.session_state.tab = "Std"; st.rerun()
        if c3.button("Historie měření", use_container_width=True): st.session_state.tab = "Hist"; st.rerun()

    elif st.session_state.tab == "Std":
        st.header("Správa podnikových norem")
        comps = pd.read_sql("SELECT id, part_number, name FROM components", conn)
        if comps.empty: st.warning("Nejsou v DB žádné díly."); st.stop()
        
        with st.form("add_std"):
            c1, c2 = st.columns(2)
            c_id = c1.selectbox("Díl", comps['id'], format_func=lambda x: comps[comps['id']==x]['part_number'].values[0])
            n_name = c2.text_input("Název normy")
            grav = st.number_input("Gravimetrický limit (mg)", value=0.5)
            
            st.markdown("**Limity kódových úrovní (0 pro bez limitu)**")
            cols = st.columns(len(VDA_CLASSES))
            lims = {cls: cols[i].text_input(cls, value="0") for i, cls in enumerate(VDA_CLASSES)}
                
            if st.form_submit_button("Uložit normu", type="primary"):
                if n_name:
                    cur = conn.cursor()
                    for c, v in lims.items():
                        if v.strip() and v != "0":
                            cur.execute("INSERT INTO customer_standards (id, component_id, norm_name, size_class, max_allowed_level, gravimetry_limit_mg) VALUES (%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), c_id, n_name, c, float(v), grav))
                    conn.commit()
                    st.success("Norma uložena!")
                else: st.error("Zadejte název normy.")

    elif st.session_state.tab == "Eval":
        if st.session_state.get("done"):
            cls_name = 'res-nok' if st.session_state.failed else ('res-warn' if st.session_state.warn else 'res-ok')
            st.markdown(f"<div class='{cls_name}'>VÝSLEDEK: {st.session_state.res_msg.upper()}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ccc-chip'>CCC kód: {st.session_state.ccc}</div>", unsafe_allow_html=True)
            st.dataframe(st.session_state.df, use_container_width=True)
            c1, c2 = st.columns(2)
            c1.download_button("Stáhnout PDF protokol", st.session_state.pdf, "protokol.pdf", "application/pdf", type="primary")
            if c2.button("Nové vyhodnocení"): st.session_state.done = False; st.rerun()
        else:
            st.header("Zápis dat a vyhodnocení")
            comps = pd.read_sql("SELECT id, part_number, name FROM components", conn)
            if comps.empty: st.warning("Přidejte nejprve díly."); st.stop()
            
            c1, c2 = st.columns(2)
            sel_c = c1.selectbox("Díl", comps.index, format_func=lambda x: f"{comps.loc[x, 'part_number']} ({comps.loc[x, 'name']})")
            cid, cname = comps.loc[sel_c, "id"], comps.loc[sel_c, 'part_number']
            
            stds = pd.read_sql(f"SELECT DISTINCT id, norm_name FROM customer_standards WHERE component_id='{cid}'", conn)
            std_id = c2.selectbox("Norma", stds['id'] if not stds.empty else [], format_func=lambda x: stds[stds['id']==x]['norm_name'].values[0]) if not stds.empty else None
            
            db_lims, db_grav = {}, 0.5
            if std_id:
                for _, r in pd.read_sql(f"SELECT size_class, max_allowed_level FROM customer_standards WHERE id='{std_id}'", conn).iterrows(): db_lims[r['size_class'].strip()] = int(r['max_allowed_level'])
                try: db_grav = float(pd.read_sql(f"SELECT gravimetry_limit_mg FROM customer_standards WHERE id='{std_id}' LIMIT 1", conn).iloc[0,0])
                except: pass

            with st.expander("Obecné informace a Gravimetrie", expanded=True):
                ca, cb, cc = st.columns(3)
                ord_n = ca.text_input("Číslo zakázky")
                rep_n = cb.text_input("Číslo protokolu")
                filt_n = cc.text_input("Číslo filtru", "F-01")
                area = st.number_input("Smáčená plocha Ac [cm²]", value=1000.0)
                grav_val = st.number_input(f"Zbytková hmotnost [mg] (Limit DB: {db_grav})", value=0.0, format="%.4f")

            st.markdown("**Matice počtu částic podle velikostí**")
            mat = {}
            for cls in VDA_CLASSES:
                cx1, cx2, cx3, cx4 = st.columns([1,2,2,2])
                cx1.write(f"**{cls}** (Limit: {db_lims.get(cls, 0)})")
                mat[cls] = {
                    "k": cx2.text_input(f"Kov {cls}", label_visibility="collapsed", placeholder="Kov"),
                    "n": cx3.text_input(f"Nekov {cls}", label_visibility="collapsed", placeholder="Nekov"),
                    "f": cx4.text_input(f"Vlákna {cls}", label_visibility="collapsed", placeholder="Vlákna")
                }

            if st.button("Vyhodnotit a uložit", type="primary", use_container_width=True):
                with st.spinner("Zpracovávám..."):
                    rep, codes, failed, warn = [], {}, False, False
                    if grav_val > db_grav: failed = True
                    
                    for c in VDA_CLASSES:
                        k = int(mat[c]["k"]) if mat[c]["k"] else 0
                        n = int(mat[c]["n"]) if mat[c]["n"] else 0
                        f = int(mat[c]["f"]) if mat[c]["f"] else 0
                        tot = k + n + f
                        lvl = calc_lvl(tot, area)
                        codes[c] = lvl
                        
                        lim = db_lims.get(c, 0)
                        num_lvl = int(lvl) if lvl != '00' else 0
                        if lim > 0:
                            if num_lvl > lim: stat = "NOK"; failed = True
                            elif num_lvl == lim: stat = "VAR"; warn = True
                            else: stat = "OK"
                        else: stat = "OK"
                        
                        rep.append({"Třída": c, "Kov": k, "Nekov": n, "Vlákna": f, "Celkem": tot, "Limit": str(lim), "CCC": lvl, "Stav": stat})
                    
                    ccc_str = gen_ccc(codes)
                    res_msg = "Specifikace nesplněna" if failed else ("Varování" if warn else "Specifikace splněna")
                    df = pd.DataFrame(rep)
                    
                    cur = conn.cursor()
                    cur.execute("INSERT INTO inspections (component_id, standard_id, filter_number, entered_ccc_string, evaluation_result) VALUES (%s,%s,%s,%s,%s) RETURNING id;", (cid, std_id, filt_n, ccc_str, res_msg))
                    iid = cur.fetchone()[0]
                    for c, lvl in codes.items(): cur.execute("INSERT INTO inspection_details (inspection_id, size_class, cleanliness_level) VALUES (%s,%s,%s);", (iid, c, int(lvl)))
                    conn.commit()
                    
                    meta = {'ord': ord_n, 'rep': rep_n, 'part': cname, 'std': "DB Norma", 'area': area, 'filt': filt_n, 'ccc': ccc_str}
                    st.session_state.pdf = make_pdf(meta, df, res_msg, failed, warn, grav_val, db_grav)
                    st.session_state.done, st.session_state.failed, st.session_state.warn, st.session_state.res_msg, st.session_state.ccc, st.session_state.df = True, failed, warn, res_msg, ccc_str, df
                    st.rerun()

    elif st.session_state.tab == "Hist":
        st.header("Historie měření")
        try:
            h_df = pd.read_sql('SELECT i.inspection_date as "Datum", c.part_number as "Díl", i.filter_number as "Filtr", i.entered_ccc_string as "CCC", i.evaluation_result as "Výsledek" FROM inspections i JOIN components c ON i.component_id = c.id ORDER BY i.inspection_date DESC;', conn)
            st.dataframe(h_df, use_container_width=True, hide_index=True)
        except: st.info("Zatím nejsou uložena žádná vyhodnocení.")
else:
    st.info("Nejprve zadejte heslo k databázi v postranním panelu vlevo.")

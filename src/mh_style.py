# MH Style and Presentation System
# Matches the Executive Monitoring Weekly Report (Edisi Spesial Mingguan)

# pyrefly: ignore[missing-import]
import streamlit as st
import os
import base64

_LOGO_B64_CACHE = None

def get_logo_b64():
    global _LOGO_B64_CACHE
    if _LOGO_B64_CACHE is not None:
        return _LOGO_B64_CACHE
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(curr_dir, '..', 'static', 'logo.svg')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            _LOGO_B64_CACHE = f"data:image/svg+xml;base64,{b64}"
            return _LOGO_B64_CACHE
    return ""

def render_logo_badge(size=22):
    b64 = get_logo_b64()
    if b64:
        return f'<img src="{b64}" style="width:{size}px; height:{size}px; vertical-align:middle; border-radius:50%; display:inline-block; flex-shrink:0; box-shadow:0 1px 4px rgba(0,0,0,0.25);" alt="Logo" />'
    return '<span style="background:#F6B100; color:#0F172A; font-weight:800; font-size:12px; padding:2px 7px; border-radius:4px; letter-spacing:0.5px;">PPI</span>'


def render_html(html_str):
    """
    Cleans leading/trailing whitespace from every line so Streamlit
    does not mistake HTML indentation for markdown code blocks.
    """
    clean_lines = [line.strip() for line in html_str.strip().split('\n') if line.strip()]
    st.markdown("".join(clean_lines), unsafe_allow_html=True)

def render_mh_top_bar(slide_num=None):
    """
    Renders top dark navy bar with circular logo emblem and MONITORING KEBIJAKAN PUBLIK title,
    plus right-aligned Slide pill badge.
    """
    slide_badge = f"""<span style="background:#2563EB; color:#FFFFFF; font-weight:600; font-size:11px; padding:3px 12px; border-radius:14px; letter-spacing:0.3px;">Slide {slide_num}</span>""" if slide_num else ""
    logo_badge = render_logo_badge(size=23)
    html = f"""<div style="background:#0F2942; border-radius:6px; padding:7px 16px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; box-shadow:0 1px 3px rgba(0,0,0,0.06);">
<div style="display:flex; align-items:center; gap:9px;">
{logo_badge}
<span style="color:#FFFFFF; font-weight:700; font-size:12.5px; letter-spacing:0.8px;">MONITORING KEBIJAKAN PUBLIK</span>
</div>
<div>{slide_badge}</div>
</div>"""
    render_html(html)

def render_mh_title(title, subtitle=None, guide_text=None):
    """
    Renders deep navy title, subtitle, and yellow PANDUAN BACA guidance bar.
    """
    guide_html = f"""<div style="display:flex; align-items:flex-start; gap:8px; background:#F8FAFC; border:1px solid #E2E8F0; padding:6px 12px; border-radius:6px; margin-top:8px;">
<span style="background:#F6B100; color:#0F172A; font-weight:800; font-size:10px; padding:2px 8px; border-radius:10px; white-space:nowrap; letter-spacing:0.4px;">PANDUAN BACA</span>
<span style="font-size:11.5px; color:#475569; font-weight:500; line-height:1.4;">{guide_text}</span>
</div>""" if guide_text else ""
    
    sub_html = f"""<div style="color:#334155; font-size:14.5px; font-weight:600; margin-top:3px;">{subtitle}</div>""" if subtitle else ""

    html = f"""<div style="margin-bottom:14px;">
<h1 style="color:#0F2942; font-size:24px; font-weight:800; margin:0; font-family:'Plus Jakarta Sans',sans-serif; letter-spacing:-0.2px;">{title}</h1>
{sub_html}
{guide_html}
</div>"""
    render_html(html)

def render_kpi_chips(chips):
    """
    Renders horizontal flex row of KPI chips.
    Each chip in chips dict:
      {
        'label': 'Penyebutan Lembaga',
        'val': '2.935',
        'sub': 'turun dari 3.375',
        'dot': '#2563EB',   # dot color
        'val_color': '#0F172A' # optional
      }
    """
    chips_html = []
    for c in chips:
        dot = c.get('dot', '#2563EB')
        val_col = c.get('val_color', '#0F172A')
        label = c.get('label', '')
        val = c.get('val', '')
        sub = c.get('sub', '')
        
        chip = f"""<div style="flex:1; min-width:110px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:8px 12px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
<div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
<span style="width:7px; height:7px; border-radius:50%; background:{dot}; display:inline-block;"></span>
<span style="font-size:11px; font-weight:600; color:#64748B;">{label}</span>
</div>
<div style="font-size:21px; font-weight:800; color:{val_col}; line-height:1.2; font-family:'Plus Jakarta Sans',sans-serif;">{val}</div>
<div style="font-size:10px; color:#64748B; margin-top:2px;">{sub}</div>
</div>"""
        chips_html.append(chip)

    html = f"""<div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:14px;">{"".join(chips_html)}</div>"""
    render_html(html)

def render_status_badge(text, variant="default"):
    """
    Returns HTML string for a colored status badge.
    Enforces white-space:nowrap and inline-block so status text never breaks into multiple lines.
    """
    styles = {
        "green": "background:#ECFDF5; color:#059669; border:1px solid #A7F3D0;",
        "amber": "background:#FEF3C7; color:#D97706; border:1px solid #FDE68A;",
        "red": "background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;",
        "blue": "background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;",
        "purple": "background:#F5F3FF; color:#7C3AED; border:1px solid #DDD6FE;",
        "slate": "background:#F1F5F9; color:#475569; border:1px solid #CBD5E1;",
    }
    st_style = styles.get(variant, styles["slate"])
    return f"""<span style="{st_style} font-size:10px; font-weight:700; padding:2.5px 8px; border-radius:4px; letter-spacing:0.3px; text-transform:uppercase; white-space:nowrap; display:inline-block; line-height:1.2;">{text}</span>"""

def render_callout_target(text):
    """
    Renders orange bordered callout with bullseye icon.
    """
    html = f"""<div style="background:#FFFFFF; border:1.5px solid #FDBA74; border-radius:8px; padding:10px 16px; display:flex; align-items:flex-start; gap:12px; margin-top:14px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
<div style="min-width:20px; height:20px; border-radius:50%; border:2px solid #EA580C; display:flex; align-items:center; justify-content:center; color:#EA580C; font-size:11px; font-weight:800; margin-top:1px;">🎯</div>
<div style="font-size:12.5px; font-weight:600; color:#0F172A; line-height:1.5;">{text}</div>
</div>"""
    render_html(html)

def render_prioritas_banner(items):
    """
    Renders Dark Navy PRIORITAS container with 3 columns.
    items: list of tuples (title, description)
    """
    cols_html = []
    for title, desc in items:
        col = f"""<div style="flex:1; min-width:200px;">
<div style="color:#FFFFFF; font-weight:700; font-size:12.5px; margin-bottom:4px;">{title}</div>
<div style="color:#CBD5E1; font-size:11px; line-height:1.45;">{desc}</div>
</div>"""
        cols_html.append(col)

    html = f"""<div style="background:#0F2942; border-radius:8px; padding:12px 18px; color:#FFFFFF; margin-top:12px;">
<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
<span style="background:#2563EB; color:#FFFFFF; font-weight:800; font-size:10px; padding:2px 8px; border-radius:3px; letter-spacing:0.6px;">PRIORITAS</span>
</div>
<div style="display:flex; flex-wrap:wrap; gap:16px;">
{"".join(cols_html)}
</div>
</div>"""
    render_html(html)

def render_mh_footer(source_text, date_label=None):
    if not date_label:
        date_label = st.session_state.get('current_date_display', 'Periode Pemantauan Terkini')
    """
    Renders standardized footer with blue square icon and source footnote.
    """
    html = f"""<div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E2E8F0; padding-top:8px; margin-top:18px; font-size:10.5px; color:#94A3B8;">
<div style="display:flex; align-items:center; gap:6px;">
<span style="background:#2563EB; width:10px; height:10px; border-radius:2px; display:inline-block;"></span>
<span style="font-weight:700; color:#475569; font-size:11px;">{date_label}</span>
</div>
<div style="font-size:9.5px; color:#94A3B8; text-align:right; max-width:70%; line-height:1.4;">
Sumber: {source_text}
</div>
</div>"""
    render_html(html)

def render_chapter_break(chapter_num, title, description, active_step, contents_list):
    """
    Renders full Chapter Break Slide (e.g. Chapter 01, 02, 03).
    active_step: 1 ('The Overview'), 2 ('The Deep Dive'), 3 ('The Action')
    contents_list: list of tuples (slide_num, title)
    """
    render_mh_top_bar(slide_num=None)
    
    # Progress stepper
    steps = [
        (1, "The Overview", "gambaran pekan"),
        (2, "The Deep Dive", "analisis berkas & sorotan"),
        (3, "The Action", "tindakan")
    ]
    stepper_html = []
    for num, st_name, st_desc in steps:
        is_active = (num == active_step)
        dot_bg = "#2563EB" if is_active else "#E2E8F0"
        dot_border = "3px solid #BFDBFE" if is_active else "none"
        text_col = "#0F2942" if is_active else "#94A3B8"
        font_wt = "700" if is_active else "500"
        stepper_html.append(f"""<div style="text-align:center; min-width:130px;">
<div style="width:16px; height:16px; border-radius:50%; background:{dot_bg}; border:{dot_border}; margin:0 auto 6px auto;"></div>
<div style="font-size:11.5px; font-weight:{font_wt}; color:{text_col};">{st_name}</div>
<div style="font-size:9.5px; color:#94A3B8;">{st_desc}</div>
</div>""")

    # Content cards grid
    items_html = []
    for s_num, s_title in contents_list:
        items_html.append(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px 12px; display:flex; align-items:center; gap:10px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
<span style="background:#EFF6FF; color:#2563EB; font-weight:800; font-size:11px; padding:2px 8px; border-radius:4px;">{s_num}</span>
<span style="font-size:12px; font-weight:600; color:#1E293B;">{s_title}</span>
</div>""")

    html = f"""<div style="text-align:center; padding:10px 0 20px 0;">
<div style="font-size:32px; font-weight:800; color:#2563EB; letter-spacing:0.5px; font-family:'Plus Jakarta Sans',sans-serif;">CHAPTER {chapter_num:02d}</div>
<div style="font-size:22px; font-weight:700; color:#0F2942; margin:2px 0 8px 0;">{title}</div>
<div style="font-size:12.5px; color:#64748B; max-width:650px; margin:0 auto 24px auto; line-height:1.5;">{description}</div>
<div style="display:flex; justify-content:center; align-items:flex-start; gap:40px; margin-bottom:28px;">
{"".join(stepper_html)}
</div>
<div style="text-align:left; max-width:800px; margin:0 auto;">
<div style="font-size:11px; font-weight:800; color:#94A3B8; letter-spacing:0.8px; margin-bottom:10px; text-transform:uppercase;">DAFTAR ISI BAB INI</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
{"".join(items_html)}
</div>
</div>
</div>"""
    render_html(html)

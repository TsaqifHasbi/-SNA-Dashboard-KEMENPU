# Clean Header and Footer (Academic & Executive Policy Intelligence)
# Neutral executive layout - Executive intelligence layout, NO slide number in footer.

# pyrefly: ignore[missing-import]
import streamlit as st

def render_html(html_str):
    """
    Strips leading and trailing whitespace from every line in html_str,
    guaranteeing that Streamlit will NEVER convert HTML markup into markdown code blocks.
    """
    clean_lines = [line.strip() for line in html_str.strip().split('\n') if line.strip()]
    st.markdown("".join(clean_lines), unsafe_allow_html=True)

def render_slide_header(title, breadcrumb=""):
    """
    Renders clean executive header with bold orange title, breadcrumb,
    and neutral academic intelligence badge (neutral executive badge).
    Transparent background ensures it adapts seamlessly to any page background.
    """
    html = f"""<div style="background:transparent; border-bottom: 2.5px solid #EA580C; padding: 4px 0 12px 0; margin-bottom: 16px;">
<div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:10px;">
<div>
<h1 style="color:#EA580C; font-size:26px; font-weight:800; margin:0 0 4px 0; text-transform:uppercase; letter-spacing:0.5px; font-family:'Plus Jakarta Sans',sans-serif;">{title}</h1>
<div style="font-size:12.5px; font-weight:600; color:#64748B;">{breadcrumb}</div>
</div>
<div style="text-align:right;">
<span style="font-size:11px; font-weight:700; color:#0F172A; text-transform:uppercase; letter-spacing:0.8px; background:#FFFFFF; padding:5px 12px; border-radius:6px; border:1px solid #E2E8F0; display:inline-block; box-shadow:0 1px 2px rgba(0,0,0,0.03);">MEDIA & POLICY INTELLIGENCE</span>
</div>
</div>
</div>"""
    render_html(html)

def render_slide_footer(slide_num=None):
    """
    Renders clean academic divider footer.
    Completely eliminates page numbers, slide counts, and origami corner badges.
    """
    html = """<div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E2E8F0; padding-top:12px; margin-top:24px;">
<div style="font-size:11px; color:#94A3B8; font-weight:500;">Platform Intelijen Opini Publik & Social Network Analysis • IndoBERT Deep Learning</div>
<div style="font-size:11px; color:#94A3B8; font-weight:600;">Pemantauan Kebijakan Publik Menuju 2029</div>
</div>"""
    render_html(html)

def fmt_val(n):
    """
    Formats large numbers into clean K, M, B strings.
    """
    if n is None: return "0"
    try:
        n = float(n)
    except (ValueError, TypeError):
        return "0"
    if n >= 1e9: return f"{n/1e9:.1f}B"
    elif n >= 1e6: return f"{n/1e6:.1f}M"
    elif n >= 1e3:
        val = n / 1e3
        return f"{val:.1f}K" if val < 100 else f"{val:.0f}K"
    return f"{int(n):,}"

def _chart_layout(height=300, **kwargs):
    """
    Standard clean Plotly layout matching executive reports.
    """
    layout = dict(
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#FFFFFF',
        margin=dict(l=15, r=15, t=28, b=36),
        font=dict(family='Plus Jakarta Sans, sans-serif', size=11, color='#475569'),
        height=height,
        xaxis=dict(
            showgrid=True,
            gridcolor='#F1F5F9',
            linecolor='#E2E8F0',
            tickfont=dict(size=10, color='#64748B')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#F1F5F9',
            linecolor='#E2E8F0',
            tickfont=dict(size=10, color='#64748B')
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10.5)
        )
    )
    layout.update(kwargs)
    return layout

# Backward compatibility aliases
render_de_header = render_slide_header
render_de_footer = render_slide_footer

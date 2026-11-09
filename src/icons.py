# Professional SVG Icons for Social Media Platforms and Executive Intelligence UI
# Replaces text emojis with crisp, responsive SVG vector graphics.

PLATFORM_ICONS = {
    'tiktok': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" style="vertical-align:middle; display:inline-block;"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64c.298-.002.595.042.88.13V9.4a6.33 6.33 0 0 0-1-.08A6.34 6.34 0 0 0 3 15.66a6.34 6.34 0 0 0 10.82 4.47 6.27 6.27 0 0 0 1.95-4.46V8.75a8.28 8.28 0 0 0 4.82 1.54V6.84a4.85 4.85 0 0 1-1-.15z"/></svg>""",
    
    'instagram': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; display:inline-block;"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>""",
    
    'youtube': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" style="vertical-align:middle; display:inline-block;"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>""",
    
    'twitter': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" style="vertical-align:middle; display:inline-block;"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>""",
    
    'threads': """<span style="display:inline-flex; align-items:center; justify-content:center; width:{size}px; height:{size}px; border-radius:50%; background:{color}; color:#FFFFFF; font-size:10px; font-weight:800; font-family:'Plus Jakarta Sans',sans-serif; vertical-align:middle; line-height:1;">@</span>""",
    
    'facebook': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" style="vertical-align:middle; display:inline-block;"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>""",
    
    'news': """<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; display:inline-block;"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>"""
}

PLATFORM_COLORS = {
    'tiktok': '#111827',
    'instagram': '#E1306C',
    'youtube': '#FF0000',
    'twitter': '#0F172A',
    'threads': '#334155',
    'facebook': '#1877F2',
    'news': '#0284C7'
}

def get_platform_icon(platform_name, size=15, custom_color=None):
    """
    Returns an inline SVG icon for the given platform.
    """
    key = platform_name.lower().replace('/x', '').replace(' ', '')
    if 'twit' in key or 'x' == key: key = 'twitter'
    elif 'tik' in key: key = 'tiktok'
    elif 'insta' in key: key = 'instagram'
    elif 'you' in key: key = 'youtube'
    elif 'thread' in key: key = 'threads'
    elif 'face' in key or 'fb' in key: key = 'facebook'
    elif 'new' in key or 'berita' in key: key = 'news'
    
    template = PLATFORM_ICONS.get(key, PLATFORM_ICONS['news'])
    color = custom_color or PLATFORM_COLORS.get(key, '#64748B')
    return template.format(size=size, color=color)

def get_platform_badge(platform_name, size=14, show_name=True):
    """
    Returns an HTML badge containing the SVG icon and platform name.
    """
    icon_svg = get_platform_icon(platform_name, size=size)
    if not show_name:
        return icon_svg
    return f"""<span style="display:inline-flex; align-items:center; gap:6px;">{icon_svg} <span style="font-size:12px; font-weight:600; color:#334155;">{platform_name}</span></span>"""

"""
================================================================================
MODUL AUTENTIKASI & MANAJEMEN AKSES PENGGUNA (KEMENTERIAN PU)
================================================================================
Menyediakan fitur login, verifikasi kredensial berbasis SHA-256,
manajemen sesi (session state), tampilan login eksekutif berstandar Kemen PU,
serta widget profil dan tombol logout di sidebar.
================================================================================
"""

import os
import sys
import hashlib
import datetime
# pyrefly: ignore[missing-import]
import streamlit as st

# User accounts bawaan (Built-in Default Credentials)
# Kata sandi disimpan dalam bentuk hash SHA-256 untuk keamanan
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("kemenpu2026".encode("utf-8")).hexdigest(),
        "name": "Administrator Sistem",
        "role": "Super Admin",
        "badge_color": "#2563EB",  # Biru Kementerian
        "icon": "🛡️",
        "email": "admin.policy@pu.go.id"
    },
    "pimpinan": {
        "password_hash": hashlib.sha256("pu2026".encode("utf-8")).hexdigest(),
        "name": "Pimpinan Eksekutif",
        "role": "Pimpinan Kementerian",
        "badge_color": "#D97706",  # Emas / Amber
        "icon": "🏛️",
        "email": "pimpinan@pu.go.id"
    },
    "analis": {
        "password_hash": hashlib.sha256("analispu2026".encode("utf-8")).hexdigest(),
        "name": "Analis Kebijakan Publik",
        "role": "Tim Analis Data & AI",
        "badge_color": "#059669",  # Hijau Zamrud
        "icon": "📊",
        "email": "analis.kebijakan@pu.go.id"
    }
}


def _hash_string(val: str) -> str:
    """Mengembalikan hash SHA-256 dari string."""
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def get_all_users() -> dict:
    """
    Mengambil data pengguna terdaftar.
    Mendukung penambahan kredensial dinamis via st.secrets['auth']['users'].
    """
    users = dict(DEFAULT_USERS)
    try:
        if hasattr(st, "secrets") and "auth" in st.secrets and "users" in st.secrets["auth"]:
            secret_users = st.secrets["auth"]["users"]
            for u_id, u_data in secret_users.items():
                users[str(u_id).lower().strip()] = {
                    "password_hash": _hash_string(str(u_data.get("password", ""))) if "password" in u_data else u_data.get("password_hash", ""),
                    "name": u_data.get("name", u_id),
                    "role": u_data.get("role", "User"),
                    "badge_color": u_data.get("badge_color", "#2563EB"),
                    "icon": u_data.get("icon", "👤"),
                    "email": u_data.get("email", f"{u_id}@pu.go.id")
                }
    except Exception:
        pass
    return users


def verify_credentials(username_input: str, password_input: str):
    """
    Memverifikasi username dan kata sandi.
    Mengembalikan data user dict jika valid, atau None jika gagal.
    """
    if not username_input or not password_input:
        return None
    
    clean_user = username_input.strip().lower()
    users = get_all_users()
    
    if clean_user not in users:
        return None
    
    user_info = users[clean_user]
    input_hash = _hash_string(password_input.strip())
    
    # Validasi via hash SHA-256 atau fallback plain text jika ada di secrets
    stored_hash = user_info.get("password_hash", "")
    if input_hash == stored_hash or password_input.strip() == stored_hash:
        return user_info
        
    return None


def login_user(username: str, user_info: dict):
    """Menyimpan sesi login ke dalam st.session_state dan me-refresh halaman."""
    st.session_state["authenticated"] = True
    st.session_state["username"] = username.strip().lower()
    st.session_state["user_info"] = user_info
    st.session_state["login_time"] = datetime.datetime.now().strftime("%d %b %Y, %H:%M WIB")
    st.rerun()


def logout_user():
    """Menghapus sesi login dan mengarahkan kembali ke halaman login."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["user_info"] = None
    st.session_state["login_time"] = None
    st.rerun()


def check_authentication() -> bool:
    """
    Penjaga pintu utama aplikasi.
    Mengembalikan True jika sesi aktif.
    Jika belum login, akan langsung merender halaman login dan menghentikan eksekusi dashboard (st.stop()).
    """
    if st.session_state.get("authenticated", False) is True:
        return True
    
    render_login_page()
    st.stop()
    return False


def render_login_page():
    """Merender halaman Login bertema elegan Kementerian PU."""
    from src.mh_style import render_logo_badge

    logo_svg = render_logo_badge(size=44)
    
    # Styling khusus halaman login - Eksekutif, Rapi & Terpusat
    st.markdown("""
    <style>
        /* Sembunyikan sidebar dan header bawaan streamlit di halaman login */
        [data-testid="stSidebar"], 
        [data-testid="stHeader"] {
            display: none !important;
        }
        
        /* Background gradient elegan */
        .stApp {
            background: linear-gradient(180deg, #F8FAFC 0%, #EEF2F6 100%) !important;
            min-height: 100vh !important;
        }
        
        /* Kunci lebar container di tengah layar agar tidak melebar di layar desktop */
        .block-container,
        [data-testid="stAppViewBlockContainer"] {
            max-width: 460px !important;
            padding-top: 48px !important;
            padding-bottom: 40px !important;
            padding-left: 20px !important;
            padding-right: 20px !important;
            margin: 0 auto !important;
        }
        
        /* Card Form Terpadu */
        div[data-testid="stForm"] {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            padding: 26px 30px 22px 30px !important;
            box-shadow: 0 10px 25px -5px rgba(15, 41, 66, 0.08), 0 8px 10px -6px rgba(15, 41, 66, 0.04) !important;
        }
        
        /* Label Input */
        div[data-testid="stForm"] label p {
            font-size: 12px !important;
            font-weight: 700 !important;
            color: #1E293B !important;
            margin-bottom: 3px !important;
        }
        
        /* Input Box */
        div[data-testid="stForm"] input {
            border-radius: 9px !important;
            border: 1.5px solid #CBD5E1 !important;
            font-size: 13.5px !important;
            color: #0F172A !important;
            padding: 10px 14px !important;
            background-color: #FAFCFE !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #2563EB !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        }
        
        /* Tombol Sign In Elegan */
        div[data-testid="stForm"] button[kind="primary"],
        div[data-testid="stForm"] button {
            background: linear-gradient(135deg, #0F2942 0%, #1E3A8A 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 9px !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px !important;
            padding: 11px 20px !important;
            box-shadow: 0 4px 14px rgba(15, 41, 66, 0.22) !important;
            transition: all 0.2s ease !important;
            margin-top: 8px !important;
        }
        div[data-testid="stForm"] button[kind="primary"]:hover,
        div[data-testid="stForm"] button:hover {
            background: linear-gradient(135deg, #1A365D 0%, #2563EB 100%) !important;
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        
        /* Error Alert Box */
        div[data-testid="stAlert"] {
            border-radius: 9px !important;
            font-size: 12px !important;
            padding: 10px 14px !important;
            margin-top: 10px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 1. Header Kementerian Resmi (Di Luar & Di Atas Card)
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 22px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 68px; height: 68px; border-radius: 16px; background: linear-gradient(135deg, #0F2942 0%, #1A365D 100%); box-shadow: 0 8px 18px rgba(15, 41, 66, 0.2); margin-bottom: 12px; border: 1.5px solid rgba(255,255,255,0.15);">
            {logo_svg}
        </div>
        <div style="font-size: 10.5px; font-weight: 800; color: #D97706; text-transform: uppercase; letter-spacing: 1.8px; margin-bottom: 3px;">
            REPUBLIK INDONESIA
        </div>
        <div style="font-size: 21px; font-weight: 800; color: #0F2942; line-height: 1.25; letter-spacing: -0.4px;">
            KEMENTERIAN PEKERJAAN UMUM
        </div>
        <div style="font-size: 12px; font-weight: 600; color: #64748B; margin-top: 4px;">
            Portal Intelijen Kebijakan Publik & IndoBERT-SNA
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Card Form Terpadu (Satu Kotak Utuh Tanpa Fragmentasi)
    with st.form("login_form", clear_on_submit=False):
        st.markdown("""
        <div style="margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #F1F5F9;">
            <div style="font-size: 15px; font-weight: 800; color: #0F2942; display: flex; align-items: center; gap: 8px;">
                <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#2563EB;"></span>
                Autentikasi Akses Sistem
            </div>
            <div style="font-size: 11.5px; color: #64748B; margin-top: 3px; line-height: 1.4;">
                Silakan masukkan akun kedinasan Anda untuk mengakses data analitik.
            </div>
        </div>
        """, unsafe_allow_html=True)

        username_val = st.text_input(
            "ID Pengguna / Username",
            placeholder="Masukkan ID pengguna...",
            help="Gunakan akun kedinasan yang terdaftar."
        )
        password_val = st.text_input(
            "Kata Sandi / Password",
            type="password",
            placeholder="••••••••••••",
            help="Kata sandi bersifat rahasia."
        )
        
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "Masuk ke Sistem (Sign In)",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            user_match = verify_credentials(username_val, password_val)
            if user_match:
                st.toast(f"Selamat datang, {user_match['name']}!", icon="✅")
                login_user(username_val, user_match)
            else:
                st.error("Nama pengguna atau kata sandi tidak sesuai. Silakan periksa kembali.")

    # 3. Footer Keamanan
    st.markdown("""
    <div style="text-align: center; margin-top: 22px; font-size: 11px; color: #64748B;">
        <div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:4px; font-weight:600; color:#475569;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            <span>Sistem Informasi Terbatas • Terproteksi SHA-256</span>
        </div>
        <div>Kementerian Pekerjaan Umum Republik Indonesia • 2026</div>
    </div>
    """, unsafe_allow_html=True)


def render_user_sidebar_profile():
    """
    Merender widget identitas pengguna aktif dan tombol Logout di Sidebar.
    """
    from src.clean_header_footer import render_html

    user = st.session_state.get("user_info", {})
    if not user:
        return

    name = user.get("name", "Pengguna Terdaftar")
    role = user.get("role", "Aparatur Sipil Negara")
    badge_color = user.get("badge_color", "#2563EB")
    icon = user.get("icon", "👤")
    login_time = st.session_state.get("login_time", "Sesi Aktif")

    # Ambil inisial nama
    initials = "".join([part[0].upper() for part in name.split()[:2]]) if name else "PU"

    render_html(f"""
    <div style="background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: {badge_color}; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 12px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                {initials}
            </div>
            <div style="flex-grow: 1; min-width: 0;">
                <div style="font-size: 12px; font-weight: 700; color: #0F2942; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.2;">
                    {name}
                </div>
                <div style="display: flex; align-items: center; gap: 4px; margin-top: 3px;">
                    <span style="font-size: 9.5px; font-weight: 700; color: {badge_color}; background: {badge_color}18; padding: 1.5px 6px; border-radius: 4px; border: 1px solid {badge_color}33;">
                        {icon} {role}
                    </span>
                </div>
            </div>
        </div>
        <div style="font-size: 9px; color: #94A3B8; margin-top: 8px; padding-top: 6px; border-top: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;">
            <span>Sesi: {login_time}</span>
            <span style="color: #10B981; font-weight: 700;">● Online</span>
        </div>
    </div>
    """)

    # Tombol Logout Elegan
    if st.sidebar.button("Keluar dari Sistem (Logout)", key="btn_logout_sidebar", use_container_width=True, type="secondary"):
        logout_user()


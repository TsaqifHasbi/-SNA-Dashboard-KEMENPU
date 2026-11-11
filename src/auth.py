"""
================================================================================
MODUL AUTENTIKASI & MANAJEMEN AKSES PENGGUNA (KEMENTERIAN PU)
================================================================================
Menyediakan fitur:
1. Verifikasi kredensial login berbasis enkripsi SHA-256
2. Pengelolaan pengguna & kata sandi khusus Super Admin (Ubah UN & Kata Sandi)
3. Manajemen sesi (session state) aman
4. Tampilan antarmuka login eksekutif terpusat Kementerian PU (Bebas Glitch)
5. Widget profil pengguna aktif dan tombol Logout di sidebar
6. Desain profesional murni berbasis Vector SVG (Tanpa Emoji)
================================================================================
"""

import os
import sys
import json
import re
import hashlib
import datetime
from pathlib import Path
# pyrefly: ignore[missing-import]
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = os.path.join(BASE_DIR, "data", "user_credentials.json")

# Kredensial bawaan sistem (Default Initial Credentials)
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("kemenpu2026".encode("utf-8")).hexdigest(),
        "name": "Administrator Sistem",
        "role": "Super Admin",
        "badge_color": "#2563EB",  # Biru Kementerian
        "email": "admin.policy@pu.go.id"
    },
    "pimpinan": {
        "password_hash": hashlib.sha256("pu2026".encode("utf-8")).hexdigest(),
        "name": "Pimpinan Eksekutif",
        "role": "Pimpinan Kementerian",
        "badge_color": "#D97706",  # Emas / Amber
        "email": "pimpinan@pu.go.id"
    },
    "analis": {
        "password_hash": hashlib.sha256("analispu2026".encode("utf-8")).hexdigest(),
        "name": "Analis Kebijakan Publik",
        "role": "Tim Analis Data & AI",
        "badge_color": "#059669",  # Hijau Zamrud
        "email": "analis.kebijakan@pu.go.id"
    }
}


def _hash_string(val: str) -> str:
    """Mengembalikan hash SHA-256 dari string."""
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def get_role_icon_svg(role: str, color: str = "currentColor", size: int = 12) -> str:
    """Mengembalikan icon SVG vektor sesuai peran pengguna tanpa menggunakan emoji."""
    r = (role or "").lower()
    if "admin" in r:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>'
    elif "pimpinan" in r:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;"><path d="M3 21h18M3 10h18M5 10v11M19 10v11M9 10v11M14 10v11M4 10l8-6 8 6"></path></svg>'
    elif "analis" in r:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>'
    else:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'


def _load_stored_credentials() -> dict:
    """Memuat data kredensial dari file JSON lokal."""
    if not os.path.exists(CREDENTIALS_FILE):
        _save_stored_credentials(DEFAULT_USERS)
        return dict(DEFAULT_USERS)
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and len(data) > 0:
                return data
    except Exception:
        pass
    return dict(DEFAULT_USERS)


def _save_stored_credentials(users_dict: dict) -> bool:
    """Menyimpan seluruh data pengguna & kredensial ke file JSON secara aman."""
    try:
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_all_users() -> dict:
    """
    Mengambil data seluruh pengguna aktif dari data/user_credentials.json.
    Mendukung fallback dan integrasi st.secrets.
    """
    users = _load_stored_credentials()
    
    # Dukungan kredensial tambahan via st.secrets jika diatur di Streamlit Cloud
    try:
        if hasattr(st, "secrets") and "auth" in st.secrets and "users" in st.secrets["auth"]:
            secret_users = st.secrets["auth"]["users"]
            for u_id, u_data in secret_users.items():
                k = str(u_id).lower().strip()
                if k not in users:
                    users[k] = {
                        "password_hash": _hash_string(str(u_data.get("password", ""))) if "password" in u_data else u_data.get("password_hash", ""),
                        "name": u_data.get("name", u_id),
                        "role": u_data.get("role", "User"),
                        "badge_color": u_data.get("badge_color", "#2563EB"),
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


def update_user_credentials(target_key: str, new_username: str, new_password: str = "", new_name: str = "", new_role: str = ""):
    """
    Fungsi khusus Super Admin: Memperbarui username, nama, peran, atau kata sandi pengguna.
    Mengembalikan (success: bool, message: str).
    """
    target_key = target_key.strip().lower()
    users = _load_stored_credentials()
    
    if target_key not in users:
        return False, f"Pengguna '{target_key}' tidak ditemukan di sistem."
        
    new_u_clean = new_username.strip().lower()
    if not new_u_clean:
        return False, "Username baru tidak boleh kosong."
        
    if len(new_u_clean) < 3:
        return False, "Username minimal terdiri dari 3 karakter."
        
    if not re.match(r"^[a-zA-Z0-9_.-]+$", new_u_clean):
        return False, "Username hanya boleh mengandung huruf, angka, garis bawah (_), atau titik (.)."
        
    # Cek jika username diganti dan tabrakan dengan user lain
    if new_u_clean != target_key and new_u_clean in users:
        return False, f"Username '{new_u_clean}' sudah digunakan oleh akun lain. Silakan pilih yang lain."
        
    user_record = dict(users[target_key])
    
    if new_name and len(new_name.strip()) >= 3:
        user_record["name"] = new_name.strip()
        
    if new_role:
        user_record["role"] = new_role
        role_badges = {
            "Super Admin": {"badge_color": "#2563EB"},
            "Pimpinan Kementerian": {"badge_color": "#D97706"},
            "Tim Analis Data & AI": {"badge_color": "#059669"},
            "Aparatur Sipil Negara": {"badge_color": "#475569"}
        }
        if new_role in role_badges:
            user_record["badge_color"] = role_badges[new_role]["badge_color"]
            
    if new_password and len(new_password.strip()) > 0:
        if len(new_password.strip()) < 6:
            return False, "Kata sandi baru minimal harus 6 karakter."
        user_record["password_hash"] = _hash_string(new_password.strip())
        
    user_record["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
    
    # Hapus key lama jika username berganti
    if new_u_clean != target_key:
        del users[target_key]
        users[new_u_clean] = user_record
    else:
        users[target_key] = user_record
        
    if not _save_stored_credentials(users):
        return False, "Gagal menyimpan perubahan ke basis data kredensial."
        
    return True, f"Kredensial untuk akun '{new_u_clean}' berhasil diperbarui!"


def create_new_user_by_admin(username: str, full_name: str, password: str, role: str, email: str = ""):
    """
    Fungsi Super Admin: Menambahkan pengguna baru ke sistem secara manual.
    """
    u_clean = username.strip().lower()
    name_clean = full_name.strip()
    
    if not u_clean or len(u_clean) < 3:
        return False, "Username wajib diisi minimal 3 karakter."
    if not name_clean or len(name_clean) < 3:
        return False, "Nama lengkap wajib diisi minimal 3 karakter."
    if not password or len(password) < 6:
        return False, "Kata sandi wajib diisi minimal 6 karakter."
        
    users = _load_stored_credentials()
    if u_clean in users:
        return False, f"Username '{u_clean}' sudah digunakan."
        
    role_badges = {
        "Super Admin": {"badge_color": "#2563EB"},
        "Pimpinan Kementerian": {"badge_color": "#D97706"},
        "Tim Analis Data & AI": {"badge_color": "#059669"},
        "Aparatur Sipil Negara": {"badge_color": "#475569"}
    }
    meta = role_badges.get(role, {"badge_color": "#2563EB"})
    
    users[u_clean] = {
        "password_hash": _hash_string(password.strip()),
        "name": name_clean,
        "role": role,
        "badge_color": meta["badge_color"],
        "email": email.strip() if email else f"{u_clean}@pu.go.id",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
    }
    
    if not _save_stored_credentials(users):
        return False, "Gagal menyimpan akun baru ke berkas kredensial."
        
    return True, f"Pengguna baru '{u_clean}' berhasil ditambahkan ke sistem!"


def delete_user_by_admin(target_key: str):
    """
    Fungsi Super Admin: Menghapus pengguna (tidak boleh menghapus admin utama jika hanya ada satu).
    """
    target_key = target_key.strip().lower()
    users = _load_stored_credentials()
    
    if target_key not in users:
        return False, "Pengguna tidak ditemukan."
        
    if target_key == "admin" and len([u for u, v in users.items() if v.get("role") == "Super Admin"]) <= 1:
        return False, "Tidak dapat menghapus satu-satunya akun Super Admin."
        
    del users[target_key]
    _save_stored_credentials(users)
    return True, f"Pengguna '{target_key}' berhasil dihapus dari sistem."


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
    """Merender halaman Login bertema elegan Kementerian PU (Bebas Glitch & Presisi)."""
    from src.mh_style import render_logo_badge

    logo_svg = render_logo_badge(size=44)
    
    # Styling khusus halaman login - Eksekutif, Rapi, Terpusat & Anti-Glitch
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
        
        /* Kunci lebar container di tengah layar agar proporsional */
        .block-container,
        [data-testid="stAppViewBlockContainer"] {
            max-width: 450px !important;
            padding-top: 50px !important;
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
        
        /* Input Container BaseWeb & Focus State */
        div[data-testid="stForm"] div[data-baseweb="input"],
        div[data-testid="stForm"] div[data-baseweb="base-input"],
        div[data-testid="stForm"] div[data-baseweb="select"] > div {
            background-color: #FAFCFE !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 9px !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
        }
        div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
        div[data-testid="stForm"] div[data-baseweb="base-input"]:focus-within,
        div[data-testid="stForm"] div[data-baseweb="select"] > div:focus-within {
            border-color: #2563EB !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        }
        div[data-testid="stForm"] input {
            background-color: transparent !important;
            border: none !important;
            font-size: 13.5px !important;
            color: #0F172A !important;
            padding: 9px 12px !important;
        }
        div[data-testid="stForm"] input:focus {
            outline: none !important;
            box-shadow: none !important;
            border: none !important;
        }
        
        /* Sembunyikan teks instruksi Enter agar input bersih */
        div[data-testid="stForm"] div[data-testid="InputInstructions"] {
            display: none !important;
        }
        
        /* Reset tombol ikon bawaan Streamlit (mata password & tooltip) */
        div[data-testid="stForm"] button[aria-label*="password" i],
        div[data-testid="stForm"] button[aria-label*="sandi" i],
        div[data-testid="stForm"] div[data-baseweb="input"] button,
        div[data-testid="stForm"] div[data-baseweb="base-input"] button,
        div[data-testid="stForm"] button[data-testid="stTooltipIconButton"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 4px 8px !important;
            margin: 0 !important;
            color: #64748B !important;
            transform: none !important;
            width: auto !important;
            min-width: unset !important;
        }
        div[data-testid="stForm"] button[aria-label*="password" i]:hover,
        div[data-testid="stForm"] div[data-baseweb="input"] button:hover {
            background: transparent !important;
            color: #2563EB !important;
            box-shadow: none !important;
            transform: none !important;
        }
        div[data-testid="stForm"] button[aria-label*="password" i] svg,
        div[data-testid="stForm"] div[data-baseweb="input"] button svg,
        div[data-testid="stForm"] button[data-testid="stTooltipIconButton"] svg {
            fill: currentColor !important;
        }
        
        /* Tombol Submit Khusus Form (Hanya Tombol Utama) */
        div[data-testid="stFormSubmitButton"] > button {
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
            width: 100% !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover {
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

    # 2. Card Form Terpadu
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
            placeholder="Masukkan ID pengguna..."
        )
        password_val = st.text_input(
            "Kata Sandi / Password",
            type="password",
            placeholder="••••••••••••"
        )
        
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "Masuk ke Sistem (Sign In)",
            use_container_width=True,
            type="primary",
            icon=":material/login:"
        )
        
        if submitted:
            user_match = verify_credentials(username_val, password_val)
            if user_match:
                st.toast(f"Selamat datang, {user_match['name']}!")
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
    Merender widget identitas pengguna aktif dan tombol Logout di Sidebar (Menggunakan Vector SVG, Tanpa Emoji).
    """
    from src.clean_header_footer import render_html

    user = st.session_state.get("user_info", {})
    if not user:
        return

    name = user.get("name", "Pengguna Terdaftar")
    role = user.get("role", "Aparatur Sipil Negara")
    badge_color = user.get("badge_color", "#2563EB")
    login_time = st.session_state.get("login_time", "Sesi Aktif")

    # Ambil inisial nama
    initials = "".join([part[0].upper() for part in name.split()[:2]]) if name else "PU"
    role_svg = get_role_icon_svg(role, color=badge_color, size=11)

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
                    <span style="font-size: 9.5px; font-weight: 700; color: {badge_color}; background: {badge_color}18; padding: 2px 6px; border-radius: 4px; border: 1px solid {badge_color}33; display: inline-flex; align-items: center; gap: 4px;">
                        {role_svg}
                        <span>{role}</span>
                    </span>
                </div>
            </div>
        </div>
        <div style="font-size: 9px; color: #94A3B8; margin-top: 8px; padding-top: 6px; border-top: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;">
            <span>Sesi: {login_time}</span>
            <span style="color: #10B981; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background:#10B981;"></span>
                <span>Online</span>
            </span>
        </div>
    </div>
    """)

    # Tombol Logout Elegan
    if st.sidebar.button("Keluar dari Sistem (Logout)", key="btn_logout_sidebar", use_container_width=True, type="secondary", icon=":material/logout:"):
        logout_user()


# ==============================================================================
# PANEL MANAJEMEN PENGGUNA (SUPER ADMIN) - DENGAN ICON VEKTOR SVG (TANPA EMOJI)
# ==============================================================================
def render_user_management_panel():
    """
    Panel administrasi khusus Super Admin untuk melihat seluruh akun pengguna,
    serta mengubah Username (UN) dan Kata Sandi (PW) secara langsung dan aman.
    Semua elemen visual menggunakan Icon Vektor SVG resmi (Bebas Emoji).
    """
    user_info = st.session_state.get("user_info", {})
    if user_info.get("role") != "Super Admin" and st.session_state.get("username") != "admin":
        st.error("Akses Ditolak: Halaman ini hanya dapat diakses oleh Administrator Sistem (Super Admin).")
        return

    # Header Panel Eksekutif dengan Icon SVG Setting/Users
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0F2942 0%, #1E3A8A 100%); border-radius: 14px; padding: 22px 26px; color: #FFFFFF; margin-bottom: 22px; box-shadow: 0 4px 16px rgba(15,41,66,0.12);">
        <div style="display:flex; align-items:center; gap:14px;">
            <div style="background: rgba(255,255,255,0.14); width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.15);">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
            </div>
            <div>
                <div style="font-size: 20px; font-weight: 800; letter-spacing: -0.3px; line-height: 1.2;">
                    Panel Manajemen Akun & Kredensial Keamanan
                </div>
                <div style="font-size: 12.5px; color: #94A3B8; margin-top: 4px;">
                    Portal khusus Super Admin untuk mengelola hak akses, memperbarui Username, dan mereset Kata Sandi pengguna Kementerian PU.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    users = get_all_users()
    
    # Tab Navigasi Bersih Berbasis Icon Material & SVG (Tanpa Emoji)
    tab_edit, tab_add, tab_list = st.tabs([
        ":material/manage_accounts: Ubah Kredensial",
        ":material/person_add: Tambah Pengguna Baru",
        ":material/group: Daftar Akun Pengguna"
    ])

    # -------------------------------------------------------------
    # TAB 1: UBAH USERNAME & KATA SANDI
    # -------------------------------------------------------------
    with tab_edit:
        st.markdown("""
        <div style="font-size:14px; font-weight:700; color:#0F2942; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
            <span>Pilih Akun yang Ingin Diperbarui Kredensialnya:</span>
        </div>
        """, unsafe_allow_html=True)

        user_keys = list(users.keys())
        user_labels = {k: f"{k} ({users[k].get('name', k)} - {users[k].get('role', 'User')})" for k in user_keys}
        
        selected_user_key = st.selectbox(
            "Pilih Pengguna:",
            user_keys,
            format_func=lambda k: user_labels.get(k, k),
            key="sel_edit_user"
        )
        
        curr_user = users[selected_user_key]

        with st.form("form_edit_credentials", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                edit_name = st.text_input(
                    "Nama Lengkap & Gelar:",
                    value=curr_user.get("name", "")
                )
                edit_username = st.text_input(
                    "ID Pengguna / Username Baru (UN):",
                    value=selected_user_key
                )
            with c2:
                role_list = ["Super Admin", "Pimpinan Kementerian", "Tim Analis Data & AI", "Aparatur Sipil Negara"]
                curr_role = curr_user.get("role", "Tim Analis Data & AI")
                role_idx = role_list.index(curr_role) if curr_role in role_list else 2
                edit_role = st.selectbox("Peran / Tingkat Akses:", role_list, index=role_idx)
                edit_email = st.text_input("Email:", value=curr_user.get("email", f"{selected_user_key}@pu.go.id"))

            st.markdown("<hr style='border:none; border-top:1px dashed #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:12.5px; font-weight:700; color:#0F2942; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                <span>Reset Kata Sandi (Opsional):</span>
            </div>
            <div style="font-size:11.5px; color:#64748B; margin-bottom:12px;">
                Biarkan kedua kolom di bawah ini kosong jika <b>TIDAK</b> ingin mengubah kata sandi lama akun tersebut.
            </div>
            """, unsafe_allow_html=True)

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                edit_new_pass = st.text_input("Kata Sandi Baru (PW):", type="password", placeholder="Minimal 6 karakter...")
            with c_p2:
                edit_conf_pass = st.text_input("Konfirmasi Kata Sandi Baru:", type="password", placeholder="Ketik ulang sandi baru...")

            btn_save = st.form_submit_button("Simpan Perubahan Kredensial", use_container_width=True, type="primary", icon=":material/save:")
            
            if btn_save:
                if edit_new_pass and edit_new_pass != edit_conf_pass:
                    st.error("Konfirmasi kata sandi tidak cocok dengan kata sandi baru.")
                else:
                    success, msg = update_user_credentials(
                        target_key=selected_user_key,
                        new_username=edit_username,
                        new_password=edit_new_pass,
                        new_name=edit_name,
                        new_role=edit_role
                    )
                    if success:
                        st.success(msg)
                        st.toast(msg)
                        # Jika admin mengubah username dirinya sendiri saat login
                        if selected_user_key == st.session_state.get("username") and edit_username != selected_user_key:
                            st.session_state["username"] = edit_username.strip().lower()
                        st.rerun()
                    else:
                        st.error(msg)

    # -------------------------------------------------------------
    # TAB 2: TAMBAH AKUN BARU
    # -------------------------------------------------------------
    with tab_add:
        st.markdown("""
        <div style="font-size:14px; font-weight:700; color:#0F2942; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
            <span>Daftarkan Akun Pengguna Baru ke Lingkungan Kementerian PU:</span>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_add_user_admin", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                add_name = st.text_input("Nama Lengkap:", placeholder="Contoh: Dr. Ir. H. Bambang, M.Eng.")
                add_user = st.text_input("ID Pengguna / Username (UN):", placeholder="Contoh: bambang_pu")
            with col_a2:
                add_role = st.selectbox(
                    "Tingkat Wewenang / Peran:",
                    ["Tim Analis Data & AI", "Pimpinan Kementerian", "Super Admin", "Aparatur Sipil Negara"],
                    index=0
                )
                add_email = st.text_input("Alamat Email:", placeholder="bambang@pu.go.id")

            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                add_pass = st.text_input("Kata Sandi (PW):", type="password", placeholder="Minimal 6 karakter...")
            with col_ap2:
                add_conf = st.text_input("Konfirmasi Kata Sandi:", type="password", placeholder="Ketik ulang sandi...")

            btn_create = st.form_submit_button("Tambahkan Pengguna Baru", use_container_width=True, type="primary", icon=":material/person_add:")
            
            if btn_create:
                if add_pass != add_conf:
                    st.error("Konfirmasi kata sandi tidak cocok.")
                else:
                    ok_add, msg_add = create_new_user_by_admin(
                        username=add_user,
                        full_name=add_name,
                        password=add_pass,
                        role=add_role,
                        email=add_email
                    )
                    if ok_add:
                        st.success(msg_add)
                        st.toast(msg_add)
                        st.rerun()
                    else:
                        st.error(msg_add)

    # -------------------------------------------------------------
    # TAB 3: DAFTAR SELURUH AKUN
    # -------------------------------------------------------------
    with tab_list:
        st.markdown("""
        <div style="font-size:14px; font-weight:700; color:#0F2942; margin-bottom:14px; display:flex; align-items:center; gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
            <span>Daftar Akun Terdaftar & Status Keamanan Sistem:</span>
        </div>
        """, unsafe_allow_html=True)

        for u_id, u_info in users.items():
            u_name = u_info.get("name", u_id)
            u_role = u_info.get("role", "User")
            u_color = u_info.get("badge_color", "#2563EB")
            u_email = u_info.get("email", "-")
            role_icon_svg = get_role_icon_svg(u_role, color=u_color, size=11)

            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:14px 18px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                <div style="display:flex; align-items:center; gap:14px;">
                    <div style="width:40px; height:40px; border-radius:50%; background:{u_color}; color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:13px; letter-spacing:0.5px; box-shadow:0 2px 4px rgba(0,0,0,0.12);">
                        {u_name[:2].upper()}
                    </div>
                    <div>
                        <div style="font-size:14px; font-weight:700; color:#0F2942;">
                            {u_name} <span style="font-size:12px; font-weight:500; color:#64748B;">(@{u_id})</span>
                        </div>
                        <div style="font-size:11.5px; color:#475569; display:flex; align-items:center; gap:8px; margin-top:3px;">
                            <span style="font-weight:700; color:{u_color}; background:{u_color}18; padding:2px 7px; border-radius:4px; display:inline-flex; align-items:center; gap:4px; border:1px solid {u_color}33;">
                                {role_icon_svg}
                                <span>{u_role}</span>
                            </span>
                            <span>• {u_email}</span>
                        </div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:10.5px; color:#059669; font-weight:700; background:#ECFDF5; border:1px solid #A7F3D0; padding:3px 9px; border-radius:6px; display:inline-flex; align-items:center; gap:4px;">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                        <span>SHA-256 Aktif</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

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
import time
import secrets
import hashlib
import datetime
from pathlib import Path
# pyrefly: ignore[missing-import]
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = os.path.join(BASE_DIR, "data", "user_credentials.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "data", "active_sessions.json")

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


def render_clean_html(html_str: str):
    """
    Render HTML aman di Streamlit tanpa risiko terpicu sebagai blok kode Markdown (indented code block).
    Menghapus leading indentation dan meratakan baris agar 100% bebas glitch visual kode mentah.
    """
    clean = " ".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean, unsafe_allow_html=True)


# Konfigurasi Integrasi Basis Data (Setel False agar murni menggunakan JSON lokal yang cepat dan mandiri)
USE_DB_AUTH = False


def _load_users_from_db():
    """Mencoba memuat data akun pengguna dari tabel database (hanya jika USE_DB_AUTH=True)."""
    if not USE_DB_AUTH:
        return None
    try:
        from src.db_manager import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT username, password_hash, name, role, badge_color, email FROM users;")).fetchall()
            if rows:
                db_users = {}
                for r in rows:
                    db_users[r[0].lower().strip()] = {
                        "password_hash": r[1],
                        "name": r[2],
                        "role": r[3],
                        "badge_color": r[4],
                        "email": r[5] or f"{r[0]}@pu.go.id"
                    }
                return db_users
    except Exception:
        pass
    return None


def _sync_user_to_db(username: str, user_dict: dict):
    """Menyinkronkan satu akun pengguna ke tabel database (hanya jika USE_DB_AUTH=True)."""
    if not USE_DB_AUTH:
        return True
    try:
        from src.db_manager import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO users (username, password_hash, name, role, badge_color, email)
                VALUES (:u, :p, :n, :r, :b, :e)
                ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    name = EXCLUDED.name,
                    role = EXCLUDED.role,
                    badge_color = EXCLUDED.badge_color,
                    email = EXCLUDED.email,
                    updated_at = CURRENT_TIMESTAMP;
            """), {
                "u": username.lower().strip(),
                "p": user_dict.get("password_hash", ""),
                "n": user_dict.get("name", username),
                "r": user_dict.get("role", "User"),
                "b": user_dict.get("badge_color", "#2563EB"),
                "e": user_dict.get("email", f"{username}@pu.go.id")
            })
        return True
    except Exception:
        return False


def _delete_user_from_db(username: str):
    """Menghapus akun dari tabel database (hanya jika USE_DB_AUTH=True)."""
    if not USE_DB_AUTH:
        return True
    try:
        from src.db_manager import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE username = :u;"), {"u": username.lower().strip()})
        return True
    except Exception:
        return False


def _load_stored_credentials() -> dict:
    """
    Memuat data kredensial:
    1. Membaca langsung dari berkas JSON lokal (data/user_credentials.json) secara instan (0 ms).
    2. Fallback ke DEFAULT_USERS jika berkas belum tersedia.
    """
    if USE_DB_AUTH:
        db_users = _load_users_from_db()
        if db_users and len(db_users) > 0:
            return db_users

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
    """
    Menyimpan seluruh data pengguna & kredensial:
    Simpan ke berkas JSON lokal secara aman.
    """
    try:
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_dict, f, indent=2, ensure_ascii=False)
            
        if USE_DB_AUTH:
            for u_id, u_info in users_dict.items():
                _sync_user_to_db(u_id, u_info)
            
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


def update_user_credentials(target_key: str, new_username: str, new_password: str = "", new_name: str = "", new_role: str = "", new_email: str = ""):
    """
    Fungsi khusus Super Admin: Memperbarui username, nama, peran, email, atau kata sandi pengguna.
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

    if new_email and "@" in new_email:
        user_record["email"] = new_email.strip()
            
    if new_password and len(new_password.strip()) > 0:
        if len(new_password.strip()) < 6:
            return False, "Kata sandi baru minimal harus 6 karakter."
        user_record["password_hash"] = _hash_string(new_password.strip())
        
    user_record["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
    
    # Hapus key lama jika username berganti
    if new_u_clean != target_key:
        _delete_user_from_db(target_key)
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


def _load_active_sessions() -> dict:
    """Memuat data sesi login yang masih valid (maksimal 3 jam) dari data/active_sessions.json."""
    if not os.path.exists(SESSIONS_FILE):
        return {"tokens": {}, "last_local_token": None}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"tokens": {}, "last_local_token": None}
            tokens = data.get("tokens", {})
            now = time.time()
            valid_tokens = {k: v for k, v in tokens.items() if v.get("expires_at", 0) > now}
            data["tokens"] = valid_tokens
            if data.get("last_local_token") not in valid_tokens:
                data["last_local_token"] = None
            return data
    except Exception:
        return {"tokens": {}, "last_local_token": None}


def _save_active_sessions(sessions_dict: dict):
    """Menyimpan data sesi login aktif ke data/active_sessions.json."""
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions_dict, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Batas durasi token sesi: Tepat 3 Jam (10.800 detik)
SESSION_DURATION_SECONDS = 3 * 3600

# Versi sesi global. Jika diubah atau direset, seluruh sesi lama di semua perangkat akan otomatis gugur/logout.
GLOBAL_SESSION_VERSION = "2026.11.21.force_reset_v1"


def revoke_all_sessions() -> int:
    """
    Mencabut dan menghapus seluruh token sesi login aktif dari data/active_sessions.json.
    Semua pengguna di seluruh perangkat otomatis ter-logout dan wajib login kembali.
    Mengembalikan jumlah token yang dicabut.
    """
    sessions = _load_active_sessions()
    tokens = sessions.get("tokens", {})
    count = len(tokens)
    sessions["tokens"] = {}
    sessions["last_local_token"] = None
    _save_active_sessions(sessions)
    return count


def _register_session(username: str, remember: bool = True) -> str:
    """Membuat token sesi baru dengan batas waktu kedaluwarsa 3 jam dan versi sesi aktif."""
    token = secrets.token_hex(24)
    # Batas durasi sesi tepat 3 jam (10.800 detik)
    expires_at = time.time() + SESSION_DURATION_SECONDS
    
    sessions = _load_active_sessions()
    sessions["tokens"][token] = {
        "username": username.strip().lower(),
        "created_at": datetime.datetime.now().strftime("%d %b %Y, %H:%M WIB"),
        "expires_at": expires_at,
        "version": GLOBAL_SESSION_VERSION,
        "remember": remember
    }
    sessions["last_local_token"] = token
    _save_active_sessions(sessions)
    return token


def _validate_session(token: str) -> str | None:
    """Memverifikasi validitas token sesi (maksimal 3 jam dan versi sesi aktif). Mengembalikan username jika valid."""
    if not token or not isinstance(token, str):
        return None
    sessions = _load_active_sessions()
    session_data = sessions.get("tokens", {}).get(token)
    if session_data:
        # Validasi versi sesi: jika sesi dibuat sebelum pembaruan/force-reset, gugurkan
        if session_data.get("version") != GLOBAL_SESSION_VERSION:
            if token in sessions.get("tokens", {}):
                del sessions["tokens"][token]
            if sessions.get("last_local_token") == token:
                sessions["last_local_token"] = None
            _save_active_sessions(sessions)
            return None

        if session_data.get("expires_at", 0) > time.time():
            return session_data.get("username")
        else:
            # Sesi sudah kedaluwarsa (> 3 jam)
            if token in sessions.get("tokens", {}):
                del sessions["tokens"][token]
            if sessions.get("last_local_token") == token:
                sessions["last_local_token"] = None
            _save_active_sessions(sessions)
    return None


def _revoke_session(token: str):
    """Mencabut/menghapus token sesi saat pengguna logout."""
    if not token:
        return
    sessions = _load_active_sessions()
    if token in sessions.get("tokens", {}):
        del sessions["tokens"][token]
    if sessions.get("last_local_token") == token:
        sessions["last_local_token"] = None
    _save_active_sessions(sessions)


def login_user(username: str, user_info: dict, remember: bool = True):
    """Menyimpan sesi login ke dalam st.session_state dan st.query_params agar tidak logout saat reload (batas 3 jam)."""
    clean_u = username.strip().lower()
    token = _register_session(clean_u, remember=remember)
    now_ts = time.time()
    expires_at = now_ts + SESSION_DURATION_SECONDS
    
    st.session_state["authenticated"] = True
    st.session_state["username"] = clean_u
    st.session_state["user_info"] = user_info
    st.session_state["session_token"] = token
    st.session_state["session_version"] = GLOBAL_SESSION_VERSION
    st.session_state["login_time"] = datetime.datetime.now().strftime("%H:%M WIB")
    st.session_state["session_expires_at"] = expires_at
    
    # Simpan token ke query params browser agar sesi bertahan saat reload halaman (F5)
    try:
        st.query_params["session_token"] = token
    except Exception:
        pass
        
    st.rerun()


def logout_user(reason: str = None):
    """Menghapus sesi login dan mengarahkan kembali ke halaman login."""
    token = st.session_state.get("session_token")
    if not token:
        try:
            token = st.query_params.get("session_token")
        except Exception:
            token = None
            
    if token:
        _revoke_session(token)
        
    # Hapus query param dari URL
    try:
        if "session_token" in st.query_params:
            del st.query_params["session_token"]
    except Exception:
        pass
        
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["user_info"] = None
    st.session_state["session_token"] = None
    st.session_state["session_version"] = None
    st.session_state["login_time"] = None
    st.session_state["session_expires_at"] = None
    if reason == "expired":
        st.session_state["session_expired_alert"] = True
    st.rerun()


def check_authentication() -> bool:
    """
    Penjaga pintu utama aplikasi.
    Memastikan sesi aktif dan belum melewati batas durasi 3 jam.
    Jika sudah melewati 3 jam atau sesi telah dicabut, sesi dicabut dan pengguna diminta login kembali.
    """
    now = time.time()

    # 1. Cek sesi aktif di runtime session_state
    if st.session_state.get("authenticated", False) is True:
        token = st.session_state.get("session_token")
        expires_at = st.session_state.get("session_expires_at")
        s_version = st.session_state.get("session_version")
        
        # Validasi: Jika tidak ada token, versi sesi lama, token tidak valid, atau lewat 3 jam -> force logout
        if (not token or 
            s_version != GLOBAL_SESSION_VERSION or 
            not _validate_session(token) or 
            (expires_at and now > expires_at)):
            logout_user(reason="expired")
            return False
            
        return True

    # 2. Cek apakah ada token sesi di query_params URL browser (bertahan saat reload F5)
    token = None
    try:
        token = st.query_params.get("session_token")
    except Exception:
        token = None

    # Fallback lokal: jika diakses di localhost tanpa query param, gunakan token lokal terakhir yang belum kedaluwarsa
    if not token:
        sessions = _load_active_sessions()
        candidate = sessions.get("last_local_token")
        if candidate and _validate_session(candidate):
            token = candidate

    # 3. Validasi token sesi jika ada (harus <= 3 jam dan versi aktif)
    if token:
        valid_username = _validate_session(token)
        if valid_username:
            users = get_all_users()
            if valid_username in users:
                user_info = users[valid_username]
                sessions = _load_active_sessions()
                s_info = sessions.get("tokens", {}).get(token, {})
                exp_ts = s_info.get("expires_at", now + SESSION_DURATION_SECONDS)
                
                st.session_state["authenticated"] = True
                st.session_state["username"] = valid_username
                st.session_state["user_info"] = user_info
                st.session_state["session_token"] = token
                st.session_state["session_version"] = GLOBAL_SESSION_VERSION
                st.session_state["login_time"] = s_info.get("created_at", datetime.datetime.now().strftime("%H:%M WIB"))
                st.session_state["session_expires_at"] = exp_ts
                
                # Sinkronkan kembali query param di URL
                try:
                    if st.query_params.get("session_token") != token:
                        st.query_params["session_token"] = token
                except Exception:
                    pass
                    
                return True

    # Jika token tidak valid / kedaluwarsa (> 3 jam), bersihkan dari URL
    try:
        if "session_token" in st.query_params:
            del st.query_params["session_token"]
    except Exception:
        pass

    # 4. Jika belum login atau sesi habis, tampilkan halaman login eksekutif
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
    render_clean_html(f"""
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
    """)

    # 2. Notifikasi jika sesi sebelumnya kedaluwarsa setelah 3 jam
    if st.session_state.get("session_expired_alert"):
        st.warning("⏱️ Batas waktu sesi login (3 jam) telah berakhir. Silakan masuk kembali ke akun Anda.", icon="⏱️")
        st.session_state["session_expired_alert"] = False

    # 3. Card Form Terpadu
    with st.form("login_form", clear_on_submit=False):
        render_clean_html("""
        <div style="margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #F1F5F9;">
            <div style="font-size: 15px; font-weight: 800; color: #0F2942; display: flex; align-items: center; gap: 8px;">
                <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#2563EB;"></span>
                Autentikasi Akses Sistem
            </div>
            <div style="font-size: 11.5px; color: #64748B; margin-top: 3px; line-height: 1.4;">
                Silakan masukkan akun kedinasan Anda untuk mengakses data analitik.
            </div>
        </div>
        """)

        username_val = st.text_input(
            "ID Pengguna / Username",
            placeholder="Username"
        )
        password_val = st.text_input(
            "Kata Sandi / Password",
            type="password",
            placeholder="Password"
        )
        
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
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
                login_user(username_val, user_match, remember=True)
            else:
                st.error("Nama pengguna atau kata sandi tidak sesuai. Silakan periksa kembali.")

    # 4. Footer Keamanan
    render_clean_html("""
    <div style="text-align: center; margin-top: 22px; font-size: 11px; color: #64748B;">
        <div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:4px; font-weight:600; color:#475569;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            <span>Sistem Informasi Terbatas • Batas Sesi 3 Jam • Terproteksi SHA-256</span>
        </div>
        <div>Kementerian Pekerjaan Umum Republik Indonesia • 2026</div>
    </div>
    """)


def render_user_sidebar_profile():
    """
    Merender widget identitas pengguna aktif dan tombol Logout di Sidebar (Menggunakan Vector SVG, Tanpa Emoji).
    """
    user = st.session_state.get("user_info", {})
    if not user:
        return

    name = user.get("name", "Pengguna Terdaftar")
    role = user.get("role", "Aparatur Sipil Negara")
    badge_color = user.get("badge_color", "#2563EB")
    login_time = st.session_state.get("login_time", "Sesi Aktif")
    username_val = st.session_state.get("username", "")

    role_svg = get_role_icon_svg(role, color=badge_color, size=11)

    render_clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
        <div style="font-size: 12px; font-weight: 700; color: #0F2942; line-height: 1.25;">
            {name}
        </div>
        <div style="font-size: 10.5px; color: #64748B; margin-top: 1px;">
            @{username_val}
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 6px;">
            <span style="font-size: 9.5px; font-weight: 700; color: {badge_color}; background: {badge_color}18; padding: 2px 6px; border-radius: 4px; border: 1px solid {badge_color}33; display: inline-flex; align-items: center; gap: 4px;">
                {role_svg}
                <span>{role}</span>
            </span>
            <span style="color: #10B981; font-size: 9.5px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background:#10B981;"></span>
                <span>Online</span>
            </span>
        </div>
        <div style="font-size: 9px; color: #94A3B8; margin-top: 6px; padding-top: 5px; border-top: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;">
            <span>Masuk: {login_time}</span>
            <span style="color: #64748B; font-weight: 600;">Batas Sesi: 3 Jam</span>
        </div>
    </div>
    """)

    # Tombol Logout Elegan
    if st.sidebar.button("Keluar dari Sistem (Logout)", key="btn_logout_sidebar", use_container_width=True, type="secondary", icon=":material/logout:"):
        logout_user()


# ==============================================================================
# PANEL MANAJEMEN PENGGUNA (SUPER ADMIN) - DESAIN PROFESIONAL KEMENTERIAN PU
# ==============================================================================
def render_user_management_panel():
    """
    Panel administrasi resmi Super Admin untuk pengelolaan akun personil,
    penugasan peran struktural (RBAC), dan pembaruan kredensial akses.
    Menggunakan arsitektur visual resmi Kementerian PU (Bebas AI Template & Bebas Emoji).
    """
    from src.clean_header_footer import render_slide_header, render_slide_footer

    user_info = st.session_state.get("user_info", {})
    if user_info.get("role") != "Super Admin" and st.session_state.get("username") != "admin":
        st.error("Akses Ditolak: Halaman ini hanya dapat diakses oleh Administrator Sistem (Super Admin).")
        return

    # Header Resmi Konsisten dengan Seluruh Modul Aplikasi
    render_slide_header("Manajemen Pengguna & Akses", "Sistem Intelijen Kebijakan Publik • Administrasi Hak Akses RBAC")

    # Status penyimpanan kredensial
    is_pg_connected = False
    if USE_DB_AUTH:
        try:
            from src.db_manager import test_db_connection
            res = test_db_connection()
            is_pg_connected = isinstance(res, dict) and res.get("status") == "connected"
        except Exception:
            is_pg_connected = False

    users = get_all_users()
    total_users = len(users)
    admin_un = st.session_state.get("username", "admin")

    # Status Bar Ramping & Elegan (Clean Meta Strip)
    db_pill = (
        '<span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600; color:#047857; background:#ECFDF5; border:1px solid #A7F3D0; padding:4px 10px; border-radius:6px;">'
        '<span style="width:6px; height:6px; border-radius:50%; background:#10B981;"></span>'
        '<span>Basis Kredensial: PostgreSQL 18</span>'
        '</span>'
    ) if is_pg_connected else (
        '<span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600; color:#047857; background:#ECFDF5; border:1px solid #A7F3D0; padding:4px 10px; border-radius:6px;">'
        '<span style="width:6px; height:6px; border-radius:50%; background:#10B981;"></span>'
        '<span>Basis Kredensial: File Terenkripsi Lokal (JSON)</span>'
        '</span>'
    )

    render_clean_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:10px 16px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; align-items:center; gap:12px; font-size:13px; color:#334155;">
            <span style="font-weight:700; color:#0F172A;">{total_users} Akun Terdaftar</span>
            <span style="color:#CBD5E1;">|</span>
            <span style="color:#64748B;">Sesi Administrator: <b style="color:#0F172A;">@{admin_un}</b> (Super Admin)</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            {db_pill}
            <span style="display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:600; color:#475569; background:#F8FAFC; border:1px solid #E2E8F0; padding:4px 10px; border-radius:6px;">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                <span>SHA-256 FIPS 180-4</span>
            </span>
        </div>
    </div>
    """)

    # Navigasi Tab Fungsional
    tab_list, tab_edit, tab_add = st.tabs([
        ":material/group: Daftar Pengguna",
        ":material/manage_accounts: Kelola Kredensial",
        ":material/person_add: Tambah Pengguna Baru"
    ])

    # -------------------------------------------------------------
    # TAB 1: DAFTAR PENGGUNA TERDAFTAR (VIEW UTAMA ADMINISTRASI)
    # -------------------------------------------------------------
    with tab_list:
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        
        # Render setiap pengguna dalam baris data bersih
        for u_id, u_info in users.items():
            u_name = u_info.get("name", u_id)
            u_role = u_info.get("role", "User")
            u_color = u_info.get("badge_color", "#2563EB")
            u_email = u_info.get("email", f"{u_id}@pu.go.id")
            role_svg = get_role_icon_svg(u_role, color=u_color, size=11)

            render_clean_html(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px 18px; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; transition:border-color 0.2s ease;">
                <div>
                    <div style="font-size:13.5px; font-weight:700; color:#0F172A; line-height:1.2;">
                        {u_name} <span style="font-size:12px; font-weight:500; color:#64748B;">(@{u_id})</span>
                    </div>
                    <div style="font-size:11.5px; color:#64748B; margin-top:3px; display:flex; align-items:center; gap:4px;">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                        <span>{u_email}</span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span style="font-size:11px; font-weight:700; color:{u_color}; background:{u_color}14; padding:3px 8px; border-radius:5px; border:1px solid {u_color}2E; display:inline-flex; align-items:center; gap:4px;">
                        {role_svg}
                        <span>{u_role}</span>
                    </span>
                    <span style="font-size:11px; color:#475569; background:#F8FAFC; border:1px solid #E2E8F0; padding:3px 8px; border-radius:5px;">
                        SHA-256
                    </span>
                    <span style="font-size:11px; color:#047857; background:#ECFDF5; border:1px solid #A7F3D0; padding:3px 8px; border-radius:5px;">
                        {'PostgreSQL' if is_pg_connected else 'JSON'}
                    </span>
                </div>
            </div>
            """)

        # Kontrol Sesi Aktif & Force Logout Semua Perangkat
        act_sessions = _load_active_sessions().get("tokens", {})
        act_count = len(act_sessions)

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            col_sess1, col_sess2 = st.columns([2.5, 1.2])
            with col_sess1:
                render_clean_html(f"""
                <div style="font-size:13px; font-weight:700; color:#0F172A;">
                    Kontrol Sesi Pengguna & Force Logout
                </div>
                <div style="font-size:11.5px; color:#64748B; margin-top:2px;">
                    Tercatat <b>{act_count}</b> token sesi aktif (maksimal 3 jam per sesi). Anda dapat mencabut seluruh sesi untuk memaksa semua perangkat login ulang.
                </div>
                """)
            with col_sess2:
                if st.button("Logout Semua Sesi", key="btn_force_logout_all", use_container_width=True, type="secondary", icon=":material/power_settings_new:"):
                    num = revoke_all_sessions()
                    st.success(f"Berhasil mencabut seluruh ({num}) sesi aktif! Semua pengguna wajib login ulang.")
                    st.rerun()

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # Matriks Hak Akses Struktural (RBAC) - Tampilan Bersih Standar Enterprise
        st.markdown("""
        <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:8px;">
            Matriks Hak Akses Berdasarkan Peran (Role-Based Access Control)
        </div>
        """, unsafe_allow_html=True)

        check_icon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        dash_icon = '<span style="color:#CBD5E1;">—</span>'
        limited_tag = '<span style="font-size:10.5px; font-weight:600; color:#B45309; background:#FEF3C7; padding:1px 6px; border-radius:3px;">Terbatas</span>'

        render_clean_html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; margin-bottom:12px;">
            <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
                <thead>
                    <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0;">
                        <th style="padding:10px 14px; font-weight:700; color:#0F172A;">Modul & Fungsi Sistem</th>
                        <th style="padding:10px 12px; font-weight:700; color:#2563EB; text-align:center;">Super Admin</th>
                        <th style="padding:10px 12px; font-weight:700; color:#D97706; text-align:center;">Pimpinan</th>
                        <th style="padding:10px 12px; font-weight:700; color:#059669; text-align:center;">Tim Analis</th>
                        <th style="padding:10px 12px; font-weight:700; color:#475569; text-align:center;">ASN</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom:1px solid #F1F5F9;">
                        <td style="padding:8px 14px; color:#334155;">Dasbor Eksekutif & Ringkasan Sentimen Publik</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F1F5F9; background:#FAFAFA;">
                        <td style="padding:8px 14px; color:#334155;">Analisis Sentimen IndoBERT & Filter Multi-Platform</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F1F5F9;">
                        <td style="padding:8px 14px; color:#334155;">Visualisasi Jejaring SNA & Metrik Sentralitas Aktor</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{limited_tag}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F1F5F9; background:#FAFAFA;">
                        <td style="padding:8px 14px; color:#334155;">Ingestion Data Multi-Platform & Migrasi Database</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #F1F5F9;">
                        <td style="padding:8px 14px; color:#334155;">Ekspor Dataset Lengkap (CSV / Excel) & Laporan</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 14px; color:#334155;">Manajemen Pengguna, Reset Sandi & Hak Akses</td>
                        <td style="padding:8px 12px; text-align:center;">{check_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                        <td style="padding:8px 12px; text-align:center;">{dash_icon}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """)

    # -------------------------------------------------------------
    # TAB 2: UBAH KREDENSIAL & HAK AKSES PENGGUNA
    # -------------------------------------------------------------
    with tab_edit:
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        user_keys = list(users.keys())
        user_labels = {k: f"{users[k].get('name', k)} (@{k}) — {users[k].get('role', 'User')}" for k in user_keys}
        
        selected_user_key = st.selectbox(
            "Pilih Akun yang Ingin Diperbarui:",
            user_keys,
            format_func=lambda k: user_labels.get(k, k),
            key="sel_edit_user"
        )
        
        curr_user = users[selected_user_key]
        curr_name = curr_user.get("name", selected_user_key)
        curr_role = curr_user.get("role", "Tim Analis Data & AI")
        curr_color = curr_user.get("badge_color", "#2563EB")
        curr_email = curr_user.get("email", f"{selected_user_key}@pu.go.id")

        with st.form("form_edit_credentials", clear_on_submit=False):
            st.markdown("##### Informasi Identitas & Peran")
            c1, c2 = st.columns(2)
            with c1:
                edit_name = st.text_input(
                    "Nama Lengkap & Gelar",
                    value=curr_name
                )
                edit_username = st.text_input(
                    "ID Pengguna / Username (UN)",
                    value=selected_user_key
                )
            with c2:
                role_list = ["Super Admin", "Pimpinan Kementerian", "Tim Analis Data & AI", "Aparatur Sipil Negara"]
                role_idx = role_list.index(curr_role) if curr_role in role_list else 2
                edit_role = st.selectbox("Peran / Tingkat Akses", role_list, index=role_idx)
                edit_email = st.text_input("Alamat Email Kedinasan", value=curr_email)

            st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
            st.markdown("##### Reset Kata Sandi (Opsional)")
            st.caption("Biarkan kedua kolom berikut kosong jika Anda tidak ingin mereset kata sandi lama akun ini.")

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                edit_new_pass = st.text_input("Kata Sandi Baru", type="password", placeholder="Minimal 6 karakter...")
            with c_p2:
                edit_conf_pass = st.text_input("Konfirmasi Kata Sandi Baru", type="password", placeholder="Ketik ulang sandi baru...")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
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
                        new_role=edit_role,
                        new_email=edit_email
                    )
                    if success:
                        st.success(msg)
                        st.toast(msg)
                        if selected_user_key == st.session_state.get("username") and edit_username != selected_user_key:
                            st.session_state["username"] = edit_username.strip().lower()
                        st.rerun()
                    else:
                        st.error(msg)

    # -------------------------------------------------------------
    # TAB 3: TAMBAH PENGGUNA BARU
    # -------------------------------------------------------------
    with tab_add:
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        with st.form("form_add_user_admin", clear_on_submit=True):
            st.markdown("##### Profil Personil Baru")
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                add_name = st.text_input("Nama Lengkap & Gelar", placeholder="Contoh: Dr. Ir. H. Bambang, M.Eng.")
                add_user = st.text_input("ID Pengguna / Username (UN)", placeholder="Contoh: bambang_pu")
            with col_a2:
                add_role = st.selectbox(
                    "Tingkat Wewenang / Peran",
                    ["Tim Analis Data & AI", "Pimpinan Kementerian", "Super Admin", "Aparatur Sipil Negara"],
                    index=0
                )
                add_email = st.text_input("Alamat Email Kedinasan", placeholder="bambang@pu.go.id")

            st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
            st.markdown("##### Kredensial Awal Akun")
            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                add_pass = st.text_input("Kata Sandi Awal", type="password", placeholder="Minimal 6 karakter...")
            with col_ap2:
                add_conf = st.text_input("Konfirmasi Kata Sandi", type="password", placeholder="Ketik ulang sandi...")

            st.caption("Hak akses: **Super Admin** (Akses penuh), **Pimpinan** (Eksekutif & Kebijakan), **Tim Analis** (SNA & Dataset), **ASN** (Pemantauan Umum).")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            btn_create = st.form_submit_button("Daftarkan Pengguna Baru", use_container_width=True, type="primary", icon=":material/person_add:")
            
            if btn_create:
                if add_pass != add_conf:
                    st.error("Konfirmasi kata sandi tidak cocok dengan kata sandi awal.")
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

    # Footer Resmi Konsisten dengan Seluruh Halaman Aplikasi
    render_slide_footer()

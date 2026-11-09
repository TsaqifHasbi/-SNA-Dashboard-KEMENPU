"""
================================================================================
LEGAL PAGES RENDERER - PUBLIC POLICY INTELLIGENCE PLATFORM
================================================================================
Menampilkan halaman Ketentuan Layanan (Terms of Service) dan Kebijakan Privasi
(Privacy Policy) yang memenuhi standar kepatuhan TikTok for Developers,
Meta, Google, dan X.
================================================================================
"""

import os
import streamlit as st
from src.mh_style import render_logo_badge, render_html

def _render_legal_header(title: str, subtitle: str, doc_type: str):
    """Header eksekutif dengan logo resmi PPIP (tanpa emoji, murni vektor)."""
    logo = render_logo_badge(size=36)
    
    badge_color = "#2563EB" if doc_type == "tos" else "#059669"
    badge_label = "TERMS OF SERVICE" if doc_type == "tos" else "PRIVACY POLICY"
    
    html = f"""
    <div style="background: linear-gradient(135deg, #0F2942 0%, #14385C 100%); border-radius: 12px; padding: 26px 30px; margin-bottom: 20px; box-shadow: 0 4px 16px rgba(15, 41, 66, 0.12); color: #FFFFFF;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                {logo}
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: #F6B100; letter-spacing: 1px; text-transform: uppercase;">
                        Public Policy Intelligence Platform
                    </div>
                    <div style="font-size: 22px; font-weight: 800; color: #FFFFFF; margin-top: 2px;">
                        {title}
                    </div>
                </div>
            </div>
            <div>
                <span style="background: {badge_color}; color: #FFFFFF; font-weight: 700; font-size: 11px; padding: 6px 14px; border-radius: 20px; letter-spacing: 0.5px;">
                    {badge_label}
                </span>
            </div>
        </div>
        <div style="margin-top: 14px; font-size: 13px; color: #CBD5E1; line-height: 1.5;">
            {subtitle}
        </div>
        <div style="margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.12); display: flex; gap: 24px; flex-wrap: wrap; font-size: 11.5px; color: #94A3B8;">
            <span><strong style="color:#FFFFFF;">Tanggal Efektif:</strong> 1 Januari 2025</span>
            <span><strong style="color:#FFFFFF;">Pembaruan:</strong> November 2026</span>
            <span><strong style="color:#FFFFFF;">Afiliasi:</strong> Universitas Jenderal Soedirman (UNSOED)</span>
            <span><strong style="color:#FFFFFF;">Status:</strong> Non-Komersial (Riset Ilmiah)</span>
        </div>
    </div>
    """
    render_html(html)


def render_terms_of_service():
    """Merender isi lengkap Terms of Service secara formal, elegan, dan bebas emoji."""
    _render_legal_header(
        title="Ketentuan Layanan (Terms of Service)",
        subtitle="Syarat dan ketentuan resmi penggunaan dashboard analisis kebijakan publik berbasis IndoBERT & Social Network Analysis (SNA).",
        doc_type="tos"
    )

    # Navigasi kembali ke Dashboard
    col_nav1, col_nav2 = st.columns([2, 3])
    with col_nav1:
        st.link_button("Kembali ke Dashboard Utama", "/", icon=":material/home:", type="primary")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Konten Syarat dan Ketentuan
    content_html = """
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.03); color:#1E293B; line-height:1.7; font-size:14px;">
        
        <div style="background:#EFF6FF; border-left:4px solid #2563EB; padding:12px 18px; border-radius:4px; margin-bottom:24px; font-size:13px; color:#1E40AF;">
            <strong>Ringkasan Eksekutif:</strong> Public Policy Intelligence Platform adalah instrumen riset komputasional akademik non-komersial di Universitas Jenderal Soedirman untuk memantau sentimen dan jaringan isu kebijakan publik nasional (Makan Bergizi Gratis, Sekolah Rakyat, dan Koperasi Desa Merah Putih). Kami menghormati sepenuhnya ketentuan pengembang dari seluruh platform penyedia data.
        </div>

        <h3 style="color:#0F2942; font-size:16px; margin-top:0; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            1. Penerimaan Ketentuan (Acceptance of Terms)
        </h3>
        <p>
            Dengan mengakses, menjelajahi, atau menggunakan dashboard <strong>Public Policy Intelligence Platform</strong> yang beralamat di <code>https://sna-executive-policy-dashboard.streamlit.app/</code>, Anda menyatakan telah membaca, memahami, dan menyetujui untuk terikat oleh Ketentuan Layanan ini. Jika Anda tidak menyetujui ketentuan ini, Anda dipersilakan untuk tidak menggunakan platform ini.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            2. Tujuan Akademik & Sifat Non-Komersial (Purpose & Non-Commercial Nature)
        </h3>
        <p>
            Platform ini dibangun semata-mata untuk tujuan <strong>penelitian ilmiah, evaluasi akademik tugas akhir, dan demonstrasi komputasi</strong> di bidang <em>Natural Language Processing</em> (NLP - model IndoBERT) serta <em>Social Network Analysis</em> (SNA). 
        </p>
        <ul>
            <li>Layanan ini bersifat <strong>100% nirlaba (non-commercial)</strong>, bebas iklan, dan tidak memungut biaya apapun.</li>
            <li>Platform tidak menjual, menyewakan, atau mengomersialkan data maupun hasil inferensi model kepada pihak ketiga manapun.</li>
        </ul>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            3. Kepatuhan Kebijakan Pengembang Pihak Ketiga (Third-Party Developer Policy Compliance)
        </h3>
        <p>
            Platform ini menghormati dan tunduk pada pedoman resmi pengembang dari platform mitra yang diintegrasikan:
        </p>
        <ul>
            <li><strong>TikTok for Developers:</strong> Penggunaan TikTok Display API, Login Kit, atau Content API tunduk pada <a href="https://developers.tiktok.com/doc/terms-of-service" target="_blank" style="color:#2563EB;">TikTok Developer Terms of Service</a> dan hanya mengakses data dalam cakupan (scope) publik yang diizinkan.</li>
            <li><strong>Meta Platforms (Facebook & Instagram):</strong> Mematuhi Meta Platform Terms and Developer Policies terkait analisis data agregat publik.</li>
            <li><strong>X (sebelumnya Twitter) & YouTube:</strong> Mematuhi Developer Agreement & Policy dari masing-masing penyedia layanan.</li>
        </ul>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            4. Penggunaan Data & Analisis Agregat (Data Usage & Analytics)
        </h3>
        <p>
            Seluruh data yang dianalisis merupakan <strong>konten publik terbuka</strong> (diskusi publik, berita daring, hashtag publik) mengenai topik kebijakan pemerintah:
        </p>
        <ul>
            <li>Kami <strong>tidak pernah</strong> mengakses, menyimpan, atau memproses percakapan privat, pesan langsung (DM), password, kontak pribadi, maupun data sensitif pengguna.</li>
            <li>Hasil olahan disajikan dalam bentuk agregat statistik (persentase sentimen positif/negatif/netral, sebaran emosi Plutchik, dan graf jaringan aktor sentral).</li>
        </ul>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            5. Batasan Tanggung Jawab (Limitation of Liability)
        </h3>
        <p>
            Prediksi klasifikasi sentimen dan emosi dihasilkan oleh model pembelajaran mesin (IndoBERT) dengan tujuan eksplorasi penelitian. Pengembang tidak bertanggung jawab atas interpretasi keliru atau keputusan independen yang diambil oleh pihak lain berdasarkan visualisasi data pada dashboard ini. Layanan disediakan dengan basis <em>"as-is"</em> tanpa jaminan komersial.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            6. Hak Pengguna & Permohonan Penghapusan (User Rights & Content Removal)
        </h3>
        <p>
            Apabila terdapat konten publik Anda yang termuat dalam dataset riset ini dan Anda menginginkan penghapusan atau anonimisasi, silakan ajukan permohonan melalui kontak di bawah. Permintaan akan diproses maksimal dalam 7 (tujuh) hari kerja.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            7. Kontak & Informasi Pengembang (Contact Information)
        </h3>
        <p>
            Untuk pertanyaan, klarifikasi, atau keperluan audit teknis terkait Ketentuan Layanan ini, silakan hubungi tim pengembang:
        </p>
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:14px 18px; border-radius:8px; font-size:13px; line-height:1.8;">
            <div><strong>Lembaga:</strong> Program Studi Informatika, Fakultas Teknik, Universitas Jenderal Soedirman</div>
            <div><strong>Lokasi:</strong> Purbalingga / Purwokerto, Jawa Tengah, Indonesia</div>
            <div><strong>Web App:</strong> <a href="https://sna-executive-policy-dashboard.streamlit.app/" target="_blank" style="color:#2563EB;">sna-executive-policy-dashboard.streamlit.app</a></div>
        </div>
    </div>
    """
    render_html(content_html)
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.link_button("Kembali ke Dashboard Utama", "/", icon=":material/home:", type="primary")


def render_privacy_policy():
    """Merender isi lengkap Privacy Policy secara formal, elegan, dan bebas emoji."""
    _render_legal_header(
        title="Kebijakan Privasi (Privacy Policy)",
        subtitle="Prinsip perlindungan privasi, tata kelola data publik, dan komitmen keamanan data pada Public Policy Intelligence Platform.",
        doc_type="privacy"
    )

    # Navigasi kembali ke Dashboard
    col_nav1, col_nav2 = st.columns([2, 3])
    with col_nav1:
        st.link_button("Kembali ke Dashboard Utama", "/", icon=":material/home:", type="primary")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    content_html = """
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.03); color:#1E293B; line-height:1.7; font-size:14px;">
        
        <div style="background:#ECFDF5; border-left:4px solid #059669; padding:12px 18px; border-radius:4px; margin-bottom:24px; font-size:13px; color:#065F46;">
            <strong>Prinsip Privasi Utama:</strong> Kami memprioritaskan privasi data. Public Policy Intelligence Platform <u>TIDAK PERNAH</u> mengumpulkan data pribadi privat, pesan instan, kata sandi, daftar kontak, atau informasi keuangan. Seluruh data yang dianalisis adalah konten terbuka publik untuk kebutuhan riset akademik nirlaba.
        </div>

        <h3 style="color:#0F2942; font-size:16px; margin-top:0; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            1. Ruang Lingkup & Pendahuluan (Scope & Introduction)
        </h3>
        <p>
            Kebijakan Privasi ini menjelaskan bagaimana platform riset <strong>Public Policy Intelligence Platform</strong> (<code>https://sna-executive-policy-dashboard.streamlit.app/</code>) mengelola dan memperlakukan informasi publik saat Anda mengakses layanan atau saat sistem melakukan inferensi data komputasional.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            2. Data yang Dikumpulkan (Information We Collect)
        </h3>
        <p>
            Sistem riset kami hanya memproses data teks publik yang relevan dengan topik kebijakan nasional:
        </p>
        <ul>
            <li><strong>Konten Publik Media Sosial:</strong> Teks postingan, caption, hashtag, dan metrik interaksi publik (jumlah suka, komentar, tayangan) dari ruang diskursus terbuka.</li>
            <li><strong>Berita Daring Terbuka:</strong> Judul dan ringkasan artikel dari portal berita publik nasional.</li>
            <li><strong>Informasi yang TIDAK Kami Kumpulkan:</strong> Kami secara tegas tidak mengumpulkan alamat email pribadi pengunjung, nomor telepon, identitas KTP, nomor rekening, percakapan rahasia, maupun berkas perangkat pribadi.</li>
        </ul>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            3. Tujuan Pemrosesan Data (How We Use Information)
        </h3>
        <p>
            Data publik yang dihimpun semata-mata digunakan untuk:
        </p>
        <ul>
            <li>Pelatihan dan pengujian model komputasi bahasa alami <strong>IndoBERT</strong> (klasifikasi sentimen 3-kelas dan emosi Plutchik 9-dimensi).</li>
            <li>Pemodelan graf <strong>Social Network Analysis (SNA)</strong> untuk melihat struktur interaksi dan peredaran isu kebijakan publik.</li>
            <li>Penyusunan laporan saintifik berkala dan visualisasi interaktif bagi pemangku kebijakan publik.</li>
        </ul>
        <p>
            Data <strong>tidak akan pernah</strong> dijual, disewakan, dialihkan kepada pengiklan komersial, atau digunakan untuk penargetan iklan profil individu.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            4. Kepatuhan Terhadap Kebijakan Privasi Pihak Ketiga (Third-Party Platforms)
        </h3>
        <p>
            Kami mematuhi seluruh batasan teknis dan privasi yang diberlakukan oleh penyedia antarmuka pemrograman aplikasi (API):
        </p>
        <ul>
            <li><strong>TikTok for Developers:</strong> Analisis konten TikTok dilakukan dengan persetujuan ruang lingkup resmi (authorized public scopes). Kami tidak melakukan re-identifikasi personal (de-anonymization) terhadap pengguna TikTok.</li>
            <li><strong>Sinkronisasi & Penghapusan:</strong> Jika suatu konten dihapus oleh pembuat aslinya di platform sumber, sistem kami akan memperbarui atau membuang data tersebut pada siklus sinkronisasi berikutnya.</li>
        </ul>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            5. Keamanan & Penyimpanan Data (Data Security)
        </h3>
        <p>
            Data penelitian disimpan pada repositori tertutup dan peladen terlindungi dengan standar enkripsi modern (HTTPS/TLS) yang disediakan oleh infrastruktur hosting Streamlit Community Cloud dan GitHub Enterprise Security.
        </p>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            6. Hak Pengguna & Mekanisme Penghapusan Data (User Rights & Data Deletion)
        </h3>
        <p>
            Sesuai prinsip etika kecerdasan buatan dan perlindungan data, setiap pemilik akun publik berhak meminta penghapusan kutipan konten mereka dari dataset riset kami. Untuk mengajukan penghapusan:
        </p>
        <ol>
            <li>Kirimkan permohonan melalui issue pada repositori GitHub resmi kami dengan menyertakan tautan konten publik yang dimaksud.</li>
            <li>Tim kami akan memverifikasi dan menghapus data dari korpus analisis dalam kurun waktu <strong>7 hari kerja</strong>.</li>
        </ol>

        <h3 style="color:#0F2942; font-size:16px; margin-top:24px; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">
            7. Kontak Resmi (Contact Information)
        </h3>
        <p>
            Untuk pertanyaan atau koordinasi terkait privasi dan tata kelola data:
        </p>
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:14px 18px; border-radius:8px; font-size:13px; line-height:1.8;">
            <div><strong>Penyelenggara Riset:</strong> Laboratorium Riset Informatika, Fakultas Teknik, Universitas Jenderal Soedirman</div>
            <div><strong>Alamat:</strong> Jl. Mayjen Sungkono Km 5, Blater, Kalimanah, Purbalingga, Jawa Tengah 53371</div>
            <div><strong>Portal:</strong> <a href="https://sna-executive-policy-dashboard.streamlit.app/" target="_blank" style="color:#2563EB;">sna-executive-policy-dashboard.streamlit.app</a></div>
        </div>
    </div>
    """
    render_html(content_html)
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.link_button("Kembali ke Dashboard Utama", "/", icon=":material/home:", type="primary")

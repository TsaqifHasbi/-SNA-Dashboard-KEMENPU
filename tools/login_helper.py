import os
import sys
import time

def open_login(platform):
    platform = platform.lower().strip()
    if platform in ['ig', 'instagram']:
        profile_dir = os.path.join(os.path.expanduser("~"), ".ig_scraper_profile")
        target_url = "https://www.instagram.com/accounts/login/"
        name = "INSTAGRAM"
        user_val = "email4tsaqif@gmail.com"
        pass_val = "Aghnasyarief4"
    elif platform in ['tt', 'tiktok']:
        profile_dir = os.path.join(os.path.expanduser("~"), ".tiktok_scraper_profile")
        target_url = "https://www.tiktok.com/login"
        name = "TIKTOK"
        user_val = "email4tsaqif@gmail.com"
        pass_val = "Aghnasyarief4"
    else:
        print(f"Platform '{platform}' tidak dikenal. Pilih: ig atau tiktok")
        return

    print("=" * 65)
    print(f"🔑 LOGIN HELPER: {name}")
    print(f"📁 Folder Profil: {profile_dir}")
    print(f"👤 Akun Target  : {user_val}")
    print("=" * 65)
    print("1. Jendela Chrome akan terbuka.")
    print("2. Form login akan otomatis dicoba terisi.")
    print("3. Jika muncul verifikasi (OTP / email / puzzle), silakan selesaikan.")
    print("4. Setelah berhasil masuk ke Beranda, tekan ENTER di terminal ini.")
    print("=" * 65)

    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument(f'--user-data-dir={profile_dir}')
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--password-store=basic')
        
        driver = uc.Chrome(options=options)
        driver.get(target_url)
        time.sleep(3)

        # Coba auto-fill untuk Instagram
        if platform in ['ig', 'instagram']:
            try:
                u_els = driver.find_elements('name', 'username')
                p_els = driver.find_elements('name', 'password')
                if u_els and p_els:
                    u_els[0].clear()
                    u_els[0].send_keys(user_val)
                    time.sleep(0.5)
                    p_els[0].clear()
                    p_els[0].send_keys(pass_val)
                    print("\n  ✨ [AUTO-FILL] Username dan password Instagram sudah otomatis diisikan!")
                    print("     Silakan klik tombol 'Log In' di jendela Chrome.")
            except Exception as e_fill:
                pass

        input("\n👉 Tekan ENTER di sini jika Anda SUDAH BERHASIL MASUK ke Beranda... ")
        print("[OK] Sesi login tersimpan permanen ke profil Chrome!")
        try:
            driver.quit()
        except:
            pass
        print(f"✅ Selesai! Sesi {name} sudah aktif dan siap digunakan scraper.")
    except Exception as e:
        print(f"[ERR] Gagal membuka Chrome: {e}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'ig'
    open_login(target)

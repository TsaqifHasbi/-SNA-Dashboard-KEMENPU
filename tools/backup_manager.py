import os
import shutil

def get_next_backup_path(file_path: str) -> str:
    """
    Mencari nama file backup berikutnya dengan penomoran bertingkat:
    nama (1).ext, nama (2).ext, nama (3).ext, dst.
    """
    dir_name = os.path.dirname(os.path.abspath(file_path))
    base_name = os.path.basename(file_path)
    stem, ext = os.path.splitext(base_name)
    
    idx = 1
    while True:
        candidate_name = f"{stem} ({idx}){ext}"
        candidate_path = os.path.join(dir_name, candidate_name)
        if not os.path.exists(candidate_path):
            return candidate_path
        idx += 1

def backup_incremental_file(file_path: str, verbose: bool = True) -> str:
    """
    Menduplikasi file_path yang ada ke file backup bertingkat:
    contoh: enriched_corpus_for_sna.parquet -> enriched_corpus_for_sna (1).parquet.
    Jika (1) sudah ada, otomatis naik ke (2), (3), dst.
    """
    if not os.path.exists(file_path):
        if verbose:
            print(f"ℹ️ File {file_path} belum ada, tidak perlu backup.")
        return None
        
    backup_path = get_next_backup_path(file_path)
    shutil.copy2(file_path, backup_path)
    if verbose:
        print(f"📦 [BACKUP BERHASIL] File lama berhasil diamankan ke:")
        print(f"   -> {os.path.basename(backup_path)}")
    return backup_path

if __name__ == '__main__':
    target = os.path.join('data', 'enriched_corpus_for_sna.parquet')
    next_path = get_next_backup_path(target)
    print(f"File Target : {target}")
    print(f"Calon Backup: {next_path}")

"""
Post-Processing Sentiment Correction Layer
===========================================
Memperbaiki klasifikasi sentimen IndoBERT yang masih salah,
terutama untuk konten sarkastik, umpatan, kritik kebijakan, hiburan viral, dan emosi kuat.

Diterapkan SETELAH inferensi IndoBERT, mengoreksi label yang jelas salah.
"""

import re

# ============================================================
# 1. KAMUS INDIKATOR NEGATIF KUAT
# ============================================================

# Umpatan & bahasa kasar (selalu negatif)
PROFANITY = {
    'ajg', 'anjg', 'anjing', 'bangsat', 'bajingan', 'brengsek', 'tolol', 'bodoh',
    'goblok', 'goblog', 'idiot', 'bego', 'dungu', 'kontol', 'memek', 'ngentot',
    'entot', 'peler', 'jembut', 'lonte', 'ngewe', 'cuks', 'cuk', 'cok', 'ancuk', 'ancok',
    'tai', 'taik', 'setan', 'iblis', 'keparat', 'kampret', 'jancok', 'jancuk',
    'asu', 'asw', 'bgst', 'anjir', 'anjrit', 'biadab', 'bedebah', 'sialan',
    'fuck', 'shit', 'damn', 'wtf', 'stfu', 'asshole', 'bullshit',
}

# Frasa negatif kuat — konteks kebijakan publik & keluhan warga
STRONG_NEGATIVE_PHRASES = [
    # Tuntutan penghentian program
    'stop mbg', 'hentikan mbg', 'bubarin mbg', 'bubarkan mbg', 'setop mbg',
    'hentikan program mbg', 'stop world tour', 'negara ancur', 'negara lu ancur', 'negara hancur',
    
    # Korupsi & skandal
    'korupsi', 'koruptor', 'korup', 'bancakan', 'pencurian', 'penipuan',
    'manipulasi', 'mark up', 'markup', 'pungli', 'sunat anggaran',
    'pemborosan', 'pemborosan apbn', 'maling', 'mencuri', 'dirampok',

    # Kerusakan Fisik Infrastruktur & Masalah Proyek PU
    'sangat buruk', 'keadaan sangat buruk', 'kondisi sangat buruk', 'kualitas sangat buruk',
    'rusak parah', 'rusak berat', 'hancur parah', 'hancur lebur',
    'jalan rusak', 'jalan berlubang', 'jalan bolong', 'jalan ambles', 'jalan amblas',
    'aspal buruk', 'aspal hancur', 'aspal mengelupas', 'aspal tipis',
    'jembatan ambruk', 'jembatan putus', 'jembatan roboh',
    'tanggul jebol', 'bendungan bocor', 'pipa bocor',
    'proyek mangkrak', 'mangkrak bertahun-tahun', 'pekerjaan amburadul',
    
    # Keracunan & bahaya makanan
    'keracunan', 'beracun', 'racun', 'mematikan', 'cacing', 'ulat',
    'basi', 'busuk', 'jorok', 'mual', 'muntah', 'diare',
    'poisoned', 'hospitalized',
    
    # Tuntutan & protes aksi (tidak memasukkan 'demo' polos agar #demo/demonstrasi teknologi tidak salah kena)
    'hidup mahasiswa', 'turunkan harga', 'turun ke jalan', 'aksi demo', 'didemo', 'unjuk rasa',
    'tuntutan aksi', 'setop pemborosan', 'menggerus', 'menggeru',
    
    # Kekecewaan mendalam & penderitaan
    'sedih banget', 'nangis', 'menangis', 'ga tega', 'gak tega',
    'miris', 'tragis', 'menyedihkan',
    'we\'re finished', 'we are finished', 'innalillahi', 'terbakar habis',
    
    # Kritik tajam / penolakan
    'banyak anak putus sekolah', 'terancam putus sekolah', 'angka putus sekolah naik',
    'tuli terhadap', 'tutup mata', 'tutup telinga',
    'pura-pura buta', 'pura-pura tuli', 'pura² buta', 'pura² tuli',
    'pura buta', 'pura tuli', 'ngorbanin', 'korbanin',
    'self centered', 'narcissistic',
    'yang gila apa mereka', 'gw yg gila', 'gmn sih ini',
    'heran kok bisa jadi presiden', 'heran kok bisa',
    'halu', 'khayalan', 'ngayal', 'blm bisa kok', 'belum bisa kok', 'bukan negara kaya',
    'omon omon', 'omon-omon',
    'lebih genting', 'problematic', 'scarce',
    'bingkai foto', 'sppg cuman ngabdi', 'sppg hanya ngabdi',
    'weekend in bali, always flying', 'broken perpajakannya',
    
    # Isu Pemborosan, Buang Anggaran & Ketidakefektifan
    'buang anggaran', 'buang-buang anggaran', 'buang uang', 'buang duit', 'buang-buang duit', 'buang-buang uang',
    'bakar uang', 'bakar duit', 'hambur uang', 'hambur duit', 'hamburkan uang', 'sia-sia', 'sia sia',
    'memilih pulang ketimbang', 'lebih memilih pulang', 'tidak betah', 'tak betah', 'ga betah',

    # Isu Penyelewengan, Penyalahgunaan & Ketidaktepatan Sasaran
    'disalahgunakan', 'menyalahgunakan', 'penyalahgunaan', 'salah gunakan', 'salah guna',
    'diselewengkan', 'penyelewengan', 'menyelewengkan', 'menyeleweng',
    'salah sasaran', 'tidak tepat sasaran', 'kurang tepat sasaran', 'salah target',
    'kurang tepat', 'tidak tepat', 'salah alokasi', 'penyimpangan', 'disimpangkan',

    # Perbandingan Pejoratif Kolonial & Kemunduran Zaman
    'penjajahan', 'penjajah', 'zaman penjajahan', 'masa penjajahan', 'era penjajahan', 'jaman penjajahan',
    'balik masa penjajahan', 'balik ke zaman penjajahan', 'zaman belanda', 'zaman jepang', 'romusha', 'kerja rodi',
    'sebelas dua belas', 'malah bukak', 'malah buka',

    # Isu Ketidakmampuan, Kelalaian & Kegagalan Birokrasi
    'ga becus', 'gak becus', 'tidak becus', 'tak becus', 'bgn ga becus', 'bgn gak becus',
    'naik pitam', 'kelalaian', 'bikin publik geleng kepala', 'arogansi kekuasaan',
    'menteror', 'ketiadaan pemeliharaan', 'menteri pu murka', 'gabut apa',

    # Isu Ketiadaan Manfaat, Kesia-siaan & Kekecewaan Efektivitas Kebijakan
    'gada manfaat', 'gada manfaatnya', 'gaada manfaat', 'gaada manfaatnya',
    'ga ada manfaat', 'ga ada manfaatnya', 'gak ada manfaat', 'gak ada manfaatnya',
    'ngga ada manfaat', 'nggak ada manfaat', 'tidak ada manfaat', 'tidak ada manfaatnya',
    'tak ada manfaat', 'tak ada manfaatnya', 'kurang bermanfaat', 'belum ada manfaat',
    'gada guna', 'gada gunanya', 'gaada guna', 'gaada gunanya',
    'ga ada guna', 'ga ada gunanya', 'gak ada guna', 'gak ada gunanya',
    'tidak ada guna', 'tidak ada gunanya', 'tak ada guna', 'tak ada gunanya',
    'gada faedah', 'gada faedahnya', 'gaada faedah', 'gaada faedahnya',
    'ga ada faedah', 'ga ada faedahnya', 'tidak ada faedah', 'tidak ada faedahnya',
    'gada efek', 'gada efeknya', 'gaada efek', 'gaada efeknya', 'ga ada efek', 'tidak ada efek',
    'gada hasil', 'gada hasilnya', 'gaada hasil', 'gaada hasilnya', 'ga ada hasil', 'tidak ada hasil',
    'gada dampak', 'gada dampaknya', 'gaada dampak', 'gaada dampaknya', 'ga ada dampak', 'tidak ada dampak',
    'gada kemajuan', 'gaada kemajuan', 'gada perkembangan', 'gaada perkembangan',
    'gada perubahan', 'gaada perubahan', 'tidak ada perubahan',
    'gada kejelasan', 'gaada kejelasan', 'ga jelas', 'gak jelas', 'kaga jelas', 'tidak jelas',
    'mana buktinya', 'mana hasilnya', 'mana janjinya', 'mana kerjanya', 'mana realisasinya',
    'cuma pencitraan', 'hanya pencitraan', 'cuma formalitas', 'hanya formalitas',
    'cuma buang anggaran', 'hanya buang anggaran', 'cuma buang duit', 'cuma bakar duit',
    'apasi tujuan', 'apa sih tujuan', 'buat apa sih',
    'kok sampe detik ini', 'kok sampe sekarang', 'kok sampai sekarang',

    # Politisasi, Manipulasi Kekuasaan & Sinisme Kepentingan Politik
    'cara licik', 'kelicikan', 'licik', 'siasat licik',
    'kepentingan politik', 'kepentingan penguasa', 'kepentingan segelintir',
    'alat politik', 'tunggangan politik', 'politisasi', 'dipolitisasi',
    'kampanye terselubung', 'beli suara', 'suap rakyat',
    'demi kekuasaan', 'demi pemilu', 'motif politik', 'langgengkan kekuasaan',
    'biar jadi pendukung', 'agar jadi pendukung',

    # Sarkasme mematikan
    'mematikan banget',
]

# Frasa sarkasme & keluhan sinis (terlihat positif/ringan tapi menyindir tajam atau diikuti realitas negatif)
SARCASM_PATTERNS = [
    # 0. Keluhan Retoris & Sinisme Ketiadaan Manfaat Kebijakan (dibatasi pada satu klausa/kalimat)
    r'\b(?:apasi|apa\s*sih|apaan\s*sih|buat\s*apa)\b[^.!?\n]{0,70}\b(?:tujuan|urgensi|faedah|fungsi|manfaat|guna)\b',
    r'\b(?:apasi|apa\s*sih|apaan\s*sih|buat\s*apa)\b[^.!?\n]{0,70}\b(?:kok|kenapa|tapi|malah)\b[^.!?\n]{0,70}\b(?:ga|gak|ngga|nggak|gada|gaada|belum|tidak|nihil)\b',
    r'\b(?:kok|kenapa)\b[^.!?\n]{0,80}\b(?:sampe\s+detik\s+ini|sampe\s+sekarang|sampai\s+sekarang|hingga\s+kini|hingga\s+saat\s+ini|sampe\s+hari\s+ini)\b[^.!?\n]{0,60}\b(?:gada|gaada|ga|gak|ngga|nggak|belum|tidak|nihil)\b',
    r'\b(?:gada|gaada|ga\s+ada|gak\s+ada|nggak\s+ada|tidak\s+ada|tak\s+ada)\s+(?:manfaat|manfaatnya|guna|gunanya|faedah|faedahnya|efek|efeknya|hasil|hasilnya|dampak|dampaknya)\b',
    r'\bkatanya\b[^.!?\n]{0,80}\b(?:tapi|namun|padahal|malah|nyatanya|faktanya)\b[^.!?\n]{0,80}\b(?:ga|gak|ngga|nggak|gada|gaada|belum|tidak|bukan|kurang|nihil)\b',
    # 0c. Sarkasme Pelayanan Publik & Kinerja Infrastruktur (Pujian Semu + Sindiran Kelambanan / Kerusakan / Kondisi Buruk)
    # Contoh: "Apresiasi respon cepat Kementerian PU ... dengan keadaan jalan yang sangat buruk, hebat sekali kemenpu"
    #         "Kemenpu keren banget masa hal sepele kaya kebocoran bendungan aja diselesainnya lama banget"
    #         "hebat betul jalan baru seminggu udah bolong-bolong parah"
    #         "terima kasih kemenpu jalan makin hancur lebur"
    r'\b(?:apresiasi|terima\s+kasih|makasih|salut|hebat|keren|mantap|top|luar\s+biasa|juara|bagus|terpuji)\b[^.!?\n]{0,90}\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun|meski|walau|walaupun)\s+(?:keadaan|kondisi|kualitas|situasi)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air|fisik)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|amburadul|jelek|kacau)\b',
    r'\b(?:hebat|keren|mantap|top|luar\s+biasa|juara|bagus|istimewa)\s+(?:banget+|bgt+|sekali|bet|bener|betul|beneran)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri|balai|pemda)\b[^.!?\n]{0,90}\b(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|jelek)\b',
    r'\b(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|jelek)\b[^.!?\n]{0,90}\b(?:hebat|keren|mantap|top|luar\s+biasa|juara|bagus|istimewa)\s+(?:banget+|bgt+|sekali|bet|bener|betul|beneran)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri|balai|pemda)\b',
    r'\b(?:selesai|menyelesaikan|diresmikan|peresmian|beres|sukses|tuntas)\b[^.!?\n]{0,90}\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun)\s+(?:keadaan|kondisi|kualitas|situasi|hasil)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air|fisik)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|amburadul|jelek|kacau)\b',
    r'\b(?:respon\s+cepat|respons\s+cepat|gercep|responsif)\b[^.!?\n]{0,90}\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun)\s+(?:keadaan|kondisi|kualitas|situasi)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|mangkrak|ambruk|lelet|lama|ambles|jebol|bolong)\b',
    r'\b(?:terima\s+kasih|makasih|thanks|tengkyu)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri)\b[^.!?\n]{0,80}\b(?:jalan|jembatan|tanggul|proyek|irigasi)\b[^.!?\n]{0,40}\b(?:makin|malah|justru|tambah)\s+(?:rusak|hancur|parah|buruk|ancur|mangkrak|bolong|ambles)\b',
    r'\bapresiasi\b[^.!?\n]{0,70}\b(?:keadaan|kondisi|kualitas)\s+(?:jalan|jembatan|aspal|infrastruktur|proyek|air)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|ancur|mangkrak|ambruk|bolong)\b',
    r'\b(?:keren|hebat|mantap|top|luar\s+biasa|bagus|pinter|pintar)\s+(?:banget+|bgt+|sekali|bet|bener|betul)\b[^.!?\n]{0,70}\b(?:masa|kok|padahal|giliran)\b[^.!?\n]{0,70}\b(?:sepele|gitu\s+aja|gini\s+aja|kecil|lama|lelet|lambat|ga\s+bisa|gak\s+bisa|tidak\s+bisa|bocor|kebocoran|rusak|ancur|hancur|bolong|ambruk)\b',
    r'\b(?:keren|hebat|mantap|bagus)\s+(?:banget+|bgt+|bet|sekali)\b[^.!?\n]{0,70}\b(?:diselesaikannya|diselesainnya|dikerjakannya|dikerjainnya|nanganinnya|penanganannya|kerjanya)\s+(?:lama|lelet|lambat|parah|molor)\b',
    r'\b(?:masa|kok)\b[^.!?\n]{0,60}\b(?:hal\s+sepele|masalah\s+sepele|gini\s+aja|gitu\s+aja|kaya\s+gitu|kaya\s+gini)\b[^.!?\n]{0,60}\b(?:lama|lelet|lambat|ga\s+becus|gak\s+becus|ga\s+bisa|gak\s+bisa|berlarut|mangkrak|molor)\b',
    r'\b(?:keren|hebat|mantap)\s+(?:banget+|bgt+|sekali)\b[^.!?\n]{0,70}\b(?:baru\s+(?:seminggu|sebulan|beberapa\s+hari)|belum\s+setahun)\b[^.!?\n]{0,40}\b(?:udah|sudah)\s+(?:rusak|bolong|hancur|ambruk|retak|jebol)\b',
    # 0b. Pujian semu kontras / sindiran peningkatan (wajib dalam satu klausa & berbatas kata penuh)
    r'\b(?:makin|semakin)?\s*(?:berguna|bermanfaat|hebat|keren|mantap|bagus)\s+(?:banget+|bgt+|sekali|betul)?[^.!?\n]{0,80}\b(?:keracunan|diare|masuk\s+rs|mual|muntah|\bmati\b|\bkorban\b|ga\s+becus|gak\s+becus|tidak\s+becus|korupsi|bancakan|nilep)\b',
    # 1. Pujian semu + Realitas bahaya/korupsi/bencana/keracunan (dengan tanda baca apa pun)
    r'\b(?:berguna|bermanfaat|hebat|keren|mantap|bagus|berkah)\s+(?:banget+|bgt+|sekali)[!.,?\s]+[^.!?\n]{0,60}\b(?:buat|untuk)\s+(?:bikin|buat)?\s*(?:keracunan|masuk\s+rs|mual|muntah|diare|mati|korban|bancakan|nilep|korupsi|bagi-bagi|vendor\s+nakal|pemborosan|utang|tekor|rusak|ancur|hancur)\b',
    # 2. Pujian semu + bantahan realitas (tapi bohong/boong, tapi kenyataannya, tapi basi/ulat)
    r'\b(?:berguna|bermanfaat|hebat|keren|mantap|bagus|enak)\s+(?:banget+|bgt+|sekali)[!.,?\s]+[^.!?\n]{0,60}\b(?:tapi|padahal|kenyataannya|faktanya|nyatanya)\s+[^.!?\n]{0,50}\b(?:bohong|boong|basi|busuk|ulat|cacing|racun|keracunan|rusak|ancur|hancur|bancakan|korup|zonk|sampah)\b',
    # 3. Keracunan / Bencana yang dibungkus kata seru pujian di awal kalimat
    r'\b(?:woi+|woy+|anjir|njir|gila)\s+[^.!?\n]{0,50}\b(?:berguna|bermanfaat|hebat|mantap|keren)\b[^.!?\n]{0,70}\b(?:keracunan|bancakan|masuk\s+rs|opname|korup|nilep|basi|ulat)\b',
    # 4. Saking bergunanya / saking bagusnya
    r'\bsaking\s+(?:berguna|bermanfaat|bagus|hebat|keren|enak)\b[^.!?\n]{0,60}\b(?:sampe|sampai)\s+(?:keracunan|masuk\s+rs|rugi|muntah|basi|protes|demo|opname)\b',
    # 5. Pas dibuka ternyata basi/berulat/zonk
    r'\b(?:enak|lezat|nikmat)\s+(?:banget+|bgt+|sekali)\b[^.!?\n]{0,60}\b(?:pas|waktu|saat)\s+(?:dibuka|dilihat|dimakan|diperiksa)\b[^.!?\n]{0,50}\b(?:basi|ulat|cacing|bau|asam|zonk)\b',
    # 6. Anggaran habis / utang numpuk
    r'\b(?:keren|hebat|mantap)\s+(?:banget+|bgt+|sekali)\b[^.!?\n]{0,70}\b(?:anggaran|apbn|duit)\b[^.!?\n]{0,50}\b(?:habis|ludes|jebol|bancakan|utang)\b',
    r'\btepuk\s+tangan\b[^.!?\n]{0,50}\b(?:buat|atas)\b[^.!?\n]{0,50}\b(?:keracunan|bancakan|korupsi|kebobrokan)\b',
    # 7. Sindiran politik & kebijakan populer (wajib berbatas kata penuh)
    r'\bmana\s+gas\s+mana\s+gas\b',
    r'2024\s*:\s*oke\s+gas[^.!?\n]{0,40}2025\s*:\s*mana\s+gas',
    r'\bgila+\s+indah\b',
    r'\bindahnya+\b',
    r'\bsppg\s+tutup\b[^.!?\n]{0,50}\bharga\b[^.!?\n]{0,30}\b(?:turun|murah)\b',
    r'\btutup\b[^.!?\n]{0,40}\bharga\s+telor\s+turun\b',
    r'\bmasih\s+(?:aja\s+)?(?:di\s*dukung|didukung|dibela)\b',
    r'\bpengen\s+tau\b[^.!?\n]{0,50}\b(?:brengsek|pidato\s+apa)\b',
    r'\bkok\s+(?:lu|kamu|dia)\s+(?:nentang|kritis)\b',
    r'\bmolto\b[^.!?\n]{0,40}\bmbg\s+mematikan\b',
    r'\bprivate\s+jet\b[^.!?\n]{0,40}\bdenpasar\b',
    r'\bweekend\s+in\s+bali\b',
    # 8. Retorika kemunduran / perbandingan masa penjajahan / satir era kolonial
    r'\b(?:balik|kembali)\s+(?:ke\s+)?(?:masa|zaman|jaman|era)\s+(?:penjajahan|belanda|jepang|kolonial)\b',
    r'\b(?:zaman|jaman|era|masa)\s+penjajahan\s+(?:kah|kali|ya|bray)\b',
    r'(?:sama\s+aja|mirip|kayak|seperti|persis)[^.!?\n]{0,30}\b11\s*[-/]\s*12\b|\b11\s*[-/]\s*12\b[^.!?\n]{0,20}\b(?:sama|mirip|kayak|seperti|persis)\b',
    r'\b(?:bukannya|tinggal)\s+[^.!?\n]{0,50}\bmalah\s+(?:buka|bukak|bikin|buat)\s+(?:sekolah\s+rakyat|program)\b',
]

# ============================================================
# 2. KAMUS INDIKATOR POSITIF KUAT
# ============================================================

STRONG_POSITIVE_PHRASES = [
    # Makanan enak & menu MBG
    'tongseng ayam', 'nasi goreng', 'ayam goreng', 'makan siang enak',
    'menu mbg hari ini', 'enak banget', 'mantap', 'lezat', 'nikmat', 'yummy',
    
    # Hiburan viral & keseruan (konservatif: hanya frasa yang jelas gembira)
    'kocak', 'lucu', 'ngakak', 'lawak', 'gemes',
    'buru-buru habisin', 'foto sama wapres', 'foto sama presiden',
    
    # Doa & apresiasi program prioritas
    'sehat sehat', 'berkah', 'alhamdulillah', 'bersyukur', 'terima kasih',
    'apresiasi', 'berhasil', 'sukses', 'bermanfaat', 'dukung mbg',
    'berguna banget', 'sangat berguna', 'berguna', 'amat berguna',
    'sangat bermanfaat', 'bermanfaat banget', 'sangat membantu', 'membantu banget',
    'sangat efektif', 'efektif banget', 'keren banget', 'mantap banget',
    
    # Program Sekolah Rakyat & Jaring Pengaman Sosial
    'sekolah rakyat mirip sekolah kalangan elit', 'mirip sekolah kalangan elit',
    'tanda harapan yang akhirnya menemukan jalan', 'harapan yang dihidupkan kembali',
    'pendidikan anak dijamin lewat pip & sekolah rakyat', 'dijamin lewat pip & sekolah rakyat',
    'suasana belajar kini jauh lebih nyaman dan aman', 'harapan baru dari sekolah rakyat',
    'titipan surat dari siswa-siswi sekolah rakyat', 'kini sekolah gratis di sekolah rakyat',
    'membangun semuanya dari nol', 'putus rantai kemiskinan', 'memutus rantai kemiskinan',
    # Capaian Infrastruktur, Perbaikan Rampung & Kabar Baik (KemenPU)
    'kabar baik', 'hadir dengan wajah baru', 'tampil dengan wajah baru',
    'resmi beroperasi', 'siap dilintasi', 'kini sudah lebih lapang',
    'mobilitas warga makin lancar', 'menurunkan angka kecelakaan',
    'sinergi kuat', 'langkah nyata', 'runtuhkan keterisolasian',
    'dirgahayu republik indonesia', 'merdeka!', 'selamat hari jadi',
]

# Pola Pembelaan Kebijakan & Afirmasi Kebaikan Program (Pro-Policy Defense Patterns)
# Mengantisipasi makian/slang yang sebenarnya ditujukan kepada pihak pengkritik atau sebagai kata seru kekaguman
PRO_POLICY_DEFENSE_PATTERNS = [
    # 1. Afirmasi kebaikan program: "udah baik dikasih makan gratis", "udah dibantu sekolah rakyat", "mending dapat makan gratis"
    r'(?:udah|sudah)\s+(?:baik|bagus|enak|gratis|mending|dibantu|dikasih|diberi)\s+',
    r'(?:mending|untung)\s+(?:ada|dikasih|diberi|dapat)\s+(?:mbg|makan\s+gratis|sekolah\s+rakyat|bantuan)',
    # 2. Kurang bersyukur / masih nyinyir: "udah dikasih makan gratis masih aja nyinyir", "udah gratis masih aja protes"
    r'(?:udah|sudah)\s+(?:gratis|dikasih|dibantu).*?(?:masih\s+(?:aja|saja|lu)?\s*(?:protes|nyinyir|ngeluh|bacot|komplain|banyak\s+omong|kurang))',
    r'(?:ga|gak|tidak)\s+(?:tahu\s+diri|bersyukur|tau\s+diri|terima\s+kasih)',
    # 3. Mengecam penentang program: "yang nolak mbg tolol", "buzzer yang jelekin mbg babi"
    r'(?:yang|yg)\s+(?:nolak|nyinyir|hujat|kritik|nyerang|fitnah|benci|gasuka|gak\s+suka|jelek-jelekin|ngejelekin)\s+(?:mbg|kdmp|program|sekolah\s+rakyat).*?\b(?:tolol|goblok|bego|babi|anjing|dungu|kampret|bangsat|sialan)\b',
    # 4. Melarang menjelekkan program: "jangan fitnah mbg anjing"
    r'(?:jangan|jgn|ngapain)\s+(?:fitnah|nyinyir|hujat|jelekin|ngejelekin)\s+(?:mbg|kdmp|program|sekolah\s+rakyat)',
    # 5. Slang penguat pujian (intensifier): "anjir enak banget", "cok mantap pol", "jancuk bergizi tenan"
    r'\b(?:anjir|njir|cok|cuk|cuks|asu|jancuk|jancok|gila|goblok)\b\s+(?:banget\s+)?(?:enak|keren|mantap|mantul|lezat|nikmat|juara|mewah|lengkap|top|kenyang|bagus|berkah|membantu|bergizi)',
    r'\b(?:enak|keren|mantap|mantul|lezat|nikmat|juara|mewah|lengkap|top|kenyang|bagus|bergizi)\b\s+(?:banget|bgt|bet|pol|tenan)?\s*(?:cok|cuk|cuks|anjir|njir|jancok|jancuk|asu)'
]

# Emoji yang jelas positif
POSITIVE_EMOJIS = {'😋', '😊', '🥰', '❤️', '💖', '💕', '👍', '🙏', '😍', '🤩', '🎉', '🥳', '✨', '💪', '🔥', '🤤'}

# Emoji yang jelas marah/sedih/hancur (jangan masukkan 😱 karena sering dipakai di konten viral/shorts humor)
NEGATIVE_EMOJIS = {'😢', '😭', '😡', '🤬', '💀', '🤮', '😤', '😫', '😩', '💔', '🖕'}

# ============================================================
# 3. POLA NETRAL / BERITA FAKTUAL
# ============================================================

NEUTRAL_INFORMATIONAL_PREFIXES = [
    r'^(?:resmi\s*:|breaking\s+news\s*:|sekilas\s+info\s*:|cuma\s+mau\s+info|maaf\s+ganggu.*?cuma\s+mau\s+info|sekadar\s+info|info\s+penting\s*:)',
    # Arahan protokoler kepresidenan & pernyataan dinas pemerintah (informasi faktual)
    r'(?:presiden\s+prabowo(?:\s+subianto)?|pemerintah|kementerian|badan\s+gizi\s+nasional|kepala\s+bgn)\s+(?:menegaskan|memberi\s+arahan|menginstruksikan|menyampaikan|menggelar|resmikan|melantik)',
    # Kegiatan kedinasan formal, sosialisasi, & bimtek
    r'(?:bimbingan\s+teknis|bimtek|sosialisasi|rapat\s+konsolidasi|rapat\s+koordinasi|rakor|lokakarya|penjamah\s+makanan|bedah\s+buku|webinar|seminar|pelatihan|narasumber\s*:|e-sertifikat|daftar\s+kement(?:e)?rian)',
    # Klarifikasi publik warga (berterima kasih ke rakyat / anggaran uang rakyat bukan uang pribadi)
    r'(?:terima\s+kasih\s+itu\s+rakyat|bukan\s+duit(?:nya)?\s+pak\s+prabowo|bukan\s+uang\s+pribadi|duitnya\s+rakyat)',
    # Analisis elektoral & pemetaan kekuatan politik objektif
    r'(?:kekuatan\s+pendukung\s+prabowo\s+di\s+pemilu\s+2029|kenapa\s+prabowo\s+(?:kemungkinan\s+besar\s+)?terpilih\s+lagi)',
    # Pengumuman rekrutmen / formasi CASN & PPPK kedinasan
    r'(?:rekrutmen\s+casn.*?dibuka|membuka\s+\d+\s+formasi\s+pppk|formasi\s+pppk\s+guru)',
    # Berita komparasi program pendidikan (explanatory journalism)
    r'(?:apa\s+bedanya\s+dengan\s+sekolah\s+rakyat|perbedaan\s+sekolah\s+negeri\s+vs\s+sekolah\s+rakyat)',
    # Konten edukasi / ensiklopedis infrastruktur akun resmi Balai/PU ("Tanggul adalah...", "Halo Sobat...", "Yuk simak...")
    r'^(?:halo,?\s+sobat|hai\s+sobat|tahukah\s+(?:kamu|sobat|anda)|yuk\s+simak)\b',
    r'\b(?:adalah\s+bangunan\s+di\s+sepanjang|memiliki\s+peran\s+penting\s+bagi\s+kehidupan|berfungsi\s+menahan\s+dan\s+mengendalikan\s+luapan)\b',
    # Pemetaan / rencana energi bersih & PLTS bendungan lintas kementerian yang bersifat informatif/positif
    r'\b(?:memetakan\s+pemanfaatan\s+bendungan\s+sebagai\s+lokasi\s+pembangkit\s+listrik|pembangkit\s+listrik\s+tenaga\s+surya\s*\(plts\)\s*terapung)\b',
]

# ============================================================
# 3b. POLA NETRAL DOMESTIK / MEME NON-KEBIJAKAN
# ============================================================
# Konten yang terdeteksi positif/negatif tapi sebenarnya bukan evaluasi
# terhadap kebijakan publik — dialihkan ke Netral.

# Hashtag domestik / parenting (ibu masak sendiri, bukan MBG sekolah)
NEUTRAL_DOMESTIC_HASHTAGS = ['#parenting']

# Frasa spesifik yang jelas bukan evaluasi kebijakan
NEUTRAL_MEME_PHRASES = [
    'mainan bisa nyanyi',
]

def _is_domestic_or_meme(text_lower):
    """Cek apakah konten adalah konten domestik/meme non-kebijakan."""
    for tag in NEUTRAL_DOMESTIC_HASHTAGS:
        if tag in text_lower:
            return True, f'domestik({tag})'
    for phrase in NEUTRAL_MEME_PHRASES:
        if phrase in text_lower:
            return True, f'meme_nonkebijakan({phrase})'
    return False, None

# Frasa masalah infrastruktur yang TIDAK bersifat negatif apabila dibingkai sebagai aksi penanganan/perbaikan aktif
_INFRA_DAMAGE_PHRASES = (
    'jalan rusak', 'jalan berlubang', 'jalan bolong', 'jalan ambles', 'jalan amblas',
    'jembatan putus', 'tanggul jebol', 'bendungan bocor', 'pipa bocor', 'rusak parah'
)
_INFRA_REPAIR_FRAME_RE = re.compile(
    r'\b(?:memperbaiki|perbaiki|perbaikan|menangani|tangani|penanganan|mengatasi|atasi|mempercepat|percepatan|'
    r'rampung|rampungkan|tuntas|menuntaskan|selesai|diselesaikan|siap\s+dilintasi|kembali\s+(?:bisa\s+dilalui|terbuka|terhubung)|'
    r'aspal\s+mulus|segera\s+diaspal|akan\s+diaspal|akan\s+segera\s+diaspal|mengeliminasi|menjawab\s+keluhan|berkoordinasi|koordinasi|menginstruksikan|instruksikan|'
    r'bergerak\s+cepat|gerak\s+cepat|mengerahkan|turunkan|bantuan|penyaluran|menyalurkan|salurkan|'
    r'normalisasi|pengerukan|pemulihan|pulihkan|mitigasi|mengantisipasi|antisipasi|mencegah|pencegahan|'
    r'evakuasi|lapor|cara\s+melapor|diprioritaskan|jembatan\s+bailey|mengurai\s+kepadatan|pelebaran\s+jalan)\b',
    re.I
)
_INFRA_NEGLECT_BLOCKER_RE = re.compile(
    r'\b(?:tak\s+kunjung|belum\s+kunjung|tidak\s+kunjung|belum\s+diperbaiki|diabaikan|tutup\s+mata|'
    r'aksi\s+protes|unjuk\s+rasa|digeruduk|mangkrak|korban\s+jiwa|menelan\s+korban|tewas|ga\s+becus|gak\s+becus|tidak\s+becus)\b',
    re.I
)
_CONDOLENCE_RE = re.compile(
    r'\b(?:tutup\s+usia|meninggal\s+dunia|berpulang|turut\s+berduka\s+cita|duka\s+cita\s+mendalam|belasungkawa|husnul\s+khotimah|almarhum)\b',
    re.I
)
_CONDOLENCE_BLAME_RE = re.compile(
    r'\b(?:keracunan|korupsi|kelalaian|proyek\s+maut|ambruk|roboh|protes|salah|bodoh|goblok)\b',
    re.I
)

_SAFE_INTEGRITY_PAT = re.compile(
    r'(?:'
    r'komisi\s+pemberantasan\s+korupsi|pencegahan\s+korupsi|anti[\s-]?korupsi|hari\s+antikorupsi|'
    r'wilayah\s+bebas\s+(?:dari\s+)?korupsi|bebas\s+pungli|stop\s+pungli|saber\s+pungli|berantas\s+korupsi|tolak\s+korupsi|'
    r'(?:tolak|anti|cegah|mencegah|pencegahan|antisuap|benturan\s+kepentingan|pakta\s+integritas|zona\s+integritas|'
    r'whistleblowing|kode\s+perilaku|pelatihan\s+(?:calon\s+)?penyuluh|bantah|membantah|tutup\s+celah|'
    r'hindari|mengantisipasi|meminimalisir|budaya\s+antisuap)\b[^.!?\n]{0,65}\b'
    r'(?:korupsi|koruptor|korup|penyelewengan|penyalahgunaan|penyimpangan|manipulasi|pungli|suap|gratifikasi|pemborosan)|'
    r'\bperaturan\b[^.!?\n]{0,40}\b(?:gratifikasi|korupsi|kpk)\b|'
    r'\bkorupsi\b[^.!?\n]{0,35}\b(?:yang\s+harus\s+kita\s+pahami|bukan\s+hanya\s+soal\s+uang)\b|'
    r'\b(?:pendataan|pengamanan)[^.!?\n]{0,55}\bpencurian\s+air\b|'
    r'\b(?:apabila\s+menemukan)[^.!?\n]{0,40}\b(?:penipuan|penyalahgunaan|penyimpangan|pungli)\b[^.!?\n]{0,80}\bsegera\s+laporkan\b|'
    r'\b(?:penipuan|penyalahgunaan)\b[^.!?\n]{0,70}\bsegera\s+laporkan\b|'
    r'\bberita\s+pejabat\s+korupsi\.\s*tapi\b|'
    r'(?:tolak\s+gratifikasi|no\s+bribery|tanpa\s+pungutan)'
    r')'
)
_SAFE_CODE_OF_CONDUCT_HDR_RE = re.compile(r'\b(?:kode\s+perilaku\s+pegawai|perilaku\s+yang\s+harus\s+dihindari)\b')
_SAFE_CODE_OF_CONDUCT_WORDS_RE = re.compile(r'\b(?:menyalahgunakan|penyalahgunaan|korupsi|suap|gratifikasi)\b')
_SAFE_SCAM_HDR_RE = re.compile(r'(?:waspada|hati[\s-]?hati|awas)\s+penipuan\b|\b(?:tanpa\s+pungutan\s+biaya|tidak\s+dipungut\s+biaya)\b')
_SAFE_PENIPUAN_RE = re.compile(r'\bpenipuan\b')
_SAFE_WASTE_PAT = re.compile(
    r'\b(?:pengolahan|bank|tpa|buang|bersih|pembersih|pilah|tumpukan|mengelola|mengurangi|angkutan|pembakar)\s+sampah\b|'
    r'\bsampah\s+(?:plastik|sembarangan|rumah\s+tangga|perairan)\b'
)
_SAFE_LEGAL_FACT_PAT = re.compile(
    r'\b(?:memutus|diputus|putusan|pengadilan|hakim|mahkamah\s+agung)\b[^.!?\n]{0,40}\b(?:gak\s+ada\s+bukti|tidak\s+ada\s+bukti)\b'
)
_SAFE_NON_HOSTILE_WORDS_PAT = re.compile(
    r'(?:'
    r'(?:tidak|tak|tiada|bukan|jangan|agar\s+tidak|supaya\s+tidak)\s+(?:akan\s+|menjadi\s+|hal\s+yang\s+|terbuang\s+|mengalir\s+)?\bsia[-\s]?sia\b|'
    r'(?:biar|agar|supaya)\s+(?:tidak|tak|gak|nggak)\s+salah\s+sasaran\b|'
    r'\bkorban\s+(?:bencana|banjir|longsor|gempa|kebakaran|erupsi|musibah)\b|'
    r'\bdemonstrasi\s+(?:teknologi|alat|mesin)\b|#demo\b'
    r')'
)
_INFRA_DAMAGE_UNION_RE = re.compile(
    r'(?<!\w)(?:' + '|'.join(re.escape(p) for p in sorted(_INFRA_DAMAGE_PHRASES, key=len, reverse=True)) + r')(?!\w)'
)
_INNALILLAHI_RE = re.compile(r'\binnalillahi\b')

_MASK_INTEGRITY_TRIGGERS = (
    'korup', 'suap', 'gratif', 'pungli', 'seleweng', 'salahguna', 'salah guna',
    'manipul', 'simpang', 'boros', 'kode perilaku', 'pencurian air'
)
_MASK_NONHOSTILE_TRIGGERS = ('sia-sia', 'sia sia', 'korban', 'demo', 'salah sasaran')
_MASK_INFRA_TRIGGERS = ('rusak', 'berlubang', 'bolong', 'ambles', 'amblas', 'putus', 'jebol', 'bocor')


def _mask_safe_contexts(text_lower):
    """Menetralkan konteks aman (edukasi antikorupsi, disclaimer rekrutmen, perbaikan jalan aktif, duka cita, faktual hukum)."""
    t = text_lower
    if any(k in t for k in _MASK_INTEGRITY_TRIGGERS):
        t = _SAFE_INTEGRITY_PAT.sub(' __konteks_integritas__ ', t)
        if _SAFE_CODE_OF_CONDUCT_HDR_RE.search(t):
            t = _SAFE_CODE_OF_CONDUCT_WORDS_RE.sub(' __kode_etik_asn__ ', t)
    if 'penipuan' in t and _SAFE_SCAM_HDR_RE.search(t):
        t = _SAFE_PENIPUAN_RE.sub(' __disclaimer_rekrutmen__ ', t)
    if 'sampah' in t:
        t = _SAFE_WASTE_PAT.sub(' __konteks_persampahan__ ', t)
    if 'bukti' in t:
        t = _SAFE_LEGAL_FACT_PAT.sub(' __fakta_hukum__ ', t)
    if any(k in t for k in _MASK_NONHOSTILE_TRIGGERS):
        t = _SAFE_NON_HOSTILE_WORDS_PAT.sub(' __konteks_aman__ ', t)
    if 'innalillahi' in t and _CONDOLENCE_RE.search(t) and not _CONDOLENCE_BLAME_RE.search(t):
        t = _INNALILLAHI_RE.sub(' __belasungkawa__ ', t)
    if any(k in t for k in _MASK_INFRA_TRIGGERS):
        if _INFRA_REPAIR_FRAME_RE.search(t) and not _INFRA_NEGLECT_BLOCKER_RE.search(t):
            t = _INFRA_DAMAGE_UNION_RE.sub(' __penanganan_infra__ ', t)
    return t


def _count_caps_words(text):
    """Hitung jumlah kata yang sepenuhnya HURUF BESAR (min 3 karakter)."""
    words = text.split()
    return sum(1 for w in words if len(w) >= 3 and w.isupper() and w.isalpha())


_CAPS_HEADLINE_KW_RE = re.compile(r'\b(?:breaking\s+news|siaran\s+pers|kemen[\s-]*pu|kementerian|ditjen|bbws|bpjn|bbpjn|bws|apbn|ikn|dpr|ri)\b')
_CAPS_PUNCT_RE = re.compile(r'[!?]{2,}')
_CAPS_HEADLINE_POLAR_RE = re.compile(r'\b(?:rusak|ancur|hancur|parah|bohong|suka|keren|mantap)\b')
_CAPS_SARC_1_RE = re.compile(r'\b(?:katanya|giliran|padahal|malah|baru\s+viral|nunggu\s+viral|gitu\s+aja|gitu\s+doang)\b[^.!?\n]{0,70}\b(?:tapi|kok|lama|lelet|lambat|rusak|ancur|hancur|parah|bobrok|bohong|mangkrak)\b')
_CAPS_SARC_2_RE = re.compile(r'\b(?:hebat|keren|mantap|top|bagus|juara)\s+(?:banget+|bgt+|sekali|bet|bener|betul)\b[^.!?\n]{0,70}\b(?:rusak|ancur|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|bobrok|kacau|jelek)\b')
_CAPS_SARC_3_RE = re.compile(r'\b(?:rusak\s+parah|hancur\s+lebur|jalan\s+rusak|jalan\s+bolong|jembatan\s+ambruk|tanggul\s+jebol|proyek\s+mangkrak|ga\s+becus|gak\s+becus|korupsi|maling|pemborosan)\b')
_CAPS_SARC_4_RE = re.compile(r'\b(?:bohong|pencitraan|ngibul|tai|ancur|bobrok)\b')
_CAPS_PRAISE_RE = re.compile(r'\b(?:suka\s+banget|suka\s+bgt|cinta\s+banget|keren\s+banget|keren\s+bgt|mantap\s+banget|mantap\s+bgt|enak\s+banget|enak\s+bgt|asli\s+cozy|cozy\s+banget|nyaman\s+banget|adem\s+banget|terima\s+kasih\s+banyak|makasih\s+banyak|alhamdulillah|juara\s+banget|top\s+banget|free\s+coffee|gratis\s+kopi|sukses\s+selalu|maju\s+terus|bangga\s+banget|selamat\s+&\s+sukses|pengajian\s+bulanan)\b')
_CAPS_COMPLAINT_RE = re.compile(r'\b(?:tapi|namun|sayang|sayangnya|kecewa|sayang\s+sekali|kotor|panas|bau|galak|payah|bobrok|lelet|lambat|bocor)\b')
_CAPS_ANGER_CUE_RE = re.compile(r'\b(?:kecewa|marah|parah|bobrok|bohong|korup|pecat|hapus|mundur|tolak|ancam|ancur|gila|gagal|usut|penjara|maling|curang)\b')
_WORD_TOKENS_RE = re.compile(r'\b\w+\b')


def classify_caps_intent(raw_text, text_lower, masked=None):
    """
    Mengklasifikasikan intensi penggunaan huruf besar (ALL CAPS):
    Membedakan secara akurat antara:
    1. 'SARCASM_ANGER'       : Kemarahan, sindiran tajam, atau cemoohan sarkas.
    2. 'ENTHUSIASTIC_PRAISE' : Pujian tulus, antusiasme tinggi, atau dukungan nyata.
    3. 'HEADLINE_NEUTRAL'    : Judul rilis resmi, akronim birokrasi, atau format berita.
    4. 'NORMAL'              : Teks biasa tanpa dominasi huruf kapital.
    """
    caps_count = _count_caps_words(raw_text)
    if caps_count < 3:
        return 'NORMAL', 'huruf_biasa'

    if masked is None:
        masked = _mask_safe_contexts(text_lower)

    # A. Cek Judul Berita / Rilis Resmi Kedinasan (Informatif Netral)
    if (
        _CAPS_HEADLINE_KW_RE.search(text_lower)
        and len(raw_text.split()) < 15
        and not _CAPS_PUNCT_RE.search(raw_text)
        and not _CAPS_HEADLINE_POLAR_RE.search(masked)
    ):
        return 'HEADLINE_NEUTRAL', 'caps_headline_resmi'

    # B. Cek Sinyal Sarkasme & Kemarahan dalam Huruf Besar (dievaluasi pada teks aman termasking)
    if (
        _CAPS_SARC_1_RE.search(masked)
        or _CAPS_SARC_2_RE.search(masked)
        or _CAPS_SARC_3_RE.search(masked)
        or _CAPS_SARC_4_RE.search(masked)
    ):
        return 'SARCASM_ANGER', 'caps_sarkas_marah'

    # C. Cek Sinyal Pujian Antusias / Dukungan Nyata dalam Huruf Besar
    has_praise_keywords = bool(_CAPS_PRAISE_RE.search(text_lower))
    if has_praise_keywords and not _CAPS_COMPLAINT_RE.search(masked):
        return 'ENTHUSIASTIC_PRAISE', 'caps_pujian_antusias'

    # D. Tanda baca repetitif (!!, ???) HANYA menjadi kemarahan jika disertai kata keluhan/protes/umpatan
    if _CAPS_PUNCT_RE.search(raw_text) and not has_praise_keywords:
        if _has_profanity(masked) or _CAPS_ANGER_CUE_RE.search(masked):
            return 'SARCASM_ANGER', 'caps_kemarahan'

    return 'NORMAL', 'huruf_biasa'


def _has_profanity(text_lower):
    return bool(set(_WORD_TOKENS_RE.findall(text_lower)) & PROFANITY)


# Kompilasi tunggal union regex untuk performa tinggi (~100x lebih cepat dari loop regex individual)
_STRONG_NEG_UNION_RE = re.compile(
    r'(?<!\w)(?:' + '|'.join(re.escape(p) for p in sorted(STRONG_NEGATIVE_PHRASES, key=len, reverse=True)) + r')(?!\w)'
)
_STRONG_POS_UNION_RE = re.compile(
    r'(?<!\w)(?:' + '|'.join(re.escape(p) for p in sorted(STRONG_POSITIVE_PHRASES, key=len, reverse=True)) + r')(?!\w)'
)
_COMPILED_SARCASM = [(pat, re.compile(pat)) for pat in SARCASM_PATTERNS]
_COMPILED_NEUTRAL_PREFIXES = [re.compile(pat) for pat in NEUTRAL_INFORMATIONAL_PREFIXES]
_COMPILED_PRO_DEFENSE = [re.compile(pat) for pat in PRO_POLICY_DEFENSE_PATTERNS]

_DEMAND_RE = re.compile(
    r'\b(?:tolong|mohon|harap|diharapkan|dimohon|perlu|harus|minta|menuntut|mendesak)\s+(?:pengawasan|diperketat|perketat|diawasi|mempercepat|percepat|diselesaikan|diperbaiki|dibangun|menuntaskan|turunkan|tuntaskan|selesaikan|dibenahi|benahi|evaluasi|agar\s+perbaikan)\b|'
    r'\bpengawasan\s+[^.!?\n]{0,50}(?:diperketat|diperkuat|ditingkatkan)\b|'
    r'\b(?:agar|supaya|biar|jangan\s+sampai)\s+(?:tidak|tak|gak|nggak|jangan)\s+(?:ada|terjadi|lagi|kesulitan|kekurangan|krisis|kebanjiran|menderita|terisolir|rugi|mangkrak|rusak|korban|terbengkalai)\b|'
    r'\bagar\s+(?:warga|rakyat|petani|masyarakat|anak)[^.!?\n]{0,60}(?:tidak\s+lagi\s+(?:kesulitan|kekurangan|krisis|kebanjiran|menderita|terisolir|rugi)|bisa\s+segera)\b|'
    r'\b(?:kapan|kok\s+belum|kapan\s+selesai|jangan\s+ditunda|jangan\s+lambat)\b|'
    r'\b(?:aspirasi\s+masyarakat|sudah\s+berkoordinasi\s+dengan\s+kementerian\s+pu\s+agar)\b'
)
_DISASTER_CASUALTY_RE = re.compile(r'\b(?:keracunan|hilang\s+ingatan|tuntutan|korban\s+jiwa|menelan\s+korban|dirawat|hospitalized|poisoned|hentikan\s+mbg)\b')
_CROSS_MINISTRY_RE = re.compile(r'\b(?:esdm|bahlil|lahadalia|pertambangan|izin\s+tambang|nikel|batu\s*bara|hilirisasi\s+tambang|subsidi\s+bbm)\b')
_CROSS_MINISTRY_CRIT_RE = re.compile(
    r'(?:bahlil|esdm|tambang|energi|nikel)[^.!?\n]{0,60}(?:kritik|kontra|masalah|kasus|sorotan|dinilai|rendah|skandal|menolak)|'
    r'(?:kritik|kontra|masalah|kasus|sorotan|dinilai|rendah|skandal|menolak)[^.!?\n]{0,60}(?:bahlil|esdm|tambang|energi|nikel)'
)
_CROSS_MINISTRY_PU_CRIT_RE = re.compile(
    r'(?:dody|hanggodo|kemen[\s-]*pu|kementerian\s+pekerjaan\s+umum)[^.!?\n]{0,60}(?:gagal|rusak|ambrol|korupsi|hancur|mangkrak|lambat|buruk|kecewa)'
)
_INFRA_RESOLUTION_RE = re.compile(
    r'\b(?:kabar\s+baik|angin\s+segar)\b[^.!?\n]{0,80}\b(?:kemen[\s-]*pu|pekerjaan\s+umum|jalan|jembatan|bendungan|irigasi|tol|revitalisasi|renovasi)\b|'
    r'\b(?:hadir|tampil)\s+dengan\s+wajah\s+baru\b|'
    r'\bkini\s+(?:sudah\s+)?(?:lebih\s+(?:lapang|lebar|aman|nyaman|mulus|lancar)|hadir\s+dengan|siap\s+dilintasi|resmi\s+beroperasi)\b|'
    r'\bsetelah\s+dilakukan\s+(?:penggantian|pelebaran|perbaikan|revitalisasi|rehabilitasi|penanganan|normalisasi)\b[^.!?\n]{0,80}\b(?:kini|lebih|aman|nyaman|lancar|mulus)\b|'
    r'\b(?:kementerian\s+pu|kemen[\s-]*pu|bbws|bws|bbpjn|bpjn)\b[^.!?\n]{0,60}\bbergerak\s+(?:cepat|bersama)\s+melakukan\s+percepatan\b|'
    r'\bsinergi\s+kuat\b[^.!?\n]{0,60}\b(?:kemen[\s-]*pu|pekerjaan\s+umum|bbws|bpjn|waduk|bendungan|irigasi)\b|'
    r'\b(?:alhamdulillah|terima\s*kasih|terimaksih)\b.{0,140}\b(?:di\s*aspal\s+mulus|jalan\s+mulus|kehebatan)\b|'
    r'\bperluas\s+jalan,\s*lancarkan\s+mobilitas\b|'
    r'\bfungsional\s+\d+\s+ruas\s+jalan\s+tol\s+tanpa\s+tarif\b'
)
_STALLED_BLOCKER_RE = re.compile(
    r'\b(?:namun|tapi|sayangnya|padahal|faktanya|nyatanya)\s+[^.!?\n]{0,60}\b(?:masih\s+tertahan|belum\s+jelas|mangkrak|batal|rusak\s+lagi|belum\s+terealisasi|kecewa|dikritik|menuai\s+kritik)\b|'
    r'\b(?:masih\s+tertahan|belum\s+kelihatan|menuai\s+kritik|dinilai\s+belum\s+memuaskan)\b'
)
_FACILITY_PRAISE_RE = re.compile(
    r'\b(?:perpus|perpustakaan|ruang\s+baca|wfc|kantor\s+pu)\b[^.!?\n]{0,70}\b(?:suka\s+banget|suka\s+bgt|nyaman|cozy|adem|dingin|kenceng|bersih|luas|bagus|keren|lengkap|gratis|free|enak|betah|rekomendasi|surganya)\b|'
    r'\b(?:suka\s+banget|suka\s+bgt|nyaman|cozy|adem|dingin|kenceng|bersih|luas|bagus|keren|lengkap|gratis|free|enak|betah|rekomendasi|surganya)\b[^.!?\n]{0,70}\b(?:perpus|perpustakaan|ruang\s+baca|wfc|kantor\s+pu)\b'
)
_FACILITY_COMPLAINT_RE = re.compile(
    r'\b(?:ac\s+mati|listrik\s+mati|wifi\s+mati|panas|gerah|bau\s+apek|apek|kotor|jorok|bising|antri|antre|bocor|galak|judes|tidak\s+ramah|pelayanan\s+buruk|mengecewakan|kecewa|sayang\s+sekali|bobrok)\b'
)
_CRY_CONTEXT_RE = re.compile(r'\b(?:sedih|duka|kecewa|miris|kasihan|korban|rusak|hancur|parah|menderita)\b')
_HARD_NEG_EMOJIS = NEGATIVE_EMOJIS - {'😭'}
_EXTREME_NEG_EMOJIS = {'😡', '🤬', '🤮', '🖕'}
_SARCASM_FAST_ANCHORS = (
    'apa', 'kok', 'katanya', 'apresiasi', 'terima kasih', 'makasih', 'salut', 'hebat', 'keren', 'mantap',
    'top', 'luar biasa', 'juara', 'bagus', 'terpuji', 'selesai', 'diresmikan', 'peresmian', 'beres',
    'tuntas', 'respon', 'masa', 'giliran', 'berguna', 'bermanfaat', 'enak', 'lezat', 'nikmat',
    'woi', 'woy', 'anjir', 'njir', 'gila', 'saking', 'tepuk', 'mana gas', 'indah', 'sppg', 'tutup',
    'masih', 'pengen', 'molto', 'private jet', 'weekend', 'penjajahan', '11', 'bukannya', 'tinggal'
)


def _has_strong_negative(text_lower, masked=None):
    clean_text = masked if masked is not None else _mask_safe_contexts(text_lower)
    m = _STRONG_NEG_UNION_RE.search(clean_text)
    if m:
        return True, m.group(0)
    return False, None


def _has_sarcasm(text_lower, masked=None):
    clean_text = masked if masked is not None else _mask_safe_contexts(text_lower)
    if not any(k in clean_text for k in _SARCASM_FAST_ANCHORS):
        return False, None
    for pat_str, pat_re in _COMPILED_SARCASM:
        if pat_re.search(clean_text):
            return True, pat_str
    return False, None


def _has_strong_positive(text_lower):
    m = _STRONG_POS_UNION_RE.search(text_lower)
    if m:
        return True, m.group(0)
    return False, None


def _count_emojis(text, emoji_set):
    return sum(1 for ch in text if ch in emoji_set)


# Pola bukti negatif nyata (skandal, penegakan hukum korupsi, keluhan tak tertangani, kecaman publik)
_REAL_NEGATIVE_SCANDAL_RE = re.compile(
    r'\b(?:ott|terjaring|tersangka|ditahan|penahanan|digeledah|penggeledahan|menggeledah|'
    r'suap|menyuap|disuap|aliran\s+dana|commitment\s+fee|proyek\s+fiktif|kerugian\s+negara|'
    r'hukuman\s+disiplin|pemberhentian\s+(?:dengan\s+hormat\s+)?tidak\s+atas|dipecat|pecat|dicopot|'
    r'kejati|kejagung|tipikor|mafia\s+(?:anggaran|infrastruktur)|audit\s+itjen|'
    r'kejanggalan\s+kekayaan|kekayaan\s+tak\s+wajar|bibit\s+ganja|tanam\s+ganja|judi\s+online|judol|absen\s+abal|'
    r'terdakwa|vonis|penjara|terseret\s+kasus|skandal|koruptor|penggelapan|pemerasan|kongkalikong)\b'
)
_REAL_KPK_PROBE_RE = re.compile(
    r'\bkpk\b[^.!?\n]{0,80}\b(?:usut|selidiki|telusuri|dalami|bidik|periksa|panggil|tahan|geledah|ott|tersangka|curiga|soroti|suap|gratifikasi|korupsi)\b|'
    r'\bdugaan\b[^.!?\n]{0,45}\b(?:korupsi|suap|gratifikasi|penyalahgunaan|penyelewengan|nepotisme|intimidasi|proyek\s+fiktif|perjalanan\s+dinas|mark[\s-]?up|pungli|curang)\b'
)
_REAL_CRITICISM_BACKLASH_RE = re.compile(
    r'\b(?:marah[\s-]?marah|marah\s+besar|murka|naik\s+pitam|ngamuk|memaki|makian|dimaki|dibentak|membentak|bego\s+lu|kata\s+bego|'
    r'sebut\s+anak\s+buahnya\s+bego|kena\s+mental|nonjok|menolak\s+jabat\s+tangan|mengabaikan\s+uluran|tidak\s+menyalami|'
    r'arogan|arogansi|slengean|songong|amatiran|toxic\s+leadership|plenger|stres\s+hingga\s+sakit\s+perut|gabut|'
    r'elektabilitas\s+terendah|kinerja\s+terbawah|penilaian\s+buruk|reshuffle|lengserkan|lengser|diminta\s+mundur|'
    r'nepotisme|tunjuk\s+keponakan|angkat\s+keponakan|jet\s+pribadi|private\s+jet|nonton\s+piala\s+dunia|kunker\s+ke\s+amerika|'
    r'somasi|intimidasi|menteror|surat\s+bocor|bocoran\s+surat|kritik\s+keras|menuai\s+kritik|ramainya\s+kritik|kritik\s+terkait\s+gaya|'
    r'menuai\s+kecaman|dikecam|mengecam|hujatan|dihujat|disentil|sentil|menuding|tuduhan|dituding|bobrok|payah|amburadul|kacau|lebih\s+parah|dzolim|'
    r'problematik|mengeluh|tak\s+kunjung|belum\s+kunjung|belum\s+diperbaiki|tidak\s+kunjung|diabaikan|'
    r'aksi\s+protes|unjuk\s+rasa|digeruduk|korban\s+jiwa|menelan\s+korban|tewas|dirumahkan|pemutusan\s+hubungan|'
    r'tidak\s+efisien|tidak\s+lolos\s+verifikasi|borok\s+internal|standar\s+ganda|sekarang\s+salah|memalukan|kekecewaan|kecewa\s+berat|'
    r'kelalaian|ketiadaan\s+pemeliharaan|bikin\s+publik\s+geleng\s+kepala|arogansi\s+kekuasaan|'
    r'warisan\s+panjang\s+persoalan|catatan\s+auditor|dibakar\s+massa|kerusakan\s+akibat\s+demo|menuai\s+sorotan\s+tajam)\b'
)

# Sinyal penyelamat false-negative dari model IndoBERT yang terbias leksikon berita bencana/proyek
_FN_POSITIVE_RESCUE_RE = re.compile(
    r'\b(?:pelayanan\s+prima|salut|apresiasi|terima\s+kasih|terimakasih|alhamdulillah|kehebatan|'
    r'kinerja\s+luar\s+biasa|respons\s+luar\s+biasa|respons\s+cepat|respon\s+cepat|gerak\s+cepat|gercep|'
    r'langkah\s+cerdas|langkah\s+nyata|langkah\s+konkret|bukti\s+nyata|kerja\s+nyata|kerja\s+keras|'
    r'solusi\s+jangka\s+panjang|kategori\s+baik|aspal\s+mulus|jalan\s+mulus|wajah\s+baru|lebih\s+lapang|'
    r'lebih\s+lancar|lancar\s+dan\s+nyaman|aman\s+dan\s+nyaman|ramah\s+bagi\s+pengguna|ramah\s+pemotor|ramah\s+pengendara|'
    r'tanpa\s+tarif|diskon\s+tarif\s+tol|swasembada\s+pangan|ketahanan\s+pangan|mendukung\s+produktivitas|'
    r'hampir\s+tuntas|sisa\s+1-2\s+persen|resmi\s+dibuka|siap\s+dilintasi|selamat\s+hari|purna\s+bakti|hari\s+bakti\s+pu|'
    r'suasana\s+kebahagiaan|bangunan\s+gedung\s+hijau|keamanan\s+dan\s+kenyamanan|benar-benar\s+mengabdi|hidup\s+bersih)\b'
)
_FN_PU_INSTITUTIONAL_RE = re.compile(
    r'\b(?:kementerian\s+pu|kementerian\s+pekerjaan\s+umum|kemen[\s-]*pu|menteri\s+pu|dody\s+hanggodo|'
    r'bbws|bws|bbpjn|bpjn|bppw|bp2jk|bpsdm|ditjen|bina\s+marga|cipta\s+karya|sumber\s+daya\s+air|'
    r'ppls|setkab|pemerintah|presiden|dpr\s+ri|komisi\s+v|balai|bbwsbs|sobatbjkw)\b'
)
_FN_NEUTRAL_ACTION_RE = re.compile(
    r'\b(?:penanganan|menangani|tangani|mengatasi|atasi|perbaikan|memperbaiki|perbaiki|pemulihan|pulihkan|'
    r'rehabilitasi|rekonstruksi|revitalisasi|pelebaran|pengaspalan|normalisasi|pengerukan|evakuasi|'
    r'pembersihan|penyaluran|menyalurkan|salurkan|mendistribusikan|distribusi\s+air|sumur\s+bor|'
    r'sabo\s*dam|sabodam|pengalihan\s+arus|dialihkan\s+melalui|mitigasi|mengantisipasi|antisipasi|'
    r'mencegah|pencegahan|mengamankan|melindungi|meninjau|kunjungan\s+kerja|rapat\s+terbatas|'
    r'berkoordinasi|koordinasi|menginstruksikan|instruksikan|melantik|pelantikan|rotasi\s+jabatan|'
    r'open\s+recruitment|rekrutmen|uji\s+sertifikasi|peraturan|edukasi|literasi|pu\s+mengajar|'
    r'pengajian|duka\s+cita|belasungkawa|tutup\s+usia|berpulang|biografi|contoh\s+soal|sumber:\s*ppls|'
    r'menjawab\s+keluhan|cegah\s+penyelewengan|pakta\s+integritas|zona\s+integritas|tolak\s+gratifikasi|'
    r'antisuap|mendorong\s+upaya|menyiapkan|siapkan|mengoperasikan|fungsional|memastikan\s+kesiapan|'
    r'pembukaan\s+pintu\s+air|meresmikan|peresmian|menekan\s+angka|mengendalikan\s+aliran|mengoptimalkan|'
    r'menghadiri|penebaran|pengelolaan\s+air|kolam\s+retensi|mendukung\s+pembangunan|melanjutkan\s+pembangunan|'
    r'pengembangan\s+sejumlah\s+fasilitas|memastikan\s+kualitas|lapisan\s+pondasi|penataan[^.!?\n]{0,25}kawasan|'
    r'absensi\s+kerja|seporsi\s+integritas|kode\s+perilaku|salah\s+nangkep|mandor\s+doang)\b'
)


def _has_real_negative_evidence(text_lower, raw_text='', masked=None, already_checked=False):
    """Memastikan pos yang memuat bukti skandal, kritik keras, umpatan, atau keluhan nyata tetap Negatif."""
    if masked is None:
        masked = _mask_safe_contexts(text_lower)
    if not already_checked:
        if _has_profanity(masked) or _has_sarcasm(text_lower, masked=masked)[0] or _has_strong_negative(text_lower, masked=masked)[0]:
            return True
    if _REAL_NEGATIVE_SCANDAL_RE.search(masked) or _REAL_KPK_PROBE_RE.search(masked) or _REAL_CRITICISM_BACKLASH_RE.search(masked):
        return True
    if raw_text and _count_emojis(raw_text, _EXTREME_NEG_EMOJIS) >= 1:
        return True
    return False


def _recover_false_negative_from_indobert(raw_text, text_lower, masked=None, already_checked=False):
    """
    Memulihkan prediksi Negatif palsu dari IndoBERT pada berita resmi/solusi/penanganan
    bencana/infrastruktur/pujian yang tidak memiliki bukti negatif nyata.
    """
    if _has_real_negative_evidence(text_lower, raw_text, masked=masked, already_checked=already_checked):
        return None
    if _CONDOLENCE_RE.search(text_lower) and not _CONDOLENCE_BLAME_RE.search(text_lower):
        return 'Netral', 1, 0.0, 'pulih_belasungkawa_netral'
    if _FN_POSITIVE_RESCUE_RE.search(text_lower):
        return 'Positif', 2, 0.78, 'pulih_apresiasi_dan_capaian_positif'
    if _FN_NEUTRAL_ACTION_RE.search(text_lower) and (
        _FN_PU_INSTITUTIONAL_RE.search(text_lower) or len(text_lower.split()) >= 8
    ):
        return 'Netral', 1, 0.0, 'pulih_aksi_penanganan_atau_info_netral'
    return None


def correct_sentiment(text, current_sentiment, current_score=0.0):
    """
    Mengoreksi label sentimen berdasarkan analisis konteks mendalam.
    
    Args:
        text: teks asli (raw_content atau cleaned_content)
        current_sentiment: label sentimen saat ini ('Positif', 'Netral', 'Negatif')
        current_score: skor sentimen saat ini (-1 sampai 1)
    
    Returns:
        (corrected_sentiment, corrected_label, corrected_score, reason)
    """
    if not text or not isinstance(text, str) or len(text.strip()) < 3:
        return current_sentiment, _sent_to_label(current_sentiment), current_score, ''
    
    text_lower = text.lower().strip()
    if '²' in text_lower or '2' in text_lower:
        text_lower = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', text_lower)
    raw_text = text.strip()
    masked_lower = _mask_safe_contexts(text_lower)
    has_prof = _has_profanity(masked_lower)
    
    # 0. CEK BERITA/INFO FAKTUAL TANPA OPINI
    is_pure_info = any(pat.search(text_lower) for pat in _COMPILED_NEUTRAL_PREFIXES)
    has_disaster_casualty = bool(_DISASTER_CASUALTY_RE.search(masked_lower))
    if is_pure_info and not has_disaster_casualty and not has_prof:
        return 'Netral', 1, 0.0, 'info_faktual_netral'

    # 0a. CEK PENGUMUMAN DUKA CITA / BELASUNGKAWA RESMI
    if _CONDOLENCE_RE.search(text_lower) and not _CONDOLENCE_BLAME_RE.search(masked_lower) and not has_prof:
        return 'Netral', 1, 0.0, 'belasungkawa_resmi_netral'

    # 0b. CEK KONTEN DOMESTIK / MEME NON-KEBIJAKAN
    is_domestic, domestic_reason = _is_domestic_or_meme(text_lower)
    if is_domestic and not has_prof and not has_disaster_casualty:
        return 'Netral', 1, 0.0, domestic_reason

    # 0c. CEK ASPIRASI, PENCEGAHAN & TUNTUTAN KONSTRUKTIF WARGA
    has_neg, neg_p = _has_strong_negative(text_lower, masked=masked_lower)
    if _DEMAND_RE.search(text_lower) and not has_prof and not has_neg and not has_disaster_casualty:
        return 'Netral', 1, 0.0, 'aspirasi_dan_tuntutan_warga'

    # 0d. CEK ISU LINTAS KEMENTERIAN (ESDM / TAMBANG / BAHLIL / NON-PU FOCUS)
    if _CROSS_MINISTRY_RE.search(text_lower):
        if _CROSS_MINISTRY_CRIT_RE.search(text_lower) and not _CROSS_MINISTRY_PU_CRIT_RE.search(masked_lower):
            return 'Netral', 1, 0.0, 'netralisasi_kritik_lintas_kementerian_esdm'

    neg_signals = 0
    pos_signals = 0
    reasons = []

    # 1. CEK INTENSI PENGGUNAAN HURUF BESAR (ALL CAPS INTENT CLASSIFICATION)
    caps_intent, caps_reason = classify_caps_intent(raw_text, text_lower, masked=masked_lower)
    if caps_intent == 'SARCASM_ANGER':
        neg_signals += 3
        reasons.append(caps_reason)
    elif caps_intent == 'ENTHUSIASTIC_PRAISE':
        pos_signals += 3
        reasons.append(caps_reason)

    # 2. CEK CAPAIAN INFRASTRUKTUR RAMPUNG / BEFORE-AFTER PERBAIKAN / TANGGAP CEPAT PEMULIHAN
    has_sarc, sarc_p = _has_sarcasm(text_lower, masked=masked_lower)
    has_infra_resolution = bool(_INFRA_RESOLUTION_RE.search(text_lower))
    has_stalled_blocker = bool(_STALLED_BLOCKER_RE.search(masked_lower))
    if (
        has_infra_resolution
        and not has_stalled_blocker
        and not has_prof
        and not has_sarc
        and not _REAL_NEGATIVE_SCANDAL_RE.search(masked_lower)
    ):
        return 'Positif', 2, max(float(current_score or 0.0), 0.85), 'capaian_perbaikan_infrastruktur_positif'

    # 2b. CEK APRESIASI FASILITAS DALAM RUANG / PERPUSTAKAAN & RUANG PUBLIK
    if _FACILITY_PRAISE_RE.search(text_lower):
        if _FACILITY_COMPLAINT_RE.search(masked_lower) and not has_infra_resolution:
            neg_signals += 2
            reasons.append('komplain_fasilitas')
        else:
            pos_signals += 3
            reasons.append('fasilitas_perpus_positif')

    # 3. CEK PEMBELAAN KEBIJAKAN / KECAMAN KEPADA PENENTANG (PRO-POLICY DEFENSE)
    is_defense = any(pat.search(text_lower) for pat in _COMPILED_PRO_DEFENSE)
    if is_defense:
        pos_signals += 3
        reasons.append('pembelaan_kebijakan_dari_penentang')
        
    # Cek frasa positif kuat (cegah jebakan "sukses bikin publik geleng kepala/gaduh")
    has_pos, pos_p = _has_strong_positive(text_lower)
    if has_pos and pos_p == 'sukses' and re.search(r'\bsukses\s+(?:bikin|membuat)\s+(?:publik\s+)?(?:geleng|heboh|kecewa|geram|marah|malu|kacau|gaduh)', masked_lower):
        has_pos, pos_p = False, None
    if has_pos:
        pos_signals += 2
        reasons.append(f'positif_kuat({pos_p})')
    
    # 4. Umpatan (bobot 3 - mutlak negatif jika bukan pembelaan kebijakan)
    if has_prof and not is_defense:
        neg_signals += 3
        reasons.append('umpatan')
    
    # 5. Frasa negatif kuat
    if has_neg:
        neg_signals += 2
        reasons.append(f'negatif_kuat({neg_p})')
    
    # 6. Sarkasme (bobot 4 - otomatis batalkan seluruh sinyal positif semu)
    if has_sarc:
        neg_signals += 4
        pos_signals = 0
        reasons.append(f'sarkasme({sarc_p})')
        
    # 7. Emoji negatif (emoji keras vs tangis tunggal '😭' yang sering dipakai bercanda Gen-Z)
    hard_neg_emoji_cnt = _count_emojis(text, _HARD_NEG_EMOJIS)
    cry_emoji_cnt = _count_emojis(text, {'😭'})
    if hard_neg_emoji_cnt >= 1 or (cry_emoji_cnt >= 1 and (neg_signals > 0 or bool(_CRY_CONTEXT_RE.search(masked_lower)))):
        neg_signals += 1
        reasons.append('emoji_negatif')
        
    # --- DETEKSI POSITIF ---
    if _count_emojis(text, POSITIVE_EMOJIS) >= 1:
        pos_signals += 1
        reasons.append('emoji_positif')

    # --- KEPUTUSAN FINAL ---
    reason_str = ', '.join(reasons)
    
    if neg_signals > pos_signals and neg_signals >= 2:
        return 'Negatif', 0, -0.85, reason_str
    
    if neg_signals > 0 and pos_signals == 0 and current_sentiment == 'Netral':
        return 'Negatif', 0, -0.65, reason_str
        
    if pos_signals > neg_signals and pos_signals >= 2:
        return 'Positif', 2, 0.85, reason_str
        
    if pos_signals > 0 and neg_signals == 0 and current_sentiment == 'Netral':
        return 'Positif', 2, 0.65, reason_str

    # 9. PULIHKAN FALSE NEGATIVE BIAS DARI MODEL INDOBERT
    if current_sentiment == 'Negatif' and neg_signals == 0:
        rescued = _recover_false_negative_from_indobert(
            raw_text, text_lower, masked=masked_lower, already_checked=is_defense is False
        )
        if rescued is not None:
            return rescued
        
    if current_sentiment == 'Netral':
        return 'Netral', 1, 0.0, reason_str or 'netral_konsisten'
        
    return current_sentiment, _sent_to_label(current_sentiment), current_score, ''

def _sent_to_label(s):
    return {'Negatif': 0, 'Netral': 1, 'Positif': 2}.get(s, 1)


# ============================================================
# 4. EMOTION CLASSIFICATION (PLUTCHIK / EKMAN VALENCE-ALIGNED)
# ============================================================

DISGUST_TEXT_PATTERNS = [
    'ulat', 'cacing', 'basi', 'busuk', 'jorok', 'kotor', 'muntah', 'mual',
    'diare', 'jijik', 'menjijikkan', 'enek', 'eneg', 'sampah', 'bau bangkai', 'najis',
    'berbau asam', 'bau asam', 'asam busuk', 'tidak layak konsumsi', 'tidak layak makan'
]
DISGUST_EMOJIS = {'🤮', '🤢', '💩'}

FEAR_TEXT_PATTERNS = [
    'keracunan', 'racun', 'mematikan', 'bahaya', 'berbahaya', 'takut', 'khawatir',
    'cemas', 'ngeri', 'hospitalized', 'poisoned', 'darurat', 'waspada', 'seram',
    'panik', 'was-was', 'waswas', 'terancam', 'mengancam', 'tembus 18k', 'rupiah anjlok',
    'krisis', 'ambruk', 'ambrol', 'bencana', 'menakutkan', 'horor'
]
FEAR_EMOJIS = {'😨', '😰', '😱', '⚠️', '🚨'}

SADNESS_TEXT_PATTERNS = [
    'sedih', 'nangis', 'menangis', 'ga tega', 'gak tega', 'miris', 'kasihan',
    'tragis', 'innalillahi', 'we are finished', "we're finished", 'terbakar habis',
    'kecewa', 'duka', 'pilu', 'nelangsa', 'menderita', 'derita', 'menyesal', 'galau'
]
SADNESS_EMOJIS = {'😭', '😢', '💔', '🥺', '😔', '😞'}

ANGER_TEXT_PATTERNS = [
    'ajg', 'anjg', 'anjing', 'bangsat', 'bajingan', 'brengsek', 'tolol', 'bodoh',
    'goblok', 'idiot', 'bego', 'dungu', 'biadab', 'bedebah', 'sialan', 'kampret',
    'ngentot', 'entot', 'cuks', 'cuk', 'cok', 'maksa', 'memaksa', 'pemaksaan',
    'peler', 'jembut', 'lonte', 'ngewe', 'arogan', 'otoriter',
    'stop mbg', 'bubarin', 'bubarkan', 'hentikan program', 'turunkan harga',
    'hidup mahasiswa', 'demo', 'tuntutan', 'pemborosan', 'korupsi', 'koruptor',
    'pencurian', 'bancakan', 'maling', 'mana gas mana gas', 'self centered',
    'narcissistic', 'halu', 'ngayal', 'pura buta', 'pura tuli', 'marah', 'kesal',
    'geram', 'murka', 'benci', 'muak', 'ngamuk',
    'ngegas', 'vendor nakal', 'pemakan anggaran', 'jangan sok paling pintar', 'ini nyawa anak',
    'disalahgunakan', 'penyalahgunaan', 'menyalahgunakan', 'diselewengkan', 'penyelewengan', 'salah sasaran', 'kurang tepat', 'tidak tepat', 'salah alokasi',
    'buang anggaran', 'buang-buang anggaran', 'buang uang', 'buang duit', 'sia-sia', 'sia sia', 'bakar uang',
    'penjajahan', 'penjajah', 'masa penjajahan', 'zaman penjajahan', 'balik masa penjajahan', '11 12', 'malah bukak', 'malah buka',
    'ga becus', 'gak becus', 'tidak becus', 'tak becus', 'bgn ga becus', 'bgn gak becus', 'bgn tidak becus',
    'gada manfaat', 'gada manfaatnya', 'gaada manfaat', 'gaada manfaatnya', 'ga ada manfaat', 'gak ada manfaat', 'tidak ada manfaat',
    'gada guna', 'gada gunanya', 'gaada guna', 'tidak ada guna', 'gada faedah', 'gada efek', 'gada hasil',
    'apasi tujuan', 'apa sih tujuan', 'apa tujuannya', 'kok sampe detik ini', 'kok sampe sekarang', 'mana buktinya', 'mana hasilnya',
    'cara licik', 'licik', 'kelicikan', 'siasat licik', 'alat politik', 'politisasi', 'kepentingan penguasa',
    'sangat buruk', 'rusak parah', 'jalan rusak', 'aspal buruk', 'aspal hancur', 'proyek mangkrak', 'hebat sekali kemenpu'
]
ANGER_EMOJIS = {'😡', '🤬', '👿', '😤', '🖕'}

SURPRISE_TEXT_PATTERNS = [
    'kaget', 'heran', 'tercengang', 'tak disangka', 'shock', 'astaga', 'wow',
    'terperangah', 'speechless', 'mendadak', 'tiba-tiba',
    'bikin heboh', 'heboh', 'tak terduga', 'ditutup permanen', 'apakah program mbg berhenti', 'bikin geger', 'geger', 'bingkai foto'
]
SURPRISE_EMOJIS = {'🤯', '😲', '😯', '😳'}

def classify_emotion(text, sentiment_name='Netral', emojis=None):
    """
    Menetapkan dimensi emosi (Plutchik/Ekman) berdasarkan:
    1. Teks komprehensif (analisis semantik mendalam)
    2. Valensi sentimen (Sentiment-Valence Constraint)
    3. Penguatan simbolik emoji (jika ada)
    """
    text_l = str(text or '').lower()
    text_l = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', text_l)
    emojis_str = str(emojis or '')
    
    # 1. Valensi Negatif -> Marah, Takut, Jijik, Sedih
    if sentiment_name == 'Negatif':
        # Cek Jijik
        if any(w in text_l for w in DISGUST_TEXT_PATTERNS) or any(e in emojis_str for e in DISGUST_EMOJIS):
            return 'Jijik'
            
        # Cek Takut / Cemas
        if any(w in text_l for w in FEAR_TEXT_PATTERNS) or any(e in emojis_str for e in FEAR_EMOJIS):
            return 'Takut'
            
        # Cek Sedih
        if any(w in text_l for w in SADNESS_TEXT_PATTERNS) or any(e in emojis_str for e in SADNESS_EMOJIS):
            return 'Sedih'
            
        # Default Negatif -> Marah (kemarahan, umpatan, kritik tajam, protes)
        return 'Marah'
        
    # 2. Valensi Positif -> Senang (Joy / Gratitude / Fun)
    elif sentiment_name == 'Positif':
        return 'Senang'
        
    # 3. Valensi Netral -> Netral atau Terkejut
    else:
        if any(w in text_l for w in SURPRISE_TEXT_PATTERNS) or any(e in emojis_str for e in SURPRISE_EMOJIS):
            return 'Terkejut'
        return 'Netral'


# ==============================================================================
# HYBRID RULE-NEURAL POST-PROCESSING: 9-CLASS PLUTCHIK EMOTION ALIGNMENT
# ==============================================================================
def align_emotion_valence_9class(text, predicted_sentiment, raw_emotion):
    """
    Hybrid Rule-Neural Post-Processing (Penyelarasan Valensi Sentimen-Emosi):
    Menyelaraskan prediksi emosi 9-kelas IndoBERT dengan valensi sentimen akhir
    untuk menangani edge-cases seperti sarkasme (tawa getir), satir, dan doa buruk.
    
    Taksonomi 9 Emosi:
    - Positif: Joy, Trust, Anticipation
    - Negatif: Anger, Sadness, Disgust, Fear
    - Netral / Ambivalen: Surprise, Neutral
    """
    sent = str(predicted_sentiment or '').strip()
    raw_emo = str(raw_emotion or '').strip()
    text_l = str(text or '').lower()
    text_l = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', text_l)
    
    # 1. Valensi Negatif
    if sent == 'Negatif':
        # Cek leksikon amarah mutlak (ngegas, stop mbg, umpatan, ga becus)
        if any(w in text_l for w in ANGER_TEXT_PATTERNS) or any(w in text_l for w in ['ga becus', 'gak becus', 'tidak becus', 'bgn ga becus']):
            return 'Anger'
            
        # Cek sensori jijik / mual / makanan basi / bau asam -> Disgust
        if any(w in text_l for w in DISGUST_TEXT_PATTERNS):
            return 'Disgust'

        # Cek bahaya keracunan / racun -> Fear
        if any(w in text_l for w in FEAR_TEXT_PATTERNS) or any(w in text_l for w in ['keracunan', 'racun', 'mematikan', 'bahaya']):
            return 'Fear'
            
        # Cek headline sensasional / penutupan mendadak / kehebohan tak terduga -> Surprise
        if any(w in text_l for w in ['bikin heboh', 'ditutup permanen', 'apakah program mbg berhenti', 'tak terduga', 'geger', 'bingkai foto']):
            return 'Surprise'
            
        # Koreksi Sarkasme: Joy yang bersentimen Negatif
        if raw_emo == 'Joy':
            if any(w in text_l for w in DISGUST_TEXT_PATTERNS):
                return 'Disgust'
            if any(w in text_l for w in FEAR_TEXT_PATTERNS) or any(w in text_l for w in ['keracunan', 'racun', 'mematikan', 'bahaya']):
                return 'Fear'
            return 'Anger'
            
        # Koreksi Trust / Anticipation yang bersentimen Negatif (doa buruk / sindiran)
        if raw_emo in ['Trust', 'Anticipation']:
            return 'Anger'
            
        return raw_emo
        
    # 2. Valensi Positif
    elif sent == 'Positif':
        positive_affirm_words = [
            'berguna', 'keren', 'mantap', 'hebat', 'terbantu', 'membantu', 'sehat', 'nutrisi',
            'senang', 'alhamdulillah', 'syukur', 'sukses', 'berkah', 'berfaedah', 'banget', 'woi',
            'mencerdaskan', 'cerdas', 'bagus', 'bermanfaat', 'berkualitas', 'solutif', 'terbaik',
            'manfaat', 'mencerdaskan bangsa'
        ]
        if raw_emo in ['Anger', 'Disgust', 'Sadness', 'Fear'] or (raw_emo == 'Neutral' and any(w in text_l for w in positive_affirm_words)):
            if any(re.search(pat, text_l) for pat in PRO_POLICY_DEFENSE_PATTERNS) or any(w in text_l for w in ['dukung', 'percaya', 'kawal', 'yakin', 'amanah', 'hebat', 'harapan', 'terima kasih', 'bantuan', 'baik', 'berguna', 'manfaat', 'mencerdaskan', 'cerdas']):
                return 'Trust'
            if any(w in text_l for w in ['mirip', 'wow', 'elit', 'keren', 'gila', 'mantap', 'banget', 'senang', 'bagus']):
                return 'Joy'
            return 'Trust' if any(w in text_l for w in ['mencerdaskan', 'cerdas', 'edukasi', 'belajar']) else 'Joy'
        return raw_emo
        
    # 3. Valensi Netral / Faktual
    if sent == 'Netral':
        # Deteksi emosi Anticipation pada teks aspirasi, desakan pengawasan, dan klausul pencegahan risiko ("agar tidak...")
        preventative_words = [
            'agar tidak', 'agar tak', 'supaya tidak', 'jangan sampai', 'diperketat', 'pengawasan',
            'antisipasi', 'mitigasi', 'harapan', 'diharapkan', 'tolong', 'mohon', 'minta', 'ke depan',
            'siapkan', 'kesiapan', 'jelang nataru', 'target', 'diprioritaskan'
        ]
        if any(w in text_l for w in preventative_words):
            return 'Anticipation'
        if raw_emo in ['Anger', 'Disgust', 'Sadness', 'Fear']:
            return 'Neutral'

    # Koreksi false-positive Joy jika teks memuat indikasi bahaya, keracunan, penipuan, atau kritik nyata
    if raw_emo == 'Joy':
        masked_l = _mask_safe_contexts(text_l)
        if re.search(r'\b(?:keracunan|racun|diare)\b', masked_l):
            return 'Fear'
        if re.search(r'\b(?:korban\s+jiwa|menelan\s+korban|ga\s+becus|gak\s+becus|tidak\s+becus|basi|busuk|bancakan|korupsi|sia-sia)\b', masked_l):
            return 'Anger'

        is_official = any(re.search(pat, text_l) for pat in [
            r'(?:presiden\s+prabowo(?:\s+subianto)?|pemerintah|badan\s+gizi\s+nasional|bgn)\s+(?:menegaskan|memberi\s+arahan|menginstruksikan|konsolidasi)',
            r'(?:bimbingan\s+teknis|bimtek|penjamah\s+makanan)'
        ])
        is_child_branding = any(w in text_l for w in ['lagu anak', 'jingle', 'ceria', 'lucu', 'menanti mobil', 'suka sayur'])
        if is_official and not is_child_branding:
            return 'Neutral'
            
    # Deteksi headline sensasional / kehebohan tak terduga -> Surprise
    if any(w in text_l for w in ['bikin heboh', 'ditutup permanen', 'apakah program mbg berhenti', 'tak terduga', 'bingkai foto']):
        return 'Surprise'
        
    return raw_emo


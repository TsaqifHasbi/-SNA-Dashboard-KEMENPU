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
    
    # Tuntutan & protes aksi
    'hidup mahasiswa', 'turunkan harga', 'turun ke jalan', 'demo',
    'tuntutan aksi', 'setop pemborosan', 'menggerus', 'menggeru',
    
    # Kekecewaan mendalam & penderitaan
    'sedih banget', 'nangis', 'menangis', 'ga tega', 'gak tega',
    'miris', 'kasihan', 'tragis', 'menyedihkan',
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
    '11 12', '11-12', 'sebelas dua belas', 'malah bukak', 'malah buka',

    # Isu Ketidakmampuan & Kegagalan Birokrasi
    'ga becus', 'gak becus', 'tidak becus', 'tak becus', 'bgn ga becus', 'bgn gak becus',

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
    'apasi tujuan', 'apa sih tujuan', 'apa tujuannya', 'buat apa sih', 'untuk apa sih',
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
    # 0. Keluhan Retoris & Sinisme Ketiadaan Manfaat Kebijakan
    r'\b(?:apasi|apa\s*si|apa\s*sih|apaan\s*sih|buat\s*apa|untuk\s*apa)\b.*?\b(?:tujuan|urgensi|faedah|fungsi|manfaat|guna)\b',
    r'\b(?:apasi|apa\s*si|apa\s*sih|buat\s*apa|untuk\s*apa)\b.*?\b(?:kok|kenapa|tapi|malah)\b.*?\b(?:ga|gak|ngga|nggak|gada|gaada|belum|tidak|nihil)\b',
    r'\b(?:kok|kenapa)\b.*?\b(?:sampe\s+detik\s+ini|sampe\s+sekarang|sampai\s+sekarang|hingga\s+kini|hingga\s+saat\s+ini|sampe\s+hari\s+ini)\b.*?\b(?:gada|gaada|ga|gak|ngga|nggak|belum|tidak|nihil)\b',
    r'\b(?:gada|gaada|ga\s+ada|gak\s+ada|nggak\s+ada|tidak\s+ada|tak\s+ada)\s+(?:manfaat|manfaatnya|guna|gunanya|faedah|faedahnya|efek|efeknya|hasil|hasilnya|dampak|dampaknya|bukti|buktinya|perubahan|kejelasan)\b',
    r'\bkatanya\b.*?\b(?:tapi|namun|padahal|malah|nyatanya|faktanya)\b.*?\b(?:ga|gak|ngga|nggak|gada|gaada|belum|tidak|bukan|kurang|nihil)\b',
    # 0c. Sarkasme Pelayanan Publik & Kinerja Infrastruktur (Pujian Semu + Sindiran Kelambanan / Kerusakan / Kondisi Buruk)
    # Contoh: "Apresiasi respon cepat Kementerian PU ... dengan keadaan jalan yang sangat buruk, hebat sekali kemenpu"
    #         "Kemenpu keren banget masa hal sepele kaya kebocoran bendungan aja diselesainnya lama banget"
    #         "hebat betul jalan baru seminggu udah bolong-bolong parah"
    #         "terima kasih kemenpu jalan makin hancur lebur"
    r'(?:apresiasi|terima\s+kasih|makasih|salut|hebat|keren|mantap|top|luar\s+biasa|juara|bagus|terpuji).*?\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun|meski|walau|walaupun)\s+(?:keadaan|kondisi|kualitas|situasi)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air|fisik)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|amburadul|jelek|kacau)',
    r'\b(?:hebat|keren|mantap|top|luar\s+biasa|juara|bagus|istimewa)\s+(?:banget+|bgt+|sekali|bet|bener|betul|beneran)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri|balai|pemda)\b.*?\b(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|jelek)\b',
    r'\b(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|jelek)\b.*?\b(?:hebat|keren|mantap|top|luar\s+biasa|juara|bagus|istimewa)\s+(?:banget+|bgt+|sekali|bet|bener|betul|beneran)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri|balai|pemda)\b',
    r'(?:selesai|menyelesaikan|diresmikan|peresmian|beres|sukses|tuntas).*?\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun)\s+(?:keadaan|kondisi|kualitas|situasi|hasil)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air|fisik)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|ambles|amblas|jebol|bocor|berantakan|ancur|amburadul|jelek|kacau)',
    r'\b(?:respon\s+cepat|respons\s+cepat|gercep|responsif)\b.*?\b(?:dengan|padahal|faktanya|nyatanya|tapi|namun)\s+(?:keadaan|kondisi|kualitas|situasi)?\s*(?:jalan|jembatan|aspal|infrastruktur|proyek|tanggul|air)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|mangkrak|ambruk|lelet|lama|ambles|jebol|bolong)',
    r'\b(?:terima\s+kasih|makasih|thanks|tengkyu)\s+(?:kemenpu|pu|kementerian\s+pu|bbpjn|bws|satker|menteri).*?\b(?:jalan|jembatan|tanggul|proyek|irigasi).*?\b(?:makin|malah|justru|tambah)\s+(?:rusak|hancur|parah|buruk|ancur|mangkrak|bolong|ambles)\b',
    r'\bapresiasi\b.*?\b(?:keadaan|kondisi|kualitas)\s+(?:jalan|jembatan|aspal|infrastruktur|proyek|air)?\s*(?:yang\s+)?(?:sangat\s+|amat\s+|begitu\s+|makin\s+)?(?:buruk|rusak|hancur|parah|ancur|mangkrak|ambruk|bolong)\b',
    r'(?:keren|hebat|mantap|top|luar\s+biasa|bagus|pinter|pintar)\s+(?:banget+|bgt+|sekali|bet|bener|betul)\b.*?\b(?:masa|kok|padahal|giliran)\b.*?\b(?:sepele|gitu\s+aja|gini\s+aja|kecil|lama|lelet|lambat|ga\s+bisa|gak\s+bisa|tidak\s+bisa|bocor|kebocoran|rusak|ancur|hancur|bolong|ambruk)\b',
    r'\b(?:keren|hebat|mantap|bagus)\s+(?:banget+|bgt+|bet|sekali)\b.*?\b(?:diselesaikannya|diselesainnya|dikerjakannya|dikerjainnya|nanganinnya|penanganannya|kerjanya)\s+(?:lama|lelet|lambat|parah|molor)\b',
    r'\b(?:masa|kok)\b.*?\b(?:hal\s+sepele|masalah\s+sepele|gini\s+aja|gitu\s+aja|kaya\s+gitu|kaya\s+gini)\b.*?\b(?:lama|lelet|lambat|ga\s+becus|gak\s+becus|ga\s+bisa|gak\s+bisa|berlarut|mangkrak|molor)\b',
    r'(?:keren|hebat|mantap)\s+(?:banget+|bgt+|sekali)\b.*?\b(?:baru\s+(?:seminggu|sebulan|beberapa\s+hari)|belum\s+setahun)\b.*?\b(?:udah|sudah)\s+(?:rusak|bolong|hancur|ambruk|retak|jebol)\b',
    # 0b. Pujian semu kontras / sindiran peningkatan (makin berguna/hebat/mantap tapi disusul keracunan/korban/ga becus)
    r'(?:makin|semakin)?\s*(?:berguna|bermanfaat|hebat|keren|mantap|bagus|sukses).*?(?:keracunan|diare|masuk\s+rs|mual|muntah|mati|korban|ga\s+becus|gak\s+becus|tidak\s+becus|korupsi|bancakan|nilep)',
    # 1. Pujian semu + Realitas bahaya/korupsi/bencana/keracunan (dengan tanda baca apa pun)
    r'(?:berguna|bermanfaat|hebat|keren|mantap|bagus|berkah)\s+(?:banget+|bgt+|sekali)[!.,?\s]+.*?(?:buat|untuk)\s+(?:bikin|buat)?\s*(?:keracunan|masuk\s+rs|mual|muntah|diare|mati|korban|bancakan|nilep|korupsi|bagi-bagi|vendor\s+nakal|pemborosan|utang|tekor|rusak|ancur|hancur)',
    # 2. Pujian semu + bantahan realitas (tapi bohong/boong, tapi kenyataannya, tapi basi/ulat)
    r'(?:berguna|bermanfaat|hebat|keren|mantap|bagus|enak)\s+(?:banget+|bgt+|sekali)[!.,?\s]+.*?(?:tapi|padahal|kenyataannya|faktanya|nyatanya)\s+.*?(?:bohong|boong|basi|busuk|ulat|cacing|racun|keracunan|rusak|ancur|hancur|bancakan|korup|zonk|sampah)',
    # 3. Keracunan / Bencana yang dibungkus kata seru pujian di awal kalimat
    r'(?:woi+|woy+|anjir|njir|gila)\s+.*?(?:berguna|bermanfaat|hebat|mantap|keren).*?(?:keracunan|bancakan|masuk\s+rs|opname|korup|nilep|basi|ulat)',
    # 4. Saking bergunanya / saking bagusnya
    r'saking\s+(?:berguna|bermanfaat|bagus|hebat|keren|enak).*?(?:sampe|sampai)\s+(?:keracunan|masuk\s+rs|rugi|muntah|basi|protes|demo|opname)',
    # 5. Pas dibuka ternyata basi/berulat/zonk
    r'(?:enak|lezat|nikmat)\s+(?:banget+|bgt+|sekali).*?(?:pas|waktu|saat)\s+(?:dibuka|dilihat|dimakan|diperiksa).*?(?:basi|ulat|cacing|bau|asam|zonk)',
    # 6. Anggaran habis / utang numpuk
    r'(?:keren|hebat|mantap)\s+(?:banget+|bgt+|sekali).*?(?:anggaran|apbn|duit).*?(?:habis|ludes|jebol|bancakan|utang)',
    r'tepuk\s+tangan.*?(?:buat|atas).*?(?:keracunan|bancakan|korupsi|kebobrokan)',
    # 7. Sindiran politik & kebijakan populer
    r'mana\s+gas\s+mana\s+gas',
    r'2024\s*:\s*oke\s+gas.*?2025\s*:\s*mana\s+gas',
    r'gila+\s+indah',
    r'indahnya+',
    r'sppg\s+tutup.*?harga.*?(?:turun|murah)',
    r'tutup.*?harga\s+telor\s+turun',
    r'masih\s+(?:aja\s+)?(?:di\s*dukung|didukung|dibela)',
    r'pengen\s+tau.*?(?:brengsek|pidato\s+apa)',
    r'kok\s+(?:lu|kamu|dia)\s+(?:nentang|kritis)',
    r'molto.*?mbg\s+mematikan',
    r'private\s+jet.*?denpasar',
    r'weekend\s+in\s+bali',
    # 8. Retorika kemunduran / perbandingan masa penjajahan / satir era kolonial
    r'(?:balik|kembali)\s+(?:ke\s+)?(?:masa|zaman|jaman|era)\s+(?:penjajahan|belanda|jepang|kolonial)',
    r'(?:zaman|jaman|era|masa)\s+penjajahan\s+(?:kah|kali|ya|bray)',
    r'\b11\s*[-/]?\s*12\b.*?(?:sekolah\s+rakyat|mbg|kdmp|kebijakan|pemerintah)',
    r'(?:bukannya|tinggal)\s+.*?\s+malah\s+(?:buka|bukak|bikin|buat)\s+(?:sekolah\s+rakyat|program)',
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
    'memutus mata rantai kemiskinan', 'pendidikan gratis 100% berasrama',
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

def _count_caps_words(text):
    """Hitung jumlah kata yang sepenuhnya HURUF BESAR (min 3 karakter)."""
    words = text.split()
    return sum(1 for w in words if len(w) >= 3 and w.isupper() and w.isalpha())

def classify_caps_intent(raw_text, text_lower):
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

    # A. Cek Judul Berita / Rilis Resmi Kedinasan (Informatif Netral)
    is_headline = bool(
        re.search(r'\b(?:breaking\s+news|siaran\s+pers|kemen[\s-]*pu|kementerian|ditjen|bbws|bpjn|bbpjn|bws|apbn|ikn|dpr|ri)\b', text_lower)
        and len(raw_text.split()) < 15
        and not re.search(r'[!?]{2,}', raw_text)
        and not re.search(r'\b(?:rusak|ancur|hancur|parah|bohong|suka|keren|mantap)\b', text_lower)
    )
    if is_headline:
        return 'HEADLINE_NEUTRAL', 'caps_headline_resmi'

    # B. Cek Sinyal Sarkasme & Kemarahan dalam Huruf Besar
    has_sarc_anger = bool(
        re.search(r'\b(?:katanya|giliran|padahal|malah|baru\s+viral|nunggu\s+viral|gitu\s+aja|gitu\s+doang)\b.*?\b(?:tapi|kok|lama|lelet|lambat|rusak|ancur|hancur|parah|bobrok|bohong|mangkrak)\b', text_lower) or
        re.search(r'\b(?:hebat|keren|mantap|top|bagus|juara)\s+(?:banget+|bgt+|sekali|bet|bener|betul)\b.*?\b(?:rusak|ancur|hancur|parah|bolong|ambruk|mangkrak|lelet|lambat|bobrok|kacau|jelek)\b', text_lower) or
        re.search(r'\b(?:rusak\s+parah|hancur\s+lebur|jalan\s+rusak|jalan\s+bolong|jembatan\s+ambruk|tanggul\s+jebol|proyek\s+mangkrak|ga\s+becus|gak\s+becus|korupsi|maling|pemborosan)\b', text_lower) or
        re.search(r'\b(?:bohong|penipuan|pencitraan|ngibul|banci|sampah|tai|ancur|bobrok)\b', text_lower)
    )
    if has_sarc_anger:
        return 'SARCASM_ANGER', 'caps_sarkas_marah'

    # C. Cek Sinyal Pujian Antusias / Dukungan Nyata dalam Huruf Besar
    has_praise_keywords = bool(
        re.search(r'\b(?:suka\s+banget|suka\s+bgt|cinta\s+banget|keren\s+banget|keren\s+bgt|mantap\s+banget|mantap\s+bgt|enak\s+banget|enak\s+bgt|asli\s+cozy|cozy\s+banget|nyaman\s+banget|adem\s+banget|terima\s+kasih\s+banyak|makasih\s+banyak|alhamdulillah|juara\s+banget|top\s+banget|free\s+coffee|gratis\s+kopi|sukses\s+selalu|maju\s+terus|bangga\s+banget)\b', text_lower)
    )
    has_complaint_context = bool(
        re.search(r'\b(?:tapi|namun|sayang|sayangnya|kecewa|sayang\s+sekali|mati|kotor|panas|bau|galak|rusak|payah|bobrok|lelet|lambat|bocor)\b', text_lower)
    )
    if has_praise_keywords and not has_complaint_context:
        return 'ENTHUSIASTIC_PRAISE', 'caps_pujian_antusias'

    # D. Jika ada tanda baca repetitif kemarahan (!!, ???) tanpa indikator positif -> Kemarahan
    if re.search(r'[!?]{2,}', raw_text) and not has_praise_keywords:
        return 'SARCASM_ANGER', 'caps_kemarahan'

    return 'NORMAL', 'huruf_biasa'

def _has_profanity(text_lower):
    words = set(re.findall(r'\b\w+\b', text_lower))
    return bool(words & PROFANITY)

def _has_strong_negative(text_lower):
    # Masking nama institusi resmi agar tidak memicu false positive korupsi
    clean_text = text_lower.replace('komisi pemberantasan korupsi', 'kpk_institusi')
    clean_text = clean_text.replace('pencegahan korupsi', 'anti_korupsi_positif')
    for phrase in STRONG_NEGATIVE_PHRASES:
        if phrase in clean_text:
            return True, phrase
    return False, None

def _has_sarcasm(text_lower):
    for pattern in SARCASM_PATTERNS:
        if re.search(pattern, text_lower):
            return True, pattern
    return False, None

def _has_strong_positive(text_lower):
    for phrase in STRONG_POSITIVE_PHRASES:
        if phrase in text_lower:
            return True, phrase
    return False, None

def _count_emojis(text, emoji_set):
    return sum(1 for ch in text if ch in emoji_set)

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
    text_lower = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', text_lower)
    raw_text = text.strip()
    
    # 0. CEK BERITA/INFO FAKTUAL TANPA OPINI
    # Jika sekadar info publik tanpa kata kasar / umpatan / kemarahan personal
    is_pure_info = False
    for pat in NEUTRAL_INFORMATIONAL_PREFIXES:
        if re.search(pat, text_lower):
            is_pure_info = True
            break
            
    # Pengecualian: jika breaking news tapi isinya keracunan / korban / tuntutan henti -> tetap negatif!
    has_disaster_casualty = any(w in text_lower for w in ['keracunan', 'hilang ingatan', 'tuntutan', 'korban', 'dirawat', 'hospitalized', 'poisoned', 'hentikan'])
    if is_pure_info and not has_disaster_casualty and not _has_profanity(text_lower):
        return 'Netral', 1, 0.0, 'info_faktual_netral'

    # 0b. CEK KONTEN DOMESTIK / MEME NON-KEBIJAKAN
    # Konten #parenting atau mainan anak → netralkan jika tidak mengandung umpatan
    is_domestic, domestic_reason = _is_domestic_or_meme(text_lower)
    if is_domestic and not _has_profanity(text_lower) and not has_disaster_casualty:
        return 'Netral', 1, 0.0, domestic_reason

    # 0c. CEK ASPIRASI, PENCEGAHAN & TUNTUTAN KONSTRUKTIF WARGA (CITIZEN DEMAND / PREVENTATIVE CONTEXT)
    # Contoh: "diharapkan mempercepat penyelesaian proyek agar warga tidak lagi kesulitan",
    #         "tolong pengawasan proyek jalan daerah di level Satker diperketat agar tidak ada lagi ruas mangkrak",
    #         "mohon segera selesaikan perbaikan jalan agar tidak ada korban"
    # Kalimat ini adalah klausa antisipatif/pencegahan & rekomendasi tata kelola, bukan sentimen permusuhan negatif!
    DEMAND_PATTERNS = [
        r'\b(?:tolong|mohon|harap|diharapkan|dimohon|perlu|harus|minta|menuntut|mendesak)\s+(?:pengawasan|diperketat|perketat|diawasi|mempercepat|percepat|diselesaikan|diperbaiki|dibangun|menuntaskan|turunkan|tuntaskan|selesaikan|dibenahi|benahi|evaluasi)\b',
        r'\bpengawasan\s+.*?(?:diperketat|diperkuat|ditingkatkan)\b',
        r'\b(?:agar|supaya|biar|jangan\s+sampai)\s+(?:tidak|tak|gak|nggak|jangan)\s+(?:ada|terjadi|lagi|kesulitan|kekurangan|krisis|kebanjiran|menderita|terisolir|rugi|mangkrak|rusak|korban|terbengkalai)\b',
        r'\bagar\s+(?:warga|rakyat|petani|masyarakat|anak).*?(?:tidak\s+lagi\s+(?:kesulitan|kekurangan|krisis|kebanjiran|menderita|terisolir|rugi)|bisa\s+segera)\b',
        r'\b(?:kapan|kok\s+belum|kapan\s+selesai|jangan\s+ditunda|jangan\s+lambat)\b'
    ]
    is_demand = any(re.search(pat, text_lower) for pat in DEMAND_PATTERNS)
    has_neg_early, _ = _has_strong_negative(text_lower)
    if is_demand and not _has_profanity(text_lower) and not has_neg_early and not has_disaster_casualty:
        return 'Netral', 1, 0.0, 'aspirasi_dan_tuntutan_warga'

    # 0d. CEK ISU LINTAS KEMENTERIAN (ESDM / TAMBANG / BAHLIL / NON-PU FOCUS)
    # Contoh: "Bahlil vs Dody: Ketika Publik Menilai Kepemimpinan... Bahlil bukan berarti bebas dari kritik... pertambangan, energi..."
    # Kritik ditujukan pada tata kelola tambang/energi ESDM, sedangkan PU/Dody hanya perbandingan/pihak pasif.
    CROSS_MINISTRY_PATTERNS = [
        r'\b(?:esdm|bahlil|lahadalia|pertambangan|izin\s+tambang|nikel|batu\s*bara|hilirisasi\s+tambang|subsidi\s+bbm)\b'
    ]
    is_cross_ministry = any(re.search(pat, text_lower) for pat in CROSS_MINISTRY_PATTERNS)
    if is_cross_ministry:
        criticism_towards_other = bool(
            re.search(r'(?:bahlil|esdm|tambang|energi|nikel).*?(?:kritik|kontra|masalah|kasus|sorotan|dinilai|rendah|skandal)', text_lower) or
            re.search(r'(?:kritik|kontra|masalah|kasus|sorotan|dinilai|rendah|skandal).*?(?:bahlil|esdm|tambang|energi|nikel)', text_lower)
        )
        pu_criticism = bool(
            re.search(r'(?:dody|hanggodo|kemen[\s-]*pu|pekerjaan[\s-]+umum|jalan|jembatan|tanggul|bendungan|proyek\s+pu).*?(?:gagal|rusak|ambrol|korupsi|hancur|mangkrak|lambat|buruk|kecewa)', text_lower)
        )
        if criticism_towards_other and not pu_criticism:
            return 'Netral', 1, 0.0, 'netralisasi_kritik_lintas_kementerian_esdm'

    neg_signals = 0
    pos_signals = 0
    reasons = []

    # 1. CEK INTENSI PENGGUNAAN HURUF BESAR (ALL CAPS INTENT CLASSIFICATION)
    # Membedakan apakah HURUF BESAR adalah Kemarahan/Sarkasme vs Dukungan/Pujian Antusias vs Headline Resmi
    caps_intent, caps_reason = classify_caps_intent(raw_text, text_lower)
    if caps_intent == 'SARCASM_ANGER':
        neg_signals += 3
        reasons.append(caps_reason)
    elif caps_intent == 'ENTHUSIASTIC_PRAISE':
        pos_signals += 3
        reasons.append(caps_reason)

    # 2. CEK APRESIASI FASILITAS, PERPUSTAKAAN & RUANG PUBLIK (KONTEKSTUAL & ANTI-SARKASME)
    FACILITY_PRAISE_PATTERNS = [
        r'\b(?:perpus|perpustakaan|ruang\s+baca|wfc|fasilitas|kantor\s+pu)\b.*?\b(?:suka\s+banget|suka\s+bgt|nyaman|cozy|adem|dingin|kenceng|bersih|luas|bagus|keren|lengkap|gratis|free|enak|betah|rekomendasi|surganya)\b',
        r'\b(?:suka\s+banget|suka\s+bgt|nyaman|cozy|adem|dingin|kenceng|bersih|luas|bagus|keren|lengkap|gratis|free|enak|betah|rekomendasi|surganya)\b.*?\b(?:perpus|perpustakaan|ruang\s+baca|wfc|fasilitas|kantor\s+pu)\b'
    ]
    FACILITY_COMPLAINT_PATTERNS = [
        r'\b(?:mati|panas|gerah|bau\s+apek|apek|kotor|jorok|sempit|bising|antri|antre|rusak|bocor|galak|judes|tidak\s+ramah|pelayanan\s+buruk|mengecewakan|kecewa|sayang\s+sekali|bobrok)\b'
    ]
    has_facility_praise = any(re.search(pat, text_lower) for pat in FACILITY_PRAISE_PATTERNS)
    has_facility_complaint = any(re.search(pat, text_lower) for pat in FACILITY_COMPLAINT_PATTERNS)

    if has_facility_praise:
        if has_facility_complaint:
            # Jika ada kata fasilitas positif tapi diikuti komplain nyata (misal: "perpus cozy tapi AC mati kotor")
            neg_signals += 2
            reasons.append('komplain_fasilitas')
        else:
            # Pujian fasilitas tulus tanpa komplain
            pos_signals += 3
            reasons.append('fasilitas_perpus_positif')

    # 3. CEK PEMBELAAN KEBIJAKAN / KECAMAN KEPADA PENENTANG (PRO-POLICY DEFENSE)
    is_defense = any(re.search(pat, text_lower) for pat in PRO_POLICY_DEFENSE_PATTERNS)
    if is_defense:
        pos_signals += 3
        reasons.append('pembelaan_kebijakan_dari_penentang')
        
    # Cek frasa positif kuat
    has_pos, pos_p = _has_strong_positive(text_lower)
    if has_pos:
        pos_signals += 2
        reasons.append(f'positif_kuat({pos_p})')
    
    # 4. Umpatan (bobot 3 - mutlak negatif jika bukan pembelaan kebijakan)
    if _has_profanity(text_lower):
        if not is_defense:
            neg_signals += 3
            reasons.append('umpatan')
    
    # 5. Frasa negatif kuat
    has_neg, neg_p = _has_strong_negative(text_lower)
    if has_neg:
        neg_signals += 2
        reasons.append(f'negatif_kuat({neg_p})')
    
    # 6. Sarkasme (bobot 4 - otomatis batalkan seluruh sinyal positif semu)
    has_sarc, sarc_p = _has_sarcasm(text_lower)
    if has_sarc:
        neg_signals += 4
        pos_signals = 0  # Batal seluruh sinyal positif semu karena pujian bersifat ironis/sarkas
        reasons.append(f'sarkasme({sarc_p})')
        
    # 7. Emoji negatif
    neg_emoji_count = _count_emojis(text, NEGATIVE_EMOJIS)
    if neg_emoji_count >= 1:
        neg_signals += 1
        reasons.append('emoji_negatif')
        
    # --- DETEKSI POSITIF ---
    
    # 6. Emoji positif
    pos_emoji_count = _count_emojis(text, POSITIVE_EMOJIS)
    if pos_emoji_count >= 1:
        pos_signals += 1
        reasons.append('emoji_positif')
        
    # 8. Konten hiburan video pendek — DIHAPUS (terlalu agresif menandai meme sebagai Positif)
    # Meme/shorts tanpa evaluasi kebijakan sebaiknya tetap di label asli IndoBERT

    # --- KEPUTUSAN FINAL ---
    
    reason_str = ', '.join(reasons)
    
    # Negatif dominan
    if neg_signals > pos_signals and neg_signals >= 2:
        return 'Negatif', 0, -0.85, reason_str
    
    if neg_signals > 0 and pos_signals == 0 and current_sentiment == 'Netral':
        return 'Negatif', 0, -0.65, reason_str
        
    # Positif dominan
    if pos_signals > neg_signals and pos_signals >= 2:
        return 'Positif', 2, 0.85, reason_str
        
    if pos_signals > 0 and neg_signals == 0 and current_sentiment == 'Netral':
        return 'Positif', 2, 0.65, reason_str
        
    # Khusus kasus informatif/reflektif santai
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
        preventative_words = ['agar tidak', 'agar tak', 'supaya tidak', 'jangan sampai', 'diperketat', 'pengawasan', 'antisipasi', 'mitigasi', 'harapan', 'diharapkan', 'tolong', 'mohon', 'minta', 'ke depan']
        if any(w in text_l for w in preventative_words):
            return 'Anticipation'

    # Koreksi false-positive Joy jika teks memuat indikasi bahaya, keracunan, penipuan, atau kritik
    if raw_emo == 'Joy':
        if any(w in text_l for w in ['keracunan', 'racun', 'korban', 'diare', 'mati', 'ga becus', 'gak becus', 'tidak becus', 'basi', 'busuk', 'bancakan', 'korupsi', 'sia-sia']):
            return 'Fear' if any(w in text_l for w in ['keracunan', 'racun', 'diare']) else 'Anger'

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


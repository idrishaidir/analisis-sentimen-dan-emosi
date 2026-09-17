# Moodify - Analisis Sentimen dan Emosi X (Twitter)

Moodify adalah aplikasi berbasis web untuk melakukan *scraping* tweet dari platform X (Twitter) dan menganalisis sentimen (Positif, Negatif, Netral) serta emosi (Marah, Takut, Sedih, Senang, Cinta, Netral) secara otomatis.

Aplikasi ini telah diperbarui khusus pada branch `mier-deploy` untuk mendukung efisiensi memori, performa produksi, dan tampilan visual (UI) yang *mobile-friendly*.

## ✨ Fitur Utama
- **Autentikasi Pengguna**: Register, Login, Lupa Password, dan proteksi Anti-Spam (Rate Limiting).
- **Scraping Otomatis (Selenium)**: Mengambil tweet berdasarkan kata kunci menggunakan *headless browser* yang dirancang tahan terhadap deteksi anti-bot (menggunakan *undetected-chromedriver*).
- **AI Ringan & Cepat (HF API)**: Tidak lagi memuat model berukuran Gigabyte ke RAM lokal. Aplikasi ini menggunakan Hugging Face Inference API untuk melakukan prediksi secara jarak jauh.
- **Visualisasi Hasil**: Menampilkan statistik analisis berupa persentase sentimen & emosi, tabel data tweet, dan grafik awan kata (*WordCloud*).
- **Manajemen Riwayat**: Menyimpan riwayat pencarian pengguna di database dan mendukung penghapusan data secara permanen.
- **Mobile Responsive**: Tampilan dirombak 100% untuk kenyamanan akses melalui layar *smartphone*.

## 🛠️ Teknologi yang Digunakan
- **Backend**: Python 3.9, Flask
- **Database**: PostgreSQL (SQLAlchemy ORM) - *Support SQLite untuk local fallback*
- **Scraping**: Selenium, `undetected-chromedriver`
- **Machine Learning**: Hugging Face API (IndoBERT)
- **Data Processing**: Pandas, NLTK, Sastrawi
- **Frontend**: HTML5, CSS3, JavaScript

## 🚀 Cara Menjalankan Aplikasi di Lokal

### 1. Persiapan Awal (Clone & Environment)
Buka terminal dan jalankan perintah berikut:
```bash
# Clone repository branch mier-deploy
git clone -b mier-deploy https://github.com/idrishaidir/analisis-sentimen-dan-emosi.git
cd analisis-sentimen-dan-emosi

# Buat virtual environment
python -m venv venv

# Aktivasi virtual environment (Untuk Windows)
.\venv\Scripts\activate
```

### 2. Instalasi Dependensi
Pastikan kamu berada dalam `venv`, lalu install semua *requirements*:
```bash
pip install -r requirements.txt
```

### 3. Menyiapkan Konfigurasi
Aplikasi membutuhkan konfigurasi *environment variables*. Di PowerShell, atur mode ke *development*:
```powershell
$env:ENVIRONMENT="development"
$env:FLASK_ENV="development"
```
*(Opsional: Jika kamu ingin menggunakan API Hugging Face tanpa rate limit yang ketat, kamu bisa menambahkan `$env:HF_TOKEN="token_hf_kamu"`)*.

### 4. Menjalankan Aplikasi
Setelah semuanya siap, jalankan aplikasi menggunakan server *development* Flask:
```bash
flask run --debug
```
Aplikasi bisa diakses melalui browser di alamat: `http://127.0.0.1:5000`

### 5. Penggunaan Fitur Scraping (Lokal)
Karena aplikasi menggunakan Selenium, pastikan koneksi internet stabil. Pertama kali kamu menjalankan scraping lokal, aplikasi mungkin akan membuka Chrome dan memintamu **Login X (Twitter) secara manual**.
Gunakan **Akun Tumbal** (bukan akun utama) untuk login. Setelah berhasil, aplikasi akan menyimpan sesi *cookies* kamu agar tidak perlu login lagi di masa depan.
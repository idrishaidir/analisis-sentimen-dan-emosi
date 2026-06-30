import os
import pandas as pd
import re
from apify_client import ApifyClient
from .preprocessing import preprocessText
from .models import predict_sentimen, predict_emosi

# --- FUNGSI ANALISIS TETAP SAMA ---
def analyze_sentiment_emotion(cleaned_path):
    try:
        print(f"🔍 Membaca file hasil preprocessing: {cleaned_path}")
        df = pd.read_csv(cleaned_path)
        if "text" not in df.columns:
            return False, "Kolom 'text' tidak ditemukan!"

        df["text"] = df["text"].fillna("")

        print("⚙️ Melakukan prediksi sentimen & emosi...")
        df["sentimen"] = df["text"].apply(predict_sentimen)
        df["emosi"] = df["text"].apply(predict_emosi)

        base_dir = os.path.dirname(cleaned_path)
        keyword = os.path.basename(cleaned_path).replace("_cleaned.csv", "")
        labeled_path = os.path.join(base_dir, f"{keyword}_label.csv")

        df.to_csv(labeled_path, index=False, encoding="utf-8")
        print(f"✅ Hasil analisis tersimpan di: {labeled_path}")
        return True, labeled_path

    except Exception as e:
        print(f"❌ TERJADI ERROR DI analyze_sentiment_emotion: {e}")
        return False, f"Error saat analisis: {e}"

# --- FUNGSI SCRAPING BARU DENGAN APIFY ---
def scraping_tweets(keyword, since, until, auth_token, limit=100):
    # 1. Siapkan struktur folder (seperti kode lamamu)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    output_dir = os.path.join(base_dir, "tweets-data", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    search_query = f"{keyword} since:{since} until:{until} lang:id"
    
    # 2. Inisialisasi Apify Client menggunakan token dari input web
    # auth_token di sini adalah API Token dari pengaturan Apify-mu
    client = ApifyClient(auth_token)
    
    # 3. Atur parameter untuk Actor "apidojo/tweet-scraper"
    run_input = {
        "searchTerms": [search_query],
        "maxItems": int(limit),
        "sort": "Latest"
    }
    
    try:
        print(f"🚀 Memulai scraping via Apify untuk: {search_query}")
        
        # Panggil Actor apidojo
        run = client.actor("apidojo/tweet-scraper").call(run_input=run_input)
        
        # Ambil data dari dataset
        dataset_items = client.dataset(run["defaultDatasetId"]).iterate_items()
        
        # 4. Ekstrak data dan ubah formatnya agar sesuai dengan kebutuhan Pandas
        tweets_data = []
        for item in dataset_items:
            # Mengambil data sesuai struktur JSON dari apidojo
            tweets_data.append({
                "created_at": item.get("createdAt", ""),
                "username": item.get("author", {}).get("userName", "anonim"),
                "full_text": item.get("text", "")
            })
            
        df = pd.DataFrame(tweets_data)
        
        # Cek jika tidak ada hasil
        if df.empty:
            print("❌ Apify tidak menemukan tweet.")
            return False, "Tidak ada tweet yang ditemukan untuk kata kunci dan tanggal tersebut."
            
        # 5. Preprocessing Data (Sama persis seperti logikamu sebelumnya)
        df = df.dropna(subset=["full_text"]).reset_index(drop=True)
        print("🧹 Memulai pembersihan teks...")
        df["text"] = df["full_text"].apply(preprocessText)
        
        # Simpan CSV bersih
        cleaned_path = os.path.join(output_dir, f"{safe_keyword}_cleaned.csv")
        df.to_csv(cleaned_path, index=False, encoding="utf-8")
        print(f"✅ Data bersih tersimpan di: {cleaned_path}")
        
        # 6. Lempar ke fungsi Analisis IndoBERT
        success, labeled_path = analyze_sentiment_emotion(cleaned_path)
        return success, labeled_path

    except Exception as e:
        print(f"❌ Error Apify: {e}")
        # Tangkap pesan error dari Apify (misal jika token salah)
        if "Unauthorized" in str(e) or "token" in str(e).lower():
            return False, "API Token Apify tidak valid atau salah."
        return False, f"Terjadi kesalahan pada sistem penarikan data: {e}"
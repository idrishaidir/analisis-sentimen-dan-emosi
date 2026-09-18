import os
import re
import pandas as pd
import shutil
from apify_client import ApifyClient

from .preprocessing import preprocessText
from .models import predict_sentimen, predict_emosi

def analyze_sentiment_emotion(csv_path):
    try:
        print(f"🔍 Mulai analisis file: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        if "text" not in df.columns:
            return False, "Kolom 'text' tidak ditemukan dalam file CSV."

        print(f"⚙️ Melakukan prediksi sentimen & emosi dengan IndoBERT...")
        df['sentimen'] = df['text'].apply(predict_sentimen)
        df['emosi'] = df['text'].apply(predict_emosi)
        
        labeled_path = csv_path.replace('_cleaned.csv', '_labeled.csv')
        df.to_csv(labeled_path, index=False, encoding='utf-8')
        
        return True, labeled_path

    except Exception as e:
        return False, f"Error saat analisis: {e}"

def scraping_tweets(keyword, limit=50, chrome_profile_path=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    tweets_dir = os.path.join(base_dir, "tweets-data")
    output_dir = os.path.join(tweets_dir, "output")
    
    # Hapus folder output lama jika ada agar bersih
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    output_filename = f"{safe_keyword}_cleaned.csv"
    cleaned_path = os.path.join(output_dir, output_filename)
    
    # Dapatkan Apify Token dari Environment Variables
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        return False, "APIFY_API_TOKEN tidak ditemukan! Harap tambahkan di Environment Variable."

    print(f"🚀 Memulai Apify Cloud Scraper untuk kata kunci: '{keyword}'")
    
    try:
        # Inisialisasi client Apify
        client = ApifyClient(apify_token)

        # Siapkan input untuk actor 'kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest'
        # Memasukkan beberapa variasi parameter agar pasti cocok dengan format pembuatnya
        search_query = f"{keyword} lang:id"
        run_input = {
            "searchTerms": [search_query],
            "query": search_query,
            "maxItems": int(limit),
            "maxTweets": int(limit)
        }

        print("☁️ Mengirim perintah ke server Apify... (Mohon tunggu beberapa detik)")
        
        # Panggil Actor pilihanmu
        run = client.actor("kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest").call(run_input=run_input)
        
        # Ekstrak Dataset ID dengan cara yang kebal terhadap perubahan versi apify-client (dict vs object)
        if isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId")
        else:
            dataset_id = getattr(run, "defaultDatasetId", None) or getattr(run, "default_dataset_id", None)
            
        tweets_data = []
        for item in client.dataset(dataset_id).iterate_items():
            # Ekstrak Teks Tweet (Sangat Kokoh)
            tweet_text = item.get("full_text") or item.get("text") or item.get("content") or ""
            if not tweet_text and "tweet" in item and isinstance(item["tweet"], dict):
                tweet_text = item["tweet"].get("full_text") or item["tweet"].get("text") or ""
                
            # Ekstrak Username (Sangat Kokoh)
            author_data = item.get("user") or item.get("author") or {}
            if not author_data and "core" in item:  # Raw Twitter GraphQL format
                try:
                    author_data = item["core"]["user_results"]["result"]["legacy"]
                except KeyError:
                    pass
            username = author_data.get("screen_name") or author_data.get("userName") or author_data.get("username") or "Unknown"
            
            # Ekstrak Tanggal
            created_at = item.get("created_at") or item.get("createdAt") or item.get("date") or "Unknown Date"
            
            if tweet_text:
                tweets_data.append({
                    "created_at": created_at,
                    "username": username,
                    "full_text": tweet_text
                })
        
        if not tweets_data:
            return False, "Tidak ada tweet yang ditemukan untuk kata kunci tersebut."

        print(f"📦 Berhasil mengambil {len(tweets_data)} tweet! Memulai Preprocessing teks...")
        
        # Konversi ke Pandas DataFrame
        df = pd.DataFrame(tweets_data)
        
        # Lakukan pembersihan (Preprocessing)
        df["text"] = df["full_text"].astype(str).apply(preprocessText)
        
        # Simpan sementara ke CSV
        df.to_csv(cleaned_path, index=False, encoding="utf-8")
        
        # Lanjut panggil Model AI (IndoBERT)
        return analyze_sentiment_emotion(cleaned_path)
        
    except Exception as e:
        return False, f"Terjadi kesalahan saat menghubungi Apify API: {e}"
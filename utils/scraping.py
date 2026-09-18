import os
import re
import csv
import time
import base64
import pickle
import shutil
import urllib.parse
import pandas as pd
import subprocess

from .preprocessing import preprocessText
from .models import predict_sentimen, predict_emosi


def extract_auth_token():
    """Extract auth_token from Base64 Environment Variable or local pickle file."""
    cookies_dir = "cookies"
    os.makedirs(cookies_dir, exist_ok=True)
    cookie_path = os.path.join(cookies_dir, "session_state.bin")
    
    # Cek apakah ada cookie dari Environment Variable (Render Production)
    env_cookie = os.getenv("TWITTER_COOKIES_B64")
    if env_cookie:
        print("🚀 Mendekode cookies dari Environment Variable...")
        try:
            cookie_bytes = base64.b64decode(env_cookie)
            with open(cookie_path, "wb") as file:
                file.write(cookie_bytes)
        except Exception as e:
            print(f"⚠️ Gagal mendekode cookies dari ENV: {e}")
            
    if not os.path.exists(cookie_path):
        print("⚠️ No saved cookies found!")
        return None
        
    try:
        with open(cookie_path, "rb") as file:
            cookies = pickle.load(file)
            
        # Cari auth_token
        for cookie in cookies:
            if cookie.get('name') == 'auth_token':
                return cookie.get('value')
    except Exception as e:
        print(f"❌ Failed to parse cookies: {e}")
        
    return None

def analyze_sentiment_emotion(csv_path):
    # (Kode fungsi ini tetap sama seperti sebelumnya)
    try:
        print(f"🔍 Mulai analisis file: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        if "text" not in df.columns:
            return False, "Kolom 'text' tidak ditemukan dalam file CSV."

        print(f"⚙️ Melakukan prediksi sentimen & emosi...")
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
    filename = f"{safe_keyword}.csv"
    relative_output = os.path.join("output", filename)
    absolute_output = os.path.join(output_dir, filename)
    
    print("\n🚀 Menyiapkan proses tweet-harvest...")
    
    auth_token = extract_auth_token()
    if not auth_token:
        # Fallback jika di-set langsung lewat .env
        auth_token = os.getenv("TWITTER_AUTH_TOKEN")
        if not auth_token:
            return False, "Cookies (auth_token) tidak ditemukan! Harap perbarui TWITTER_COOKIES_B64."

    # Render Linux menggunakan 'tweet-harvest' global, Windows menggunakan 'npx.cmd'
    is_production = os.getenv('ENVIRONMENT') == 'production'
    
    # Hanya gunakan keyword, TANPA since/until date sesuai dengan penemuan terbarumu!
    search_query = f"{keyword} lang:id"
    
    if is_production:
        command = [
            "tweet-harvest",
            "-o", relative_output, "-s", search_query,
            "--tab", "LATEST", "-l", str(limit),
            "--token", auth_token
        ]
    else:
        command = [
            r"C:\Program Files\nodejs\npx.cmd", "-y", "tweet-harvest@latest",
            "-o", relative_output, "-s", search_query,
            "--tab", "LATEST", "-l", str(limit),
            "--token", auth_token
        ]
    
    print("🚀 Menjalankan:", " ".join(command))
    
    try:
        # Jalankan tweet-harvest
        subprocess.run(command, check=True, cwd=base_dir) 
        
        # Cek ketersediaan file
        for i in range(10):
            if os.path.exists(absolute_output):
                break
            time.sleep(1)
            
        if not os.path.exists(absolute_output):
            return False, f"File hasil scraping tidak ditemukan. Bot mungkin dicegat oleh Twitter."
            
        print(f"✅ File ditemukan: {absolute_output}")
        
        # Deteksi delimiter otomatis
        try:
            df = pd.read_csv(absolute_output, encoding="utf-8-sig", delimiter=";")
            if "full_text" not in df.columns:
                df = pd.read_csv(absolute_output, encoding="utf-8-sig", delimiter=",")
        except pd.errors.EmptyDataError:
            return False, "Tidak ada tweet yang ditemukan untuk kata kunci tersebut."
            
        if "full_text" not in df.columns:
            possible_text_col = df.columns[0]
            df.rename(columns={possible_text_col: "full_text"}, inplace=True)
            
        print("⚙️ Preprocessing teks...")
        df["text"] = df["full_text"].astype(str).apply(preprocessText)
        
        cleaned_path = os.path.join(output_dir, f"{safe_keyword}_cleaned.csv")
        df.to_csv(cleaned_path, index=False, encoding="utf-8")
        
        # 9. Lanjut ke Model AI
        return analyze_sentiment_emotion(cleaned_path)
        
    except subprocess.CalledProcessError as e:
        return False, f"Gagal menjalankan tweet-harvest: {e}"
    except Exception as e:
        return False, f"Terjadi kesalahan internal: {e}"
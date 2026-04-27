import os
import subprocess
import pandas as pd
import re
import time
import shutil

from .preprocessing import preprocessText

from .models import predict_sentimen, predict_emosi

def analyze_sentiment_emotion(cleaned_path):
    try:
        print(f"🔍 Membaca file hasil preprocessing: {cleaned_path}")
        df = pd.read_csv(cleaned_path)
        if "text" not in df.columns:
            print("❌ Kolom 'text' tidak ditemukan di file cleaned!")
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


def scraping_tweets(keyword, since, until, auth_token, limit=100):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    tweets_dir = os.path.join(base_dir, "tweets-data")
    output_dir = os.path.join(tweets_dir, "output")
    
    # if os.path.exists(output_dir):
    #     shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    filename = f"{safe_keyword}.csv"
    relative_output = os.path.join("output", filename)
    absolute_output = os.path.join(output_dir, filename)
    search_query = f"{keyword} since:{since} until:{until} lang:id"
    npx_path = r"C:\Program Files\nodejs\npx.cmd"
    
    command = [
        npx_path, "-y", "tweet-harvest@2.6.1",
        "-o", relative_output, "-s", search_query,
        "--tab", "LATEST", "-l", str(limit),
        "--token", auth_token
    ]
    
    print("🚀 Menjalankan:", " ".join(command))
    print("📂 CWD:", tweets_dir)
    print("📄 Akan menyimpan ke:", absolute_output)
    
    try:
        subprocess.run(command, check=True, cwd=base_dir)
        
        for i in range(5):
            if os.path.exists(absolute_output):
                break
            print(f"⏳ Menunggu file muncul... ({i+1}s)")
            time.sleep(1)
            
        if not os.path.exists(absolute_output):
            print("❌ File hasil scraping tidak ditemukan.")
            return False, f"File hasil scraping tidak ditemukan: {absolute_output}"
            
        print(f"✅ File ditemukan: {absolute_output}")
        df = pd.read_csv(absolute_output, encoding="utf-8-sig")
        
        if "full_text" not in df.columns:
            possible_text_col = df.columns[0]
            print(f"⚠️ Kolom 'full_text' tidak ditemukan, gunakan kolom pertama: {possible_text_col}")
            df.rename(columns={possible_text_col: "full_text"}, inplace=True)
            
        df = df[df["full_text"].str.lower() != "full_text"]
        # df = df[["full_text"]].dropna().reset_index(drop=True)
        df = df.dropna(subset=["full_text"]).reset_index(drop=True)
        df["text"] = df["full_text"].apply(preprocessText)
        
        # Ambil kolom tanggal dan username jika tersedia dari Twitter
        available_cols = [col for col in ["created_at", "username", "full_text", "text"] if col in df.columns]
        cleaned_df = df[available_cols]
        
        cleaned_path = os.path.join(output_dir, f"{safe_keyword}_cleaned.csv")
        cleaned_df.to_csv(cleaned_path, index=False, encoding="utf-8")
        
        print(f"✅ Data bersih tersimpan di: {cleaned_path}")
        print("\n📁 Isi folder output:")
        print(os.listdir(output_dir))
        
        success, labeled_path = analyze_sentiment_emotion(cleaned_path)
        
        if success:
            print(f"🎉 Analisis sentimen & emosi selesai → {labeled_path}")
            return True, labeled_path
        else:
            print(f"⚠️ Gagal melakukan analisis lanjutan! Error: {labeled_path}")
            return False, labeled_path 
        
    except subprocess.CalledProcessError as e:
        return False, f"Gagal menjalankan tweet-harvest: {e}"
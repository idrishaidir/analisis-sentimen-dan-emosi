from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import os
import pandas as pd
import re, string, torch, time, shutil
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

import nltk
for pkg in ['punkt_tab', 'stopwords']:
    try:
        nltk.data.find(f'tokenizers/{pkg}' if pkg == 'punkt_tab' else f'corpora/{pkg}')
    except LookupError:
        nltk.download(pkg)


app = Flask(__name__)
app.secret_key = "secret123"

# =========================================================
# 🔧 PREPROCESSING
# =========================================================
def cleaningText(text):
    text = text.lower()
    text = re.sub(r"http\S+|www.\S+", "", text)
    text = re.sub(r"@\w+|#", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenizingText(text):
    return word_tokenize(text)

def filteringText(tokens):
    stop_words = set(stopwords.words("indonesian"))
    return [word for word in tokens if word not in stop_words]

def stemmingText(tokens):
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()
    return [stemmer.stem(word) for word in tokens]

def toSentence(tokens):
    return " ".join(tokens)

def preprocessText(text):
    text = cleaningText(text)
    tokens = tokenizingText(text)
    tokens = filteringText(tokens)
    tokens = stemmingText(tokens)
    return toSentence(tokens)

# =========================================================
# 🧠 LOAD MODELS
# =========================================================
print("🔍 Loading models...")
sentiment_model = "w11wo/indonesian-roberta-base-sentiment-classifier"
emotion_model = "Atherizz/emolog-indobert"

tokenizer_sen = AutoTokenizer.from_pretrained(sentiment_model)
model_sen = AutoModelForSequenceClassification.from_pretrained(sentiment_model)

tokenizer_emo = AutoTokenizer.from_pretrained(emotion_model)
model_emo = AutoModelForSequenceClassification.from_pretrained(emotion_model)
print("✅ Models loaded successfully!")

# =========================================================
# 🧠 PREDIKSI SENTIMEN & EMOSI (sesuai model)
# =========================================================
def predict_sentimen(text):
    inputs = tokenizer_sen(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model_sen(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_id = torch.argmax(probs, dim=1).item()
    
    # urutan label sesuai repo model w11wo
    sentiment_labels = ["negative", "neutral", "positive"]
    return sentiment_labels[label_id]


def predict_emosi(text):
    inputs = tokenizer_emo(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model_emo(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_id = torch.argmax(probs, dim=1).item()
    
    # urutan label sesuai repo Atherizz/emolog-indobert
    emotion_labels = ["Senang", "Sedih", "Marah", " Takut", "Jijik", "Terkejut", "Netral"]
    return emotion_labels[label_id]

# =========================================================
# 🤖 FUNGSI PREDIKSI SENTIMEN & EMOSI OTOMATIS
# =========================================================
def analyze_sentiment_emotion(cleaned_path):
    print(f"🔍 Membaca file hasil preprocessing: {cleaned_path}")
    df = pd.read_csv(cleaned_path)
    if "text" not in df.columns:
        print("❌ Kolom 'text' tidak ditemukan di file cleaned!")
        return False, "Kolom 'text' tidak ditemukan!"

    # Prediksi sentimen dan emosi
    print("⚙️ Melakukan prediksi sentimen & emosi...")
    df["sentimen"] = df["text"].apply(predict_sentimen)
    df["emosi"] = df["text"].apply(predict_emosi)

    # Simpan hasil akhir
    base_dir = os.path.dirname(cleaned_path)
    keyword = os.path.basename(cleaned_path).replace("_cleaned.csv", "")
    labeled_path = os.path.join(base_dir, f"{keyword}_label.csv")

    df.to_csv(labeled_path, index=False, encoding="utf-8")
    print(f"✅ Hasil analisis tersimpan di: {labeled_path}")
    return True, labeled_path


# =========================================================
# 🐦 SCRAPING FUNCTION (FIX TANPA SUBFOLDER)
# =========================================================
def scraping_tweets(keyword, since, until, auth_token, limit=100):
    import shutil, time

    base_dir = os.path.dirname(os.path.abspath(__file__))
    tweets_dir = os.path.join(base_dir, "tweets-data")
    output_dir = os.path.join(tweets_dir, "output")

    # Bersihkan output lama
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    filename = f"{safe_keyword}.csv"
    relative_output = os.path.join("output", filename)  # ✅ hanya "output/..."
    absolute_output = os.path.join(output_dir, filename)

    search_query = f"{keyword} since:{since} until:{until} lang:id"
    npx_path = r"C:\Program Files\nodejs\npx.cmd"

    command = [
        npx_path,
        "-y",
        "tweet-harvest@2.6.1",
        "-o", relative_output,
        "-s", search_query,
        "--tab", "LATEST",
        "-l", str(limit),
        "--token", auth_token
    ]

    print("🚀 Menjalankan:", " ".join(command))
    print("📂 CWD:", tweets_dir)
    print("📄 Akan menyimpan ke:", absolute_output)

    try:
        subprocess.run(command, check=True, cwd=base_dir)

        # Tunggu file muncul
        for i in range(5):
            if os.path.exists(absolute_output):
                break
            print(f"⏳ Menunggu file muncul... ({i+1}s)")
            time.sleep(1)

        if not os.path.exists(absolute_output):
            print("❌ File hasil scraping tidak ditemukan.")
            print("📁 Isi output_dir:", os.listdir(output_dir))
            return False, f"File hasil scraping tidak ditemukan: {absolute_output}"

        print(f"✅ File ditemukan: {absolute_output}")

        # Baca CSV dengan aman dari BOM dan header nyasar
        df = pd.read_csv(absolute_output, encoding="utf-8-sig")

        # Jika kolom 'full_text' tidak ditemukan, periksa kemungkinan salah header
        if "full_text" not in df.columns:
            possible_text_col = df.columns[0]
            print(f"⚠️ Kolom 'full_text' tidak ditemukan, gunakan kolom pertama: {possible_text_col}")
            df.rename(columns={possible_text_col: "full_text"}, inplace=True)

        # Hapus baris yang salah berisi header (misal: 'full_text' sebagai isi data)
        df = df[df["full_text"].str.lower() != "full_text"]

        # Pastikan hanya ambil teks
        df = df[["full_text"]].dropna().reset_index(drop=True)

        # Preprocessing teks
        df["text"] = df["full_text"].apply(preprocessText)

        # Simpan hanya kolom text
        cleaned_df = df[["text"]]

        cleaned_path = os.path.join(output_dir, f"{safe_keyword}_cleaned.csv")
        cleaned_df.to_csv(cleaned_path, index=False, encoding="utf-8")

        print(f"✅ Data bersih tersimpan di: {cleaned_path}")
        print("\n📁 Isi folder output:")
        print(os.listdir(output_dir))

        # 🔁 Setelah cleaning, langsung analisis sentimen & emosi
        success, labeled_path = analyze_sentiment_emotion(cleaned_path)
        if success:
            print(f"🎉 Analisis sentimen & emosi selesai → {labeled_path}")
            return True, labeled_path
        else:
            print("⚠️ Gagal melakukan analisis lanjutan!")
            return False, labeled_path
        
    except subprocess.CalledProcessError as e:
        return False, f"Gagal menjalankan tweet-harvest: {e}"



# =========================================================
# 🌐 ROUTES
# =========================================================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        auth_token = request.form.get("auth_token")
        keyword = request.form.get("keyword")
        since = request.form.get("since")
        until = request.form.get("until")
        limit = request.form.get("limit")

        if not all([auth_token, keyword, since, until, limit]):
            flash("❌ Semua field wajib diisi!", "error")
            return redirect(url_for("index"))

        try:
            limit = int(limit)
        except ValueError:
            flash("⚠️ Jumlah tweet harus berupa angka!", "error")
            return redirect(url_for("index"))

        success, message = scraping_tweets(keyword, since, until, auth_token, limit)
        if success:
            flash(f"✅ Scraping & preprocessing selesai! Data bersih di {message}", "success")
        else:
            flash(f"⚠️ Gagal memproses data: {message}", "error")

        return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/result")
def result():
    # Pastikan file hasil terakhir ada
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets-data", "output")
    csv_files = [f for f in os.listdir(output_dir) if f.endswith("_label.csv")]
    if not csv_files:
        flash("❌ Belum ada hasil analisis!", "error")
        return redirect(url_for("index"))

    latest_file = max([os.path.join(output_dir, f) for f in csv_files], key=os.path.getmtime)
    df = pd.read_csv(latest_file)

    # Hitung distribusi
    sentiment_counts = df["sentimen"].value_counts().to_dict()
    emotion_counts = df["emosi"].value_counts().to_dict()

    return render_template(
        "result.html",
        file_name=os.path.basename(latest_file),
        sentiment_counts=sentiment_counts,
        emotion_counts=emotion_counts,
    )


# =========================================================
# 🚀 RUN
# =========================================================
if __name__ == "__main__":
    print("📂 Current working directory:", os.getcwd())
    print("📄 File path:", os.path.abspath(__file__))
    app.run(debug=True)

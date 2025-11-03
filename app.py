from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
import time
from collections import Counter
from wordcloud import WordCloud

from utils.scraping import scraping_tweets

app = Flask(__name__)
app.secret_key = "secret123"

# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    """Menampilkan landing page (Home)"""
    return render_template("index.html")

@app.route("/analisis", methods=["GET", "POST"])
def analisis():
    """Menampilkan dan memproses form analisis"""
    if request.method == "POST":
        auth_token = request.form.get("auth_token")
        keyword = request.form.get("keyword")
        since = request.form.get("since")
        until = request.form.get("until")
        limit = request.form.get("limit")

        if not all([auth_token, keyword, since, until, limit]):
            flash("❌ Semua field wajib diisi!", "error")
            return redirect(url_for("analisis"))

        try:
            limit = int(limit)
        except ValueError:
            flash("⚠️ Jumlah tweet harus berupa angka!", "error")
            return redirect(url_for("analisis"))

        success, message = scraping_tweets(keyword, since, until, auth_token, limit)
        
        if success:
            return redirect(url_for("result"))
        else:
            flash(f"⚠️ Gagal memproses data: {message}", "error")
            return redirect(url_for("analisis"))

    return render_template("analisis.html")


@app.route("/result")
def result():
    """Menampilkan halaman visualisasi hasil (DENGAN JUMLAH TWEET)"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets-data", "output")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    csv_files = [f for f in os.listdir(output_dir) if f.endswith("_label.csv")]
    if not csv_files:
        flash("❌ Belum ada hasil analisis!", "error")
        return redirect(url_for("analisis"))

    latest_file = max([os.path.join(output_dir, f) for f in csv_files], key=os.path.getmtime)
    df = pd.read_csv(latest_file)

    tweet_count = len(df)

    sentiment_counts = df["sentimen"].value_counts().to_dict()
    emotion_counts = df["emosi"].value_counts().to_dict()

    file_basename = os.path.basename(latest_file)
    keyword = file_basename.replace("_label.csv", "").replace("_", " ")

    all_text = " ".join(df["text"].fillna("").dropna())
    word_counts = Counter(all_text.split()).most_common(50) 
    word_counts_dict = {word: count for word, count in word_counts if word != ""}
    
    wordcloud_url_for_template = None
    if word_counts_dict:
        try:
            wordcloud_save_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "static", "assets", "wordcloud.png"
            )
            os.makedirs(os.path.dirname(wordcloud_save_path), exist_ok=True)

            wc = WordCloud(
                width=800, 
                height=400, 
                background_color='#fbebee', 
                colormap='magma',
                max_words=50
            ).generate_from_frequencies(word_counts_dict)
            
            wc.to_file(wordcloud_save_path)
            
            wordcloud_url_for_template = "assets/wordcloud.png"

        except Exception as e:
            print(f"❌ Error saat membuat word cloud: {e}")

    return render_template(
        "result.html",
        file_name=file_basename,
        sentiment_counts=sentiment_counts,
        emotion_counts=emotion_counts,
        keyword=keyword, 
        wordcloud_url=wordcloud_url_for_template,
        tweet_count=tweet_count
    )

@app.route("/tutorial")
def tutorial():
    """Menampilkan halaman tutorial"""
    return render_template("tutorial.html")

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    print("📂 Current working directory:", os.getcwd())
    print("📄 File path:", os.path.abspath(__file__))
    app.run(debug=True)
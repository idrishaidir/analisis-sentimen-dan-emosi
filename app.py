from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import pandas as pd
import time
import datetime 
from collections import Counter
from wordcloud import WordCloud
from utils.scraping import scraping_tweets

app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analisis", methods=["GET", "POST"])
def analisis():
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
            if 'history' not in session:
                session['history'] = []
            
            safe_keyword = keyword.replace(" ", "_")
            file_name = f"{safe_keyword}_label.csv"
            current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
            
            history_item = {
                'keyword': keyword,
                'date': current_time,
                'file': file_name,
                'limit': limit
            }

            session['history'] = [h for h in session['history'] if h['keyword'] != keyword]
            session['history'].insert(0, history_item)
            session.modified = True

            return redirect(url_for("result", file=file_name))
        else:
            flash(f"⚠️ Gagal memproses data: {message}", "error")
            return redirect(url_for("analisis"))

    return render_template("analisis.html")


@app.route("/result")
def result():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets-data", "output")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    requested_file = request.args.get('file')
    
    if requested_file:
        target_file = os.path.join(output_dir, requested_file)
    else:
        csv_files = [f for f in os.listdir(output_dir) if f.endswith("_label.csv")]
        if not csv_files:
            flash("❌ Belum ada hasil analisis!", "error")
            return redirect(url_for("analisis"))
        target_file = max([os.path.join(output_dir, f) for f in csv_files], key=os.path.getmtime)

    if not os.path.exists(target_file):
        flash("❌ File analisis tidak ditemukan (mungkin sudah dihapus).", "error")
        return redirect(url_for("analisis"))

    try:
        df = pd.read_csv(target_file)
    except Exception as e:
        flash(f"❌ Gagal membaca file: {e}", "error")
        return redirect(url_for("analisis"))

    tweet_count = len(df)
    sentiment_counts = df["sentimen"].value_counts().to_dict()
    emotion_counts = df["emosi"].value_counts().to_dict()

    file_basename = os.path.basename(target_file)
    keyword = file_basename.replace("_label.csv", "").replace("_", " ")

    all_text = " ".join(df["text"].fillna("").dropna().astype(str))
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
                width=800, height=400, background_color='#fbebee', 
                colormap='magma', max_words=50
            ).generate_from_frequencies(word_counts_dict)
            
            wc.to_file(wordcloud_save_path)
            wordcloud_url_for_template = "assets/wordcloud.png"

        except Exception as e:
            print(f"❌ Error saat membuat word cloud: {e}")

    if 'full_text' not in df.columns:
        df['full_text'] = df['text'] 
    
    tweets_data = df.to_dict(orient='records')

    return render_template(
        "result.html",
        file_name=file_basename,
        sentiment_counts=sentiment_counts,
        emotion_counts=emotion_counts,
        keyword=keyword, 
        wordcloud_url=wordcloud_url_for_template,
        tweet_count=tweet_count,
        tweets=tweets_data
    )

@app.route("/history")
def history():
    history_data = session.get('history', [])
    return render_template("history.html", history=history_data)

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

if __name__ == "__main__":
    print("📂 Current working directory:", os.getcwd())
    print("📄 File path:", os.path.abspath(__file__))
    app.run(debug=True)
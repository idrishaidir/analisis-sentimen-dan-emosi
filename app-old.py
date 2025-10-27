from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import os

import pandas as pd
import re,string
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory




app = Flask(__name__)
app.secret_key = "secret123"  # Untuk flash message

# Fungsi scraping tweet
def scraping_tweets(keyword, since, until, auth_token, limit=100, filename=None):
    # Dapatkan base directory proyek
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Buat folder output absolut
    output_dir = os.path.join(base_dir, "tweets-data", "output")
    os.makedirs(output_dir, exist_ok=True)

    # File output hanya nama file saja, tanpa path tweets-data
    output_filename = f"{keyword}.csv"
    output_path = os.path.join(output_dir, output_filename)

    # Query pencarian tweet
    search_query = f'{keyword} since:{since} until:{until} lang:id'

    # Path ke npx (Windows)
    npx_path = r"C:\Program Files\nodejs\npx.cmd"

    # Perintah scraping
    command = [
        npx_path,
        "-y",
        "tweet-harvest@2.6.1",
        "-o", output_filename,  # hanya nama file, bukan path penuh
        "-s", search_query,
        "--tab", "LATEST",
        "-l", str(limit),
        "--token", auth_token
    ]

    print("🚀 Menjalankan:", " ".join(command))

    try:
        # Jalankan di folder output supaya file disimpan di situ
        subprocess.run(command, check=True, cwd=output_dir)
        return True, output_path
    except subprocess.CalledProcessError as e:
        return False, str(e)




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

        # Pastikan limit berupa angka
        try:
            limit = int(limit)
        except ValueError:
            flash("⚠️ Jumlah tweet harus berupa angka!", "error")
            return redirect(url_for("index"))

        success, message = scraping_tweets(keyword, since, until, auth_token, limit)

        if success:
            flash(f"✅ Scraping selesai! Data tersimpan di {message}", "success")
        else:
            flash(f"⚠️ Gagal scraping: {message}", "error")

        return redirect(url_for("index"))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)

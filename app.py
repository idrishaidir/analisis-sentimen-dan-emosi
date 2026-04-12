from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import pandas as pd
import time
import datetime 
from collections import Counter
from wordcloud import WordCloud
from utils.scraping import scraping_tweets
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from datetime import datetime
from flask_mail import Mail, Message
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "secret123"

# verifikasi email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'email-lau-@gmail.com'
app.config['MAIL_PASSWORD'] = 'mikir-kids'
mail = Mail(app)

# Inisialisasi Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/moodify_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Tabel Users
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), nullable=True)
    histories = db.relationship('AnalysisHistory', backref='owner', lazy=True)

# Tabel Analysis History
class AnalysisHistory(db.Model):
    __tablename__ = 'analysis_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    keyword = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    tweet_count = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Cek apakah email sudah terdaftar
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("❌ Email sudah digunakan!", "error")
            return redirect(url_for("register"))

        # Buat token verifikasi unik
        token = secrets.token_hex(16)
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(
            username=username,
            email=email,
            password=hashed_pw,
            verification_token=token,
            is_verified=False
        )
        
        db.session.add(new_user)
        db.session.commit()

        # Kirim Email Verifikasi
        msg = Message('Verifikasi Akun moodify', sender='noreply@moodify.com', recipients=[email])
        link = url_for('verify_email', token=token, _external=True)
        msg.body = f'Halo {username}, silakan klik link berikut untuk verifikasi akun kamu: {link}'
        mail.send(msg)

        flash("✅ Registrasi berhasil! Silakan cek email kamu untuk verifikasi.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None # Hapus token setelah digunakan
        db.session.commit()
        flash("🎉 Email berhasil diverifikasi! Silakan login.", "success")
    else:
        flash("⚠️ Token verifikasi tidak valid atau sudah kadaluarsa.", "error")
    return redirect(url_for("login"))

# Inisialisasi Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Mengarahkan user ke route login jika belum terautentikasi

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    # Jika user sudah login, arahkan langsung ke halaman analisis
    if current_user.is_authenticated:
        return redirect(url_for('analisis'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False

        # 1. Cari user berdasarkan email
        user = User.query.filter_by(email=email).first()

        # 2. Validasi keberadaan user dan kecocokan password
        if not user or not check_password_hash(user.password, password):
            flash("❌ Email atau password salah!", "error")
            return redirect(url_for("login"))

        # 3. Cek apakah email sudah diverifikasi
        if not user.is_verified:
            flash("⚠️ Akun kamu belum diverifikasi. Silakan cek email kamu!", "error")
            return redirect(url_for("login"))

        # 4. Login berhasil
        login_user(user, remember=remember)
        flash(f"👋 Selamat datang kembali, {user.username}!", "success")
        
        # Arahkan ke halaman yang sebelumnya ingin diakses (next page) atau ke analisis
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('analisis'))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("✅ Kamu telah berhasil keluar.", "success")
    return redirect(url_for("index"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analisis", methods=["GET", "POST"])
@login_required
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
            # Simpan riwayat ke MySQL secara permanen
            new_record = AnalysisHistory(
                user_id=current_user.id, # Ambil ID dari user yang sedang login
                keyword=keyword,
                filename=file_name,
                tweet_count=int(limit)
            )
            db.session.add(new_record)
            db.session.commit()
            
            return redirect(url_for("result", file=file_name))
        
        else:
            flash(f"⚠️ Gagal memproses data: {message}", "error")
            return redirect(url_for("analisis"))

    return render_template("analisis.html")


@app.route("/result")
@login_required
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
@login_required
def history():
    # Ambil data dari database berdasarkan user yang sedang login
    user_history = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(AnalysisHistory.date_created.desc()).all()
    return render_template("history.html", history=user_history)

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

if __name__ == "__main__":
    print("📂 Current working directory:", os.getcwd())
    print("📄 File path:", os.path.abspath(__file__))
    app.run(debug=True)
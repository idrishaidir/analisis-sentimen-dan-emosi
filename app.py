from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import pandas as pd
import time
from collections import Counter
from wordcloud import WordCloud
from utils.scraping import scraping_tweets
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kentang@gmail.com'
app.config['MAIL_PASSWORD'] = 'taruh_password_disini'
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/moodify_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    histories = db.relationship('AnalysisHistory', backref='owner', lazy=True)

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
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("❌ Email sudah digunakan!", "error")
            return redirect(url_for("register"))

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

        msg = Message('hallo! verifikasi akun moodify kamu yuk ✨', 
                    sender='noreply@moodify.com', 
                    recipients=[email])

        link = url_for('verify_email', token=token, _external=True)

        msg.html = f"""
        <div style="font-family: 'Poppins', Arial, sans-serif; background-color: #F3EFE6; padding: 40px 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; border: 1px solid #B0B5C1; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(45, 50, 80, 0.05);">
                
                <div style="background-color: #2D3250; padding: 30px; text-align: center;">
                    <h1 style="font-family: 'Playfair Display', Georgia, serif; color: #F3EFE6; margin: 0; font-size: 28px; font-weight: 700;">moodify</h1>
                </div>
                
                <div style="padding: 40px 30px; color: #2D3250; line-height: 1.6;">
                    <p style="font-size: 18px; font-weight: 600;">Hii, {username}! 👋</p>
                    <p>Makasih banyak ya udah mau mampir dan join di <b>moodify</b>. Kita seneng banget kamu ada di sini!</p>
                    <p>Biar akun kamu makin <i>gacor</i> dan semua fitur analisisnya kebuka, tolong verifikasi email kamu dulu ya. Lowkey excited banget nih nungguin kamu mulai analisis emosi publik bareng kita. 🫶</p>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{link}" style="background-color: #2D3250; color: #F3EFE6; padding: 15px 30px; text-decoration: none; border-radius: 30px; font-weight: 600; display: inline-block;">
                            Gas, Verifikasi Akun! 🚀
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">Kalau tombolnya nggak jalan, kamu bisa copas link ini ke browser ya:<br>
                    <a href="{link}" style="color: #2D3250; font-weight: 600; word-break: break-all;">{link}</a></p>
                    
                    <hr style="border: 0; border-top: 1px solid #B0B5C1; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #888; text-align: center; margin: 0;">
                        dikirim dengan penuh kasih sayang oleh tim moodify 🕊️<br>
                        &copy; 2026 moodify, Inc.
                    </p>
                </div>
            </div>
        </div>
        """
        mail.send(msg)

        flash("✅ Registrasi berhasil! Silakan cek email kamu untuk verifikasi.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None 
        db.session.commit()
        flash("🎉 Email berhasil diverifikasi! Silakan login.", "success")
    else:
        flash("⚠️ Token verifikasi tidak valid atau sudah kadaluarsa.", "error")
    return redirect(url_for("login"))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

@app.before_request
def make_session_permanent():
    session.permanent = True

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('analisis'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("❌ Email atau password salah!", "error")
            return redirect(url_for("login"))

        if not user.is_verified:
            flash("⚠️ Akun kamu belum diverifikasi. Silakan cek email kamu!", "error")
            return redirect(url_for("login"))

        login_user(user, remember=remember)
        flash(f"👋 Selamat datang kembali, {user.username}!", "success")
        
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
            safe_keyword = keyword.replace(" ", "_")
            file_name = f"{safe_keyword}_label.csv"
            
            new_record = AnalysisHistory(
                user_id=current_user.id, 
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
    user_history = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(AnalysisHistory.date_created.desc()).all()
    return render_template("history.html", history=user_history)

@app.route("/delete_history/<int:history_id>", methods=["POST"])
@login_required
def delete_history(history_id):
    history_record = AnalysisHistory.query.get_or_404(history_id)
    
    if history_record.user_id != current_user.id:
        flash("❌ Kamu tidak memiliki izin untuk menghapus riwayat ini.", "error")
        return redirect(url_for("history"))
        
    try:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets-data", "output")
        file_path = os.path.join(output_dir, history_record.filename)
        
        if os.path.exists(file_path):
            os.remove(file_path) 
        
        db.session.delete(history_record)
        db.session.commit()
        
        flash(f"✅ Riwayat analisis '{history_record.keyword}' berhasil dihapus secara permanen.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Gagal menghapus riwayat: {e}", "error")
        
    return redirect(url_for("history"))

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

if __name__ == "__main__":
    print("📂 Current working directory:", os.getcwd())
    print("📄 File path:", os.path.abspath(__file__))
    app.run(debug=True)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("❌ Email tidak terdaftar dalam sistem!", "error")
            return redirect(url_for("forgot_password"))

        token = secrets.token_hex(16)
        user.reset_token = token
        db.session.commit()

        msg = Message('Reset password akun moodify kamu 🗝️', 
                    sender='noreply@moodify.com', 
                    recipients=[email])

        link = url_for('reset_password', token=token, _external=True)

        msg.html = f"""
        <div style="font-family: 'Poppins', Arial, sans-serif; background-color: #F3EFE6; padding: 40px 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; border: 1px solid #B0B5C1; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(45, 50, 80, 0.05);">
                
                <div style="background-color: #2D3250; padding: 30px; text-align: center;">
                    <h1 style="font-family: 'Playfair Display', Georgia, serif; color: #F3EFE6; margin: 0; font-size: 28px; font-weight: 700;">moodify</h1>
                </div>
                
                <div style="padding: 40px 30px; color: #2D3250; line-height: 1.6;">
                    <p style="font-size: 18px; font-weight: 600;">Hii, {user.username}! 👋</p>
                    <p>Ada permintaan untuk mereset password akun <b>moodify</b> kamu nih. Kalau ini memang kamu, silakan klik tombol di bawah untuk membuat password baru ya.</p>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{link}" style="background-color: #2D3250; color: #F3EFE6; padding: 15px 30px; text-decoration: none; border-radius: 30px; font-weight: 600; display: inline-block;">
                            Atur Ulang Password 🛠️
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">Kalau kamu merasa tidak meminta ini, abaikan saja email ini ya. Keamanan akunmu lowkey tetap aman kok. 😉</p>
                    <p style="font-size: 14px; color: #666;">Atau copas link ini ke browser:<br>
                    <a href="{link}" style="color: #2D3250; font-weight: 600; word-break: break-all;">{link}</a></p>
                    
                    <hr style="border: 0; border-top: 1px solid #B0B5C1; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #888; text-align: center; margin: 0;">
                        dikirim oleh tim moodify dengan penuh perhatian 🕊️<br>
                        &copy; 2026 moodify, Inc.
                    </p>
                </div>
            </div>
        </div>
        """
        mail.send(msg)

        flash("📧 Link reset password telah dikirim ke email kamu. Silakan periksa inbox/spam!", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        flash("⚠️ Token reset tidak valid atau sudah kadaluarsa.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        password_baru = request.form.get("password")
        
        hashed_pw = generate_password_hash(password_baru, method='pbkdf2:sha256')
        user.password = hashed_pw
        user.reset_token = None 
        db.session.commit()

        flash("🎉 Password berhasil diperbarui! Silakan login dengan password baru.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)
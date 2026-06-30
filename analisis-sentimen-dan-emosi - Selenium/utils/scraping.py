import os
import time
import pandas as pd
import re
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .preprocessing import preprocessText
from .models import predict_sentimen, predict_emosi

def analyze_sentiment_emotion(cleaned_path):
    try:
        print(f"🔍 Membaca file: {cleaned_path}")
        df = pd.read_csv(cleaned_path)
        if "text" not in df.columns:
            return False, "Kolom 'text' tidak ditemukan!"

        df["text"] = df["text"].fillna("")

        print("⚙️ Melakukan prediksi sentimen & emosi...")
        df["sentimen"] = df["text"].apply(predict_sentimen)
        df["emosi"] = df["text"].apply(predict_emosi)

        labeled_path = cleaned_path.replace("_cleaned.csv", "_label.csv")
        df.to_csv(labeled_path, index=False, encoding="utf-8")
        
        print(f"✅ Hasil tersimpan di: {labeled_path}")
        return True, labeled_path
    except Exception as e:
        return False, f"Error saat analisis: {e}"


def scraping_tweets(keyword, limit=100, chrome_profile_path=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    output_dir = os.path.join(base_dir, "tweets-data", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    
    print("\n\n🚀 Menginisiasi Selenium WebDriver...")
    # Konfigurasi Chrome untuk mengurangi deteksi otomatisasi
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    if chrome_profile_path:
        options.add_argument(f"--user-data-dir={chrome_profile_path}")
        # Gunakan profile Chrome yang sudah login agar browser nyata dipakai
        options.add_argument('--profile-directory=Default')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--lang=en-US,en')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option('prefs', {
        'credentials_enable_service': False,
        'profile.password_manager_enabled': False,
        'intl.accept_languages': 'en-US,en'
    })
    options.add_argument('--log-level=3') # Sembunyikan log warning dari console

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)

        # Sembunyikan properti webdriver dari deteksi
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.navigator.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: (parameters) => (
                                parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                Promise.resolve({ state: 'denied' })
                            )
                        })
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                '''
            })
        except Exception:
            pass

        print("\n🔐 Membuka halaman login X...")
        driver.get("https://x.com/i/flow/login")
        
        # --- LOGIN MANUAL ---
        print("\n" + "!"*50)
        print("⚠️ HARAP LOGIN SECARA MANUAL DI BROWSER YANG TERBUKA.")
        print("!"*50 + "\n")

        print("⏳ Menunggu pengguna login via browser...")
        
        try:
            WebDriverWait(driver, 300).until(
                EC.url_contains("x.com/home")
            )
            print("✅ Login otomatis terdeteksi! Melanjutkan proses scraping...")
            
            import time
            time.sleep(3) 
            
        except TimeoutException:
            print("❌ Waktu login habis (lebih dari 5 menit).")
            driver.quit()
            return False, "Waktu login habis. Silakan coba lagi."
        
        print("✅ Melanjutkan proses scraping...")
        
        search_query = f"{keyword}"
        print(f"🔍 Mencari tweet: {search_query}")
        
        encoded_query = urllib.parse.quote_plus(search_query)
        search_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
        driver.get(search_url)

        limit = int(limit)

        def scrape_current_page():
            page_tweets = []
            seen = set()
            scroll_attempts = 0

            while len(page_tweets) < limit and scroll_attempts < 15:
                time.sleep(3)
                articles = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')

                new_tweets_found = 0
                for article in articles:
                    if len(page_tweets) >= limit:
                        break

                    try:
                        text_elem = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                        tweet_text = text_elem.text.strip()

                        if not tweet_text or tweet_text in seen:
                            continue

                        user_elem = article.find_element(By.XPATH, './/div[@data-testid="User-Name"]')
                        username_text = user_elem.text.split('\n')[0] if '\n' in user_elem.text else "Unknown"

                        try:
                            time_elem = article.find_element(By.XPATH, './/time')
                            created_at = time_elem.get_attribute("datetime")
                        except:
                            created_at = "Unknown Date"

                        page_tweets.append({
                            "created_at": created_at,
                            "username": username_text,
                            "full_text": tweet_text
                        })
                        seen.add(tweet_text)
                        new_tweets_found += 1
                    except Exception:
                        continue

                if new_tweets_found == 0:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            return page_tweets

        print("⏳ Mulai mengumpulkan data... (Proses ini mungkin memakan waktu)")
        tweets_data = scrape_current_page()

        if not tweets_data:
            print("⚠️ Tidak ada hasil dengan filter tanggal. Mencoba ulang tanpa since/until...")
            search_query = f"{keyword} lang:id"
            encoded_query = urllib.parse.quote_plus(search_query)
            fallback_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
            driver.get(fallback_url)
            tweets_data = scrape_current_page()

        if not tweets_data:
            return False, "Tidak ada tweet yang ditemukan untuk periode tersebut atau bot dicegat oleh X."
            
        print(f"✅ Berhasil mengambil {len(tweets_data)} tweet menggunakan Selenium.")
        
        # 8. Konversi ke DataFrame dan Preprocessing
        df = pd.DataFrame(tweets_data)
        
        print("⚙️ Preprocessing teks...")
        df["text"] = df["full_text"].apply(preprocessText)
        
        cleaned_path = os.path.join(output_dir, f"{safe_keyword}_cleaned.csv")
        df.to_csv(cleaned_path, index=False, encoding="utf-8")
        
        # 9. Lanjut ke Model AI
        return analyze_sentiment_emotion(cleaned_path)
        
    except TimeoutException:
        return False, "Gagal/Timeout saat login. Pastikan kredensial benar dan internet stabil."
    except Exception as e:
        return False, f"Terjadi kesalahan pada Selenium: {e}"
    finally:
        # PENTING: Tutup browser agar memori RAM tidak penuh
        if driver is not None:
            driver.quit()
        print("🛑 Browser Selenium ditutup.")
import os
import time
import pandas as pd
import re
import urllib.parse
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .preprocessing import preprocessText
from .models import predict_sentimen, predict_emosi

def save_cookies(driver, filename="session_state.bin"):
    """Save browser session state to file for reuse"""
    try:
        cookies_dir = "cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        cookie_path = os.path.join(cookies_dir, filename)
        
        with open(cookie_path, "wb") as file:
            pickle.dump(driver.get_cookies(), file)
        print(f"✅ Cookies saved to {cookie_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to save cookies: {e}")
        return False

import base64

def load_cookies(driver, filename="session_state.bin"):
    """Load browser session state from file or Environment Variable"""
    try:
        cookies_dir = "cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        cookie_path = os.path.join(cookies_dir, filename)
        
        # Cek apakah ada cookie dari Environment Variable (Render Production)
        env_cookie = os.getenv("TWITTER_COOKIES_B64")
        if env_cookie:
            print("🚀 Mendekode cookies rahasia dari Environment Variable...")
            try:
                cookie_bytes = base64.b64decode(env_cookie)
                with open(cookie_path, "wb") as file:
                    file.write(cookie_bytes)
            except Exception as e:
                print(f"⚠️ Gagal mendekode cookies dari ENV: {e}")
        
        if not os.path.exists(cookie_path):
            print(f"⚠️ No saved cookies found at {cookie_path}")
            return False
            
        with open(cookie_path, "rb") as file:
            cookies = pickle.load(file)
            
        # Add saved cookies to current session
        for cookie in cookies:
            try:
                # Add domain to cookie if missing
                if 'domain' not in cookie:
                    cookie['domain'] = '.x.com'
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ Cookie warning: {e}")
                
        return True
    except Exception as e:
        print(f"❌ Failed to load cookies: {e}")
        return False

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


def scraping_tweets(keyword, limit=50, chrome_profile_path=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    output_dir = os.path.join(base_dir, "tweets-data", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    
    print("🚀 Menginisiasi Selenium WebDriver...")
    
    # Detect production vs local environment
    is_production = os.getenv('ENVIRONMENT') == 'production'
    
    options = uc.ChromeOptions()
    
    # Production (Render server) configuration
    if is_production:
        print("💻 Running in PRODUCTION mode (headless)")
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # Ekstra optimasi memori untuk Render (Free Tier 512MB)
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--window-size=800,600')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--js-flags="--max-old-space-size=128"')
        chrome_profile_path = None  # Don't use profile in production
    else:
        print("💻 Running in LOCAL development mode")
        # Tidak lagi menggunakan --user-data-dir karena kita sudah memakai cookies pickle (session_state.bin)
        # Hal ini mencegah crash "DevToolsActivePort" jika folder profile terkunci.
    
    # Common options untuk production & local
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = None
    try:
        driver = uc.Chrome(options=options)
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
        time.sleep(3)
        
        # Try to load saved cookies first
        cookies_loaded = load_cookies(driver, "session_state.bin")
        
        if cookies_loaded:
            print("🚀 Cookies loaded! Checking if still logged in...")
            time.sleep(2)
            
            # Refresh to let cookies take effect
            driver.refresh()
            time.sleep(3)
            
            # Check if login was successful using cookies
            try:
                # Look for an element that only appears when logged in
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='AppTabBar_Home_Link']"))
                )
                print("✅ Login berhasil menggunakan saved cookies!")
            except TimeoutException:
                print("⚠️ Cookies expired atau invalid. Need manual login.")
                cookies_loaded = False
                driver.get("https://x.com/i/flow/login")
                time.sleep(2)
        
        # If cookies tidak ada atau expired, manual login
        if not cookies_loaded:
            print("\n" + "!"*50)
            print("🚨 HARAP LOGIN SECARA MANUAL DI BROWSER YANG TERBUKA.")
            print("🚨 Login ini hanya perlu dilakukan SEKALI.")
            print("🚨 Script akan menunggu maksimal 5 menit...")
            print("!"*50 + "\n")
            
            try:
                # Tunggu sampai elemen 'Home' atau indikator login sukses muncul (max 5 menit)
                WebDriverWait(driver, 300).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='AppTabBar_Home_Link']"))
                )
                print("✅ Login manual berhasil!")
                
                # Save cookies for next time
                save_cookies(driver, "session_state.bin")
                print("💾 Cookies disimpan untuk session berikutnya.")
                
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
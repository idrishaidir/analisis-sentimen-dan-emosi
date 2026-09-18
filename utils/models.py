import os
import time
import requests
import socket
import urllib3.util.connection as urllib3_cn

# HACK: Paksa Requests (urllib3) untuk selalu menggunakan IPv4
# Render sering mengalami bug DNS IPv6 ([Errno -5] No address associated with hostname) pada image linux-slim
def allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = allowed_gai_family

print("Loading models configuration via HF Inference API...")
sentiment_model_name = "Ha1dir/sentimen-indobert"
emotion_model_name = "Ha1dir/emosi-indobert"

HF_TOKEN = os.getenv("HF_TOKEN")
# Hugging Face recently deprecated the api-inference domain. Migrated to router.huggingface.co
API_URL_SEN = f"https://router.huggingface.co/hf-inference/models/{sentiment_model_name}"
API_URL_EMO = f"https://router.huggingface.co/hf-inference/models/{emotion_model_name}"

def query_hf_api(url, payload, retries=3):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            
            # Deteksi jika limit habis (429 Too Many Requests)
            if response.status_code == 429:
                raise ValueError("Limit kuota AI Hugging Face telah habis. Silakan tunggu sekitar 1 jam lagi.")
                
            result = response.json()
            
            # Jika model sedang loading/dipanaskan (cold start), tunggu sesuai estimated_time
            if isinstance(result, dict) and "estimated_time" in result:
                wait_time = result["estimated_time"]
                print(f"Model di server HF sedang dipanaskan, menunggu {wait_time} detik...")
                time.sleep(min(wait_time, 15))
                continue
                
            return result
        except ValueError as ve:
            # Jika errornya karena limit, langsung lempar ke atas agar proses scraping berhenti
            raise ve
        except Exception as e:
            print(f"Error calling HF API: {e}")
            time.sleep(2)
    return None

def predict_sentimen(text):
    if not text or text.strip() == "":
        return "Netral"
    
    sentiment_labels = ["Positif", "Negatif", "Netral"]
    result = query_hf_api(API_URL_SEN, {"inputs": text})
    
    if result is None:
        return "Netral"
    
    try:
        # Expected format: [[{"label": "LABEL_0", "score": 0.99}, ...]]
        predictions = result[0]
        best_pred = max(predictions, key=lambda x: x.get("score", 0.0))
        label_str = best_pred.get("label", "LABEL_2")
        
        if label_str.isdigit():
            label_id = int(label_str)
        elif "LABEL_" in label_str:
            label_id = int(label_str.replace("LABEL_", ""))
        else:
            for label in sentiment_labels:
                if label.lower() == label_str.lower():
                    return label
            return "Netral"
            
        return sentiment_labels[label_id]
    except Exception as e:
        print("Gagal mem-parsing hasil sentimen:", e)
        return "Netral"

def predict_emosi(text):
    if not text or text.strip() == "":
        return "Netral"
        
    emotion_labels = ["Marah", "Takut", "Sedih", "Senang", "Cinta", "Netral"]
    result = query_hf_api(API_URL_EMO, {"inputs": text})
    
    if result is None:
        return "Netral"
    
    try:
        predictions = result[0]
        best_pred = max(predictions, key=lambda x: x.get("score", 0.0))
        label_str = best_pred.get("label", "LABEL_5")
        
        if label_str.isdigit():
            label_id = int(label_str)
        elif "LABEL_" in label_str:
            label_id = int(label_str.replace("LABEL_", ""))
        else:
            for label in emotion_labels:
                if label.lower() == label_str.lower():
                    return label
            return "Netral"
            
        return emotion_labels[label_id]
    except Exception as e:
        print("Gagal mem-parsing hasil emosi:", e)
        return "Netral"
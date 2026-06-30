import re, string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
import pandas as pd
import os           

for pkg in ['punkt_tab', 'stopwords']:
    try:
        nltk.data.find(f'tokenizers/{pkg}' if pkg == 'punkt_tab' else f'corpora/{pkg}')
    except LookupError:
        nltk.download(pkg)

# --- Memuat kamus_gaul.csv ---
def load_kamus():
    """Membaca kamus_gaul.csv dari direktori root proyek."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kamus_path = os.path.join(base_dir, "kamus_gaul.csv")
    
    if os.path.exists(kamus_path):
        print(f"🔍 Menemukan {kamus_path}. Memuat kamus...")
        try:  
            df_kamus = pd.read_csv(
                kamus_path, 
                sep=';',        
                header=None,    
                names=['kata', 'arti']
            )

            if not df_kamus.empty:
                kamus_dict = pd.Series(df_kamus.arti.values, index=df_kamus.kata).to_dict()
                print("✅ Kamus normalisasi (sep=';') berhasil dimuat.")
                return kamus_dict
            else:
                print("⚠️ Peringatan: kamus_gaul.csv kosong. Kamus tidak dimuat.")
                return {}
        except Exception as e:
            print(f"❌ Error saat memuat kamus_gaul.csv: {e}")
            return {}
    else:
        print(f"ℹ️ Info: File kamus_gaul.csv tidak ditemukan di {kamus_path}. Langkah normalisasi akan dilewati.")
        return {}


kamus_dict = load_kamus()


def normalize(text, kamus):
    if not kamus:
        return text
    tokens_kamus = text.split()
    tokens_normalized_kamus = [kamus.get(token, token) for token in tokens_kamus]
    return ' '.join(tokens_normalized_kamus)

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
    text = text.lower()
    text = re.sub(r"http\S+|www.\S+", "", text)
    text = re.sub(r"@\w+|#", "", text)
    text = re.sub(r"\d+", "", text)
    
    text = normalize(text, kamus_dict)
    
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip()
    
    tokens = tokenizingText(text)
    tokens = filteringText(tokens)
    tokens = stemmingText(tokens)
    
    return toSentence(tokens)
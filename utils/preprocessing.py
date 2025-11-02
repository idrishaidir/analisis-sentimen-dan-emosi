import re, string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Download NLTK data if not present
for pkg in ['punkt_tab', 'stopwords']:
    try:
        nltk.data.find(f'tokenizers/{pkg}' if pkg == 'punkt_tab' else f'corpora/{pkg}')
    except LookupError:
        nltk.download(pkg)

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
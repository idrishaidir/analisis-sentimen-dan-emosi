import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

print("🔍 Loading models...")
sentiment_model_name = "w11wo/indonesian-roberta-base-sentiment-classifier"
emotion_model_name = "Atherizz/emolog-indobert"

# Load models and tokenizers once when this module is imported
tokenizer_sen = AutoTokenizer.from_pretrained(sentiment_model_name)
model_sen = AutoModelForSequenceClassification.from_pretrained(sentiment_model_name)
tokenizer_emo = AutoTokenizer.from_pretrained(emotion_model_name)
model_emo = AutoModelForSequenceClassification.from_pretrained(emotion_model_name)
print("✅ Models loaded successfully!")

def predict_sentimen(text):
    # FIX: Lewati model jika teks kosong
    if not text or text.strip() == "":
        return "neutral"
    
    inputs = tokenizer_sen(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model_sen(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_id = torch.argmax(probs, dim=1).item()
    
    sentiment_labels = ["negative", "neutral", "positive"]
    return sentiment_labels[label_id]


def predict_emosi(text):
    # FIX: Lewati model jika teks kosong
    if not text or text.strip() == "":
        return "Netral"
        
    inputs = tokenizer_emo(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model_emo(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_id = torch.argmax(probs, dim=1).item()
    
    emotion_labels = ["Senang", "Sedih", "Marah", " Takut", "Jijik", "Terkejut", "Netral"]
    return emotion_labels[label_id]
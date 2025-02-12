from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig
import torch
import numpy as np
from scipy.special import softmax

SAVE_DIR = "D:/AI-Agents/sentiment_model"  # Path to saved model

# Load locally saved model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(SAVE_DIR)
config = AutoConfig.from_pretrained(SAVE_DIR)
model = AutoModelForSequenceClassification.from_pretrained(SAVE_DIR)

# Define a preprocess function
def preprocess(text):
    new_text = []
    for t in text.split(" "):
        t = '@user' if t.startswith('@') and len(t) > 1 else t
        t = 'http' if t.startswith('http') else t
        new_text.append(t)
    return " ".join(new_text)

# Test with a sample text
text = "Bitcoin price is going up!"
text = preprocess(text)
encoded_input = tokenizer(text, return_tensors='pt')

# Get model prediction
with torch.no_grad():
    output = model(**encoded_input)

# Convert to probabilities
scores = output[0][0].numpy()
scores = softmax(scores)

# Get sentiment ranking
ranking = np.argsort(scores)[::-1]
for i in range(scores.shape[0]):
    label = config.id2label[ranking[i]]
    score = scores[ranking[i]]
    print(f"{i+1}) {label} {np.round(float(score), 4)}")
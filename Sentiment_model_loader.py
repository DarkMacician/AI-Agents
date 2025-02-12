from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig
import os

MODEL = f"cardiffnlp/twitter-roberta-base-sentiment-latest"
SAVE_DIR = "sentiment_model"  # Local directory to save the model

# Download and save the tokenizer & model
tokenizer = AutoTokenizer.from_pretrained(MODEL)
config = AutoConfig.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)

# Create directory if it doesn't exist
os.makedirs(SAVE_DIR, exist_ok=True)

# Save model and tokenizer locally
model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)
config.save_pretrained(SAVE_DIR)

print(f"Model saved to {SAVE_DIR}")
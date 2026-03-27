import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm
import os

# Find the CSV file
csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
print(f"Found CSV files: {csv_files}")

if not csv_files:
    print("No CSV file found in current directory")
    exit()

filename = csv_files[0]
print(f"\nUsing file: {filename}")

# Load BERTweet sentiment model
print("\nLoading BERTweet sentiment model...")
model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)
print(f"Using device: {device}")

# Load data
print("\nLoading tweets...")
df = pd.read_csv(filename)
print(f"Loaded {len(df)} tweets")
print(f"Columns: {df.columns.tolist()}")

# Function to analyze sentiment
def get_sentiment(text):
    if pd.isna(text) or not isinstance(text, str) or text.startswith('http'):
        return None, None
    
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
    
    labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
    return labels[pred], probs.cpu().numpy()[0]

# Analyze tweets
print("\nAnalyzing sentiment...")
results = []
for idx, row in tqdm(df.iterrows(), total=len(df)):
    text = row['text']
    sentiment, probs = get_sentiment(text)
    results.append({
        'text': text[:100] if text else '',
        'sentiment': sentiment,
        'neg_prob': probs[0] if probs is not None else None,
        'neu_prob': probs[1] if probs is not None else None,
        'pos_prob': probs[2] if probs is not None else None
    })

# Display results
result_df = pd.DataFrame(results)
print("\n" + "="*60)
print("SENTIMENT ANALYSIS RESULTS (First 10)")
print("="*60)
print(result_df[['text', 'sentiment']].head(10))

print("\n" + "="*60)
print("SENTIMENT DISTRIBUTION")
print("="*60)
print(result_df['sentiment'].value_counts())

# Save results
result_df.to_csv('tweet_sentiments_output.csv', index=False)
print("\n✓ Results saved to tweet_sentiments_output.csv")

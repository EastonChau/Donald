import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import pytesseract
import re
import time
from datetime import datetime
import os

# ==================================================
# CONFIGURATION SECTION
# ==================================================

INPUT_CSV = "realDonaldTrump_2025-01-01_to_2026-04-30_tweets.csv"
OUTPUT_CSV = "realDonaldTrump_2025-01-01_to_2026-04-30_tweets_with_ocr.csv"

TESSERACT_PATH = None  # Set to None for auto-detection, or provide full path

# Minimum confidence threshold (0-100) - only keep text with confidence above this
MIN_CONFIDENCE = 60

# Minimum meaningful text length to consider OCR result valid
MIN_TEXT_LENGTH = 3

# Words that indicate non-standard/meaningless text (to filter out)
MEANINGLESS_PATTERNS = [
    r'^[^\w\s]+$',  # Only punctuation/symbols
    r'^[\d\s]+$',   # Only numbers and spaces
    r'^\.+$',       # Only dots
    r'^_+$',        # Only underscores
    r'^[\W_]+$',    # Only non-word characters
    r'^\s*$',       # Empty or whitespace only
]

# ==================================================
# END OF CONFIGURATION
# ==================================================

def setup_tesseract():
    """Configure Tesseract OCR path if provided"""
    if TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        print(f"✅ Using Tesseract at: {TESSERACT_PATH}")
    else:
        print("✅ Using default Tesseract installation")

def download_image(url, max_retries=3):
    """Download image from URL with retry logic"""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            else:
                print(f"   ⚠️  Failed to download {url}: Status {response.status_code}")
                return None
        except Exception as e:
            print(f"   ⚠️  Attempt {attempt + 1} failed for {url}: {str(e)[:50]}")
            time.sleep(1)
    return None

def preprocess_image(image):
    """Preprocess image for better OCR results"""
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Resize if too small (improves OCR accuracy)
    width, height = image.size
    if width < 400 or height < 200:
        scale = max(400/width, 200/height)
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image

def extract_text_from_image(image_url):
    """Extract text from image URL using OCR"""
    if not image_url or pd.isna(image_url) or image_url == '':
        return None, None

    # Handle multiple image URLs (comma-separated)
    image_urls = [url.strip() for url in image_url.split(',')]

    all_ocr_text = []
    total_confidence = 0
    text_count = 0

    for url in image_urls:
        if not url:
            continue

        print(f"   📸 Processing image: {url[:60]}...")

        # Download image
        image = download_image(url)
        if image is None:
            continue

        try:
            # Preprocess image
            image = preprocess_image(image)

            # Perform OCR with confidence data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            # Extract text with confidence filtering
            extracted_texts = []
            confidences = []

            for i, conf in enumerate(ocr_data['conf']):
                if conf > MIN_CONFIDENCE:
                    text = ocr_data['text'][i].strip()
                    if len(text) > MIN_TEXT_LENGTH:
                        extracted_texts.append(text)
                        confidences.append(conf)

            if extracted_texts:
                combined_text = ' '.join(extracted_texts)
                avg_confidence = sum(confidences) / len(confidences)
                all_ocr_text.append(combined_text)
                total_confidence += avg_confidence
                text_count += 1
                print(f"   ✅ Extracted {len(extracted_texts)} text blocks (avg conf: {avg_confidence:.1f}%)")
            else:
                print(f"   ℹ️  No meaningful text found in image (below confidence threshold)")

        except Exception as e:
            print(f"   ❌ OCR failed: {str(e)[:100]}")
            continue

    if all_ocr_text:
        full_ocr_text = ' '.join(all_ocr_text)
        full_ocr_text = re.sub(r'\s+', ' ', full_ocr_text).strip()
        avg_confidence_all = total_confidence / text_count if text_count > 0 else 0
        return full_ocr_text, avg_confidence_all

    return None, None

def is_meaningful_ocr(ocr_text):
    """Check if OCR text is meaningful (not just noise)"""
    if not ocr_text or len(ocr_text) < MIN_TEXT_LENGTH:
        return False

    # Check against meaningless patterns
    for pattern in MEANINGLESS_PATTERNS:
        if re.match(pattern, ocr_text):
            return False

    # Check if text has at least 2 actual words (not just random characters)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', ocr_text)
    if len(words) < 2 and len(ocr_text) < 10:
        return False

    return True

def combine_tweet_and_ocr(tweet_text, ocr_text):
    """Combine tweet text and OCR text intelligently"""
    if not ocr_text:
        return tweet_text

    if not is_meaningful_ocr(ocr_text):
        return tweet_text

    # Clean both texts
    tweet_text = tweet_text.strip() if tweet_text else ''
    ocr_text = ocr_text.strip()

    # Remove any URL placeholders from OCR text
    ocr_text = re.sub(r'https?://\S+', '', ocr_text)
    ocr_text = re.sub(r'www\.\S+', '', ocr_text)
    ocr_text = re.sub(r'\s+', ' ', ocr_text).strip()

    if not ocr_text:
        return tweet_text

    # Check if OCR text is already in tweet text (avoid duplication)
    if ocr_text.lower() in tweet_text.lower():
        return tweet_text

    # Check if tweet text is very short (likely just a link or placeholder)
    if len(tweet_text) < 50 or tweet_text.startswith('https://'):
        return f"{ocr_text} [{tweet_text}]" if tweet_text and not tweet_text.startswith('https://') else ocr_text

    # Combine with separator
    return f"{tweet_text} [OCR: {ocr_text}]"

def process_tweets_with_ocr(input_file, output_file):
    """Main function to process tweets and add OCR text"""
    print("=" * 70)
    print("TWITTER IMAGE OCR PROCESSOR")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print("=" * 70)

    # Setup Tesseract
    setup_tesseract()

    # Read CSV
    print("\n📖 Reading CSV file...")
    df = pd.read_csv(input_file)
    print(f"✅ Loaded {len(df)} tweets")

    # Process each tweet
    print("\n🖼️  Processing images with OCR and combining text...")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"\n[{idx + 1}/{len(df)}] Tweet ID: {row['post_id']}")
        print(f"   Date: {row['date']} {row['time']} {row['timezone']}")

        # Get image URL
        image_url = row['image'] if pd.notna(row['image']) else ''

        ocr_text = None
        if image_url and image_url.strip():
            # Extract text from image
            ocr_text, confidence = extract_text_from_image(image_url)

            if ocr_text and is_meaningful_ocr(ocr_text):
                print(f"   📝 OCR Result: \"{ocr_text[:100]}{'...' if len(ocr_text) > 100 else ''}\"")
                print(f"   📊 Confidence: {confidence:.1f}%")
            else:
                print(f"   ℹ️  No meaningful text found in image")
                ocr_text = None
        else:
            print(f"   ℹ️  No image attached to this tweet")

        # Combine tweet text with OCR and update the 'text' column
        tweet_text = row['text'] if pd.notna(row['text']) else ''

        combined = combine_tweet_and_ocr(tweet_text, ocr_text)
        df.at[idx, 'text'] = combined  # Replace original text with combined version

        # Add delay to be respectful to image servers
        if image_url and image_url.strip():
            time.sleep(0.5)

    # Save to CSV (keeping original column structure, just with updated 'text' column)
    print("\n" + "=" * 70)
    print("💾 Saving results...")
    df.to_csv(output_file, index=False, encoding='utf-8')

    # Print statistics
    print(f"\n✅ OCR processing complete!")
    print(f"   Output saved to: {output_file}")

    # Count how many tweets had images and got OCR
    total_with_images = df[df['image'] != ''].shape[0]
    # Since we don't store OCR separately, we estimate by checking if text contains "[OCR:"
    successful_ocr = df[df['text'].str.contains('\[OCR:', na=False)].shape[0]

    print(f"\n📊 OCR Statistics:")
    print(f"   Total tweets with images: {total_with_images}")
    print(f"   Successful OCR extractions: {successful_ocr}")
    if total_with_images > 0:
        print(f"   Success rate: {successful_ocr/total_with_images*100:.1f}%")

    # Show sample of combined text
    print(f"\n📝 Sample of combined text (first 5 tweets with OCR):")
    sample = df[df['text'].str.contains('\[OCR:', na=False)].head(5)
    if len(sample) > 0:
        for idx, row in sample.iterrows():
            print(f"\n   Tweet ID: {row['post_id']}")
            print(f"   Combined: {row['text'][:150]}...")
    else:
        print("   No tweets with OCR text found in sample")

    return df

def main():
    try:
        # Process tweets
        result_df = process_tweets_with_ocr(INPUT_CSV, OUTPUT_CSV)

        print("\n" + "=" * 70)
        print("🎉 OCR PROCESSING COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    except FileNotFoundError:
        print(f"❌ Error: Could not find input file '{INPUT_CSV}'")
        print("   Please ensure the file exists in the current directory.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

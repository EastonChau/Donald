# ============================================================
# COMPREHENSIVE OCR PROCESSOR FOR TRUMP TWEETS
# ============================================================

# Install required libraries
!pip install pandas pillow pytesseract opencv-python-headless numpy
!apt-get install tesseract-ocr tesseract-ocr-eng -y

# Import libraries
import pandas as pd
import requests
import time
import os
import re
from datetime import datetime
from google.colab import files
import pytesseract
from PIL import Image
from io import BytesIO
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
class Config:
    # Image download settings
    DOWNLOAD_TIMEOUT = 15
    MAX_RETRIES = 2
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # OCR settings
    OCR_CONFIG = '--psm 6 -l eng'  # PSM 6 = assume uniform text block
    
    # Text detection settings
    MIN_TEXT_LENGTH = 5  # Minimum characters to consider as "text"
    MIN_TEXT_CONFIDENCE = 30  # Minimum confidence score (0-100)
    
    # Processing
    DELAY_BETWEEN_IMAGES = 0.5
    DELAY_BETWEEN_POSTS = 0.2

# ============================================================
# VIDEO DETECTION
# ============================================================
def is_video_url(url):
    """Detect if URL is a video"""
    if not url or pd.isna(url) or url == '':
        return False
    
    url_lower = str(url).lower()
    
    # Video extensions
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
    if any(url_lower.endswith(ext) for ext in video_extensions):
        return True
    
    # Video platforms
    video_patterns = [
        'youtube.com/watch', 'youtu.be/', 'vimeo.com/', 'tiktok.com/',
        'instagram.com/reel', 'instagram.com/tv', 'twitch.tv',
        'twitter.com/i/videos', '/video/', 'videos/'
    ]
    
    if any(pattern in url_lower for pattern in video_patterns):
        return True
    
    return False

# ============================================================
# IMAGE DOWNLOADER
# ============================================================
def download_image(url):
    """Download image from URL"""
    for attempt in range(Config.MAX_RETRIES):
        try:
            headers = {'User-Agent': Config.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=Config.DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'video' in content_type:
                return None, 'video'
            
            # Open image
            img = Image.open(BytesIO(response.content))
            return img, 'image'
            
        except Exception as e:
            if attempt == Config.MAX_RETRIES - 1:
                return None, f'error: {str(e)[:50]}'
            time.sleep(1)
    
    return None, 'download_failed'

# ============================================================
# TEXT DETECTION IN IMAGE
# ============================================================
def has_readable_text(img):
    """
    Detect if image contains readable text using multiple methods
    Returns: (has_text, extracted_text, confidence_score)
    """
    try:
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Perform OCR
        extracted_text = pytesseract.image_to_string(img, config=Config.OCR_CONFIG)
        
        # Clean text
        extracted_text = extracted_text.strip()
        extracted_text = ' '.join(extracted_text.split())
        
        # Check if text length is sufficient
        if len(extracted_text) >= Config.MIN_TEXT_LENGTH:
            # Get confidence data
            try:
                confidence_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                conf_values = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
                avg_confidence = sum(conf_values) / len(conf_values) if conf_values else 0
            except:
                avg_confidence = 70  # Default confidence if can't calculate
            
            # Filter out images with very low confidence or gibberish
            if avg_confidence >= Config.MIN_TEXT_CONFIDENCE:
                # Check if text seems meaningful (contains letters/words)
                words = extracted_text.split()
                if len(words) >= 2:  # At least 2 words
                    return True, extracted_text, avg_confidence
        
        return False, '', 0
        
    except Exception as e:
        return False, f'OCR error: {str(e)[:50]}', 0

# ============================================================
# PROCESS IMAGE URL
# ============================================================
def process_image_url(image_url):
    """Process a single image URL: download, OCR, detect text"""
    if not image_url or pd.isna(image_url) or image_url == '':
        return None, 'no_url', '', 0
    
    # Check if it's a video
    if is_video_url(image_url):
        return None, 'video', '', 0
    
    # Download image
    img, status = download_image(image_url)
    
    if img is None:
        return None, status, '', 0
    
    # Check for text in image
    has_text, extracted_text, confidence = has_readable_text(img)
    
    if has_text:
        return 'image_with_text', 'text_found', extracted_text, confidence
    else:
        return 'image_no_text', 'no_text_found', '', 0

# ============================================================
# EXTRACT IMAGE URLS FROM TEXT
# ============================================================
def extract_image_urls_from_text(text):
    """Extract image URLs from tweet text"""
    if not text or pd.isna(text):
        return []
    
    text = str(text)
    
    # Twitter/X image URL patterns
    patterns = [
        r'https?://pbs\.twimg\.com/media/[^\s]+\.(jpg|jpeg|png|gif|webp)',
        r'https?://t\.co/[A-Za-z0-9]+',
        r'https?://twitter\.com/[^/]+/status/[0-9]+/photo/[0-9]+'
    ]
    
    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)
    
    return list(set(urls))  # Remove duplicates

# ============================================================
# MAIN PROCESSING FUNCTION
# ============================================================
def process_tweets_csv(input_file, output_file='2025DonaldData_processed.csv'):
    """Main function to process the CSV file"""
    
    print("="*70)
    print("🚀 STARTING OCR PROCESSING FOR TRUMP TWEETS")
    print("="*70)
    
    # Read CSV
    print(f"\n📂 Reading file: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df)} rows")
    print(f"  Columns: {list(df.columns)}")
    
    # Check Tesseract
    try:
        tesseract_version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract OCR version: {tesseract_version}")
    except:
        print("❌ Tesseract not found! Please install with: !apt-get install tesseract-ocr")
        return None
    
    # Add new columns
    df['text_OCR'] = ''  # Original text + OCR text
    df['image_status'] = ''  # Status of image processing
    df['ocr_extracted_text'] = ''  # Only OCR text
    df['ocr_confidence'] = 0  # Confidence score
    df['image_urls_found'] = ''  # URLs found in the tweet
    
    # Statistics
    stats = {
        'total': len(df),
        'with_images': 0,
        'videos_skipped': 0,
        'images_with_text': 0,
        'images_without_text': 0,
        'download_errors': 0
    }
    
    print("\n" + "="*70)
    print("📸 PROCESSING TWEETS")
    print("="*70)
    
    for idx, row in df.iterrows():
        print(f"\n📝 Row {idx + 1}/{len(df)} - Date: {row['date']}")
        
        # Get original text
        original_text = str(row['text']) if pd.notna(row['text']) else ""
        
        # Check image column first
        image_column = str(row['image']) if pd.notna(row['image']) else ""
        
        # Extract image URLs from text and image column
        image_urls = []
        
        # From image column (comma-separated)
        if image_column and image_column != 'nan':
            urls = [url.strip() for url in image_column.split(',') if url.strip()]
            image_urls.extend(urls)
        
        # From text column (t.co links)
        text_urls = extract_image_urls_from_text(original_text)
        image_urls.extend(text_urls)
        
        # Remove duplicates
        image_urls = list(set(image_urls))
        
        # Store found URLs
        df.at[idx, 'image_urls_found'] = ' | '.join(image_urls) if image_urls else ''
        
        if not image_urls:
            print(f"  ℹ No images found in this post")
            df.at[idx, 'text_OCR'] = original_text
            df.at[idx, 'image_status'] = 'no_images'
            df.at[idx, 'ocr_extracted_text'] = ''
            continue
        
        print(f"  🖼 Found {len(image_urls)} potential image(s)")
        stats['with_images'] += 1
        
        # Process each image URL
        all_ocr_texts = []
        processed_count = 0
        
        for i, url in enumerate(image_urls[:5], 1):  # Limit to 5 images per post
            print(f"    Processing image {i}/{min(len(image_urls), 5)}...")
            
            result, status, ocr_text, confidence = process_image_url(url)
            
            if result == 'image_with_text':
                print(f"      ✓ Text found! ({len(ocr_text)} chars, confidence: {confidence:.0f}%)")
                all_ocr_texts.append(f"[Image {i}] {ocr_text}")
                processed_count += 1
                stats['images_with_text'] += 1
                df.at[idx, 'image_status'] = 'has_text'
                df.at[idx, 'ocr_confidence'] = confidence
                
            elif result == 'image_no_text':
                print(f"      ⚠ Image downloaded but no readable text found")
                stats['images_without_text'] += 1
                if df.at[idx, 'image_status'] == '':
                    df.at[idx, 'image_status'] = 'no_text'
                    
            elif status == 'video':
                print(f"      🎬 Skipping video content")
                stats['videos_skipped'] += 1
                if df.at[idx, 'image_status'] == '':
                    df.at[idx, 'image_status'] = 'video_skipped'
                    
            else:
                print(f"      ❌ Failed: {status}")
                stats['download_errors'] += 1
                if df.at[idx, 'image_status'] == '':
                    df.at[idx, 'image_status'] = 'error'
            
            time.sleep(Config.DELAY_BETWEEN_IMAGES)
        
        # Combine OCR text
        if all_ocr_texts:
            ocr_combined = ' | '.join(all_ocr_texts)
            df.at[idx, 'ocr_extracted_text'] = ocr_combined
            # Combine with original text
            df.at[idx, 'text_OCR'] = f"{original_text} [OCR: {ocr_combined}]"
        else:
            df.at[idx, 'text_OCR'] = original_text
            if image_urls and not all_ocr_texts:
                df.at[idx, 'ocr_extracted_text'] = '(No readable text found in images)'
        
        time.sleep(Config.DELAY_BETWEEN_POSTS)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 PROCESSING COMPLETE - SUMMARY")
    print("="*70)
    print(f"Total tweets processed: {stats['total']}")
    print(f"Tweets with images: {stats['with_images']}")
    print(f"  - Images with readable text: {stats['images_with_text']}")
    print(f"  - Images without text: {stats['images_without_text']}")
    print(f"  - Videos skipped: {stats['videos_skipped']}")
    print(f"  - Download errors: {stats['download_errors']}")
    
    # Save to CSV
    print(f"\n💾 Saving results to: {output_file}")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ File saved successfully")
    
    return df, stats

# ============================================================
# DISPLAY SAMPLE RESULTS
# ============================================================
def display_sample_results(df):
    """Display sample of processed results"""
    print("\n" + "="*70)
    print("📋 SAMPLE RESULTS")
    print("="*70)
    
    # Show tweets with OCR text
    ocr_tweets = df[df['ocr_extracted_text'].notna() & (df['ocr_extracted_text'] != '')]
    ocr_tweets = ocr_tweets[~ocr_tweets['ocr_extracted_text'].str.contains('No readable text', na=False)]
    
    if len(ocr_tweets) > 0:
        print(f"\n✅ Tweets with OCR-extracted text ({len(ocr_tweets)} found):")
        for idx, row in ocr_tweets.head(3).iterrows():
            print(f"\n📅 {row['date']} {row['time']}")
            print(f"📝 Original: {str(row['text'])[:80]}...")
            print(f"🔍 OCR Text: {row['ocr_extracted_text'][:100]}...")
            print(f"📊 Confidence: {row['ocr_confidence']:.0f}%")
            print("-" * 40)
    else:
        print("\n⚠ No tweets with readable text found in images")
    
    # Show tweets with videos
    videos = df[df['image_status'] == 'video_skipped']
    if len(videos) > 0:
        print(f"\n🎬 Tweets with videos ({len(videos)} found):")
        for idx, row in videos.head(2).iterrows():
            print(f"  - {row['date']}: {str(row['text'])[:60]}...")
    
    # Show tweets with images but no text
    no_text = df[df['image_status'] == 'no_text']
    if len(no_text) > 0:
        print(f"\n🖼 Tweets with images but no readable text ({len(no_text)} found):")
        for idx, row in no_text.head(2).iterrows():
            print(f"  - {row['date']}: {str(row['text'])[:60]}...")

# ============================================================
# CREATE SUMMARY REPORT
# ============================================================
def create_summary_report(df, stats, output_file='ocr_summary.txt'):
    """Create a detailed summary report"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("OCR PROCESSING SUMMARY REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("STATISTICS:\n")
        f.write(f"  • Total tweets processed: {stats['total']}\n")
        f.write(f"  • Tweets with images: {stats['with_images']}\n")
        f.write(f"  • Images with readable text: {stats['images_with_text']}\n")
        f.write(f"  • Images without readable text: {stats['images_without_text']}\n")
        f.write(f"  • Videos skipped: {stats['videos_skipped']}\n")
        f.write(f"  • Download errors: {stats['download_errors']}\n\n")
        
        # Success rate
        if stats['images_with_text'] > 0:
            success_rate = (stats['images_with_text'] / stats['images_without_text'] * 100) if stats['images_without_text'] > 0 else 100
            f.write(f"  • OCR success rate: {success_rate:.1f}%\n\n")
        
        f.write("COLUMN DESCRIPTIONS:\n")
        f.write("  • text_OCR: Original text + OCR extracted text (if any)\n")
        f.write("  • image_status: Status of image processing\n")
        f.write("    - has_text: Image contained readable text\n")
        f.write("    - no_text: Image downloaded but no text found\n")
        f.write("    - video_skipped: Video content skipped\n")
        f.write("    - error: Download or processing error\n")
        f.write("    - no_images: No images found in tweet\n")
        f.write("  • ocr_extracted_text: Only the text extracted from images\n")
        f.write("  • ocr_confidence: OCR confidence score (0-100)\n")
        f.write("  • image_urls_found: URLs of images found in the tweet\n")
    
    print(f"\n📄 Summary report saved to: {output_file}")
    files.download(output_file)

# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    # Upload your CSV file
    print("Please upload your CSV file (2025DonaldData.csv)")
    uploaded = files.upload()
    
    if uploaded:
        filename = list(uploaded.keys())[0]
        print(f"\n✓ File uploaded: {filename}")
        
        # Process the file
        df, stats = process_tweets_csv(filename, '2025DonaldData_processed.csv')
        
        if df is not None:
            # Display sample results
            display_sample_results(df)
            
            # Download results
            print("\n📥 Downloading processed CSV...")
            files.download('2025DonaldData_processed.csv')
            
            # Create and download summary report
            create_summary_report(df, stats)
            
            print("\n✅ Processing complete!")
        else:
            print("❌ Processing failed")

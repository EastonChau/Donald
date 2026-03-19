import requests
import csv
import re
import time
from datetime import datetime, timedelta

# ==================================================
# USER CONFIGURATION SECTION - ENTER YOUR CREDENTIALS HERE
# ==================================================

# Enter your Bearer Token here
BEARER_TOKEN = ""

# Target username and date range
TARGET_USERNAME = "realDonaldTrump"
START_DATE = "2025-01-01"  # Format: YYYY-MM-DD
END_DATE = "2025-12-30"     # Format: YYYY-MM-DD
OUTPUT_CSV = f"{TARGET_USERNAME}_{START_DATE}_to_{END_DATE}_tweets.csv"

# ==================================================
# END OF USER CONFIGURATION SECTION
# ==================================================

def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            return data['data']['id']
    else:
        print(f"Error getting user ID: {response.status_code}")
        print(response.text)
        return None

def get_tweets_in_date_range(user_id, start_date, end_date):
    start_time = f"{start_date}T00:00:00Z"
    end_time = f"{end_date}T23:59:59Z"
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "tweet.fields": "created_at,public_metrics,entities,attachments",
        "expansions": "attachments.media_keys",
        "media.fields": "url,type",
        "max_results": 100
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    all_tweets = []
    page_count = 0
    
    print(f"Fetching tweets from {start_date} to {end_date}...")
    
    while True:
        page_count += 1
        print(f"Fetching page {page_count}...")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 429:
            wait_time = 60
            print(f"Rate limit hit. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        elif response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break
            
        data = response.json()
        
        media_dict = {}
        if 'includes' in data and 'media' in data['includes']:
            for media in data['includes']['media']:
                if 'media_key' in media:
                    media_dict[media['media_key']] = media
        
        if 'data' in data:
            for tweet in data['data']:
                tweet['media_urls'] = []
                if 'attachments' in tweet and 'media_keys' in tweet['attachments']:
                    for media_key in tweet['attachments']['media_keys']:
                        if media_key in media_dict:
                            media = media_dict[media_key]
                            if media.get('type') == 'photo' and 'url' in media:
                                media_url = media['url']
                                if '?format=' in media_url:
                                    media_url = re.sub(r'&name=\w+', '&name=orig', media_url)
                                tweet['media_urls'].append(media_url)
            all_tweets.extend(data['data'])
            print(f"   Found {len(data['data'])} tweets on this page. Total so far: {len(all_tweets)}")
        
        if 'meta' in data and 'next_token' in data['meta']:
            params['pagination_token'] = data['meta']['next_token']
            time.sleep(1)
        else:
            break
    
    return all_tweets

def create_csv(tweets, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['date', 'time', 'text', 'image', 'post_link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for tweet in tweets:
            created_at = datetime.strptime(tweet['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
            date_str = created_at.strftime('%Y-%m-%d')
            time_str = created_at.strftime('%H:%M:%S')
            text = tweet['text'].replace('\n', ' ').replace('\r', ' ')
            image = ', '.join(tweet['media_urls']) if tweet['media_urls'] else ''
            post_link = f"https://twitter.com/{TARGET_USERNAME}/status/{tweet['id']}"
            
            writer.writerow({
                'date': date_str,
                'time': time_str,
                'text': text,
                'image': image,
                'post_link': post_link
            })
    
    print(f"✅ CSV file created: {filename}")

def main():
    print("=" * 60)
    print(f"Twitter Post Extractor")
    print(f"Username: @{TARGET_USERNAME}")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print("=" * 60)
    
    user_id = get_user_id(TARGET_USERNAME)
    if not user_id:
        print("❌ Could not get user ID. Exiting.")
        return
    
    print(f"User ID: {user_id}")
    
    tweets = get_tweets_in_date_range(user_id, START_DATE, END_DATE)
    
    if tweets:
        print(f"\n✅ Total tweets found: {len(tweets)}")
        create_csv(tweets, OUTPUT_CSV)
        
        # Print summary statistics
        dates = {}
        for tweet in tweets:
            date = tweet['created_at'][:10]
            dates[date] = dates.get(date, 0) + 1
        
        print("\n📊 Tweets per day:")
        for date, count in sorted(dates.items()):
            print(f"   {date}: {count} tweets")
    else:
        print("❌ No tweets found in the specified date range")

if __name__ == "__main__":
    main()
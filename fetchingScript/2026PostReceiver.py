import requests
import csv
import re
import time
from datetime import datetime, timedelta
import pytz

# ==================================================
# USER CONFIGURATION SECTION - ENTER YOUR CREDENTIALS HERE
# ==================================================

# Enter your Bearer Token here
BEARER_TOKEN = ""

# Target username and date range
TARGET_USERNAME = "realDonaldTrump"
START_DATE = "2024-12-01"  # Format: YYYY-MM-DD (Dec 1, 2024)
END_DATE = "2026-04-30"     # Format: YYYY-MM-DD (Apr 30, 2026)
OUTPUT_CSV = f"{TARGET_USERNAME}_{START_DATE}_to_{END_DATE}_tweets.csv"

# ==================================================
# END OF USER CONFIGURATION SECTION
# ==================================================

def convert_utc_to_eastern(utc_datetime_str):
    """Convert UTC time string to US Eastern Time (handles EST/EDT automatically)"""
    # Parse the UTC time (API returns format like '2024-12-01T15:30:45.000Z')
    utc_time = datetime.strptime(utc_datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Set timezone to UTC
    utc_time = pytz.UTC.localize(utc_time)

    # Convert to US Eastern time (automatically handles EST/EDT based on date)
    eastern = pytz.timezone('US/Eastern')
    eastern_time = utc_time.astimezone(eastern)

    return eastern_time

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
    # Convert dates to UTC for API query (API expects UTC)
    # Note: The API queries based on UTC time, so we need to adjust
    start_time = f"{start_date}T00:00:00Z"  # UTC midnight
    end_time = f"{end_date}T23:59:59Z"      # UTC end of day

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

    print(f"Fetching tweets from {start_date} to {end_date} (UTC)...")
    print(f"Note: Times will be converted to US Eastern Time (EST/EDT)")

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
        fieldnames = ['date', 'time', 'timezone', 'text', 'image', 'post_link', 'utc_time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for tweet in tweets:
            # Convert UTC to Eastern Time
            eastern_time = convert_utc_to_eastern(tweet['created_at'])
            date_str = eastern_time.strftime('%Y-%m-%d')
            time_str = eastern_time.strftime('%H:%M:%S')

            # Determine if EST or EDT
            tz_name = eastern_time.tzname()  # Returns 'EST' or 'EDT'

            text = tweet['text'].replace('\n', ' ').replace('\r', ' ')
            image = ', '.join(tweet['media_urls']) if tweet['media_urls'] else ''
            post_link = f"https://twitter.com/{TARGET_USERNAME}/status/{tweet['id']}"

            # Original UTC time for reference
            utc_original = tweet['created_at']

            writer.writerow({
                'date': date_str,
                'time': time_str,
                'timezone': tz_name,
                'text': text,
                'image': image,
                'post_link': post_link,
                'utc_time': utc_original
            })

    print(f"✅ CSV file created: {filename}")

def main():
    print("=" * 60)
    print(f"Twitter Post Extractor")
    print(f"Username: @{TARGET_USERNAME}")
    print(f"Date Range: {START_DATE} to {END_DATE} (UTC)")
    print(f"Output Timezone: US Eastern (EST/EDT)")
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
            # Convert to Eastern for date grouping
            eastern_time = convert_utc_to_eastern(tweet['created_at'])
            date = eastern_time.strftime('%Y-%m-%d')
            dates[date] = dates.get(date, 0) + 1

        print("\n📊 Tweets per day (Eastern Time):")
        for date, count in sorted(dates.items()):
            print(f"   {date}: {count} tweets")
    else:
        print("❌ No tweets found in the specified date range")

if __name__ == "__main__":
    main()
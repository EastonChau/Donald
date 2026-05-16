import requests
import csv
import re
import time
from datetime import datetime
import pytz

# ==================================================
# USER CONFIGURATION SECTION
# ==================================================

BEARER_TOKEN = ""
TARGET_USERNAME = "realDonaldTrump"
START_DATE = "2025-01-01"
END_DATE = "2026-04-30"
OUTPUT_CSV = f"{TARGET_USERNAME}_{START_DATE}_to_{END_DATE}_tweets.csv"

# Maximum per request
MAX_RESULTS_PER_PAGE = 100

# ==================================================
# END OF CONFIGURATION
# ==================================================

def convert_utc_to_eastern(utc_datetime_str):
    """Convert UTC time string to US Eastern Time (handles EST/EDT automatically)"""
    utc_time = datetime.strptime(utc_datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    utc_time = pytz.UTC.localize(utc_time)
    eastern = pytz.timezone('US/Eastern')
    eastern_time = utc_time.astimezone(eastern)
    return eastern_time

def get_full_tweet_text(tweet_data):
    """Extract full tweet text, handling note_tweet (long tweets)"""
    # Check for note_tweet first (contains full text of long tweets)
    if 'note_tweet' in tweet_data and 'text' in tweet_data['note_tweet']:
        return tweet_data['note_tweet']['text']

    # Fall back to regular text field
    return tweet_data.get('text', '')

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

def get_all_tweets(user_id, start_date, end_date):
    """Fetch ALL tweets in date range using automatic pagination"""
    start_time = f"{start_date}T00:00:00Z"
    end_time = f"{end_date}T23:59:59Z"
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"

    all_tweets = []
    page_count = 0
    next_token = None

    print(f"Fetching tweets from {start_date} to {end_date}...")
    print(f"Max {MAX_RESULTS_PER_PAGE} tweets per request (API limit)")
    print(f"Will automatically paginate to fetch all available tweets\n")

    while True:
        page_count += 1

        # Build parameters - ADDED note_tweet to fields
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "tweet.fields": "created_at,public_metrics,entities,attachments,note_tweet",  # Added note_tweet
            "expansions": "attachments.media_keys",
            "media.fields": "url,type",
            "max_results": MAX_RESULTS_PER_PAGE
        }

        # Add pagination token if we have one
        if next_token:
            params["pagination_token"] = next_token

        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

        print(f"📄 Fetching page {page_count}...", end=" ")

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            wait_time = 60
            print(f"\n⏱️  Rate limit hit. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        elif response.status_code != 200:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        # Process media attachments
        media_dict = {}
        if 'includes' in data and 'media' in data['includes']:
            for media in data['includes']['media']:
                if 'media_key' in media:
                    media_dict[media['media_key']] = media

        # Process tweets
        tweets_in_page = 0
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

                # Store the full text
                tweet['full_text'] = get_full_tweet_text(tweet)

            all_tweets.extend(data['data'])
            tweets_in_page = len(data['data'])

            # Show sample of text length to confirm full text is being retrieved
            if page_count == 1 and tweets_in_page > 0:
                sample_tweet = data['data'][0]
                sample_text = sample_tweet['full_text']
                print(f"✅ Got {tweets_in_page} tweets (Total so far: {len(all_tweets)})")
                print(f"   📝 Sample text length: {len(sample_text)} chars (first 100 chars: {sample_text[:100]}...)")
            else:
                print(f"✅ Got {tweets_in_page} tweets (Total so far: {len(all_tweets)})")

        # Check for next page
        if 'meta' in data and 'next_token' in data['meta']:
            next_token = data['meta']['next_token']
            time.sleep(1)  # Be respectful to rate limits
        else:
            print(f"\n✨ No more pages available. Fetch complete!")
            break

    # Sort chronologically (oldest first)
    all_tweets.sort(key=lambda x: x['created_at'])

    return all_tweets

def create_csv(tweets, filename):
    """Save tweets to CSV with Eastern Time conversion and full text"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['date', 'time', 'timezone', 'post_id', 'text', 'image', 'likes', 'retweets', 'replies', 'views']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for tweet in tweets:
            eastern_time = convert_utc_to_eastern(tweet['created_at'])
            date_str = eastern_time.strftime('%Y-%m-%d')
            time_str = eastern_time.strftime('%H:%M:%S')
            tz_name = eastern_time.tzname()

            metrics = tweet.get('public_metrics', {})
            likes = metrics.get('like_count', 0)
            retweets = metrics.get('retweet_count', 0)
            replies = metrics.get('reply_count', 0)
            views = metrics.get('impression_count', 0)

            # Use the full text we stored
            text = tweet['full_text'].replace('\n', ' ').replace('\r', ' ')

            image = ', '.join(tweet['media_urls']) if tweet['media_urls'] else ''

            writer.writerow({
                'date': date_str,
                'time': time_str,
                'timezone': tz_name,
                'post_id': tweet['id'],
                'text': text,
                'image': image,
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'views': views
            })

    print(f"\n✅ CSV file created: {filename}")

def main():
    print("=" * 60)
    print(f"Twitter Post Extractor (With Full Text & Pagination)")
    print(f"Username: @{TARGET_USERNAME}")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Output Timezone: US Eastern (EST/EDT)")
    print("=" * 60)

    user_id = get_user_id(TARGET_USERNAME)
    if not user_id:
        print("❌ Could not get user ID. Exiting.")
        return

    print(f"User ID: {user_id}\n")

    tweets = get_all_tweets(user_id, START_DATE, END_DATE)

    if tweets:
        print(f"\n{'='*60}")
        print(f"📊 FETCH COMPLETE")
        print(f"   Total tweets retrieved: {len(tweets)}")
        print(f"   Date range: {tweets[0]['created_at'][:10]} to {tweets[-1]['created_at'][:10]}")

        # Calculate average text length
        avg_length = sum(len(t['full_text']) for t in tweets) / len(tweets)
        print(f"   Average text length: {avg_length:.0f} characters")
        print(f"{'='*60}")

        create_csv(tweets, OUTPUT_CSV)

        # Summary statistics
        dates = {}
        total_likes = total_retweets = total_replies = total_views = 0
        long_tweets_count = 0

        for tweet in tweets:
            eastern_time = convert_utc_to_eastern(tweet['created_at'])
            date = eastern_time.strftime('%Y-%m-%d')
            dates[date] = dates.get(date, 0) + 1

            metrics = tweet.get('public_metrics', {})
            total_likes += metrics.get('like_count', 0)
            total_retweets += metrics.get('retweet_count', 0)
            total_replies += metrics.get('reply_count', 0)
            total_views += metrics.get('impression_count', 0)

            # Count tweets longer than standard 280 chars
            if len(tweet['full_text']) > 280:
                long_tweets_count += 1

        print(f"\n📈 Engagement Statistics:")
        print(f"   Total likes: {total_likes:,}")
        print(f"   Total retweets: {total_retweets:,}")
        print(f"   Total replies: {total_replies:,}")
        print(f"   Total views: {total_views:,}")
        print(f"   Avg likes/tweet: {total_likes/len(tweets):.1f}")
        print(f"   Long tweets (>280 chars): {long_tweets_count} ({long_tweets_count/len(tweets)*100:.1f}%)")

        print(f"\n📅 Tweets per day ({len(dates)} unique days):")
        for date, count in sorted(dates.items())[:10]:
            print(f"   {date}: {count} tweets")
        if len(dates) > 10:
            print(f"   ... and {len(dates)-10} more days")
    else:
        print("❌ No tweets found in the specified date range")

if __name__ == "__main__":
    main()

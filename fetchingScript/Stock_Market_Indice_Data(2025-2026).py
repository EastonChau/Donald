# Import required libraries
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Define the tickers for the indices
# ^DJI - Dow Jones Industrial Average
# ^GSPC - S&P 500
# ^IXIC - NASDAQ Composite
tickers = {
    '^DJI': 'DJIA',
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ Composite'
}

# Define the date range
start_date = '2025-01-01'
end_date = '2026-01-01'

print("Fetching data for DJIA, S&P 500, and NASDAQ Composite...")
print("-" * 50)

# Initialize an empty list to store dataframes
dataframes = []

# Fetch data for each index
for ticker, name in tickers.items():
    try:
        # Download the data
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if not data.empty:
            # Extract only the closing prices and rename the column
            closing_prices = data[['Close']].copy()
            closing_prices.columns = [name]

            # Store in list
            dataframes.append(closing_prices)

            print(f"✓ Successfully fetched {name} data")
            print(f"  Date range: {closing_prices.index[0].strftime('%Y-%m-%d')} to {closing_prices.index[-1].strftime('%Y-%m-%d')}")
            print(f"  Number of trading days: {len(closing_prices)}")
            print()
        else:
            print(f"✗ No data available for {name}")
            print()

    except Exception as e:
        print(f"✗ Error fetching {name}: {str(e)}")
        print()

# Combine all dataframes
if dataframes:
    # Start with the first dataframe
    combined_df = dataframes[0]

    # Join with remaining dataframes
    for df in dataframes[1:]:
        combined_df = combined_df.join(df, how='outer')

    # Reset index to make Date a column
    combined_df.reset_index(inplace=True)
    combined_df.rename(columns={'index': 'Date'}, inplace=True)

    # Format Date column with hour and minutes (market closing time: 16:00:00)
    # For daily data, yfinance typically uses the closing timestamp (4:00 PM ET)
    combined_df['Date'] = pd.to_datetime(combined_df['Date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Save to CSV
    csv_filename = 'Index_Closing_Prices(2025-2026).csv'
    combined_df.to_csv(csv_filename, index=False)
    print(f"\n✓ Data saved to {csv_filename}")

# Import required libraries
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Define the tickers for the indices
# ^DJI - Dow Jones Industrial Average
# ^GSPC - S&P 500
# ^IXIC - NASDAQ Composite
tickers = {
    '^DJI': 'DJIA',
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ Composite'
}

# Define the date range
start_date = '2025-01-01'
end_date = '2026-01-01'

print("Fetching 1-hour interval data for DJIA, S&P 500, and NASDAQ Composite...")
print("-" * 50)

# Initialize an empty list to store dataframes
dataframes = []

# Fetch data for each index
for ticker, name in tickers.items():
    try:
        # Download the data with 1-hour interval
        # interval='1h' gives hourly data
        data = yf.download(ticker, start=start_date, end=end_date, interval='1h', progress=False)

        if not data.empty:
            # Extract only the closing prices and rename the column
            closing_prices = data[['Close']].copy()
            closing_prices.columns = [name]

            # Store in list
            dataframes.append(closing_prices)

            print(f"✓ Successfully fetched {name} data")
            print(f"  Date range: {closing_prices.index[0]} to {closing_prices.index[-1]}")
            print(f"  Number of hourly records: {len(closing_prices)}")
            print()
        else:
            print(f"✗ No data available for {name}")
            print()

    except Exception as e:
        print(f"✗ Error fetching {name}: {str(e)}")
        print()

# Combine all dataframes
if dataframes:
    # Start with the first dataframe
    combined_df = dataframes[0]

    # Join with remaining dataframes
    for df in dataframes[1:]:
        combined_df = combined_df.join(df, how='outer')

    # Reset index to make the datetime a column
    combined_df.reset_index(inplace=True)

    # Rename the first column (which contains the datetime) to 'Date'
    # This approach works regardless of what the column is named
    combined_df.rename(columns={combined_df.columns[0]: 'Date'}, inplace=True)

    # Format Date column and remove timezone offset (+00:00)
    combined_df['Date'] = pd.to_datetime(combined_df['Date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Save to CSV
    csv_filename = 'Index_Closing_Prices_1h(2025-2026).csv'
    combined_df.to_csv(csv_filename, index=False)
    print(f"\n✓ Data saved to {csv_filename}")
    print(f"  Total hourly records: {len(combined_df)}")

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Read the two CSV files
hourly_df = pd.read_csv('Index_Closing_Prices_1h(2025-2026).csv')
daily_df = pd.read_csv('Index_Closing_Prices(2025-2026).csv')

# Convert Date columns to datetime
hourly_df['Date'] = pd.to_datetime(hourly_df['Date'])
daily_df['Date'] = pd.to_datetime(daily_df['Date'])

# For daily data, set the time to 21:30:00 (after market close)
daily_df['Date'] = daily_df['Date'] + pd.Timedelta(hours=21, minutes=30)

# Combine the dataframes
combined_df = pd.concat([hourly_df, daily_df], ignore_index=True)

# Sort by Date to maintain chronological order
combined_df = combined_df.sort_values('Date').reset_index(drop=True)

# Extract date and time into separate columns
combined_df['Trading_Date'] = combined_df['Date'].dt.strftime('%Y-%m-%d')
combined_df['Time'] = combined_df['Date'].dt.strftime('%H:%M:%S')

# Reorder columns
combined_df = combined_df[['Trading_Date', 'Time', 'DJIA', 'S&P 500', 'NASDAQ Composite']]

# Save the combined data
combined_df.to_csv('Index_Closing_Prices_2025-2026.csv', index=False)

print(f"✓ Combined file saved as 'Index_Closing_Prices_2025-2026.csv'")
print(f"  Total rows: {len(combined_df)}")
print(f"  Hourly rows: {len(hourly_df)}")
print(f"  Daily rows: {len(daily_df)}")

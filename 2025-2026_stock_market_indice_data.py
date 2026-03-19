# -*- coding: utf-8 -*-

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
start_date = '2025-01-20'
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

    # Format Date column
    combined_df['Date'] = pd.to_datetime(combined_df['Date']).dt.date

    # Display information about the data
    print("\n" + "="*50)
    print("DATA OVERVIEW")
    print("="*50)
    print(f"Total trading days: {len(combined_df)}")
    print(f"Date range: {combined_df['Date'].min()} to {combined_df['Date'].max()}")

    print("\nFirst 5 rows of the data:")
    print(combined_df.head())

    print("\nLast 5 rows of the data:")
    print(combined_df.tail())

    # Save to CSV
    csv_filename = 'index_closing_prices_2025.csv'
    combined_df.to_csv(csv_filename, index=False)
    print(f"\n✓ Data saved to {csv_filename}")

    # Display summary statistics
    print("\n" + "="*50)
    print("SUMMARY STATISTICS")
    print("="*50)
    print(combined_df.describe())

    # Check for missing data
    print("\n" + "="*50)
    print("MISSING DATA CHECK")
    print("="*50)
    missing_data = combined_df.isnull().sum()
    print(missing_data)

    # Download the CSV file in Colab
    try:
        from google.colab import files
        files.download(csv_filename)
        print("\n✓ File download initiated")
    except:
        print("\nNote: Not running in Google Colab or file download failed")
        print(f"You can find the file at: {csv_filename}")

else:
    print("No data was fetched successfully.")
    print("\nNote: Since we're trying to fetch future data (2025), it may not be available yet.")
    print("To test the code with historical data, change the dates to a past period:")
    print("start_date = '2024-01-20'")
    print("end_date = '2024-12-31'")

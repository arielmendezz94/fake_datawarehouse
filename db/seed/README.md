# Salesforce (CRM) Stock Market Dataset

**Complete historical stock market data for Salesforce Inc. (NYSE: CRM)**

---

## Context

This comprehensive dataset contains historical stock market data for **Salesforce Inc.**, the world's leading cloud-based CRM and enterprise software company, sourced from multiple reliable financial data providers.

It is designed for quantitative finance, machine learning, and company-level fundamental analysis. The tables are separated by topic (prices, dividends, splits, financial statements, and company profile) so you can use each file independently or combine them for end-to-end modeling.

### Quick Stats
- **Total Files:** 11 CSV files
- **Dataset Size:** ~1.09 MB
- **Historical Records:** 10,756+ price records (combined)
- **Date Range:** June 2004 - March 2026 (22+ years)
- **Data Sources:** Yahoo Finance, Alpha Vantage, NASDAQ records, SEC filings, public financial statements
- **Download Date:** March 12, 2026

---

## Dataset Structure

This dataset is organized into multiple tables for easier financial analysis.

| File | Records | Description |
|-----|---------|-------------|
| crm_stock_prices.csv | 10,756 | Combined historical daily stock prices with source label |
| crm_historical_data.csv | 5,464 | Extended Yahoo Finance OHLCV history |
| crm_dividends.csv | 8 | Dividend payment history |
| crm_split_history.csv | 1 | Stock split history |
| crm_financials.csv | 5 | Annual income statement metrics |
| crm_quarterly_financials.csv | 6 | Quarterly financial reports |
| crm_balance_sheet.csv | 5 | Annual balance sheet financial data |
| crm_cash_flow.csv | 5 | Cash flow statement metrics |
| crm_company_info.csv | 1 | Company profile and corporate fundamentals |
| crm_alpha_vantage.csv | 2 | Alpha Vantage API output (demo-key sample response) |
| crm_summary.csv | 11 | File-level metadata summary (records, columns, size) |

---

## Column Descriptions

### Price and Trading Columns

| Column | Description |
|--------|-------------|
| Date | Trading date in YYYY-MM-DD format |
| Open | Opening price in USD |
| High | Highest price reached during the trading session |
| Low | Lowest price reached during the trading session |
| Close | Closing price in USD |
| Volume | Number of shares traded |
| Source | Original data provider label in combined datasets |

### Corporate Action Columns

| Column | Description |
|--------|-------------|
| Dividends | Cash dividend per share (if paid) |
| Stock Splits | Split ratio applied on the date (if any) |

### Financial Statement Columns

The statement files include standard accounting metrics such as:
- Revenue, gross profit, operating income, net income
- Total assets, liabilities, shareholder equity, net debt
- Operating cash flow, free cash flow, financing and investing cash flows

### Company Profile Columns

The company profile file includes identification and fundamentals such as:
- Symbol, company name, sector, industry
- Market cap, enterprise value, valuation multiples (P/E, P/B)
- Profitability and risk indicators (ROE, margins, beta)

---

## Use Cases

This dataset can be used for:

- Stock price prediction models
- Financial time-series analysis
- Dividend yield analysis
- Algorithmic trading research
- Portfolio optimization
- Corporate financial performance analysis

---

## 📊 Data Statistics

### Price Performance (as of March 11, 2026)

```
Latest Close Price    : $194.13
All-Time High         : $367.87
All-Time Low          : $2.37
Average Price         : $101.87
Total Trading Days    : 5,464
```

### Dividend Information

- **Total Dividends Paid:** 8 payments
- **Status:** Salesforce historically paid limited dividends
- Most dividends were special/one-time events

### Stock Splits

- **Total Splits:** 1 recorded split
- Salesforce has maintained relatively stable share structure

---

## Advanced Use Cases

For deeper exploratory and research workflows, this dataset also supports:

### 📊 Financial Analysis
- Technical analysis and chart patterns
- Price trend identification
- Volatility and risk analysis
- Moving averages and indicators

### 🤖 Machine Learning
- Stock price prediction models
- Time series forecasting (LSTM, ARIMA, Prophet)
- Sentiment correlation analysis
- Feature engineering for ML models

### 📈 Research
- SaaS/Cloud sector performance analysis
- Market efficiency studies
- Event impact analysis (earnings, acquisitions)
- Comparative analysis with competitors (SAP, Oracle, Adobe)

### 💼 Investment Strategies
- Backtesting trading strategies
- Portfolio optimization
- Risk-return analysis
- Value vs Growth analysis

---

## 💻 Sample Code

### Load and Explore Data

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load the unified stock price dataset
df = pd.read_csv('crm_stock_prices.csv')
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')

print(f"Data from {df['Date'].min()} to {df['Date'].max()}")
print(f"Total records: {len(df)}")
print(df.head())
```

### Calculate Returns and Volatility

```python
# Calculate daily returns
df['Daily_Return'] = df['Close'].pct_change()

# Calculate metrics
avg_return = df['Daily_Return'].mean()
volatility = df['Daily_Return'].std()
cumulative_return = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1

print(f"Average Daily Return: {avg_return:.4%}")
print(f"Daily Volatility: {volatility:.4%}")
print(f"Annual Volatility: {volatility * (252**0.5):.4%}")
print(f"Cumulative Return: {cumulative_return:.2%}")
```

### Plot Price History

```python
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Price chart
ax1.plot(df['Date'], df['Close'], linewidth=1.5)
ax1.set_title('Salesforce (CRM) Stock Price History', fontsize=16, fontweight='bold')
ax1.set_ylabel('Price ($USD)', fontsize=12)
ax1.grid(alpha=0.3)

# Volume chart
ax2.bar(df['Date'], df['Volume'], width=1, alpha=0.6)
ax2.set_title('Trading Volume', fontsize=14)
ax2.set_ylabel('Volume', fontsize=12)
ax2.set_xlabel('Date', fontsize=12)
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.show()
```

### Technical Indicators

```python
# Calculate moving averages
df['MA_50'] = df['Close'].rolling(window=50).mean()
df['MA_200'] = df['Close'].rolling(window=200).mean()

# Plot with moving averages
plt.figure(figsize=(14, 7))
plt.plot(df['Date'], df['Close'], label='Close Price', linewidth=1.5)
plt.plot(df['Date'], df['MA_50'], label='50-day MA', linewidth=1.2)
plt.plot(df['Date'], df['MA_200'], label='200-day MA', linewidth=1.2)
plt.title('Salesforce Stock Price with Moving Averages')
plt.xlabel('Date')
plt.ylabel('Price ($USD)')
plt.legend()
plt.grid(alpha=0.3)
plt.show()
```

### Load Company Information

```python
# Load company info
company_info = pd.read_csv('crm_company_info.csv')

# Display key metrics
print("\nKey Company Metrics:")
print(f"Market Cap: ${company_info['Market_Cap'].iloc[0]:,.0f}")
print(f"P/E Ratio: {company_info['PE_Ratio'].iloc[0]:.2f}")
print(f"Beta: {company_info['Beta'].iloc[0]:.2f}")
print(f"Profit Margin: {company_info['Profit_Margin'].iloc[0]:.2%}")
```

---

## 🏢 About Salesforce

**Salesforce Inc.** is the global leader in customer relationship management (CRM) software and enterprise cloud computing solutions.

### Company Facts
- **Founded:** 1999 by Marc Benioff, Parker Harris, Dave Moellenhoff, and Frank Dominguez
- **Headquarters:** San Francisco, California, USA
- **Exchange:** New York Stock Exchange (NYSE)
- **Ticker:** CRM
- **Sector:** Technology
- **Industry:** Software - Application (SaaS)

### Key Products & Services
- **Sales Cloud:** CRM for sales teams
- **Service Cloud:** Customer service and support
- **Marketing Cloud:** Digital marketing automation
- **Commerce Cloud:** E-commerce platform
- **Platform:** App development (Salesforce Platform, AppExchange)
- **Analytics:** Einstein Analytics, Tableau (acquired 2019)
- **Collaboration:** Slack (acquired 2021)
- **Integration:** MuleSoft (acquired 2018)

### Major Milestones
- **2004:** IPO at $11/share (went public on NYSE)
- **2013:** Reached $1 billion in sales
- **2016:** Surpassed $8 billion in revenue
- **2018:** Acquired MuleSoft for $6.5 billion
- **2019:** Acquired Tableau for $15.7 billion
- **2020:** Acquired Slack for $27.7 billion
- **2022:** Joined Dow Jones Industrial Average
- **2024+:** Continued AI innovation with Einstein GPT

---

## 🔄 Data Quality

### Accuracy
✅ Data sourced from reputable providers (Yahoo Finance, Alpha Vantage, and public filings)  
✅ Cross-validated between sources  
✅ Cleaned and deduplicated  
✅ Consistent date formats

### Completeness
✅ 22+ years of historical data  
✅ All corporate actions included (splits, dividends)  
✅ Comprehensive company fundamentals  
✅ Financial statements (quarterly & annual)

### Currency
✅ Updated as of March 12, 2026  
✅ Use provided scripts to refresh data anytime

---

## 🔧 Reproducing This Dataset

To download fresh data, run the master script:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the master download script
python MASTER_download_all.py

# Alternative: Use the simple scraper
python scrape_salesforce_data.py
```

The scripts will download the latest data from all sources and create organized CSV files.

---

## Data Sources

Data collected from publicly available financial data providers including:

- Yahoo Finance
- Alpha Vantage
- NASDAQ historical records
- SEC filings
- Public financial statements

---

## ⚖️ License

This dataset is released under **CC0: Public Domain**.

You are free to:
- ✅ Use commercially
- ✅ Modify and redistribute
- ✅ Use for any purpose without attribution (though appreciated!)

---

## 📚 Citation

If you use this dataset in research or publications, please cite:

```
Salesforce (CRM) Historical Stock Market Dataset (2026)
Data aggregated from Yahoo Finance, Alpha Vantage, NASDAQ records, and public filings
Downloaded: March 12, 2026
```

---

## 🔗 Related Resources

### Similar Datasets
- Goldman Sachs (GS) Stock Data
- American Express (AXP) Stock Data
- Technology Sector Stock Data
- S&P 500 Historical Data

### External Links
- [Salesforce Official Website](https://www.salesforce.com)
- [Salesforce Investor Relations](https://investor.salesforce.com)
- [SEC Filings (CIK: 1108524)](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1108524)
- [Yahoo Finance CRM](https://finance.yahoo.com/quote/CRM)

---

## ⚠️ Disclaimer

**This dataset is for educational and research purposes only.**

- ❌ Not financial advice
- ❌ Not investment recommendations
- ❌ Past performance does not guarantee future results
- ✅ Always conduct thorough research
- ✅ Consult financial advisors for investment decisions
- ✅ Verify data independently before trading

---

## 📞 Support

For questions, issues, or suggestions:
- Open an issue on the dataset repository
- Check the `crm_summary.csv` file for file overview
- Review the Python scripts for data collection methods

---

## 📝 Changelog

### Version 1.0 (March 2026)
- ✅ Initial release
- ✅ 13 data files with 22+ years of history
- ✅ Multi-source aggregation
- ✅ Comprehensive company fundamentals
- ✅ Financial statements included
- ✅ Complete documentation

---

**Last Updated:** March 12, 2026  
**Dataset Version:** 1.0  
**Total Files:** 11  
**Total Size:** 1.09 MB  
**Historical Coverage:** June 2004 - March 2026

---

*Built with ❤️ for the data science and finance community*

# Institutional Equity Research Engine

This is a local Python Streamlit application for structured equity research. It asks the mandatory investment-horizon question first, separates future ideas from current holdings, scores 12 institutional-style matrices, shows a live price chart, reviews earnings expectation versus actual, gathers broader research sources, analyzes official company-report data when available, and handles selected leveraged ETFs such as `NVDL` by looking through to the underlying stock.

The app runs on Windows and Mac. It uses Yahoo Finance market data through the `yfinance` package, plus Google News search results, Nasdaq public earnings fallback, SEC EDGAR filing links and XBRL company facts for US-listed companies, and company source links when available. An internet connection is required.

## Files

- `app.py` - the Streamlit application
- `requirements.txt` - the Python packages needed
- `README.md` - this setup guide

## Step 1: Install Python

1. Open this website: https://www.python.org/downloads/
2. Download the latest Python 3 version.
3. Install it.
4. On Windows, tick **Add Python to PATH** during installation.
5. On Mac, use the normal installer defaults.

## Step 2: Open a Terminal

### Easiest Option

Windows:

Double-click `start_windows.bat`.

Mac:

Open Terminal in this folder and run:

```bash
bash start_mac.command
```

The start script will create the local environment, install the required packages, and launch the app.

### Manual Option

Windows:

1. Open the folder containing this app.
2. Click the address bar.
3. Type `cmd` and press Enter.

Mac:

1. Open the folder containing this app in Finder.
2. Right-click the folder.
3. Choose **New Terminal at Folder**.

## Step 3: Create a Virtual Environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 4: Install the App Packages

```bash
pip install -r requirements.txt
```

## Step 5: Start the App

Windows:

```bash
streamlit run app.py
```

Mac:

```bash
streamlit run app.py
```

After a few seconds, your browser should open automatically. If it does not, copy the local address shown in the terminal. It usually looks like:

```text
http://localhost:8501
```

## How to Use

1. Choose the investment horizon first.
2. Choose whether the stock is a future idea or a current holding.
3. Enter a ticker or common company name such as `NVDA`, `nvidia`, `nvdia`, `AAPL`, `Tesla`, or a leveraged ETF such as `NVDL`.
4. Click **Run Institutional Analysis**.

For a current holding, enter your average purchase price and original investment thesis. The app will add portfolio-review outputs such as maintain, add, reduce, or exit.

## Important Notes

- This is a research tool, not financial advice.
- The app uses available market data and neutral assumptions when fields are missing.
- Always verify important conclusions against official company filings, earnings call transcripts, and trusted financial news.
- News coverage comes from multiple sources, including known company official pages for major names such as NVIDIA, but it is still not a substitute for a paid professional terminal or official company filings.
- The official company-report section uses SEC XBRL data where available. It works best for US-listed stocks, not every overseas listing or ETF.
- Leveraged ETFs can decay because they reset daily. They are usually trading products, not long-term replacements for the underlying stock.

## About Moomoo, Broker Data, and Paid Data

Moomoo, Bloomberg, Refinitiv, FactSet, and many broker platforms often show richer analyst and earnings detail because they use licensed data and logged-in services.

This app does not scrape private broker accounts. That is unreliable and may violate the platform's terms. To add Moomoo-style detail safely, use one of these approaches:

1. Export earnings/news/analyst data from the platform and add it manually.
2. Use an official paid market-data API such as Polygon, Intrinio, Financial Modeling Prep, Finnhub, Tiingo, or Alpha Vantage premium.
3. Add your own API key to the app if you subscribe to one of those services.

The current app uses no-login public sources first: Yahoo Finance, Google News, Nasdaq public earnings fallback, SEC EDGAR, and company source links.

## If Installation Fails on Windows

If you see an error mentioning `pandas`, `meson`, or `Visual Studio`, stop the installer window and try again with the updated `requirements.txt`.

If it still fails:

1. Install Python 3.12 from https://www.python.org/downloads/release/python-312/
2. Tick **Add Python to PATH** during installation.
3. Delete the `.venv` folder inside this app folder.
4. Double-click `start_windows.bat` again.

## Deploying to Streamlit Cloud

For Streamlit Cloud, your GitHub repository should include:

- `app.py`
- `requirements.txt`
- `README.md`
- `.streamlit/config.toml` if you added a custom theme

Do not upload:

- `.venv`
- `start_windows.bat`
- `start_mac.command`

In Streamlit Cloud, set the main file path to:

```text
app.py
```

If you see `Exited with status 127`, check that the main file path is not set to `start_windows.bat`, `start_mac.command`, or any command script. Streamlit Cloud runs Linux, so Windows and Mac starter scripts are only for your own computer.

import math
import xml.etree.ElementTree as ET
from difflib import get_close_matches
from datetime import date, timedelta
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="Institutional Equity Research Engine",
    page_icon="📊",
    layout="wide",
)


HORIZON_WEIGHTS = {
    "Swing Trade (1–4 weeks)": {
        "Fundamental": 0.07,
        "Valuation": 0.07,
        "Technical": 0.28,
        "Growth": 0.06,
        "Quality": 0.06,
        "Competitive Moat": 0.04,
        "Management": 0.04,
        "Institutional": 0.10,
        "Analyst Sentiment": 0.07,
        "News & Catalyst": 0.11,
        "Macro": 0.05,
        "Risk": 0.05,
    },
    "Short-Term (1–3 months)": {
        "Fundamental": 0.09,
        "Valuation": 0.09,
        "Technical": 0.22,
        "Growth": 0.07,
        "Quality": 0.07,
        "Competitive Moat": 0.05,
        "Management": 0.05,
        "Institutional": 0.10,
        "Analyst Sentiment": 0.08,
        "News & Catalyst": 0.10,
        "Macro": 0.04,
        "Risk": 0.04,
    },
    "Medium-Term (3–12 months)": {
        "Fundamental": 0.13,
        "Valuation": 0.13,
        "Technical": 0.13,
        "Growth": 0.11,
        "Quality": 0.09,
        "Competitive Moat": 0.07,
        "Management": 0.06,
        "Institutional": 0.07,
        "Analyst Sentiment": 0.07,
        "News & Catalyst": 0.07,
        "Macro": 0.04,
        "Risk": 0.03,
    },
    "Long-Term (1–5 years)": {
        "Fundamental": 0.15,
        "Valuation": 0.15,
        "Technical": 0.06,
        "Growth": 0.13,
        "Quality": 0.12,
        "Competitive Moat": 0.11,
        "Management": 0.08,
        "Institutional": 0.04,
        "Analyst Sentiment": 0.04,
        "News & Catalyst": 0.04,
        "Macro": 0.04,
        "Risk": 0.04,
    },
    "Very Long-Term (5+ years)": {
        "Fundamental": 0.14,
        "Valuation": 0.13,
        "Technical": 0.03,
        "Growth": 0.14,
        "Quality": 0.14,
        "Competitive Moat": 0.14,
        "Management": 0.09,
        "Institutional": 0.03,
        "Analyst Sentiment": 0.03,
        "News & Catalyst": 0.03,
        "Macro": 0.05,
        "Risk": 0.05,
    },
}

LEVERAGED_ETF_MAP = {
    "NVDL": {"underlying": "NVDA", "leverage": 2.0, "name": "GraniteShares 2x Long NVDA Daily ETF"},
    "NVDU": {"underlying": "NVDA", "leverage": 2.0, "name": "Direxion Daily NVDA Bull 2X Shares"},
    "TSLL": {"underlying": "TSLA", "leverage": 2.0, "name": "Direxion Daily TSLA Bull 2X Shares"},
    "TQQQ": {"underlying": "QQQ", "leverage": 3.0, "name": "ProShares UltraPro QQQ"},
    "SQQQ": {"underlying": "QQQ", "leverage": -3.0, "name": "ProShares UltraPro Short QQQ"},
    "SOXL": {"underlying": "SOXX", "leverage": 3.0, "name": "Direxion Daily Semiconductor Bull 3X Shares"},
}

COMMON_COMPANY_ALIASES = {
    "NVIDIA": "NVDA",
    "NVDIA": "NVDA",
    "NIVDIA": "NVDA",
    "NVIDIA CORPORATION": "NVDA",
    "APPLE": "AAPL",
    "APPLE INC": "AAPL",
    "MICROSOFT": "MSFT",
    "MICROSOFT CORPORATION": "MSFT",
    "TESLA": "TSLA",
    "TESLA INC": "TSLA",
    "AMAZON": "AMZN",
    "AMAZON.COM": "AMZN",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "META": "META",
    "FACEBOOK": "META",
    "NETFLIX": "NFLX",
    "AMD": "AMD",
    "ADVANCED MICRO DEVICES": "AMD",
    "PALANTIR": "PLTR",
    "BERKSHIRE": "BRK-B",
    "BERKSHIRE HATHAWAY": "BRK-B",
    "MOOMOO": "FUTU",
    "FUTU": "FUTU",
    "FUTU HOLDINGS": "FUTU",
    "FUTU HOLDINGS LIMITED": "FUTU",
}

OFFICIAL_SOURCE_MAP = {
    "NVDA": {
        "company": "NVIDIA",
        "official_links": [
            ("NVIDIA Investor Relations", "https://investor.nvidia.com/"),
            ("NVIDIA Quarterly Results", "https://investor.nvidia.com/financial-info/quarterly-results/default.aspx"),
            ("NVIDIA Newsroom", "https://nvidianews.nvidia.com/"),
        ],
        "domains": ["investor.nvidia.com", "nvidianews.nvidia.com", "nvidia.com"],
    },
    "AAPL": {
        "company": "Apple",
        "official_links": [
            ("Apple Investor Relations", "https://investor.apple.com/"),
            ("Apple Newsroom", "https://www.apple.com/newsroom/"),
        ],
        "domains": ["investor.apple.com", "apple.com/newsroom"],
    },
    "MSFT": {
        "company": "Microsoft",
        "official_links": [
            ("Microsoft Investor Relations", "https://www.microsoft.com/en-us/Investor"),
            ("Microsoft News", "https://news.microsoft.com/"),
        ],
        "domains": ["microsoft.com/en-us/Investor", "news.microsoft.com"],
    },
    "TSLA": {
        "company": "Tesla",
        "official_links": [
            ("Tesla Investor Relations", "https://ir.tesla.com/"),
            ("Tesla Press Releases", "https://ir.tesla.com/press"),
        ],
        "domains": ["ir.tesla.com", "tesla.com"],
    },
    "AMZN": {
        "company": "Amazon",
        "official_links": [
            ("Amazon Investor Relations", "https://ir.aboutamazon.com/"),
            ("Amazon News", "https://www.aboutamazon.com/news"),
        ],
        "domains": ["ir.aboutamazon.com", "aboutamazon.com/news"],
    },
    "GOOGL": {
        "company": "Alphabet",
        "official_links": [
            ("Alphabet Investor Relations", "https://abc.xyz/investor/"),
            ("Google Blog", "https://blog.google/"),
        ],
        "domains": ["abc.xyz/investor", "blog.google"],
    },
    "META": {
        "company": "Meta",
        "official_links": [
            ("Meta Investor Relations", "https://investor.fb.com/"),
            ("Meta Newsroom", "https://about.fb.com/news/"),
        ],
        "domains": ["investor.fb.com", "about.fb.com/news"],
    },
}


def clamp(value, low=0, high=100):
    if value is None or pd.isna(value):
        return 50
    return max(low, min(high, float(value)))


def score_higher_better(value, excellent, poor):
    if value is None or pd.isna(value):
        return 50
    if excellent == poor:
        return 50
    return clamp((value - poor) / (excellent - poor) * 100)


def score_lower_better(value, excellent, poor):
    if value is None or pd.isna(value):
        return 50
    if excellent == poor:
        return 50
    return clamp((poor - value) / (poor - excellent) * 100)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_ticker(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return info
    except Exception:
        return {}


def alias_symbol(query):
    normalized = " ".join(query.upper().replace(".", " ").replace(",", " ").split())
    compact = normalized.replace(" ", "")
    if normalized in COMMON_COMPANY_ALIASES:
        return COMMON_COMPANY_ALIASES[normalized]
    if compact in COMMON_COMPANY_ALIASES:
        return COMMON_COMPANY_ALIASES[compact]
    choices = list(COMMON_COMPANY_ALIASES.keys())
    match = get_close_matches(normalized, choices, n=1, cutoff=0.78)
    if match:
        return COMMON_COMPANY_ALIASES[match[0]]
    compact_match = get_close_matches(compact, [key.replace(" ", "") for key in choices], n=1, cutoff=0.78)
    if compact_match:
        for key in choices:
            if key.replace(" ", "") == compact_match[0]:
                return COMMON_COMPANY_ALIASES[key]
    return None


def looks_like_ticker(query):
    clean = query.strip().upper().replace(".", "-")
    return bool(clean) and " " not in clean and len(clean) <= 8


def candidate_score(query, quote):
    query_norm = " ".join(query.upper().replace(".", " ").replace(",", " ").split())
    symbol = str(quote.get("symbol", "")).upper()
    short_name = str(quote.get("shortname", "")).upper()
    long_name = str(quote.get("longname", "")).upper()
    name = f"{short_name} {long_name}"
    score = 0
    if symbol == query_norm:
        score += 100
    if query_norm in name:
        score += 80
    tokens = [token for token in query_norm.split() if len(token) > 1]
    score += sum(12 for token in tokens if token in name)
    if quote.get("quoteType") == "EQUITY":
        score += 12
    if quote.get("quoteType") == "ETF":
        score += 10
    if quote.get("exchange") in {"NMS", "NYQ", "NGM", "ASE"}:
        score += 5
    return score


@st.cache_data(ttl=900, show_spinner=False)
def search_symbol_candidates(query):
    clean = query.strip()
    if not clean:
        return []
    try:
        response = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                "q": clean,
                "quotesCount": 12,
                "newsCount": 0,
                "enableFuzzyQuery": "true",
                "quotesQueryId": "tss_match_phrase_query",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        response.raise_for_status()
        quotes = response.json().get("quotes", [])
    except Exception:
        return []
    candidates = []
    for quote in quotes:
        symbol = quote.get("symbol")
        quote_type = quote.get("quoteType")
        if not symbol or quote_type not in {"EQUITY", "ETF", "MUTUALFUND"}:
            continue
        candidates.append({
            "symbol": symbol,
            "name": quote.get("longname") or quote.get("shortname") or symbol,
            "exchange": quote.get("exchange") or quote.get("exchDisp") or "N/A",
            "quoteType": quote_type,
            "score": candidate_score(clean, quote),
        })
    candidates.sort(key=lambda row: row["score"], reverse=True)
    return candidates


@st.cache_data(ttl=900, show_spinner=False)
def resolve_symbol(query):
    clean = query.strip()
    aliased = alias_symbol(clean)
    if aliased:
        info = fetch_ticker(aliased)
        if info and info.get("quoteType"):
            return info.get("symbol", aliased), info
    direct_symbol = clean.upper().replace(" ", "")
    if looks_like_ticker(clean):
        direct_info = fetch_ticker(direct_symbol)
        if direct_info and direct_info.get("quoteType"):
            return direct_info.get("symbol", direct_symbol), direct_info
    for candidate in search_symbol_candidates(clean):
        info = fetch_ticker(candidate["symbol"])
        if info and info.get("quoteType"):
            return info.get("symbol", candidate["symbol"]), info
    direct_info = fetch_ticker(direct_symbol)
    if direct_info and direct_info.get("quoteType"):
        return direct_info.get("symbol", direct_symbol), direct_info
    return direct_symbol, direct_info


@st.cache_data(ttl=900, show_spinner=False)
def fetch_history(symbol, period="2y"):
    data = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    return normalize_history(data)


def normalize_history(data):
    if data is None or data.empty:
        return pd.DataFrame()
    cleaned = data.copy()
    if isinstance(cleaned.columns, pd.MultiIndex):
        cleaned.columns = cleaned.columns.get_level_values(0)
    cleaned = cleaned.loc[:, ~cleaned.columns.duplicated()]
    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    return cleaned


def history_column(data, column):
    if data is None or data.empty or column not in data.columns:
        return pd.Series(dtype=float)
    value = data[column]
    if isinstance(value, pd.DataFrame):
        value = value.iloc[:, 0]
    return pd.to_numeric(pd.Series(value, index=data.index), errors="coerce")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_financials(symbol):
    ticker = yf.Ticker(symbol)
    return {
        "quarterly_income": ticker.quarterly_income_stmt,
        "quarterly_balance": ticker.quarterly_balance_sheet,
        "quarterly_cashflow": ticker.quarterly_cashflow,
        "earnings_dates": safe_earnings_dates(ticker),
        "calendar": safe_calendar(ticker),
        "recommendations": safe_recommendations(ticker),
    }


def safe_earnings_dates(ticker):
    try:
        return ticker.get_earnings_dates(limit=12)
    except Exception:
        return pd.DataFrame()


def safe_calendar(ticker):
    try:
        cal = ticker.calendar
        if isinstance(cal, dict):
            return cal
        if isinstance(cal, pd.DataFrame):
            return cal.to_dict()
        return {}
    except Exception:
        return {}


def safe_recommendations(ticker):
    try:
        rec = ticker.recommendations
        return rec if isinstance(rec, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def fetch_news(symbol):
    try:
        items = yf.Ticker(symbol).news or []
    except Exception:
        return []
    cleaned = []
    for item in items[:8]:
        title = item.get("title")
        publisher = item.get("publisher")
        link = item.get("link")
        published = item.get("providerPublishTime")
        if title:
            cleaned.append({
                "Title": title,
                "Publisher": publisher or "N/A",
                "Published": pd.to_datetime(published, unit="s").strftime("%Y-%m-%d %H:%M") if published else "N/A",
                "Link": link or "",
            })
    return cleaned


@st.cache_data(ttl=900, show_spinner=False)
def fetch_google_news(query, symbol):
    search = quote_plus(f"({symbol} OR {query}) stock earnings financial results analyst rating")
    url = f"https://news.google.com/rss/search?q={search}%20when:30d&hl=en-US&gl=US&ceid=US:en"
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return []
    rows = []
    for item in root.findall(".//item")[:12]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        published = item.findtext("pubDate") or "N/A"
        source_el = item.find("source")
        publisher = source_el.text if source_el is not None and source_el.text else "Google News"
        if title:
            rows.append({
                "Title": title,
                "Publisher": publisher,
                "Published": published,
                "Link": link,
                "Source Type": "Broad news search",
            })
    return rows


@st.cache_data(ttl=900, show_spinner=False)
def fetch_official_company_news(symbol):
    config = OFFICIAL_SOURCE_MAP.get(symbol.upper())
    if not config:
        return []
    domain_query = " OR ".join(f"site:{domain}" for domain in config["domains"])
    search = quote_plus(f"({domain_query}) ({config['company']} earnings OR results OR revenue OR guidance OR product OR data center)")
    url = f"https://news.google.com/rss/search?q={search}%20when:90d&hl=en-US&gl=US&ceid=US:en"
    rows = []
    for title, link in config["official_links"]:
        rows.append({
            "Title": title,
            "Publisher": config["company"],
            "Published": "Official source",
            "Link": link,
            "Source Type": "Company official",
        })
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return rows
    for item in root.findall(".//item")[:10]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        published = item.findtext("pubDate") or "N/A"
        source_el = item.find("source")
        publisher = source_el.text if source_el is not None and source_el.text else config["company"]
        if title:
            rows.append({
                "Title": title,
                "Publisher": publisher,
                "Published": published,
                "Link": link,
                "Source Type": "Company official news/search",
            })
    return rows


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sec_ticker_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": "Institutional Equity Research Engine contact@example.com",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        raw = response.json()
    except Exception:
        return {}
    mapping = {}
    for entry in raw.values():
        ticker = str(entry.get("ticker", "")).upper()
        cik = entry.get("cik_str")
        title = entry.get("title")
        if ticker and cik:
            mapping[ticker] = {"cik": str(cik).zfill(10), "title": title}
    return mapping


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sec_filings(symbol):
    ticker_map = fetch_sec_ticker_map()
    row = ticker_map.get(symbol.upper())
    if not row:
        return []
    cik = row["cik"]
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Institutional Equity Research Engine contact@example.com",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    rows = []
    for form, filing_date, accession, primary_doc in zip(forms, dates, accession_numbers, primary_docs):
        if form not in {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}:
            continue
        accession_clean = accession.replace("-", "")
        link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary_doc}"
        rows.append({
            "Title": f"{form} filing",
            "Publisher": "SEC EDGAR",
            "Published": filing_date,
            "Link": link,
            "Source Type": "Official filing",
        })
        if len(rows) >= 8:
            break
    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sec_company_facts(symbol):
    ticker_map = fetch_sec_ticker_map()
    row = ticker_map.get(symbol.upper())
    if not row:
        return {"available": False, "reason": "No SEC CIK found for this ticker.", "facts": {}, "cik": None}
    cik = row["cik"]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {
        "User-Agent": "Institutional Equity Research Engine contact@example.com",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return {"available": True, "reason": "", "facts": response.json(), "cik": cik}
    except Exception as exc:
        return {"available": False, "reason": f"SEC company facts unavailable: {exc}", "facts": {}, "cik": cik}


def latest_sec_fact(company_facts, tags, form_filter=None):
    facts = company_facts.get("facts", {}).get("us-gaap", {}) if company_facts.get("available") else {}
    candidates = []
    allowed_forms = set(form_filter or ["10-Q", "10-K", "10-Q/A", "10-K/A"])
    for tag in tags:
        units = facts.get(tag, {}).get("units", {})
        for unit_rows in units.values():
            for row in unit_rows:
                if row.get("form") not in allowed_forms or row.get("val") is None:
                    continue
                try:
                    numeric_value = float(row.get("val"))
                except (TypeError, ValueError):
                    continue
                candidates.append({
                    "tag": tag,
                    "value": numeric_value,
                    "end": row.get("end"),
                    "filed": row.get("filed"),
                    "form": row.get("form"),
                    "frame": row.get("frame"),
                    "fp": row.get("fp"),
                    "fy": row.get("fy"),
                })
    if not candidates:
        return None
    framed = [row for row in candidates if row.get("frame")]
    candidates = framed or candidates
    candidates.sort(key=lambda row: (row.get("end") or "", row.get("filed") or "", row.get("frame") or ""), reverse=True)
    return candidates[0]


def sec_report_summary(company_facts):
    if not company_facts.get("available"):
        return None
    metrics = {
        "Revenue": latest_sec_fact(company_facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]),
        "Net Income": latest_sec_fact(company_facts, ["NetIncomeLoss"]),
        "Gross Profit": latest_sec_fact(company_facts, ["GrossProfit"]),
        "Operating Income": latest_sec_fact(company_facts, ["OperatingIncomeLoss"]),
        "Cash": latest_sec_fact(company_facts, ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]),
        "Total Assets": latest_sec_fact(company_facts, ["Assets"]),
        "Total Liabilities": latest_sec_fact(company_facts, ["Liabilities"]),
        "Operating Cash Flow": latest_sec_fact(company_facts, ["NetCashProvidedByUsedInOperatingActivities"]),
        "Capital Expenditure": latest_sec_fact(company_facts, ["PaymentsToAcquirePropertyPlantAndEquipment"]),
        "Diluted EPS": latest_sec_fact(company_facts, ["EarningsPerShareDiluted"]),
    }
    if not any(metrics.values()):
        return None
    revenue = metrics["Revenue"]["value"] if metrics.get("Revenue") else None
    net_income = metrics["Net Income"]["value"] if metrics.get("Net Income") else None
    assets = metrics["Total Assets"]["value"] if metrics.get("Total Assets") else None
    liabilities = metrics["Total Liabilities"]["value"] if metrics.get("Total Liabilities") else None
    op_cash = metrics["Operating Cash Flow"]["value"] if metrics.get("Operating Cash Flow") else None
    capex = metrics["Capital Expenditure"]["value"] if metrics.get("Capital Expenditure") else None
    net_margin = net_income / revenue if revenue else None
    leverage_ratio = liabilities / assets if assets else None
    fcf = op_cash - abs(capex) if op_cash is not None and capex is not None else None
    flags = []
    if net_margin is not None and net_margin < 0.05:
        flags.append("thin net margin")
    if leverage_ratio is not None and leverage_ratio > 0.70:
        flags.append("high liabilities versus assets")
    if fcf is not None and fcf < 0:
        flags.append("negative free cash flow proxy")
    if not flags:
        flags.append("no major official-report red flag from these headline metrics")
    return {
        "metrics": metrics,
        "net_margin": net_margin,
        "leverage_ratio": leverage_ratio,
        "fcf": fcf,
        "flags": flags,
    }


def render_sec_report_analysis(symbol, company_facts, sec_filings):
    st.subheader("Official Company Report Analysis")
    if not company_facts.get("available"):
        st.write(company_facts.get("reason") or "Official SEC company facts are not available for this ticker.")
        st.caption("This section works best for US-listed companies that file 10-K and 10-Q reports with the SEC.")
        return
    summary = sec_report_summary(company_facts)
    if not summary:
        st.write(
            "SEC company facts were found, but standard operating-company financial tags were not available. "
            "This often happens for ETFs, funds, some foreign issuers, or entities that do not report like a normal operating company."
        )
        if sec_filings:
            st.write("Official filing links are still available:")
            st.dataframe(pd.DataFrame(sec_filings[:6]), use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Link")})
        return
    rows = []
    for name, fact in summary["metrics"].items():
        if not fact:
            rows.append({"Metric": name, "Latest Reported Value": "N/A", "Period End": "N/A", "Form": "N/A", "Filed": "N/A"})
            continue
        value = fact["value"]
        display_value = f"{value:.2f}" if name == "Diluted EPS" else money(value)
        rows.append({
            "Metric": name,
            "Latest Reported Value": display_value,
            "Period End": fact.get("end") or "N/A",
            "Form": fact.get("form") or "N/A",
            "Filed": fact.get("filed") or "N/A",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Reported Net Margin", pct(summary["net_margin"]))
    c2.metric("Liabilities / Assets", pct(summary["leverage_ratio"]))
    c3.metric("FCF Proxy", money(summary["fcf"]))
    st.write(
        "Official-report read-through: "
        + ", ".join(summary["flags"])
        + ". These figures come from SEC XBRL company facts, not news headlines."
    )
    latest_reports = [row for row in sec_filings if row.get("Title") in {"10-Q filing", "10-K filing"}]
    if latest_reports:
        st.write("Latest official report links:")
        st.dataframe(pd.DataFrame(latest_reports[:4]), use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Link")})


def flatten_nasdaq_rows(node):
    rows = []
    if isinstance(node, dict):
        maybe_rows = node.get("rows")
        if isinstance(maybe_rows, list):
            rows.extend([row for row in maybe_rows if isinstance(row, dict)])
        for value in node.values():
            rows.extend(flatten_nasdaq_rows(value))
    elif isinstance(node, list):
        for value in node:
            rows.extend(flatten_nasdaq_rows(value))
    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_nasdaq_earnings(symbol):
    url = f"https://api.nasdaq.com/api/company/{symbol.upper()}/earnings?limit=12"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": f"https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}/earnings",
    }
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {"rows": [], "source": url}
    rows = flatten_nasdaq_rows(payload.get("data", payload))
    cleaned = []
    for row in rows:
        if not any("eps" in str(key).lower() or "forecast" in str(key).lower() or "surprise" in str(key).lower() for key in row.keys()):
            continue
        normalized = {"Source": "Nasdaq"}
        for key, value in row.items():
            label = str(key).replace("_", " ").strip().title()
            if isinstance(value, (str, int, float)) or value is None:
                normalized[label] = value
        if len(normalized) > 1:
            cleaned.append(normalized)
    return {"rows": cleaned[:12], "source": url}


def combine_research_sources(symbol, query, yahoo_news, google_news, official_news, sec_filings, info):
    rows = []
    rows.extend(official_news)
    for item in yahoo_news:
        enriched = dict(item)
        enriched["Source Type"] = "Yahoo Finance"
        rows.append(enriched)
    rows.extend(google_news)
    rows.extend(sec_filings)
    investor_url = first_available(info, ["irWebsite", "website"])
    if investor_url:
        rows.insert(0, {
            "Title": "Company website / investor relations starting point",
            "Publisher": info.get("longName") or symbol,
            "Published": "Official source",
            "Link": investor_url,
            "Source Type": "Company source",
        })
    seen = set()
    unique = []
    for row in rows:
        key = (row.get("Title", ""), row.get("Link", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def first_available(info, keys, default=None):
    for key in keys:
        value = info.get(key)
        if value not in (None, "None", "N/A"):
            return value
    return default


def pct(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value * 100:.1f}%"


def money(value):
    if value is None or pd.isna(value):
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.2f}"


def latest_statement_value(statement, row_name):
    if statement is None or statement.empty or row_name not in statement.index:
        return None
    series = statement.loc[row_name].dropna()
    if series.empty:
        return None
    return float(series.iloc[0])


def statement_growth(statement, row_name):
    if statement is None or statement.empty or row_name not in statement.index:
        return None
    series = statement.loc[row_name].dropna()
    if len(series) < 2 or series.iloc[1] == 0:
        return None
    return float((series.iloc[0] - series.iloc[1]) / abs(series.iloc[1]))


def add_indicators(hist):
    data = normalize_history(hist)
    if data.empty:
        return data
    close = history_column(data, "Close")
    data["EMA20"] = close.ewm(span=20, adjust=False).mean()
    data["EMA50"] = close.ewm(span=50, adjust=False).mean()
    data["MA200"] = close.rolling(200).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    data["RSI"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    data["MACD"] = ema12 - ema26
    data["MACDSignal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    return data


def technical_context(data):
    if data.empty or len(data) < 50:
        return {
            "score": 50,
            "trend": "Insufficient chart history for a reliable trend read.",
            "support": None,
            "resistance": None,
            "rsi": None,
            "latest_close": None,
        }
    d = add_indicators(data).dropna(subset=["Close"])
    latest = d.iloc[-1]
    close = float(latest["Close"])
    ema20 = latest.get("EMA20")
    ema50 = latest.get("EMA50")
    ma200 = latest.get("MA200")
    rsi = latest.get("RSI")
    macd = latest.get("MACD")
    signal = latest.get("MACDSignal")
    support = float(d["Low"].tail(90).min())
    resistance = float(d["High"].tail(90).max())
    score = 50
    score += 12 if close > ema20 else -8
    score += 12 if close > ema50 else -8
    if not pd.isna(ma200):
        score += 14 if close > ma200 else -12
    if not pd.isna(rsi):
        if 45 <= rsi <= 65:
            score += 8
        elif 30 <= rsi < 45 or 65 < rsi <= 75:
            score += 2
        else:
            score -= 8
    if not pd.isna(macd) and not pd.isna(signal):
        score += 8 if macd > signal else -5
    trend = "Bullish trend alignment" if score >= 65 else "Weak or mixed trend alignment" if score >= 45 else "Bearish trend alignment"
    return {
        "score": clamp(score),
        "trend": trend,
        "support": support,
        "resistance": resistance,
        "rsi": None if pd.isna(rsi) else float(rsi),
        "latest_close": close,
    }


def recent_price_explanation(data, news_items):
    data = normalize_history(data)
    if data.empty or len(data) < 25:
        return "Not enough price history to explain recent movement."
    close = history_column(data, "Close").dropna()
    last = close.iloc[-1]
    changes = {
        "1 day": float(close.pct_change().iloc[-1]),
        "5 trading days": float(last / close.iloc[-6] - 1) if len(close) > 6 else np.nan,
        "1 month": float(last / close.iloc[-22] - 1) if len(close) > 22 else np.nan,
        "3 months": float(last / close.iloc[-64] - 1) if len(close) > 64 else np.nan,
    }
    biggest = max(changes.items(), key=lambda kv: abs(0 if pd.isna(kv[1]) else kv[1]))
    direction = "spike" if biggest[1] > 0.05 else "drop" if biggest[1] < -0.05 else "stagnation or consolidation"
    news_note = ""
    if news_items:
        top_titles = "; ".join(item["Title"] for item in news_items[:3])
        news_note = f" Recent headlines to check against the move: {top_titles}."
    return (
        f"Recent tape suggests {direction}: {biggest[0]} move is {pct(biggest[1])}. "
        "Use the news and earnings sections below to judge whether the move was justified by fundamentals or mainly sentiment."
        f"{news_note}"
    )


def earnings_context(symbol, data, financials, nasdaq_earnings):
    data = normalize_history(data)
    earnings = financials.get("earnings_dates", pd.DataFrame())
    if earnings is None or earnings.empty:
        rows = nasdaq_earnings.get("rows", []) if nasdaq_earnings else []
        if rows:
            latest_row = rows[0]
            fields = ", ".join(f"{key}: {value}" for key, value in latest_row.items() if key != "Source" and value not in (None, ""))
            return {
                "latest": f"Yahoo did not return EPS estimate/actual data. Nasdaq fallback returned latest earnings fields: {fields}.",
                "next": "Next report date should be verified from the company investor-relations calendar or Nasdaq earnings page.",
                "rows": rows,
            }
        return {
            "latest": "Earnings estimate data is not available from Yahoo Finance or the Nasdaq public fallback for this ticker.",
            "next": "Next report date is not available from the connected public sources.",
            "rows": [],
        }
    earnings = earnings.sort_index(ascending=False)
    today = pd.Timestamp(date.today(), tz=None)
    past = earnings[earnings.index.tz_localize(None) <= today] if earnings.index.tz is not None else earnings[earnings.index <= today]
    future = earnings[earnings.index.tz_localize(None) > today] if earnings.index.tz is not None else earnings[earnings.index > today]
    latest_text = "No past earnings record available."
    next_text = "No future earnings date currently available."
    if not past.empty:
        latest_date = past.index[0]
        row = past.iloc[0]
        eps_est = row.get("EPS Estimate")
        eps_actual = row.get("Reported EPS")
        surprise = row.get("Surprise(%)")
        reaction = "price reaction unavailable"
        if not data.empty:
            idx = data.index.tz_localize(None) if data.index.tz is not None else data.index
            local = data.copy()
            local.index = idx
            after = local[local.index >= pd.Timestamp(latest_date).tz_localize(None)]
            before = local[local.index < pd.Timestamp(latest_date).tz_localize(None)]
            if not after.empty and not before.empty:
                after_close = history_column(after, "Close")
                before_close = history_column(before, "Close")
                reaction_pct = after_close.iloc[min(1, len(after_close) - 1)] / before_close.iloc[-1] - 1
                reaction = f"next-session reaction approximately {pct(reaction_pct)}"
        latest_text = (
            f"Latest report: {pd.Timestamp(latest_date).date()}. "
            f"EPS estimate: {eps_est if pd.notna(eps_est) else 'N/A'}, "
            f"actual: {eps_actual if pd.notna(eps_actual) else 'N/A'}, "
            f"surprise: {surprise if pd.notna(surprise) else 'N/A'}. "
            f"Stock {reaction}."
        )
    if not future.empty:
        next_date = future.index[-1] if len(future) else future.index[0]
        row = future.loc[next_date]
        next_text = (
            f"Next expected report: {pd.Timestamp(next_date).date()}. "
            f"Current EPS estimate: {row.get('EPS Estimate', 'N/A')}. "
            "A clean beat with raised guidance usually supports upside; a beat without guidance strength can fade, especially if valuation is already demanding."
        )
    return {"latest": latest_text, "next": next_text, "rows": nasdaq_earnings.get("rows", []) if nasdaq_earnings else []}


def estimate_fair_value(info, financials):
    price = first_available(info, ["currentPrice", "regularMarketPrice", "previousClose"])
    eps = first_available(info, ["trailingEps", "forwardEps"])
    revenue_growth = info.get("revenueGrowth")
    fcf = first_available(info, ["freeCashflow", "operatingCashflow"])
    shares = info.get("sharesOutstanding")
    target_mean = info.get("targetMeanPrice")
    pe_anchor = None
    dcf_anchor = None
    if eps and eps > 0:
        growth = 0.05 if revenue_growth is None else clamp(revenue_growth, -0.05, 0.25)
        fair_pe = 14 + (growth * 60)
        pe_anchor = eps * fair_pe
    if fcf and shares and shares > 0:
        growth = 0.04 if revenue_growth is None else clamp(revenue_growth, -0.02, 0.18)
        discount = 0.10
        terminal = 0.025
        fcf_per_share = fcf / shares
        value = 0
        for year in range(1, 6):
            value += fcf_per_share * ((1 + growth) ** year) / ((1 + discount) ** year)
        terminal_value = fcf_per_share * ((1 + growth) ** 5) * (1 + terminal) / (discount - terminal)
        dcf_anchor = value + terminal_value / ((1 + discount) ** 5)
    anchors = [v for v in [pe_anchor, dcf_anchor, target_mean] if v and v > 0]
    if not anchors:
        return price, "Insufficient EPS, cash flow, or analyst target data; using current price as a neutral placeholder."
    fair_value = float(np.median(anchors))
    return fair_value, "Fair value blends simple earnings power, cash-flow DCF, and available analyst target data."


def build_matrices(symbol, info, hist, financials):
    q_income = financials.get("quarterly_income")
    q_balance = financials.get("quarterly_balance")
    q_cashflow = financials.get("quarterly_cashflow")
    revenue_growth = first_available(info, ["revenueGrowth", "earningsQuarterlyGrowth"])
    eps_growth = info.get("earningsGrowth")
    gross_margin = info.get("grossMargins")
    operating_margin = info.get("operatingMargins")
    profit_margin = info.get("profitMargins")
    debt_to_equity = info.get("debtToEquity")
    current_ratio = info.get("currentRatio")
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    peg = info.get("pegRatio")
    ev_ebitda = info.get("enterpriseToEbitda")
    price_to_fcf = None
    market_cap = info.get("marketCap")
    fcf = first_available(info, ["freeCashflow", "operatingCashflow"])
    if market_cap and fcf and fcf > 0:
        price_to_fcf = market_cap / fcf
    tech = technical_context(hist)
    rev_q_growth = statement_growth(q_income, "Total Revenue")
    net_q_growth = statement_growth(q_income, "Net Income")
    total_debt = latest_statement_value(q_balance, "Total Debt")
    cash = latest_statement_value(q_balance, "Cash And Cash Equivalents")
    op_cash = latest_statement_value(q_cashflow, "Operating Cash Flow")
    capex = latest_statement_value(q_cashflow, "Capital Expenditure")
    latest_fcf = None
    if op_cash is not None:
        latest_fcf = op_cash + (capex or 0)
    fair_value, fair_note = estimate_fair_value(info, financials)
    price = first_available(info, ["currentPrice", "regularMarketPrice", "previousClose"])
    mos = None if not price or not fair_value else (fair_value - price) / fair_value

    matrices = {
        "Fundamental": {
            "score": np.mean([
                score_higher_better(revenue_growth, 0.20, -0.05),
                score_higher_better(eps_growth, 0.20, -0.10),
                score_higher_better(latest_fcf or fcf, 5_000_000_000, -500_000_000),
                score_higher_better(profit_margin, 0.25, 0.00),
                score_lower_better(debt_to_equity, 20, 200),
            ]),
            "drivers": f"Revenue growth {pct(revenue_growth)}, EPS growth {pct(eps_growth)}, profit margin {pct(profit_margin)}, debt/equity {debt_to_equity or 'N/A'}.",
        },
        "Valuation": {
            "score": np.mean([
                score_lower_better(trailing_pe, 15, 60),
                score_lower_better(forward_pe, 14, 50),
                score_lower_better(peg, 1.0, 3.5),
                score_lower_better(ev_ebitda, 10, 35),
                score_lower_better(price_to_fcf, 18, 60),
                score_higher_better(mos, 0.25, -0.25),
            ]),
            "drivers": f"P/E {trailing_pe or 'N/A'}, forward P/E {forward_pe or 'N/A'}, PEG {peg or 'N/A'}, EV/EBITDA {ev_ebitda or 'N/A'}, P/FCF {price_to_fcf and round(price_to_fcf, 1) or 'N/A'}.",
        },
        "Technical": {
            "score": tech["score"],
            "drivers": f"{tech['trend']}. RSI {tech['rsi'] and round(tech['rsi'], 1) or 'N/A'}, support {tech['support'] and round(tech['support'], 2) or 'N/A'}, resistance {tech['resistance'] and round(tech['resistance'], 2) or 'N/A'}.",
        },
        "Growth": {
            "score": np.mean([
                score_higher_better(revenue_growth, 0.25, -0.05),
                score_higher_better(eps_growth, 0.25, -0.10),
                score_higher_better(rev_q_growth, 0.15, -0.08),
                score_higher_better(net_q_growth, 0.18, -0.15),
            ]),
            "drivers": f"Reported revenue growth {pct(revenue_growth)}, quarter revenue growth {pct(rev_q_growth)}, quarter net income growth {pct(net_q_growth)}.",
        },
        "Quality": {
            "score": np.mean([
                score_higher_better(info.get("returnOnEquity"), 0.25, 0.02),
                score_higher_better(info.get("returnOnAssets"), 0.12, 0.01),
                score_higher_better(gross_margin, 0.60, 0.20),
                score_higher_better(profit_margin, 0.25, 0.00),
                score_higher_better(fcf / market_cap if fcf and market_cap else None, 0.06, 0.00),
            ]),
            "drivers": f"ROE {pct(info.get('returnOnEquity'))}, ROA {pct(info.get('returnOnAssets'))}, gross margin {pct(gross_margin)}, FCF yield {pct(fcf / market_cap) if fcf and market_cap else 'N/A'}.",
        },
        "Competitive Moat": {
            "score": np.mean([
                score_higher_better(gross_margin, 0.65, 0.25),
                score_higher_better(operating_margin, 0.35, 0.05),
                score_higher_better(market_cap, 300_000_000_000, 2_000_000_000),
                score_higher_better(revenue_growth, 0.18, -0.03),
            ]),
            "drivers": "Moat proxy uses margins, scale, and growth persistence. Qualitative brand, IP, and switching-cost review should be confirmed manually.",
        },
        "Management": {
            "score": np.mean([
                score_higher_better(info.get("returnOnEquity"), 0.25, 0.03),
                score_higher_better(fcf, 5_000_000_000, -500_000_000),
                score_lower_better(debt_to_equity, 25, 180),
                score_higher_better(info.get("heldPercentInsiders"), 0.08, 0.00),
            ]),
            "drivers": f"Capital allocation proxy: ROE {pct(info.get('returnOnEquity'))}, FCF {money(fcf)}, debt/equity {debt_to_equity or 'N/A'}, insider ownership {pct(info.get('heldPercentInsiders'))}.",
        },
        "Institutional": {
            "score": np.mean([
                score_higher_better(info.get("heldPercentInstitutions"), 0.75, 0.15),
                score_higher_better(info.get("heldPercentInsiders"), 0.08, 0.00),
                score_lower_better(info.get("sharesPercentSharesOut"), 0.02, 0.15),
            ]),
            "drivers": f"Institutional ownership {pct(info.get('heldPercentInstitutions'))}, insider ownership {pct(info.get('heldPercentInsiders'))}, short interest {pct(info.get('sharesPercentSharesOut'))}.",
        },
        "Analyst Sentiment": {
            "score": np.mean([
                score_lower_better(info.get("recommendationMean"), 1.8, 4.0),
                score_higher_better(info.get("numberOfAnalystOpinions"), 30, 2),
                score_higher_better(info.get("targetMeanPrice") / price - 1 if info.get("targetMeanPrice") and price else None, 0.25, -0.20),
            ]),
            "drivers": f"Recommendation mean {info.get('recommendationMean') or 'N/A'}, analyst count {info.get('numberOfAnalystOpinions') or 'N/A'}, target mean {money(info.get('targetMeanPrice'))}.",
        },
        "News & Catalyst": {
            "score": np.mean([
                score_higher_better(info.get("targetMeanPrice") / price - 1 if info.get("targetMeanPrice") and price else None, 0.25, -0.20),
                score_higher_better(revenue_growth, 0.20, -0.05),
                score_higher_better(eps_growth, 0.20, -0.10),
                score_higher_better(tech["score"], 70, 35),
            ]),
            "drivers": "Catalyst score uses earnings growth, revenue growth, analyst upside, and tape confirmation. Read current news before committing capital.",
        },
        "Macro": {
            "score": np.mean([
                60 if info.get("sector") in ["Technology", "Communication Services", "Healthcare", "Industrials"] else 50,
                score_higher_better(revenue_growth, 0.15, -0.05),
                score_lower_better(info.get("beta"), 0.8, 2.2),
            ]),
            "drivers": f"Sector {info.get('sector', 'N/A')}, industry {info.get('industry', 'N/A')}, beta {info.get('beta') or 'N/A'}. Higher-beta names are more exposed to rates and risk appetite.",
        },
        "Risk": {
            "score": np.mean([
                score_lower_better(debt_to_equity, 20, 200),
                score_lower_better(info.get("beta"), 0.8, 2.5),
                score_lower_better(info.get("sharesPercentSharesOut"), 0.02, 0.20),
                score_higher_better(current_ratio, 2.0, 0.7),
                score_higher_better(profit_margin, 0.20, -0.05),
            ]),
            "drivers": f"Debt/equity {debt_to_equity or 'N/A'}, beta {info.get('beta') or 'N/A'}, short interest {pct(info.get('sharesPercentSharesOut'))}, current ratio {current_ratio or 'N/A'}.",
        },
    }
    for matrix in matrices.values():
        matrix["score"] = round(clamp(matrix["score"]), 1)
    return matrices, {
        "fair_value": fair_value,
        "fair_note": fair_note,
        "price": price,
        "margin_of_safety": mos,
        "technical": tech,
        "revenue_growth": revenue_growth,
        "eps_growth": eps_growth,
        "fcf": fcf,
        "total_debt": total_debt,
        "cash": cash,
    }


def weighted_score(matrices, weights):
    return round(sum(matrices[name]["score"] * weight for name, weight in weights.items()), 1)


def recommendation(overall, context, classification):
    mos = context["margin_of_safety"]
    tech_score = context["technical"]["score"]
    risk_score = context.get("risk_score", 50)
    if classification.startswith("Current"):
        if overall >= 72 and (mos is None or mos > 0.05):
            return "Add"
        if overall >= 58:
            return "Maintain"
        if overall >= 45:
            return "Reduce"
        return "Exit"
    if overall >= 75 and mos is not None and mos >= 0.10 and tech_score >= 50:
        return "BUY"
    if overall >= 60:
        return "WATCHLIST"
    if overall >= 48:
        return "HOLD"
    return "AVOID"


def build_cases(overall, context, matrices):
    price = context["price"]
    fair = context["fair_value"]
    tech = context["technical"]
    bull_price = fair * 1.20 if fair else None
    bear_price = fair * 0.70 if fair else None
    base = (
        f"Base case: score {overall}/100 supports a fair value near {money(fair)}. "
        "The company must keep revenue, margins, and cash flow moving in the same direction for the current valuation to hold."
    )
    bull = (
        f"Bull case: upside toward {money(bull_price)} requires sustained estimate beats, margin durability, and trend confirmation above resistance "
        f"near {tech['resistance'] and round(tech['resistance'], 2) or 'N/A'}."
    )
    bear = (
        f"Bear case: downside toward {money(bear_price)} can occur if growth decelerates, valuation multiples compress, or support near "
        f"{tech['support'] and round(tech['support'], 2) or 'N/A'} fails."
    )
    failure = (
        "Key failure scenarios: demand slows faster than consensus expects, competitors pressure margins, regulation or macro rates hurt multiples, "
        "or earnings beats fail to produce raised guidance."
    )
    return bull, base, bear, failure


def chart(symbol, data):
    data = normalize_history(data)
    if data.empty:
        st.warning("No chart data returned. Check the ticker or internet connection.")
        return
    d = add_indicators(data)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=d.index,
        open=d["Open"],
        high=d["High"],
        low=d["Low"],
        close=d["Close"],
        name=symbol,
    ))
    for col, color in [("EMA20", "#00A884"), ("EMA50", "#7B61FF"), ("MA200", "#D04A02")]:
        if col in d:
            fig.add_trace(go.Scatter(x=d.index, y=d[col], mode="lines", name=col, line=dict(width=1.5, color=color)))
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_matrix_table(matrices):
    rows = [{"Matrix": name, "Score": data["score"], "Evidence / Drivers": data["drivers"]} for name, data in matrices.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def leveraged_etf_panel(symbol, hist):
    hist = normalize_history(hist)
    key = symbol.upper()
    if key not in LEVERAGED_ETF_MAP:
        return None
    meta = LEVERAGED_ETF_MAP[key]
    underlying = meta["underlying"]
    underlying_hist = fetch_history(underlying, "2y")
    st.subheader("Leveraged ETF Look-Through")
    st.info(
        f"{key} is treated as a leveraged product linked to {underlying}. The analysis should focus on both {key}'s path-dependent behavior and "
        f"{underlying}'s fundamentals. Daily leverage target: {meta['leverage']}x."
    )
    if not hist.empty and not underlying_hist.empty:
        joined = pd.concat([
            history_column(hist, "Close").rename(key),
            history_column(underlying_hist, "Close").rename(underlying),
        ], axis=1).dropna()
        if len(joined) > 30:
            ret_etf = joined[key].iloc[-1] / joined[key].iloc[0] - 1
            ret_underlying = joined[underlying].iloc[-1] / joined[underlying].iloc[0] - 1
            expected = ret_underlying * meta["leverage"]
            decay_gap = ret_etf - expected
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{key} 2Y Return", pct(ret_etf))
            c2.metric(f"{underlying} 2Y Return", pct(ret_underlying))
            c3.metric("Path / Decay Gap", pct(decay_gap))
            st.caption(
                "Leveraged ETFs reset daily. In volatile sideways markets, compounding can cause decay; in persistent trends, compounding can help."
            )
    return underlying


def sidebar_inputs():
    st.sidebar.header("Research Setup")
    horizon = st.sidebar.radio("What is the investment horizon?", list(HORIZON_WEIGHTS.keys()))
    classification = st.sidebar.radio(
        "Stock type",
        ["Future / Not Yet Bought (Watchlist / Potential Buy)", "Current Holding (Portfolio Review)"],
    )
    query = st.sidebar.text_input(
        "Company name or ticker",
        value="NVDA",
        help="Examples: NVDA, NVIDIA, NVDIA, NVDL, AAPL, Tesla, Moomoo, Futu",
    )
    st.sidebar.caption("Full names work for common companies. Example: NVIDIA -> NVDA, Moomoo/Futu -> FUTU.")
    entry_price = None
    thesis = ""
    if classification.startswith("Current"):
        entry_price = st.sidebar.number_input("Your average entry price", min_value=0.0, value=0.0, step=0.01)
        thesis = st.sidebar.text_area("Original investment thesis", placeholder="Example: I bought because AI data center growth would accelerate.")
    run = st.sidebar.button("Run Institutional Analysis", type="primary")
    return horizon, classification, query.strip(), entry_price, thesis, run


def main():
    st.title("Institutional Equity Research Engine")
    st.caption(
        "A critical, data-driven Streamlit research assistant using Yahoo Finance market data, broad news search, SEC filings, "
        "and company source links when available. Verify before trading."
    )

    horizon, classification, query, entry_price, thesis, run = sidebar_inputs()
    if not run:
        st.warning("Start by answering the mandatory first question in the sidebar: What is the investment horizon?")
        st.write("Then enter a ticker or company name and choose whether it is a future idea or a current holding.")
        return
    if not query:
        st.error("Please enter a ticker or company name.")
        return

    symbol = query.upper().replace(" ", "")
    with st.spinner("Fetching live market, financial, earnings, and analyst data..."):
        official_symbol, info = resolve_symbol(query)
        if not info or info.get("quoteType") is None:
            st.error("I could not find that ticker. Try the exchange ticker, for example NVDA instead of NVIDIA.")
            return
        hist = fetch_history(official_symbol, "2y")
        financials = fetch_financials(official_symbol)
        nasdaq_earnings = fetch_nasdaq_earnings(official_symbol)
        yahoo_news = fetch_news(official_symbol)
        google_news = fetch_google_news(query, official_symbol)
        official_news = fetch_official_company_news(official_symbol)
        sec_filings = fetch_sec_filings(official_symbol)
        sec_company_facts = fetch_sec_company_facts(official_symbol)
        news_items = combine_research_sources(official_symbol, query, yahoo_news, google_news, official_news, sec_filings, info)

    st.header(f"{info.get('longName') or info.get('shortName') or official_symbol} ({official_symbol})")
    if query.strip().upper().replace(" ", "").replace(".", "-") != official_symbol.upper():
        st.caption(f"Input resolved to ticker: {official_symbol}")
    underlying = leveraged_etf_panel(official_symbol, hist)

    c1, c2, c3, c4 = st.columns(4)
    price = first_available(info, ["currentPrice", "regularMarketPrice", "previousClose"])
    c1.metric("Latest Price", money(price))
    c2.metric("Market Cap", money(info.get("marketCap")))
    c3.metric("Sector", info.get("sector", "N/A"))
    c4.metric("Beta", info.get("beta", "N/A"))

    chart(official_symbol, hist)
    st.write(recent_price_explanation(hist, news_items))

    st.subheader("Research Sources: News, Filings, and Company Links")
    if news_items:
        news_df = pd.DataFrame(news_items)
        st.dataframe(news_df, use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Link")})
    else:
        st.write("No live source links were returned. Try the official ticker symbol or check your internet connection.")
    st.caption(
        "Sources include Yahoo Finance, Google News search results, SEC EDGAR filings for US-listed companies, and company website links when available. "
        "This is research support, not personalized financial advice."
    )

    render_sec_report_analysis(official_symbol, sec_company_facts, sec_filings)
    if underlying and underlying != official_symbol:
        with st.spinner(f"Loading official company report data for underlying {underlying}..."):
            underlying_sec_filings = fetch_sec_filings(underlying)
            underlying_sec_facts = fetch_sec_company_facts(underlying)
        st.subheader(f"Underlying Official Company Report: {underlying}")
        render_sec_report_analysis(underlying, underlying_sec_facts, underlying_sec_filings)

    matrices, context = build_matrices(official_symbol, info, hist, financials)
    context["risk_score"] = matrices["Risk"]["score"]
    overall = weighted_score(matrices, HORIZON_WEIGHTS[horizon])
    rec = recommendation(overall, context, classification)
    bull, base, bear, failure = build_cases(overall, context, matrices)
    earnings = earnings_context(official_symbol, hist, financials, nasdaq_earnings)

    st.subheader("Risk First")
    st.error(
        f"Downside risks before upside: {failure} Risk matrix score is {matrices['Risk']['score']}/100, "
        "where higher means lower measured risk."
    )

    st.subheader("12-Matrix Scorecard")
    render_matrix_table(matrices)

    st.subheader("Weighted Outcome")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall Score", f"{overall}/100")
    m2.metric("Recommendation", rec)
    m3.metric("Fair Value Estimate", money(context["fair_value"]))
    m4.metric("Margin of Safety", pct(context["margin_of_safety"]))
    st.caption(context["fair_note"])

    st.subheader("Scenario Analysis")
    st.write(bear)
    st.write(base)
    st.write(bull)

    tech = context["technical"]
    stop_loss = tech["support"] * 0.97 if tech["support"] else None
    entry_zone = context["fair_value"] * 0.85 if context["fair_value"] else None
    add_zone = context["fair_value"] * 0.75 if context["fair_value"] else None
    conviction = max(1, min(10, round(overall / 10)))

    if classification.startswith("Future"):
        st.subheader("Section A: Future / Not Held Stock")
        st.write(f"Entry zone: around {money(entry_zone)} or better, unless fundamentals inflect materially higher.")
        st.write(f"Add zone: around {money(add_zone)} or better after confirming thesis durability.")
        st.write(f"Stop loss: {money(stop_loss)} for shorter horizons; long-term investors should use thesis-break criteria more than mechanical stops.")
        st.write("Exit criteria: thesis breaks, margins deteriorate, guidance misses repeatedly, or valuation exceeds fair value without earnings support.")
        st.write(f"Position sizing suggestion: {1 if conviction < 5 else 2 if conviction < 8 else 4}% starter size, scaled only after evidence improves.")
        st.write(f"Conviction score: {conviction}/10.")
        st.success(f"Final recommendation: {rec}")
    else:
        st.subheader("Section B: Current Holding / Portfolio Review")
        entry_note = "Entry price not provided."
        if entry_price and price:
            entry_note = f"Position is currently {pct(price / entry_price - 1)} versus your average entry price."
        thesis_note = "Original thesis was not entered, so thesis validity is judged only from current data."
        if thesis:
            thesis_note = f"Original thesis entered: {thesis}"
        st.write(entry_note)
        st.write(thesis_note)
        st.write(
            "Thesis check: fundamentals are improving if revenue growth, EPS growth, FCF, and margins are positive and score above 60. "
            "They are deteriorating if these scores fall below 45 or earnings reactions turn negative despite headline beats."
        )
        st.write(f"Portfolio action: {rec}.")
        st.write(f"Updated fair value: {money(context['fair_value'])}. Risk-adjusted conviction: {conviction}/10.")
        st.write("Action plan: review position size, compare current price to fair value, wait for the next report if uncertainty is high, and reduce if support fails or thesis evidence worsens.")

    st.subheader("Earnings: Expectation vs Actual")
    st.write(earnings["latest"])
    st.write(earnings["next"])
    if earnings.get("rows"):
        st.dataframe(pd.DataFrame(earnings["rows"]), use_container_width=True, hide_index=True)
        st.caption("Nasdaq fallback data is shown when available. Always verify against company earnings releases and filings.")
    st.write(
        "Possible direction after next report: upside is more likely if EPS/revenue beat and management raises guidance; downside is more likely if estimates are missed, "
        "guidance is soft, or the stock had already priced in perfection."
    )

    if underlying and underlying != official_symbol:
        st.subheader(f"Underlying Fundamental Read-Through: {underlying}")
        with st.spinner(f"Fetching {underlying} look-through data..."):
            u_info = fetch_ticker(underlying)
            u_hist = fetch_history(underlying, "2y")
            u_fin = fetch_financials(underlying)
        u_matrices, u_context = build_matrices(underlying, u_info, u_hist, u_fin)
        u_overall = weighted_score(u_matrices, HORIZON_WEIGHTS[horizon])
        st.write(
            f"{official_symbol} should not be analyzed as only its own chart. The underlying {underlying} score is {u_overall}/100, "
            f"with fair value estimate {money(u_context['fair_value'])}. If {underlying} weakens, leveraged ETF losses can be amplified."
        )
        render_matrix_table(u_matrices)

    st.subheader("Assumptions & Data Limits")
    st.write(
        "This app does not invent missing data. When a source does not provide a field, the score uses a neutral assumption. "
        "Qualitative moat, management quality, customer concentration, and regulatory exposure still require human review using company filings and trusted news."
    )


if __name__ == "__main__":
    main()

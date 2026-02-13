"""
Buffett-ish Portfolio Builder (Brokerage)
- Sleeves: anchor, value_hedge, growth, ai_tilt, financials, healthcare
- Primary factor: Price-to-Earnings (lower is better, within reason)
- Secondary: profitability / balance sheet proxies where available

Install:
  pip install yfinance pandas numpy

Run:
  python buffett_portfolio_builder.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


# -----------------------------
# Config you can change easily
# -----------------------------

SLEEVE_TARGET_WEIGHTS = {
    "anchor": 0.30,
    "value_hedge": 0.15,
    "growth": 0.15,
    "ai_tilt": 0.10,
    "financials": 0.05,
    "healthcare": 0.05,
    "small_mid": 0.07,
    "international": 0.05,
    "energy": 0.04,
    "infrastructure": 0.04,
}


# Sleeve-specific guardrails + factor weights.
# - "max_*": screening guardrails
# - "w_*": scoring weights (higher = more important)
SLEEVE_RULES = {
    "anchor": {
        "max_pe": 35, "max_beta": 1.30,
        "w_pe": 1.2, "w_quality": 0.6, "w_balance": 0.4, "w_risk": 0.6, "w_div": 0.2,
    },
    "value_hedge": {
        "max_pe": 25, "max_beta": 1.25,
        "w_pe": 1.6, "w_quality": 1.0, "w_balance": 0.8, "w_risk": 0.6, "w_div": 0.8,
    },
    "growth": {
        "max_pe": 50, "max_beta": 1.60,
        "w_pe": 1.0, "w_quality": 0.8, "w_balance": 0.4, "w_risk": 0.4, "w_div": 0.1,
    },
    "ai_tilt": {
        "max_pe": 70, "max_beta": 1.90,
        "w_pe": 0.7, "w_quality": 0.7, "w_balance": 0.4, "w_risk": 0.2, "w_div": 0.0,
    },
    "financials": {
        "max_pe": 22, "max_beta": 1.40,
        "w_pe": 1.7, "w_quality": 0.9, "w_balance": 0.6, "w_risk": 0.6, "w_div": 0.3,
    },
    "healthcare": {
        "max_pe": 40, "max_beta": 1.40,
        "w_pe": 1.2, "w_quality": 1.1, "w_balance": 0.6, "w_risk": 0.5, "w_div": 0.2,
    },
    "small_mid": {
        "max_pe": 40, "max_beta": 1.60,
        "w_pe": 1.2, "w_quality": 0.7, "w_balance": 0.6, "w_risk": 0.4, "w_div": 0.1,
    },
    "international": {
        "max_pe": 35, "max_beta": 1.40,
        "w_pe": 1.3, "w_quality": 0.8, "w_balance": 0.5, "w_risk": 0.5, "w_div": 0.2,
    },
    "energy": {
        "max_pe": 25, "max_beta": 1.60,
        "w_pe": 1.8, "w_quality": 0.6, "w_balance": 0.8, "w_risk": 0.3, "w_div": 0.4,
    },
    "infrastructure": {
        "max_pe": 35, "max_beta": 1.50,
        "w_pe": 1.2, "w_quality": 0.8, "w_balance": 0.6, "w_risk": 0.4, "w_div": 0.2,
    },
}


# Universe: ~40 ETFs and stocks per sector
UNIVERSE = {

    "anchor": [
        # ETFs
        "VOO", "VTI", "IVV", "ITOT", "SPY", "SCHX", "SPLG", "SPTM",
        # Stocks
        "AAPL", "MSFT", "GOOGL", "AMZN", "BRK-B", "JPM", "V", "JNJ", "WMT", "PG", 
        "MA", "HD", "DIS", "NVDA", "META", "LLY", "AVGO", "TSM", "XOM", "CVX",
        "ABBV", "MRK", "KO", "PEP", "COST", "CSCO", "ACN", "MCD", "TMO", "ABT",
        "ORCL", "CRM", "ADBE", "NKE", "DHR", "TXN", "UNH", "PM", "NEE", "HON"
    ],

    "value_hedge": [
        # ETFs
        "SCHD", "VTV", "IWD", "DGRO", "QUAL", "HDV", "VYM", "DVY",
        # Stocks
        "KO", "PG", "PEP", "MCD", "CVX", "JNJ", "WMT", "VZ", "T", "PM",
        "MO", "BMY", "MMM", "CAT", "DE", "UPS", "RTX", "BA", "GD", "LMT",
        "XOM", "COP", "PSX", "MPC", "KMB", "CL", "GIS", "K", "HSY", "CPB",
        "SO", "DUK", "D", "AEP", "EXC", "ED", "ES", "FE", "ETR", "WEC"
    ],

    "growth": [
        # ETFs
        "SCHG", "VUG", "SPYG", "IWF", "VONG", "MGK", "IVW", "SPBO",
        # Stocks
        "MSFT", "AMZN", "GOOGL", "META", "NFLX", "TSLA", "NVDA", "CRM", "ADBE", "NOW",
        "SHOP", "SQ", "UBER", "ABNB", "SNOW", "DDOG", "NET", "CRWD", "ZS", "OKTA",
        "TEAM", "WDAY", "PANW", "FTNT", "MRVL", "ANET", "SNPS", "CDNS", "INTU", "ISRG",
        "REGN", "VRTX", "ALNY", "MRNA", "BNTX", "ILMN", "GILD", "BIIB", "AMGN", "CELG"
    ],

    "ai_tilt": [
        # ETFs
        "SMH", "SOXX", "XSD", "SOXQ", "PSI", "IGV", "QTEC", "SKYY",
        # Stocks
        "NVDA", "AVGO", "TSM", "ASML", "AMD", "MU", "QCOM", "INTC", "MRVL", "ARM",
        "PLTR", "SNOW", "AI", "BBAI", "SOUN", "MSFT", "GOOGL", "META", "AMZN", "ORCL",
        "CRM", "NOW", "ADBE", "INTU", "PANW", "CRWD", "ZS", "NET", "DDOG", "S",
        "ANET", "SNPS", "CDNS", "KLAC", "LRCX", "AMAT", "NXPI", "TXN", "ADI", "MCHP"
    ],

    "financials": [
        # ETFs
        "VFH", "XLF", "FNCL", "IYF", "KBE", "IAI", "KRE", "KBWB",
        # Stocks
        "JPM", "BAC", "GS", "MS", "BLK", "BRK-B", "C", "WFC", "SCHW", "AXP",
        "USB", "PNC", "TFC", "COF", "BK", "STT", "NTRS", "BEN", "TROW", "IVZ",
        "V", "MA", "PYPL", "SQ", "FIS", "FISV", "ADP", "PAYX", "BR", "MMC",
        "AON", "WTW", "AJG", "BRO", "AFL", "MET", "PRU", "ALL", "TRV", "CB"
    ],

    "healthcare": [
        # ETFs
        "VHT", "XLV", "FHLC", "IXJ", "IYH", "VBK", "IBB", "XBI",
        # Stocks
        "UNH", "LLY", "JNJ", "MRK", "ABBV", "TMO", "ABT", "DHR", "PFE", "BMY",
        "AMGN", "GILD", "REGN", "VRTX", "ISRG", "SYK", "BSX", "MDT", "EW", "ZBH",
        "BAX", "BDX", "HOLX", "ALGN", "IDXX", "IQV", "A", "LH", "DGX", "CVS",
        "CI", "HUM", "CNC", "MOH", "ELV", "HCA", "THC", "UHS", "CYH", "LPLA"
    ],

    "small_mid": [
        # ETFs
        "VB", "VO", "IJR", "IJH", "AVUV", "VBR", "IWM", "SCHA",
        # Stocks
        "URI", "FAST", "HUBB", "POOL", "WST", "ODFL", "TDY", "ROL", "WSO", "FICO",
        "VRSK", "MSCI", "SPGI", "MCO", "TRU", "EFX", "JKHY", "BR", "FDS", "IEX",
        "PH", "ITW", "EMR", "ETN", "ROK", "AME", "ROP", "FTV", "XYL", "IEX",
        "DOV", "FAST", "SNA", "PCAR", "CHRW", "JBHT", "KNX", "LSTR", "EXPD", "SAIA"
    ],

    "international": [
        # ETFs
        "VXUS", "IEFA", "VEA", "VWO", "AVEM", "IXUS", "ACWX", "VSGX",
        # Stocks
        "ASML", "NVO", "SAP", "TSM", "TM", "SONY", "NVS", "UL", "BABA", "SHOP",
        "SE", "MELI", "PDD", "JD", "BIDU", "NIO", "XPEV", "LI", "GRAB", "DIDI",
        "TCEHY", "BABA", "PDD", "JD", "NTES", "BILI", "IQ", "VIPS", "TME", "BEKE",
        "RIO", "BHP", "VALE", "FCX", "SCCO", "GOLD", "NEM", "AEM", "KGC", "AU"
    ],

    "energy": [
        # ETFs
        "XLE", "VDE", "FENY", "IXC", "IYE", "PXE", "PSCE", "RYE",
        # Stocks
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HAL",
        "BKR", "NOV", "FTI", "HP", "CHK", "DVN", "FANG", "MRO", "APA", "HES",
        "PXD", "CXO", "OVV", "CTRA", "EQT", "AR", "RRC", "SM", "MGY", "PR",
        "LNG", "TELL", "NEXT", "GLNG", "FLNG", "KMI", "WMB", "OKE", "EPD", "ET"
    ],

    "infrastructure": [
        # ETFs
        "PAVE", "IFRA", "NFRA", "IGF", "PKB", "PXI", "ITB", "XHB",
        # Stocks
        "CAT", "NEE", "UNP", "DE", "NSC", "CSX", "SO", "DUK", "D", "AEP",
        "EXC", "ED", "ES", "FE", "ETR", "WEC", "PEG", "XEL", "PCG", "SRE",
        "AWK", "WM", "RSG", "WCN", "CWST", "GFL", "URI", "VMC", "MLM", "NUE",
        "STLD", "RS", "CMC", "CLF", "X", "MT", "TX", "GGB", "VALE", "FCX"
    ]
}



# Buffett-ish screening settings
# (PE is primary; these just guardrail junk/expensive names)
@dataclass
class ScreenConfig:
    pe_max: float = 30.0            # reject if trailing P/E is above this
    pe_min: float = 5.0             # reject if trailing P/E is absurdly low (often distressed/one-offs)
    require_positive_profit_margin: bool = True
    debt_to_equity_max: Optional[float] = None  # set e.g. 2.0 if you want
    min_return_on_equity: Optional[float] = None  # set e.g. 0.10 (10%) if you want
    allow_missing_fields: bool = True  # ETFs sometimes lack fields; True keeps them from being auto-rejected

SCREEN = ScreenConfig(
    pe_max=30.0,
    pe_min=5.0,
    require_positive_profit_margin=False,  # ETFs can have weird/missing margin fields
    debt_to_equity_max=None,
    min_return_on_equity=None,
    allow_missing_fields=True,
)

# Selection: 6 ETFs + 6 stocks per sleeve
PICKS_PER_SLEEVE = {
    "anchor": 12,
    "value_hedge": 12,
    "growth": 12,
    "ai_tilt": 12,
    "financials": 12,
    "healthcare": 12,
    "small_mid": 12,
    "international": 12,
    "energy": 12,
    "infrastructure": 12
}

# Track which are ETFs for balanced selection
ETF_TICKERS = {
    "VOO", "VTI", "IVV", "ITOT", "SPY", "SCHD", "VTV", "IWD", "DGRO", "QUAL", "HDV",
    "SCHG", "VUG", "SPYG", "IWF", "SMH", "SOXX", "XSD", "VFH", "XLF", "FNCL", "IYF", "KBE",
    "VHT", "XLV", "FHLC", "IXJ", "VB", "VO", "IJR", "IJH", "AVUV", "VBR",
    "VXUS", "IEFA", "VEA", "VWO", "AVEM", "XLE", "VDE", "FENY", "IXC",
    "PAVE", "IFRA", "NFRA", "IGF"
}



# -----------------------------
# Data + scoring
# -----------------------------

def safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float, np.floating)):
            if math.isnan(float(x)):
                return None
            return float(x)
        # sometimes yfinance returns strings
        return float(x)
    except Exception:
        return None


def fetch_metrics(ticker: str) -> Dict[str, Optional[float]]:
    t = yf.Ticker(ticker)
    info = t.info or {}

    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    profit_margin = safe_float(info.get("profitMargins"))
    roe = safe_float(info.get("returnOnEquity"))
    debt_to_equity = safe_float(info.get("debtToEquity"))
    market_cap = safe_float(info.get("marketCap"))
    div_yield = safe_float(info.get("dividendYield"))
    beta = safe_float(info.get("beta"))
    price_to_book = safe_float(info.get("priceToBook"))
    peg = safe_float(info.get("pegRatio"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    
    # Momentum factors - fetch historical prices
    try:
        hist = t.history(period="6mo")
        if not hist.empty and len(hist) > 60:
            current_price = hist['Close'].iloc[-1]
            price_3m_ago = hist['Close'].iloc[-63] if len(hist) >= 63 else hist['Close'].iloc[0]
            price_6m_ago = hist['Close'].iloc[0]
            high_52w = safe_float(info.get("fiftyTwoWeekHigh"))
            
            return_3m = ((current_price - price_3m_ago) / price_3m_ago) * 100 if price_3m_ago > 0 else None
            return_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100 if price_6m_ago > 0 else None
            proximity_52w = (current_price / high_52w) * 100 if high_52w and high_52w > 0 else None
        else:
            return_3m = return_6m = proximity_52w = None
    except:
        return_3m = return_6m = proximity_52w = None

    return {
        "ticker": ticker,
        "trailingPE": trailing_pe,
        "forwardPE": forward_pe,
        "profitMargins": profit_margin,
        "returnOnEquity": roe,
        "debtToEquity": debt_to_equity,
        "marketCap": market_cap,
        "dividendYield": div_yield,
        "beta": beta,
        "priceToBook": price_to_book,
        "pegRatio": peg,
        "revenueGrowth": revenue_growth,
        "return_3m": return_3m,
        "return_6m": return_6m,
        "proximity_52w": proximity_52w,
    }



def passes_screen(row: pd.Series, cfg: ScreenConfig) -> Tuple[bool, List[str]]:
    reasons = []
    sleeve = row.get("sleeve")
    rules = SLEEVE_RULES.get(sleeve, {})
    pe_max = rules.get("max_pe", cfg.pe_max)
    beta_max = rules.get("max_beta", None)

    pe = row.get("trailingPE")
    fpe = row.get("forwardPE")

    # Prefer trailing P/E; fallback to forward P/E if trailing missing
    pe_used = pe if pe is not None else fpe

    if pe_used is None:
        if not cfg.allow_missing_fields:
            reasons.append("missing PE (trailing/forward)")
    else:
        if pe_used < cfg.pe_min:
            reasons.append(f"PE<{cfg.pe_min}")
        if pe_used > pe_max:
            reasons.append(f"PE>{pe_max}")

    # Optional quality checks (keep light to avoid over-filtering ETFs)
    if cfg.require_positive_profit_margin:
        pm = row.get("profitMargins")
        if pm is None and not cfg.allow_missing_fields:
            reasons.append("missing profitMargins")
        elif pm is not None and pm <= 0:
            reasons.append("profitMargins<=0")

    if cfg.debt_to_equity_max is not None:
        dte = row.get("debtToEquity")
        if dte is None and not cfg.allow_missing_fields:
            reasons.append("missing debtToEquity")
        elif dte is not None and dte > cfg.debt_to_equity_max:
            reasons.append(f"debtToEquity>{cfg.debt_to_equity_max}")

    if cfg.min_return_on_equity is not None:
        roe = row.get("returnOnEquity")
        if roe is None and not cfg.allow_missing_fields:
            reasons.append("missing returnOnEquity")
        elif roe is not None and roe < cfg.min_return_on_equity:
            reasons.append(f"returnOnEquity<{cfg.min_return_on_equity}")

    # Sleeve risk guardrail
    if beta_max is not None:
        b = row.get("beta")
        if b is None:
            if not cfg.allow_missing_fields:
                reasons.append("missing beta")
        else:
            if b > beta_max:
                reasons.append(f"beta>{beta_max}")

    return (len(reasons) == 0), reasons



def score_row(row: pd.Series) -> float:
    """
    Multi-factor scoring:
      40% Value: P/E, P/B, dividend yield
      30% Momentum: 3m/6m returns, 52w proximity
      20% Quality: ROE, profit margin, revenue growth
      10% Risk: beta, volatility
    """

    sleeve = row.get("sleeve")
    rules = SLEEVE_RULES.get(sleeve, {})
    
    # Base weights
    w_pe = rules.get("w_pe", 1.0)
    w_quality = rules.get("w_quality", 0.7)
    w_balance = rules.get("w_balance", 0.5)
    w_risk = rules.get("w_risk", 0.5)
    w_div = rules.get("w_div", 0.1)

    score = 0.0
    
    # === VALUE FACTORS (40%) ===
    trailing_pe = row.get("trailingPE")
    forward_pe = row.get("forwardPE")
    pe = trailing_pe if trailing_pe is not None else forward_pe
    
    if pe is not None and pe > 0:
        score += w_pe * (50.0 / pe) * 0.4  # 40% weight on value
    
    pb = row.get("priceToBook")
    if pb is not None and pb > 0:
        score += (10.0 / pb) * 0.4
    
    div = row.get("dividendYield")
    if div is not None and div > 0:
        score += w_div * (100.0 * div) * 0.4
    
    # === MOMENTUM FACTORS (30%) ===
    ret_3m = row.get("return_3m")
    ret_6m = row.get("return_6m")
    prox_52w = row.get("proximity_52w")
    
    if ret_3m is not None:
        score += (ret_3m / 10.0) * 0.3  # Normalize: 10% return = 1 point
    if ret_6m is not None:
        score += (ret_6m / 20.0) * 0.3  # Normalize: 20% return = 1 point
    if prox_52w is not None:
        score += (prox_52w / 20.0) * 0.3  # Near 52w high = bonus
    
    # === QUALITY FACTORS (20%) ===
    roe = row.get("returnOnEquity")
    pm = row.get("profitMargins")
    rev_growth = row.get("revenueGrowth")
    
    if roe is not None and roe > 0:
        score += w_quality * (5.0 * roe) * 0.2
    if pm is not None and pm > 0:
        score += w_quality * (5.0 * pm) * 0.2
    if rev_growth is not None and rev_growth > 0:
        score += (rev_growth * 10.0) * 0.2  # 10% growth = 1 point
    
    # === RISK FACTORS (10%) ===
    beta = row.get("beta")
    dte = row.get("debtToEquity")
    
    if beta is not None and beta > 0:
        score += w_risk * (2.0 / beta) * 0.1
    else:
        score -= 0.1
    
    if dte is not None and dte >= 0:
        score += w_balance * (5.0 / (1.0 + dte)) * 0.1

    return score

    roe = row.get("returnOnEquity")
    pm = row.get("profitMargins")
    dte = row.get("debtToEquity")
    beta = row.get("beta")
    div = row.get("dividendYield")

    score = 0.0

    # 1) Valuation: invert PE (cap extreme values for stability)
    if pe is not None and pe > 0:
        score += w_pe * (100.0 / min(pe, 200.0))
    else:
        score -= 0.5  # small penalty for missing PE

    # 2) Quality
    if roe is not None:
        score += w_quality * (10.0 * roe)   # roe often 0.0–0.5
    if pm is not None:
        score += w_quality * (5.0 * pm)     # pm often 0.0–0.4

    # 3) Balance sheet: prefer lower D/E (but D/E varies wildly by sector)
    if dte is not None and dte >= 0:
        score += w_balance * (5.0 / (1.0 + dte))  # bounded 0–5

    # 4) Risk: prefer lower beta
    if beta is not None and beta > 0:
        score += w_risk * (2.0 / beta)  # beta 1 -> 2; beta 2 -> 1
    else:
        score -= 0.1

    # 5) Dividend yield: modest bonus (yield is usually 0.00–0.06)
    if div is not None and div > 0:
        score += w_div * (100.0 * div)  # 3% => +3 * w_div

    return score



def build_portfolio(
    universe: Dict[str, List[str]],
    sleeve_weights: Dict[str, float],
    screen: ScreenConfig,
    picks_per_sleeve: int = 1,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      - picks_df: final selected tickers + weights
      - all_df: all tickers with metrics + pass/fail + score
    """
    rows = []
    for sleeve, tickers in universe.items():
        for tk in tickers:
            m = fetch_metrics(tk)
            m["sleeve"] = sleeve
            rows.append(m)

    all_df = pd.DataFrame(rows)

    # Screen + score
    pass_flags = []
    fail_reasons = []
    scores = []
    for _, r in all_df.iterrows():
        passed, reasons = passes_screen(r, screen)
        pass_flags.append(passed)
        fail_reasons.append("; ".join(reasons) if reasons else "")
        scores.append(score_row(r))

    all_df["passes_screen"] = pass_flags
    all_df["fail_reasons"] = fail_reasons
    all_df["score"] = scores
    all_df["pe_used"] = all_df["trailingPE"].fillna(all_df["forwardPE"])

    # Pick top names per sleeve: 6 ETFs + 6 stocks
    picks = []
    for sleeve, w in sleeve_weights.items():
        num_picks = PICKS_PER_SLEEVE.get(sleeve, 12)
        target_etfs = 6
        target_stocks = 6
        
        sleeve_df = all_df[all_df["sleeve"] == sleeve].copy()
        
        # Separate ETFs and stocks
        sleeve_df["is_etf"] = sleeve_df["ticker"].isin(ETF_TICKERS)
        
        # Get passing ETFs and stocks
        etf_df = sleeve_df[
            (sleeve_df["is_etf"]) &
            (sleeve_df["passes_screen"])
        ].sort_values("score", ascending=False).head(target_etfs)
        
        stock_df = sleeve_df[
            (~sleeve_df["is_etf"]) &
            (sleeve_df["passes_screen"])
        ].sort_values("score", ascending=False).head(target_stocks)
        
        # If not enough passing, fall back to best-scoring regardless of screen
        if len(etf_df) < target_etfs:
            etf_df = sleeve_df[sleeve_df["is_etf"]].sort_values("score", ascending=False).head(target_etfs)
        if len(stock_df) < target_stocks:
            stock_df = sleeve_df[~sleeve_df["is_etf"]].sort_values("score", ascending=False).head(target_stocks)
        
        # Combine
        sleeve_picks = pd.concat([etf_df, stock_df])
        
        # Split sleeve weight evenly across the selected tickers
        per_pick_weight = w / len(sleeve_picks)

        for _, r in sleeve_picks.iterrows():
            picks.append({
                "sleeve": sleeve,
                "ticker": r["ticker"],
                "target_weight": per_pick_weight,
                "pe_used": r.get("pe_used"),
                "trailingPE": r.get("trailingPE"),
                "forwardPE": r.get("forwardPE"),
                "dividendYield": r.get("dividendYield"),
                "beta": r.get("beta"),
                "score": r["score"],
                "passes_screen": r["passes_screen"],
                "fail_reasons": r["fail_reasons"],
            })


    picks_df = pd.DataFrame(picks)

    # Normalize (in case any rounding)
    picks_df["target_weight"] = picks_df["target_weight"] / picks_df["target_weight"].sum()

    return picks_df.sort_values(["sleeve", "target_weight"], ascending=[True, False]), all_df.sort_values(["sleeve", "score"], ascending=[True, False])


def send_report_email(selected_file, universe_file, summary_file=None):
    import os
    import boto3
    
    bucket = os.getenv("S3_BUCKET")
    sender = os.getenv("SENDER_EMAIL")
    recipient = os.getenv("RECIPIENT_EMAIL")
    region = os.getenv("AWS_REGION", "us-west-2")

    if not all([bucket, sender, recipient]):
        print("Skipping email: S3_BUCKET, SENDER_EMAIL, or RECIPIENT_EMAIL not set")
        return

    s3 = boto3.client("s3", region_name=region)
    ses = boto3.client("ses", region_name=region)

    selected_key = f"portfolio/{selected_file}"
    universe_key = f"universe/{universe_file}"
    
    s3.upload_file(selected_file, bucket, selected_key)
    s3.upload_file(universe_file, bucket, universe_key)
    print(f"Uploaded to S3: s3://{bucket}/{selected_key}")

    # Generate presigned URLs (valid for 7 days)
    selected_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': selected_key}, ExpiresIn=604800)
    universe_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': universe_key}, ExpiresIn=604800)

    # Upload summary if provided
    summary_url = None
    if summary_file:
        summary_key = f"summaries/{summary_file}"
        s3.upload_file(summary_file, bucket, summary_key)
        summary_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': summary_key}, ExpiresIn=604800)
        
        # Read summary for email body
        with open(summary_file, 'r') as f:
            summary_text = f.read()
    else:
        summary_text = ""

    body = f"""Daily Buffett Portfolio Report

{summary_text}

📥 Download Files (links valid 7 days):

Selected Portfolio CSV:
{selected_url}

Universe Metrics CSV:
{universe_url}"""
    
    if summary_url:
        body += f"\n\nFull Summary TXT:\n{summary_url}"

    # Convert markdown-style formatting to HTML and make URLs clickable
    import re
    html_body = body.replace('\n', '<br>\n')
    html_body = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_body)  # **bold**
    html_body = html_body.replace('  ', '&nbsp;&nbsp;')  # Preserve indentation
    
    # Convert URLs to clickable links
    html_body = re.sub(r'(https://[^\s<]+)', r'<a href="\1">\1</a>', html_body)
    
    ses.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": "Daily Portfolio Report"},
            "Body": {
                "Text": {"Data": body},
                "Html": {"Data": f"<html><body style='font-family: monospace; white-space: pre-wrap;'>{html_body}</body></html>"}
            }
        },
    )
    print(f"Email sent to {recipient}")


def main():
    from datetime import datetime
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    selected_file = f"selected_portfolio_{timestamp}.csv"
    universe_file = f"universe_metrics_{timestamp}.csv"

    try:
        picks_df, all_df = build_portfolio(
            universe=UNIVERSE,
            sleeve_weights=SLEEVE_TARGET_WEIGHTS,
            screen=SCREEN,
            picks_per_sleeve=PICKS_PER_SLEEVE,
        )

        print("\n=== SELECTED PORTFOLIO ===")
        print(picks_df.to_string(index=False))

        print("\n=== NOTES ===")
        print("- 'passes_screen=False' means it violated guardrails (often missing data for ETFs).")
        print("- P/E data for ETFs can be missing or approximate; use as a rough value signal.")
        print("- This is a portfolio construction assistant, not financial advice.")

        picks_df.to_csv(selected_file, index=False)
        all_df.to_csv(universe_file, index=False)
        print(f"\nSaved: {selected_file}, {universe_file}")

        # Generate summary with news
        from summary_generator import save_summary
        summary_file = save_summary(picks_df, timestamp)

        send_report_email(selected_file, universe_file, summary_file)

    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()

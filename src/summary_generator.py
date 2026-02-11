"""
Portfolio Summary Generator
Fetches news and generates weekly summary for selected picks
"""

import yfinance as yf
from datetime import datetime, timedelta


def get_ticker_news(ticker, max_articles=3):
    """Get recent news for a ticker"""
    try:
        t = yf.Ticker(ticker)
        news = t.news[:max_articles] if hasattr(t, 'news') and t.news else []
        return [{"title": n.get("title", ""), "link": n.get("link", "")} for n in news]
    except:
        return []


def generate_weekly_summary(picks_df):
    """Generate summary of picks with news"""
    summary = []
    summary.append("=" * 60)
    summary.append("📊 WEEKLY PORTFOLIO SUMMARY")
    summary.append(f"🗓️  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    summary.append("=" * 60)
    summary.append("")
    
    # Sleeve emojis
    sleeve_emoji = {
        "anchor": "⚓",
        "value_hedge": "🛡️",
        "growth": "🚀",
        "ai_tilt": "🤖",
        "financials": "🏦",
        "healthcare": "🏥",
        "small_mid": "📈",
        "international": "🌍",
        "energy": "⚡",
        "infrastructure": "🏗️"
    }
    
    # Group by sleeve
    for sleeve in picks_df['sleeve'].unique():
        sleeve_picks = picks_df[picks_df['sleeve'] == sleeve]
        emoji = sleeve_emoji.get(sleeve, "📌")
        summary.append(f"\n{emoji} {sleeve.upper().replace('_', ' ')}")
        summary.append("-" * 60)
        
        for _, row in sleeve_picks.iterrows():
            ticker = row['ticker']
            weight = row['target_weight'] * 100
            pe = row.get('pe_used', 'N/A')
            score = row.get('score', 0)
            
            summary.append(f"\n💼 **{ticker}** ({weight:.1f}% allocation)")
            pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else str(pe)
            summary.append(f"  📉 PE Ratio: {pe_str}")
            summary.append(f"  ⭐ Score: {score:.2f}")
            
            # Why picked
            reasons = []
            if row.get('passes_screen'):
                reasons.append("✅ Passed all screening criteria")
            if isinstance(pe, (int, float)) and pe < 20:
                reasons.append(f"💰 Attractive valuation (PE: {pe:.1f})")
            if row.get('dividendYield') and row['dividendYield'] > 0.02:
                reasons.append(f"💵 Dividend yield: {row['dividendYield']*100:.1f}%")
            
            if reasons:
                summary.append(f"  🎯 Why: {'; '.join(reasons)}")
            
            # Recent news
            news = get_ticker_news(ticker, max_articles=2)
            if news:
                summary.append("  📰 Recent News:")
                for article in news:
                    summary.append(f"    • {article['title']}")
                    summary.append(f"      🔗 {article['link']}")
    
    summary.append("\n" + "=" * 60)
    summary.append("⚠️  DISCLAIMER: This is automated analysis, not financial advice.")
    summary.append("=" * 60)
    
    return "\n".join(summary)


def save_summary(picks_df, timestamp):
    """Generate and save summary"""
    summary = generate_weekly_summary(picks_df)
    filename = f"portfolio_summary_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write(summary)
    
    print(f"Summary saved: {filename}")
    return filename

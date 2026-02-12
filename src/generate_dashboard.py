#!/usr/bin/env python3
"""
Interactive Portfolio Dashboard Generator
Creates HTML dashboard with tabs for each sleeve showing top performers
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd


def fetch_performance_data(ticker: str, days: int = 30) -> dict:
    """Get price history and calculate performance metrics"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        
        if hist.empty:
            return None
        
        start_price = hist['Close'].iloc[0]
        current_price = hist['Close'].iloc[-1]
        change_pct = ((current_price - start_price) / start_price) * 100
        
        info = stock.info
        
        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'current_price': current_price,
            'change_pct': change_pct,
            'volume': hist['Volume'].iloc[-1],
            'pe_ratio': info.get('trailingPE'),
            'market_cap': info.get('marketCap'),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'history': hist['Close'].tolist(),
            'dates': [d.strftime('%Y-%m-%d') for d in hist.index]
        }
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def generate_dashboard(portfolio_csv: str, output_html: str = 'dashboard.html'):
    """Generate interactive dashboard with sleeve tabs"""
    
    # Read portfolio
    df = pd.read_csv(portfolio_csv)
    
    # Group by sleeve
    sleeves = {}
    for _, row in df.iterrows():
        sleeve = row.get('Sleeve', 'Other')
        if sleeve not in sleeves:
            sleeves[sleeve] = []
        sleeves[sleeve].append(row['Ticker'])
    
    # Fetch performance for all holdings
    print("Fetching performance data...")
    sleeve_data = {}
    for sleeve, tickers in sleeves.items():
        print(f"  {sleeve}...")
        sleeve_data[sleeve] = []
        for ticker in tickers:
            perf = fetch_performance_data(ticker)
            if perf:
                sleeve_data[sleeve].append(perf)
        # Sort by performance
        sleeve_data[sleeve].sort(key=lambda x: x['change_pct'], reverse=True)
    
    # Calculate portfolio totals
    total_value = sum(h['current_price'] for sleeve in sleeve_data.values() for h in sleeve)
    avg_change = sum(h['change_pct'] for sleeve in sleeve_data.values() for h in sleeve) / len([h for sleeve in sleeve_data.values() for h in sleeve])
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Portfolio Dashboard - {datetime.now().strftime('%Y-%m-%d')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .header .stats {{ display: flex; justify-content: center; gap: 40px; margin-top: 20px; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 5px; }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        
        .tabs {{ display: flex; background: #1e293b; padding: 0 20px; overflow-x: auto; }}
        .tab {{ padding: 15px 25px; cursor: pointer; border-bottom: 3px solid transparent; white-space: nowrap; }}
        .tab:hover {{ background: #334155; }}
        .tab.active {{ border-bottom-color: #667eea; color: #667eea; }}
        
        .content {{ padding: 20px; max-width: 1400px; margin: 0 auto; }}
        .sleeve-panel {{ display: none; }}
        .sleeve-panel.active {{ display: block; }}
        
        .holdings-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; margin-top: 20px; }}
        .holding-card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
        .holding-card:hover {{ border-color: #667eea; transform: translateY(-2px); transition: all 0.3s; }}
        .holding-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px; }}
        .ticker {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .name {{ font-size: 14px; color: #94a3b8; margin-top: 5px; }}
        .change {{ font-size: 28px; font-weight: bold; }}
        .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #334155; }}
        .metric {{ font-size: 12px; color: #94a3b8; }}
        .metric-value {{ font-size: 16px; color: #e2e8f0; font-weight: 600; }}
        .chart-mini {{ height: 60px; margin-top: 15px; }}
        
        .winner-badge {{ background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .loser-badge {{ background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Buffett Portfolio Dashboard</h1>
        <p>Last Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">${total_value:,.2f}</div>
                <div class="stat-label">Total Value</div>
            </div>
            <div class="stat">
                <div class="stat-value {'positive' if avg_change >= 0 else 'negative'}">
                    {'+' if avg_change >= 0 else ''}{avg_change:.2f}%
                </div>
                <div class="stat-label">30-Day Performance</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len([h for s in sleeve_data.values() for h in s])}</div>
                <div class="stat-label">Holdings</div>
            </div>
        </div>
    </div>
    
    <div class="tabs">
"""
    
    # Generate tabs
    for i, sleeve in enumerate(sleeve_data.keys()):
        active = 'active' if i == 0 else ''
        html += f'        <div class="tab {active}" onclick="showSleeve(\'{sleeve}\')">{sleeve.replace("_", " ").title()}</div>\n'
    
    html += '    </div>\n    <div class="content">\n'
    
    # Generate sleeve panels
    for i, (sleeve, holdings) in enumerate(sleeve_data.items()):
        active = 'active' if i == 0 else ''
        html += f'        <div class="sleeve-panel {active}" id="{sleeve}">\n'
        html += f'            <h2 style="margin-bottom: 20px; color: #667eea;">{sleeve.replace("_", " ").title()} ({len(holdings)} holdings)</h2>\n'
        html += '            <div class="holdings-grid">\n'
        
        for rank, holding in enumerate(holdings, 1):
            badge = ''
            if rank == 1:
                badge = '<span class="winner-badge">🏆 Top Performer</span>'
            elif rank == len(holdings):
                badge = '<span class="loser-badge">📉 Needs Attention</span>'
            
            change_class = 'positive' if holding['change_pct'] >= 0 else 'negative'
            
            html += f"""
                <div class="holding-card">
                    <div class="holding-header">
                        <div>
                            <div class="ticker">{holding['ticker']}</div>
                            <div class="name">{holding['name']}</div>
                        </div>
                        <div class="change {change_class}">
                            {'+' if holding['change_pct'] >= 0 else ''}{holding['change_pct']:.2f}%
                        </div>
                    </div>
                    {badge}
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">${holding['current_price']:.2f}</div>
                            <div>Current Price</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{holding['pe_ratio']:.1f if holding['pe_ratio'] else 'N/A'}</div>
                            <div>P/E Ratio</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{holding['dividend_yield']:.2f}%</div>
                            <div>Dividend Yield</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${holding['market_cap']/1e9:.1f}B</div>
                            <div>Market Cap</div>
                        </div>
                    </div>
                    <canvas id="chart-{sleeve}-{holding['ticker']}" class="chart-mini"></canvas>
                </div>
"""
        
        html += '            </div>\n        </div>\n'
    
    html += """    </div>
    
    <script>
        function showSleeve(sleeve) {
            // Hide all panels
            document.querySelectorAll('.sleeve-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            
            // Show selected
            document.getElementById(sleeve).classList.add('active');
            event.target.classList.add('active');
        }
        
        // Generate mini charts
"""
    
    # Add chart data
    for sleeve, holdings in sleeve_data.items():
        for holding in holdings:
            dates_json = json.dumps(holding['dates'])
            prices_json = json.dumps(holding['history'])
            color = '#10b981' if holding['change_pct'] >= 0 else '#ef4444'
            
            html += f"""
        new Chart(document.getElementById('chart-{sleeve}-{holding['ticker']}'), {{
            type: 'line',
            data: {{
                labels: {dates_json},
                datasets: [{{
                    data: {prices_json},
                    borderColor: '{color}',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ display: false }},
                    y: {{ display: false }}
                }}
            }}
        }});
"""
    
    html += """
    </script>
</body>
</html>
"""
    
    # Write file
    with open(output_html, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated: {output_html}")
    print(f"📊 Total Value: ${total_value:,.2f}")
    print(f"📈 30-Day Change: {'+' if avg_change >= 0 else ''}{avg_change:.2f}%")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generate_dashboard.py <portfolio.csv> [output.html]")
        sys.exit(1)
    
    portfolio_csv = sys.argv[1]
    output_html = sys.argv[2] if len(sys.argv) > 2 else 'dashboard.html'
    
    generate_dashboard(portfolio_csv, output_html)

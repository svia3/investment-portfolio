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


def fetch_performance_data(ticker: str, days: int = 7) -> dict:
    """Get price history and calculate performance metrics - reduced to 7 days for speed"""
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
            'history': hist['Close'].tolist()[-7:],  # Only last 7 days
            'dates': [d.strftime('%m/%d') for d in hist.index][-7:]  # Shorter date format
        }
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def generate_dashboard(portfolio_csv: str, output_html: str = 'dashboard.html'):
    """Generate interactive dashboard with sleeve tabs and My Holdings tab"""
    
    # Import holdings
    from my_holdings import MY_HOLDINGS, TOTAL_INVESTED
    
    # Read portfolio
    df = pd.read_csv(portfolio_csv)
    
    # Group by sleeve
    sleeves = {}
    for _, row in df.iterrows():
        sleeve = row.get('sleeve', 'Other')
        if sleeve not in sleeves:
            sleeves[sleeve] = []
        sleeves[sleeve].append(row['ticker'])
    
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
    
    # Calculate MY actual holdings totals for header
    my_holdings_total = 0
    my_holdings_count = 0
    for account, holdings in MY_HOLDINGS.items():
        for ticker, data in holdings.items():
            perf = fetch_performance_data(ticker)
            if perf:
                my_holdings_total += perf['current_price'] * data['quantity']
                my_holdings_count += 1
    
    total_invested = sum(TOTAL_INVESTED.values())
    my_gain = my_holdings_total - total_invested
    my_gain_pct = (my_gain / total_invested * 100) if total_invested > 0 else 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        .chart-mini {{ height: 80px; margin-top: 15px; position: relative; }}
        
        .time-selector {{ display: flex; gap: 5px; margin-top: 10px; justify-content: center; }}
        .time-btn {{ background: #334155; color: #94a3b8; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; }}
        .time-btn:hover {{ background: #475569; }}
        .time-btn.active {{ background: #667eea; color: white; }}
        
        .winner-badge {{ background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .loser-badge {{ background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Portfolio Dashboard</h1>
        <p>Last Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">${my_holdings_total:,.2f}</div>
                <div class="stat-label">Current Value</div>
            </div>
            <div class="stat">
                <div class="stat-value {'positive' if my_gain >= 0 else 'negative'}">
                    ${my_gain:+,.2f} ({my_gain_pct:+.2f}%)
                </div>
                <div class="stat-label">Total Gain/Loss</div>
            </div>
            <div class="stat">
                <div class="stat-value">{my_holdings_count}</div>
                <div class="stat-label">My Holdings</div>
            </div>
        </div>
    </div>
    
    <div class="tabs">
"""
    
    # Generate tabs - My Holdings first, then sleeves
    html += '        <div class="tab active" onclick="showSleeve(\'my-holdings\')">💼 My Holdings</div>\n'
    for i, sleeve in enumerate(sleeve_data.keys()):
        html += f'        <div class="tab" onclick="showSleeve(\'{sleeve}\')">{sleeve.replace("_", " ").title()}</div>\n'
    
    html += '    </div>\n    <div class="content">\n'
    
    # Generate My Holdings panel first
    html += '        <div class="sleeve-panel active" id="my-holdings">\n'
    html += '            <h2 style="margin-bottom: 20px; color: #667eea;">💼 My Actual Holdings</h2>\n'
    
    # Calculate total portfolio value and prepare pie chart data
    my_holdings_data = []
    account_totals = {}
    account_cost_basis = {}
    
    for account, holdings in MY_HOLDINGS.items():
        account_value = 0
        account_cost = 0
        for ticker, data in holdings.items():
            quantity = data['quantity']
            cost_basis = data['cost_basis']
            perf = fetch_performance_data(ticker)
            if perf:
                value = perf['current_price'] * quantity
                account_value += value
                account_cost += cost_basis
                my_holdings_data.append({
                    'account': account,
                    'ticker': ticker,
                    'quantity': quantity,
                    'cost_basis': cost_basis,
                    'perf': perf,
                    'value': value
                })
        account_totals[account] = account_value
        account_cost_basis[account] = account_cost
    
    total_portfolio_value = sum(account_totals.values())
    total_invested = sum(TOTAL_INVESTED.values())
    total_gain = total_portfolio_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0
    gain_class = 'positive' if total_gain >= 0 else 'negative'
    
    # Add summary stats
    html += f'''
        <div class="metric-grid">
            <div class="metric-card green">
                <div class="metric-label">Current Value</div>
                <div class="metric-value">${total_portfolio_value:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Invested</div>
                <div class="metric-value">${total_invested:,.2f}</div>
            </div>
            <div class="metric-card {gain_class}">
                <div class="metric-label">Total Gain/Loss</div>
                <div class="metric-value">${total_gain:+,.2f} ({total_gain_pct:+.2f}%)</div>
            </div>
        </div>
        
        <div style="max-width: 600px; margin: 30px auto;">
            <canvas id="portfolio-pie-chart"></canvas>
        </div>
    '''
    
    for account in MY_HOLDINGS.keys():
        acct_value = account_totals.get(account, 0)
        acct_invested = TOTAL_INVESTED.get(account, 0)
        acct_gain = acct_value - acct_invested
        acct_gain_pct = (acct_gain / acct_invested * 100) if acct_invested > 0 else 0
        html += f'            <h3 style="color: #94a3b8; margin: 30px 0 15px 0;">{account}: ${acct_value:,.2f} ({acct_gain:+,.2f} / {acct_gain_pct:+.2f}%)</h3>\n'
        html += '            <div class="holdings-grid">\n'
        
        for holding in [h for h in my_holdings_data if h['account'] == account]:
            perf = holding['perf']
            quantity = holding['quantity']
            value = holding['value']
            cost_basis = holding['cost_basis']
            gain = value - cost_basis
            gain_pct = (gain / cost_basis * 100) if cost_basis > 0 else 0
            change_class = 'positive' if perf['change_pct'] >= 0 else 'negative'
            gain_class_holding = 'positive' if gain >= 0 else 'negative'
            pe_display = f"{perf['pe_ratio']:.1f}" if perf['pe_ratio'] is not None else 'N/A'
            mkt_cap_display = f"${perf['market_cap']/1e9:.1f}B" if perf['market_cap'] else 'N/A'
            pct_of_portfolio = (value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            html += f"""
            <div class="holding-card">
                <div class="holding-header">
                    <div>
                        <div class="ticker">{perf['ticker']}</div>
                        <div class="name">{perf['name']}</div>
                    </div>
                    <div class="change {gain_class_holding}">
                        ${gain:+,.2f} ({gain_pct:+.1f}%)
                    </div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">${value:,.2f}</div>
                        <div>Current Value</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{quantity:.3f}</div>
                        <div>Shares</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${perf['current_price']:.2f}</div>
                        <div>Price</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{pct_of_portfolio:.1f}%</div>
                        <div>% of Total</div>
                    </div>
                </div>
                <canvas id="chart-my-{perf['ticker']}-{account.replace(' ', '-')}" class="chart-mini"></canvas>
            </div>
"""
        html += '            </div>\n'
    html += '        </div>\n'
    
    # Generate sleeve panels
    for i, (sleeve, holdings) in enumerate(sleeve_data.items()):
        html += f'        <div class="sleeve-panel" id="{sleeve}">\n'
        html += f'            <h2 style="margin-bottom: 20px; color: #667eea;">{sleeve.replace("_", " ").title()} ({len(holdings)} holdings)</h2>\n'
        html += '            <div class="holdings-grid">\n'
        
        for rank, holding in enumerate(holdings, 1):
            badge = ''
            if rank == 1:
                badge = '<span class="winner-badge">🏆 Top Performer</span>'
            elif rank == len(holdings):
                badge = '<span class="loser-badge">📉 Needs Attention</span>'
            
            change_class = 'positive' if holding['change_pct'] >= 0 else 'negative'
            pe_display = f"{holding['pe_ratio']:.1f}" if holding['pe_ratio'] is not None else 'N/A'
            mkt_cap_display = f"${holding['market_cap']/1e9:.1f}B" if holding['market_cap'] else 'N/A'
            change_display = f"{'+' if holding['change_pct'] >= 0 else ''}{holding['change_pct']:.2f}%"
            
            html += f"""
                <div class="holding-card">
                    <div class="holding-header">
                        <div>
                            <div class="ticker">{holding['ticker']}</div>
                            <div class="name">{holding['name']}</div>
                        </div>
                        <div class="change {change_class}">
                            {change_display} <small style="opacity:0.7">(7d)</small>
                        </div>
                    </div>
                    {badge}
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">${holding['current_price']:.2f}</div>
                            <div>Current Price</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{pe_display}</div>
                            <div>P/E Ratio</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{holding['dividend_yield']:.2f}%</div>
                            <div>Dividend Yield</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{mkt_cap_display}</div>
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
    
    # Add pie chart for portfolio allocation
    pie_labels = []
    pie_values = []
    pie_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22']
    
    for i, holding in enumerate(my_holdings_data):
        pie_labels.append(f"{holding['ticker']} ({holding['account']})")
        pie_values.append(holding['value'])
    
    html += f"""
        new Chart(document.getElementById('portfolio-pie-chart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(pie_labels)},
                datasets: [{{
                    data: {json.dumps(pie_values)},
                    backgroundColor: {json.dumps(pie_colors[:len(pie_labels)])}
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'right' }},
                    title: {{ display: true, text: 'Portfolio Allocation', color: '#e2e8f0', font: {{ size: 18 }} }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return context.label + ': $' + value.toFixed(2) + ' (' + percentage + '%)';
                            }}
                        }}
                    }}
                }}
            }}
        }});
    """
    
    # Add chart data - My Holdings first
    for holding in my_holdings_data:
        perf = holding['perf']
        account = holding['account'].replace(' ', '-')
        dates_json = json.dumps(perf['dates'])
        prices_json = json.dumps(perf['history'])
        color = '#10b981' if perf['change_pct'] >= 0 else '#ef4444'
        
        html += f"""
        new Chart(document.getElementById('chart-my-{perf['ticker']}-{account}'), {{
            type: 'line',
            data: {{
                labels: {dates_json},
                datasets: [{{
                    data: {prices_json},
                    borderColor: '{color}',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '{color}',
                    pointHoverBorderColor: 'white',
                    pointHoverBorderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 4,
                plugins: {{ 
                    legend: {{ display: false }},
                    tooltip: {{
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: '{color}',
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {{
                            title: function(context) {{
                                return context[0].label;
                            }},
                            label: function(context) {{
                                return '$' + context.parsed.y.toFixed(2);
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ display: false }},
                    y: {{ display: false }}
                }},
                interaction: {{ 
                    mode: 'index', 
                    intersect: false 
                }}
            }}
        }});
"""
    
    # Add chart data for sleeves
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
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '{color}',
                    pointHoverBorderColor: 'white',
                    pointHoverBorderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 4,
                plugins: {{ 
                    legend: {{ display: false }},
                    tooltip: {{
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: '{color}',
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {{
                            title: function(context) {{
                                return context[0].label;
                            }},
                            label: function(context) {{
                                return '$' + context.parsed.y.toFixed(2);
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ display: false }},
                    y: {{ display: false }}
                }},
                interaction: {{ 
                    mode: 'index', 
                    intersect: false 
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
    print(f"📊 Current Value: ${total_portfolio_value:,.2f}")
    print(f"💰 Total Invested: ${total_invested:,.2f}")
    print(f"📈 Total Gain/Loss: ${total_gain:+,.2f} ({total_gain_pct:+.2f}%)")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generate_dashboard.py <portfolio.csv> [output.html]")
        sys.exit(1)
    
    portfolio_csv = sys.argv[1]
    output_html = sys.argv[2] if len(sys.argv) > 2 else 'dashboard.html'
    
    generate_dashboard(portfolio_csv, output_html)

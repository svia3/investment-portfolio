#!/usr/bin/env python3
"""
Unified Financial + Investment Report
Combines portfolio performance (yahoo-finance) with personal finance tracking (finance-manager)
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
import yfinance as yf
import pandas as pd


def get_portfolio_value(portfolio_csv: str) -> dict:
    """Calculate current portfolio value and performance"""
    df = pd.read_csv(portfolio_csv)
    
    total_value = 0
    holdings = []
    
    for _, row in df.iterrows():
        ticker = row['Ticker']
        try:
            stock = yf.Ticker(ticker)
            current_price = stock.info.get('currentPrice', stock.info.get('regularMarketPrice', 0))
            
            # Assume equal weight if no shares specified
            shares = row.get('Shares', 1)
            value = current_price * shares
            total_value += value
            
            holdings.append({
                'ticker': ticker,
                'price': current_price,
                'shares': shares,
                'value': value,
                'name': stock.info.get('shortName', ticker)
            })
        except Exception as e:
            print(f"Warning: Could not fetch {ticker}: {e}")
    
    return {
        'total_value': total_value,
        'holdings': holdings,
        'timestamp': datetime.now().isoformat()
    }


def analyze_transactions(transactions_csv: str) -> dict:
    """Analyze personal finance transactions"""
    try:
        result = subprocess.run(
            ['python', str(Path(__file__).parent.parent / '.agents/skills/finance-manager/scripts/analyze_finances.py'), transactions_csv],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Warning: Could not analyze transactions: {e}")
        return {}


def generate_unified_report(portfolio_csv: str, transactions_csv: str = None, output_html: str = 'unified_report.html'):
    """Generate comprehensive financial report"""
    
    # Get portfolio data
    print("Fetching portfolio data...")
    portfolio = get_portfolio_value(portfolio_csv)
    
    # Get transaction analysis if provided
    finance_data = {}
    if transactions_csv and Path(transactions_csv).exists():
        print("Analyzing transactions...")
        finance_data = analyze_transactions(transactions_csv)
    
    # Calculate key metrics
    total_portfolio = portfolio['total_value']
    savings_rate = finance_data.get('summary', {}).get('savings_rate', 0)
    monthly_savings = finance_data.get('summary', {}).get('net_savings', 0)
    
    # Generate HTML report
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Unified Financial Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; }}
        .metric-card.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .metric-card.orange {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .metric-value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ font-size: 14px; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .chart-container {{ margin: 30px 0; height: 300px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Unified Financial Report</h1>
        <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        
        <div class="metric-grid">
            <div class="metric-card green">
                <div class="metric-label">Portfolio Value</div>
                <div class="metric-value">${total_portfolio:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Savings Rate</div>
                <div class="metric-value">{savings_rate:.1f}%</div>
            </div>
            <div class="metric-card orange">
                <div class="metric-label">Monthly Savings</div>
                <div class="metric-value">${monthly_savings:,.2f}</div>
            </div>
        </div>
        
        <h2>💼 Portfolio Holdings</h2>
        <table>
            <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Shares</th>
                <th>Price</th>
                <th>Value</th>
                <th>% of Portfolio</th>
            </tr>
"""
    
    for holding in portfolio['holdings']:
        pct = (holding['value'] / total_portfolio * 100) if total_portfolio > 0 else 0
        html += f"""
            <tr>
                <td><strong>{holding['ticker']}</strong></td>
                <td>{holding['name']}</td>
                <td>{holding['shares']:.2f}</td>
                <td>${holding['price']:.2f}</td>
                <td>${holding['value']:.2f}</td>
                <td>{pct:.1f}%</td>
            </tr>
"""
    
    html += """
        </table>
        
        <div class="chart-container">
            <canvas id="portfolioChart"></canvas>
        </div>
"""
    
    if finance_data:
        html += f"""
        <h2>💰 Financial Summary</h2>
        <div class="metric-grid">
            <div class="metric-card green">
                <div class="metric-label">Total Income</div>
                <div class="metric-value">${finance_data.get('summary', {}).get('total_income', 0):,.2f}</div>
            </div>
            <div class="metric-card orange">
                <div class="metric-label">Total Expenses</div>
                <div class="metric-value">${abs(finance_data.get('summary', {}).get('total_expenses', 0)):,.2f}</div>
            </div>
        </div>
"""
    
    # Add Chart.js visualization
    labels = json.dumps([h['ticker'] for h in portfolio['holdings']])
    values = json.dumps([h['value'] for h in portfolio['holdings']])
    
    html += f"""
        <script>
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: {labels},
                    datasets: [{{
                        data: {values},
                        backgroundColor: [
                            '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
                            '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'right' }},
                        title: {{ display: true, text: 'Portfolio Allocation' }}
                    }}
                }}
            }});
        </script>
    </div>
</body>
</html>
"""
    
    # Write report
    with open(output_html, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Report generated: {output_html}")
    print(f"📊 Portfolio Value: ${total_portfolio:,.2f}")
    if finance_data:
        print(f"💰 Savings Rate: {savings_rate:.1f}%")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python unified_financial_report.py <portfolio.csv> [transactions.csv] [output.html]")
        print("\nExample:")
        print("  python unified_financial_report.py selected_portfolio.csv")
        print("  python unified_financial_report.py selected_portfolio.csv transactions.csv report.html")
        sys.exit(1)
    
    portfolio_csv = sys.argv[1]
    transactions_csv = sys.argv[2] if len(sys.argv) > 2 else None
    output_html = sys.argv[3] if len(sys.argv) > 3 else 'unified_report.html'
    
    generate_unified_report(portfolio_csv, transactions_csv, output_html)

#!/usr/bin/env python3
"""
Enhanced Portfolio Runner with Dashboard Generation
Runs portfolio selection, generates dashboard, uploads to S3, sends email
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import boto3

# Configuration
BUCKET_NAME = "buffett-portfolio-reports"
REGION = "us-west-2"
EMAIL_TO = "stephenvia3@gmail.com"

def run_portfolio_selection():
    """Run the main portfolio builder"""
    print("🔍 Running portfolio selection...")
    result = subprocess.run(
        ['python', '/app/test-buffet-portfolio.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Portfolio selection failed: {result.stderr}")
        sys.exit(1)
    
    print("✅ Portfolio selection complete")
    return result.stdout

def generate_and_upload_dashboard():
    """Generate dashboard and upload to S3"""
    print("📊 Generating interactive dashboard...")
    
    # Find latest portfolio CSV in current directory
    portfolio_files = sorted(Path('/app').glob('selected_portfolio_*.csv'))
    
    if not portfolio_files:
        print("❌ No portfolio file found")
        sys.exit(1)
    
    latest_portfolio = portfolio_files[-1]
    dashboard_path = Path('/app/dashboard.html')
    
    # Generate dashboard
    subprocess.run(
        ['python', '/app/generate_dashboard.py', str(latest_portfolio), str(dashboard_path)],
        check=True
    )
    
    # Upload to S3 with public-read ACL
    print("☁️  Uploading dashboard to S3...")
    s3 = boto3.client('s3', region_name=REGION)
    
    with open(dashboard_path, 'rb') as f:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='dashboard.html',
            Body=f,
            ContentType='text/html',
            CacheControl='no-cache',
            ACL='public-read'
        )
    
    dashboard_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/dashboard.html"
    print(f"✅ Dashboard uploaded: {dashboard_url}")
    
    return dashboard_url

def send_email_with_dashboard(dashboard_url: str, portfolio_summary: str):
    """Send email with link to dashboard"""
    print("📧 Sending email...")
    
    ses = boto3.client('ses', region_name=REGION)
    
    # Extract key metrics from summary
    lines = portfolio_summary.split('\n')
    summary_text = '\n'.join(lines[:10]) if lines else "Portfolio updated"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }}
            .content {{ padding: 20px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Daily Portfolio Update</h1>
            <p>{datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <div class="content">
            <p>Your Buffett-style portfolio has been updated with the latest market data.</p>
            
            <a href="{dashboard_url}" class="button">📈 View Interactive Dashboard →</a>
            
            <h3>Quick Summary:</h3>
            <div class="summary">{summary_text}</div>
            
            <p><small>Dashboard updates daily at 9 AM PT with live market data.</small></p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Daily Portfolio Update - {datetime.now().strftime('%B %d, %Y')}

View your interactive dashboard:
{dashboard_url}

Quick Summary:
{summary_text}

Dashboard updates daily at 9 AM PT with live market data.
    """
    
    try:
        response = ses.send_email(
            Source=EMAIL_TO,
            Destination={'ToAddresses': [EMAIL_TO]},
            Message={
                'Subject': {'Data': f'📊 Portfolio Update - {datetime.now().strftime("%b %d")}'},
                'Body': {
                    'Text': {'Data': text_body},
                    'Html': {'Data': html_body}
                }
            }
        )
        print(f"✅ Email sent: {response['MessageId']}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def main():
    """Main execution flow"""
    print("=" * 60)
    print("🚀 Starting Enhanced Portfolio Runner")
    print("=" * 60)
    
    # Step 1: Run portfolio selection
    portfolio_summary = run_portfolio_selection()
    
    # Step 2: Generate and upload dashboard
    dashboard_url = generate_and_upload_dashboard()
    
    # Step 3: Send email with dashboard link
    send_email_with_dashboard(dashboard_url, portfolio_summary)
    
    print("\n" + "=" * 60)
    print("✅ All tasks completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()

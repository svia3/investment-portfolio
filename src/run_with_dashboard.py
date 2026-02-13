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
    
    # Upload to S3
    print("☁️  Uploading dashboard to S3...")
    s3 = boto3.client('s3', region_name=REGION)
    
    with open(dashboard_path, 'rb') as f:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='dashboard.html',
            Body=f,
            ContentType='text/html',
            CacheControl='no-cache'
        )
    
    dashboard_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/dashboard.html"
    
    # Generate presigned URL (valid for 7 days) since bucket doesn't allow public access
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': 'dashboard.html'},
        ExpiresIn=604800  # 7 days
    )
    
    print(f"✅ Dashboard uploaded: {dashboard_url}")
    print(f"📧 Presigned URL (7 days): {presigned_url}")
    
    return presigned_url

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
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px; }}
            .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; white-space: pre-wrap; }}
            .link {{ font-size: 16px; color: #667eea; }}
        </style>
    </head>
    <body>
        <h2>📊 Portfolio Update - {datetime.now().strftime('%B %d, %Y')}</h2>
        
        <div class="summary">{summary_text}</div>
        
        <p class="link">
            <a href="{dashboard_url}">View Interactive Dashboard →</a>
        </p>
    </body>
    </html>
    """
    
    text_body = f"""Portfolio Update - {datetime.now().strftime('%B %d, %Y')}

{summary_text}

View Dashboard: {dashboard_url}
    """
    
    try:
        response = ses.send_email(
            Source=EMAIL_TO,
            Destination={'ToAddresses': [EMAIL_TO]},
            Message={
                'Subject': {'Data': f'Portfolio Update - {datetime.now().strftime("%b %d")}'},
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

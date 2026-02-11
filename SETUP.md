# Quick Setup Guide

## Your script has been enhanced with:
✅ Timestamped CSV outputs (selected_portfolio_2026-02-11_14-30.csv)
✅ S3 upload functionality
✅ SES email with presigned download links
✅ Error handling

## Manual Update Needed

The `send_report_email()` function has been added to your script. You need to update the `main()` function to use timestamped filenames.

See `scripts/main_update.txt` for the updated main() function code.

## Deployment Steps

### 1. Verify SES Email (one-time)
```bash
aws ses verify-email-identity --email-address your-email@example.com --region us-west-2
```
Check your email and click the verification link.

### 2. Deploy Infrastructure
```bash
cd /home/svia/personal-projects/investment-portfolio
./infra/deploy.sh us-west-2 YOUR_AWS_ACCOUNT_ID
```

This will:
- Create S3 bucket: `buffett-portfolio-reports`
- Create ECR repository
- Build and push Docker image
- Create IAM role with S3 + SES permissions

### 3. Create ECS Task Definition
```bash
# Update task-definition-template.json with your:
# - AWS Account ID
# - Region
# - Verified sender email
# - Recipient email

aws ecs register-task-definition \
  --cli-input-json file://infra/task-definition-template.json \
  --region us-west-2
```

### 4. Create CloudWatch Log Group
```bash
aws logs create-log-group \
  --log-group-name /ecs/buffett-portfolio \
  --region us-west-2
```

### 5. Schedule Daily Run with EventBridge
```bash
# Create EventBridge Scheduler rule
aws scheduler create-schedule \
  --name buffett-portfolio-daily \
  --schedule-expression "cron(0 14 * * ? *)" \
  --schedule-expression-timezone "America/Los_Angeles" \
  --flexible-time-window Mode=OFF \
  --target '{
    "Arn": "arn:aws:ecs:us-west-2:ACCOUNT_ID:cluster/default",
    "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/EventBridgeECSRole",
    "EcsParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:us-west-2:ACCOUNT_ID:task-definition/buffett-portfolio-task:1",
      "LaunchType": "FARGATE",
      "NetworkConfiguration": {
        "awsvpcConfiguration": {
          "Subnets": ["subnet-xxxxx"],
          "SecurityGroups": ["sg-xxxxx"],
          "AssignPublicIp": "ENABLED"
        }
      }
    }
  }' \
  --region us-west-2
```

## Test Locally First

```bash
cd /home/svia/personal-projects/investment-portfolio

# Set environment variables
export S3_BUCKET=buffett-portfolio-reports
export SENDER_EMAIL=your-verified-email@example.com
export RECIPIENT_EMAIL=your-email@example.com
export AWS_REGION=us-west-2

# Run the script
python scripts/test-buffet-portfolio.py
```

## Test with Docker

```bash
docker build -t buffett-portfolio .

docker run --rm \
  -e S3_BUCKET=buffett-portfolio-reports \
  -e SENDER_EMAIL=your-verified-email@example.com \
  -e RECIPIENT_EMAIL=your-email@example.com \
  -e AWS_REGION=us-west-2\
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  buffett-portfolio
```

## What Happens Daily

1. EventBridge triggers ECS Fargate task at 2 PM PT
2. Container starts, runs your script
3. Generates timestamped CSVs
4. Uploads to S3: `s3://buffett-portfolio-reports/selected_portfolio_2026-02-11_14-00.csv`
5. Sends email with 7-day presigned download links
6. Container exits
7. You get email with portfolio report

## Cost Estimate (Daily Run)

- ECS Fargate (0.25 vCPU, 0.5 GB, ~5 min): ~$0.01/day
- S3 storage: ~$0.01/month
- SES: First 62,000 emails free
- **Total: ~$0.30/month**

## Troubleshooting

- Check ECS task logs: CloudWatch Logs → `/ecs/buffett-portfolio`
- Verify SES sandbox status if emails aren't sending
- Ensure security group allows outbound HTTPS (for yfinance API)

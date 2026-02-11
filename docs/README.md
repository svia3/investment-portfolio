# Investment Portfolio - Buffett Strategy

Automated daily portfolio analysis using ECS Fargate + Docker.

## Features
- 📊 Multi-sleeve portfolio construction (anchor, value, growth, AI, etc.)
- 📈 Automated scoring based on PE, ROE, dividends, beta
- 📰 Daily news summaries for each pick
- 📧 Email reports with presigned S3 download links
- 🗂️ Historical data stored in S3

## Quick Deploy
```bash
./infra/deploy-complete.sh <aws-region> <aws-account-id> <email>
```

Example:
```bash
./infra/deploy-complete.sh us-west-2 123456789012 you@example.com
```

This will:
- Create S3 bucket and ECR repository
- Build and push Docker image
- Set up IAM roles and permissions
- Verify SES email (you'll need to click verification link)
- Register ECS task definition
- Schedule daily runs at 6 AM PT

## Structure
```
├── src/                          # Source code
│   ├── test-buffet-portfolio.py  # Main portfolio builder
│   └── summary_generator.py      # News & summary generator
├── infra/                        # Infrastructure & deployment
│   ├── deploy-complete.sh        # One-command deployment
│   ├── deploy.sh                 # Infrastructure setup
│   ├── Dockerfile                # Container definition
│   ├── task-definition-template.json
│   └── task-role-policy.json
├── docs/                         # Documentation
│   ├── README.md
│   └── SETUP.md
└── requirements.txt              # Python dependencies
```

## Cost
~$0.30/month for daily runs

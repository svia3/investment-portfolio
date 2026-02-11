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
./deploy-complete.sh
```

## Structure
```
├── scripts/
│   ├── test-buffet-portfolio.py  # Main portfolio builder
│   └── summary_generator.py      # News & summary generator
├── infra/
│   ├── deploy.sh                 # Infrastructure setup
│   ├── task-definition-template.json
│   └── task-role-policy.json
├── Dockerfile
├── requirements.txt
└── deploy-complete.sh            # One-command deployment
```

## Configuration
Update `deploy-complete.sh` and `infra/task-definition-template.json` with your:
- AWS Account ID
- AWS Region
- Email address
- Schedule preferences

Cost: ~$0.30/month

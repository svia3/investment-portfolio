#!/bin/bash
# Complete deployment for Buffett Portfolio
# Usage: ./deploy-complete.sh <aws-region> <aws-account-id> <email>

set -e

# Disable AWS CLI pager
export AWS_PAGER=""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ $# -lt 3 ]; then
  echo "Usage: ./deploy-complete.sh <aws-region> <aws-account-id> <email>"
  echo "Example: ./deploy-complete.sh us-west-2 123456789012 you@example.com"
  exit 1
fi

REGION="$1"
ACCOUNT_ID="$2"
EMAIL="$3"

echo "🚀 Starting deployment..."

# Step 1: Deploy infrastructure
echo ""
echo "📦 Step 1: Deploying infrastructure (S3, ECR, IAM, Docker)..."
"${SCRIPT_DIR}/deploy.sh" ${REGION} ${ACCOUNT_ID}

# Step 2: Verify SES email
echo ""
echo "📧 Step 2: Verifying SES email..."
VERIFIED=$(aws ses get-identity-verification-attributes --identities ${EMAIL} --region ${REGION} --query "VerificationAttributes.\"${EMAIL}\".VerificationStatus" --output text 2>/dev/null)

if [ "$VERIFIED" = "Success" ]; then
  echo "✅ Email ${EMAIL} already verified"
else
  aws ses verify-email-identity --email-address ${EMAIL} --region ${REGION}
  echo "⚠️  CHECK YOUR EMAIL and click the verification link!"
  read -p "Press Enter after verifying your email..."
fi

# Step 3: Create CloudWatch log group
echo ""
echo "📝 Step 3: Creating CloudWatch log group..."
aws logs create-log-group \
  --log-group-name /ecs/portfolio-tracker \
  --region ${REGION} 2>/dev/null || echo "Log group already exists"

# Step 4: Register ECS task definition
echo ""
echo "🐳 Step 4: Registering ECS task definition..."

# Create task definition with actual values
cat > /tmp/task-definition.json <<EOF
{
  "family": "portfolio-tracker-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "taskRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/PortfolioTaskRole",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "portfolio-tracker",
      "image": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/portfolio-tracker:latest",
      "essential": true,
      "environment": [
        {
          "name": "S3_BUCKET",
          "value": "portfolio-tracker-reports"
        },
        {
          "name": "SENDER_EMAIL",
          "value": "${EMAIL}"
        },
        {
          "name": "RECIPIENT_EMAIL",
          "value": "${EMAIL}"
        },
        {
          "name": "AWS_REGION",
          "value": "${REGION}"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/portfolio-tracker",
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file:///tmp/task-definition.json \
  --region ${REGION}

# Step 5: Get VPC info for EventBridge
echo ""
echo "🔍 Step 5: Getting VPC information..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region ${REGION})
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query "Subnets[0].SubnetId" --output text --region ${REGION})
SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=${VPC_ID}" "Name=group-name,Values=default" --query "SecurityGroups[0].GroupId" --output text --region ${REGION})

echo "VPC: ${VPC_ID}"
echo "Subnet: ${SUBNET_ID}"
echo "Security Group: ${SG_ID}"

# Step 6: Create EventBridge IAM role
echo ""
echo "🔐 Step 6: Creating EventBridge IAM role..."
aws iam create-role --role-name EventBridgeECSRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "scheduler.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' --region ${REGION} 2>/dev/null || echo "Role already exists"

aws iam put-role-policy --role-name EventBridgeECSRole \
  --policy-name EventBridgeECSPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["ecs:RunTask"],
      "Resource": "*"
    },{
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": "*"
    }]
  }'

# Step 7: Create/Update EventBridge Scheduler (daily at 6 AM PT)
echo ""
echo "⏰ Step 7: Creating/updating daily schedule (6 AM PT)..."

# Get latest task definition revision
LATEST_REVISION=$(aws ecs describe-task-definition --task-definition portfolio-tracker-task --region ${REGION} --query 'taskDefinition.revision' --output text)
TASK_DEF_ARN="arn:aws:ecs:${REGION}:${ACCOUNT_ID}:task-definition/portfolio-tracker-task:${LATEST_REVISION}"

# Try to update existing schedule first
aws scheduler update-schedule \
  --name portfolio-tracker-daily \
  --schedule-expression "cron(0 14 * * ? *)" \
  --schedule-expression-timezone "America/Los_Angeles" \
  --flexible-time-window Mode=OFF \
  --target "{
    \"Arn\": \"arn:aws:ecs:${REGION}:${ACCOUNT_ID}:cluster/default\",
    \"RoleArn\": \"arn:aws:iam::${ACCOUNT_ID}:role/EventBridgeECSRole\",
    \"EcsParameters\": {
      \"TaskDefinitionArn\": \"${TASK_DEF_ARN}\",
      \"LaunchType\": \"FARGATE\",
      \"NetworkConfiguration\": {
        \"awsvpcConfiguration\": {
          \"Subnets\": [\"${SUBNET_ID}\"],
          \"SecurityGroups\": [\"${SG_ID}\"],
          \"AssignPublicIp\": \"ENABLED\"
        }
      }
    }
  }" \
  --region ${REGION} 2>/dev/null && echo "✅ Schedule updated to revision ${LATEST_REVISION}" || \
aws scheduler create-schedule \
  --name portfolio-tracker-daily \
  --schedule-expression "cron(0 14 * * ? *)" \
  --schedule-expression-timezone "America/Los_Angeles" \
  --flexible-time-window Mode=OFF \
  --target "{
    \"Arn\": \"arn:aws:ecs:${REGION}:${ACCOUNT_ID}:cluster/default\",
    \"RoleArn\": \"arn:aws:iam::${ACCOUNT_ID}:role/EventBridgeECSRole\",
    \"EcsParameters\": {
      \"TaskDefinitionArn\": \"${TASK_DEF_ARN}\",
      \"LaunchType\": \"FARGATE\",
      \"NetworkConfiguration\": {
        \"awsvpcConfiguration\": {
          \"Subnets\": [\"${SUBNET_ID}\"],
          \"SecurityGroups\": [\"${SG_ID}\"],
          \"AssignPublicIp\": \"ENABLED\"
        }
      }
    }
  }" \
  --region ${REGION} && echo "✅ Schedule created with revision ${LATEST_REVISION}"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Summary:"
echo "  - S3 Bucket: portfolio-tracker-reports"
echo "  - Docker Image: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/portfolio-tracker:latest"
echo "  - Daily run: 6:00 AM Pacific Time"
echo "  - Email: ${EMAIL}"
echo ""
echo "🧪 Test manually:"
echo "  ./infra/manually-run-task.sh"
echo ""
echo "📊 View logs:"
echo "  ./infra/view-logs.sh [--follow]"

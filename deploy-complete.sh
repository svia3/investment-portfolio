#!/bin/bash
# Complete deployment for Buffett Portfolio
# Update these variables with your information:

REGION="us-west-2"
ACCOUNT_ID="YOUR_ACCOUNT_ID"
EMAIL="your-email@example.com"

echo "🚀 Starting deployment..."

# Step 1: Deploy infrastructure
echo ""
echo "📦 Step 1: Deploying infrastructure (S3, ECR, IAM, Docker)..."
./infra/deploy.sh ${REGION} ${ACCOUNT_ID}

# Step 2: Verify SES email
echo ""
echo "📧 Step 2: Verifying SES email..."
aws ses verify-email-identity --email-address ${EMAIL} --region ${REGION}
echo "⚠️  CHECK YOUR EMAIL and click the verification link!"
read -p "Press Enter after verifying your email..."

# Step 3: Create CloudWatch log group
echo ""
echo "📝 Step 3: Creating CloudWatch log group..."
aws logs create-log-group \
  --log-group-name /ecs/buffett-portfolio \
  --region ${REGION} 2>/dev/null || echo "Log group already exists"

# Step 4: Register ECS task definition
echo ""
echo "🐳 Step 4: Registering ECS task definition..."
aws ecs register-task-definition \
  --cli-input-json file://infra/task-definition-template.json \
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

# Step 7: Create EventBridge Scheduler (daily at 6 AM PT)
echo ""
echo "⏰ Step 7: Creating daily schedule (6 AM PT)..."
aws scheduler create-schedule \
  --name buffett-portfolio-daily \
  --schedule-expression "cron(0 14 * * ? *)" \
  --schedule-expression-timezone "America/Los_Angeles" \
  --flexible-time-window Mode=OFF \
  --target "{
    \"Arn\": \"arn:aws:ecs:${REGION}:${ACCOUNT_ID}:cluster/default\",
    \"RoleArn\": \"arn:aws:iam::${ACCOUNT_ID}:role/EventBridgeECSRole\",
    \"EcsParameters\": {
      \"TaskDefinitionArn\": \"arn:aws:ecs:${REGION}:${ACCOUNT_ID}:task-definition/buffett-portfolio-task:1\",
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
  --region ${REGION} 2>/dev/null || echo "Schedule already exists"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Summary:"
echo "  - S3 Bucket: buffett-portfolio-reports"
echo "  - Docker Image: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/buffett-portfolio:latest"
echo "  - Daily run: 6:00 AM Pacific Time"
echo "  - Email: ${EMAIL}"
echo ""
echo "🧪 Test manually:"
echo "  aws ecs run-task \\"
echo "    --cluster default \\"
echo "    --task-definition buffett-portfolio-task:1 \\"
echo "    --launch-type FARGATE \\"
echo "    --network-configuration \"awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}\" \\"
echo "    --region ${REGION}"

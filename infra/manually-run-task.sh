#!/bin/bash
# Manually run ECS task for testing
# Usage: ./run-task.sh

set -e

REGION="us-west-2"
CLUSTER="default"
TASK_DEF="buffett-portfolio-task"

echo "🚀 Running ECS task manually..."

# Get VPC info
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region ${REGION})
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query "Subnets[0].SubnetId" --output text --region ${REGION})
SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=${VPC_ID}" "Name=group-name,Values=default" --query "SecurityGroups[0].GroupId" --output text --region ${REGION})

# Run task
TASK_ARN=$(aws ecs run-task \
  --cluster ${CLUSTER} \
  --task-definition ${TASK_DEF} \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}" \
  --region ${REGION} \
  --query 'tasks[0].taskArn' \
  --output text)

echo "✅ Task started: ${TASK_ARN}"
echo ""
echo "📊 View logs:"
echo "  aws logs tail /ecs/buffett-portfolio --follow --region ${REGION}"
echo ""
echo "🔍 Check task status:"
echo "  aws ecs describe-tasks --cluster ${CLUSTER} --tasks ${TASK_ARN} --region ${REGION}"

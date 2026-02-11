#!/bin/bash
# Deploy script for Buffett Portfolio ECS Task
# Usage: ./deploy.sh <aws-region> <aws-account-id>

set -e

# Disable AWS CLI pager
export AWS_PAGER=""

REGION=${1:-us-west-2}
ACCOUNT_ID=${2}
REPO_NAME="buffett-portfolio"
IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"
BUCKET_NAME="buffett-portfolio-reports"

if [ -z "$ACCOUNT_ID" ]; then
  echo "Usage: ./deploy.sh <aws-region> <aws-account-id>"
  exit 1
fi

echo "=== Step 1: Create S3 Bucket ==="
aws s3 mb s3://${BUCKET_NAME} --region ${REGION} 2>/dev/null || echo "Bucket already exists"

echo "=== Step 2: Create ECR Repository ==="
aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION} 2>/dev/null || echo "Repository already exists"

echo "=== Step 3: Build and Push Docker Image ==="
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if image already exists in ECR
IMAGE_EXISTS=$(aws ecr describe-images \
  --repository-name ${REPO_NAME} \
  --image-ids imageTag=${IMAGE_TAG} \
  --region ${REGION} 2>/dev/null || echo "")

if [ -n "$IMAGE_EXISTS" ]; then
  echo "Image ${IMAGE_TAG} already exists in ECR, skipping build"
else
  echo "Building new image with tag ${IMAGE_TAG}"
  docker build -f infra/Dockerfile -t ${REPO_NAME}:${IMAGE_TAG} .
  docker tag ${REPO_NAME}:${IMAGE_TAG} ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}
  docker tag ${REPO_NAME}:${IMAGE_TAG} ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest
  docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}
  docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest
  echo "Pushed tags: ${IMAGE_TAG}, latest"
fi

echo "=== Step 4: Create IAM Role for ECS Task ==="
ROLE_NAME="BuffettPortfolioTaskRole"

aws iam create-role --role-name ${ROLE_NAME} \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "Role already exists"

aws iam put-role-policy --role-name ${ROLE_NAME} \
  --policy-name BuffettPortfolioPolicy \
  --policy-document file://infra/task-role-policy.json

echo "=== Deployment Complete ==="
echo "Next steps:"
echo "1. Verify sender email in SES: aws ses verify-email-identity --email-address your-email@example.com --region ${REGION}"
echo "2. Create ECS task definition (see infra/task-definition-template.json)"
echo "3. Create EventBridge Scheduler rule to run daily"
echo ""
echo "Image URI: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}"

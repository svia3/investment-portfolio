#!/bin/bash
# Update S3 bucket policy to allow public read access for dashboard

BUCKET_NAME="portfolio-tracker-reports"
REGION="us-west-2"

echo "Setting up public access for dashboard..."

# First, disable block public access
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
  --region "$REGION"

# Then create bucket policy for public read on dashboard.html
cat > /tmp/dashboard-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadDashboard",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::portfolio-tracker-reports/dashboard.html"
    }
  ]
}
EOF

# Apply policy
aws s3api put-bucket-policy \
  --bucket "$BUCKET_NAME" \
  --policy file:///tmp/dashboard-policy.json \
  --region "$REGION"

echo "✅ Dashboard will be publicly accessible at:"
echo "https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/dashboard.html"

rm /tmp/dashboard-policy.json

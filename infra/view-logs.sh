#!/bin/bash
# View ECS task logs
# Usage: ./view-logs.sh [--follow]

REGION="us-west-2"
LOG_GROUP="/ecs/buffett-portfolio"

if [ "$1" = "--follow" ]; then
  echo "📊 Following logs (Ctrl+C to stop)..."
  aws logs tail ${LOG_GROUP} --follow --region ${REGION}
else
  echo "📊 Recent logs (last 50 lines)..."
  aws logs tail ${LOG_GROUP} --since 1h --region ${REGION}
  echo ""
  echo "💡 Tip: Use --follow to stream live logs"
fi

#!/bin/bash

# Determine the directory of the script
if [ -n "$BASH_SOURCE" ]; then
  # Bash
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -n "$ZSH_VERSION" ]; then
  # Zsh
  SCRIPT_DIR="$(cd "$(dirname "${(%):-%N}")" && pwd)"
else
  # Fallback for other shells
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi

# Set environment variables by sourcing the set_variables script.
echo "Setting environment variables..."
echo ""
source "$SCRIPT_DIR/set_variables.sh"

# Get the Cloud Run Custom Audience and the run invoker service account email address.
export AUDIENCE=$(terraform output -raw custom_audience)
export RUN_INVOKER_SERVICE_ACCOUNT=$(terraform output -raw terraform_service_account)
export TOKEN=$(gcloud auth print-identity-token --impersonate-service-account=$RUN_INVOKER_SERVICE_ACCOUNT --audiences=$AUDIENCE)
curl -X GET -H "Authorization: Bearer ${TOKEN}" "${AUDIENCE}/health"

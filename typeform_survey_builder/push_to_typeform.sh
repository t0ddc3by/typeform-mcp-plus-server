#!/bin/bash
# Push a Typeform payload to the API — create or update a form
#
# Usage:
#   Update existing form:
#     ./push_to_typeform.sh <payload.json> <form_id> <token>
#
#   Create new form (no form_id needed — workspace must be set in payload):
#     ./push_to_typeform.sh --create <payload.json> <token>
#
#   Or use the converter's --push flag instead:
#     python md_to_typeform.py survey.md --config config.json --output payload.json \
#       --workspace "Custom Curriculum" --token $TYPEFORM_TOKEN --push --form-id oi3zZtSx

set -euo pipefail

# ── Parse mode ──
if [ "${1:-}" = "--create" ]; then
  MODE="create"
  PAYLOAD="${2:?Usage: push_to_typeform.sh --create <payload.json> <token>}"
  TOKEN="${3:?Provide Typeform personal access token}"
  FORM_ID=""
else
  MODE="update"
  PAYLOAD="${1:?Usage: push_to_typeform.sh <payload.json> <form_id> <token>}"
  FORM_ID="${2:?Provide form ID}"
  TOKEN="${3:?Provide Typeform personal access token}"
fi

if [ "$MODE" = "create" ]; then
  echo "Creating new form from ${PAYLOAD}..."

  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://api.typeform.com/forms" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d @"${PAYLOAD}")

  HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
  BODY=$(echo "${RESPONSE}" | sed '$d')

  if [ "${HTTP_CODE}" -eq 201 ] || [ "${HTTP_CODE}" -eq 200 ]; then
    FIELDS=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('fields',[])))")
    NEW_ID=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])")
    URL=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['_links']['display'])")
    WORKSPACE=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('workspace',{}).get('href','unknown'))")
    echo "✅ Form created: ${FIELDS} fields"
    echo "   Form ID:   ${NEW_ID}"
    echo "   URL:        ${URL}"
    echo "   Workspace:  ${WORKSPACE}"
  else
    echo "❌ Failed with HTTP ${HTTP_CODE}:"
    echo "${BODY}" | python3 -m json.tool 2>/dev/null || echo "${BODY}"
    exit 1
  fi

else
  echo "Pushing payload to form ${FORM_ID}..."

  RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    "https://api.typeform.com/forms/${FORM_ID}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d @"${PAYLOAD}")

  HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
  BODY=$(echo "${RESPONSE}" | sed '$d')

  if [ "${HTTP_CODE}" -eq 200 ]; then
    FIELDS=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('fields',[])))")
    URL=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['_links']['display'])")
    WORKSPACE=$(echo "${BODY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('workspace',{}).get('href','unknown'))")
    echo "✅ Success: ${FIELDS} fields pushed"
    echo "   URL:        ${URL}"
    echo "   Workspace:  ${WORKSPACE}"
  else
    echo "❌ Failed with HTTP ${HTTP_CODE}:"
    echo "${BODY}" | python3 -m json.tool 2>/dev/null || echo "${BODY}"
    exit 1
  fi
fi

#!/bin/sh
# Ki Enterprise - Vault Initialization Script
# Uses vault CLI to write secrets (no curl/jq dependency)
# Actual secret values come from environment variables (see infrastructure/vault/.env, gitignored)
set -e

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-ki-vault-root-token}"

export VAULT_ADDR
export VAULT_TOKEN

echo "Waiting for Vault to be ready..."
until vault status > /dev/null 2>&1; do
  sleep 2
done

echo "Vault is ready."

# Enable KV v2 secrets engine at path ki-enterprise
echo "Enabling KV secrets engine..."
vault secrets enable -path=ki-enterprise kv-v2 2>/dev/null || true

echo "Writing secrets to Vault..."

# ============================================================
# OpenAI
# ============================================================
echo "  > OpenAI..."
vault kv put ki-enterprise/openai \
  api_key="${OPENAI_API_KEY}"

# ============================================================
# Google Gemini (Google AI Studio)
# ============================================================
echo "  > Google Gemini..."
vault kv put ki-enterprise/google-gemini \
  api_key="${GEMINI_API_KEY}" \
  project_id="${GEMINI_PROJECT_ID}"

# ============================================================
# Mistral AI
# ============================================================
echo "  > Mistral AI..."
vault kv put ki-enterprise/mistral \
  api_key="${MISTRAL_API_KEY}"

# ============================================================
# Groq AI
# ============================================================
echo "  > Groq AI..."
vault kv put ki-enterprise/groq \
  api_key="${GROQ_API_KEY}"

# ============================================================
# OpenRouter
# ============================================================
echo "  > OpenRouter..."
vault kv put ki-enterprise/openrouter \
  api_key="${OPENROUTER_API_KEY}"

# ============================================================
# HuggingFace
# ============================================================
echo "  > HuggingFace..."
vault kv put ki-enterprise/huggingface \
  api_key="${HUGGINGFACE_API_KEY}"

# ============================================================
# Ollama Cloud
# ============================================================
echo "  > Ollama Cloud..."
vault kv put ki-enterprise/ollama \
  api_key="${OLLAMA_CLOUD_API_KEY}"

# ============================================================
# Eden AI
# ============================================================
echo "  > Eden AI..."
vault kv put ki-enterprise/edenai \
  api_key="${EDENAI_API_KEY}"

# ============================================================
# Cloudflare (Workers AI + R2/S3 Storage)
# ============================================================
echo "  > Cloudflare..."
vault kv put ki-enterprise/cloudflare \
  api_token="${CLOUDFLARE_API_TOKEN}" \
  account_id="${CLOUDFLARE_ACCOUNT_ID}" \
  s3_access_key="${CLOUDFLARE_S3_ACCESS_KEY}" \
  s3_secret_key="${CLOUDFLARE_S3_SECRET_KEY}" \
  s3_endpoint="${CLOUDFLARE_S3_ENDPOINT}"

echo ""
echo "=== All secrets written to Vault successfully! ==="
echo ""
echo "Available secret paths under 'ki-enterprise/':"
echo "  - ki-enterprise/openai"
echo "  - ki-enterprise/google-gemini"
echo "  - ki-enterprise/mistral"
echo "  - ki-enterprise/groq"
echo "  - ki-enterprise/openrouter"
echo "  - ki-enterprise/huggingface"
echo "  - ki-enterprise/ollama"
echo "  - ki-enterprise/edenai"
echo "  - ki-enterprise/cloudflare"

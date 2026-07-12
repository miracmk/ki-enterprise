#!/bin/bash
# LiteLLM Model Güncelleme Scripti
# Her gün 00:01'de OpenRouter free modellerini günceller
# İsteğe bağlı: diğer sağlayıcıların modelleri de buradan güncellenebilir

set -euo pipefail

CONFIG_FILE="/opt/ki-enterprise/infrastructure/litellm/config.yaml"
OPENROUTER_API_KEY="***REMOVED-OPENROUTER-KEY***"
LOG_FILE="/opt/ki-enterprise/storage/logs/litellm-model-update.log"

mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Model güncelleme başladı..." >> "$LOG_FILE"

# OpenRouter free modellerini çek
FREE_MODELS=$(curl -s "https://openrouter.ai/api/v1/models" | jq -r '.data[] | select(.id | test(":free$")) | .id')

if [ -z "$FREE_MODELS" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HATA: OpenRouter'dan model listesi alınamadı!" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(echo "$FREE_MODELS" | wc -l) adet free model bulundu." >> "$LOG_FILE"

# OpenRouter bölümünü oluştur
OR_SECTION="# ============================================================
# OpenRouter (Free Models Only)
# ============================================================"

while IFS= read -r model_id; do
    # model_id formatı: provider/model-name:free
    # model_name için readable bir isim oluştur
    base_id="${model_id%:free}"
    model_name="openrouter-$(echo "$base_id" | sed 's|/|-|g' | sed 's|_|-|g' | sed 's|\.|-|g' | tr '[:upper:]' '[:lower:]')"
    
    OR_SECTION="$OR_SECTION
  - model_name: $model_name
    litellm_params:
      model: openrouter/$model_id
      api_key: $OPENROUTER_API_KEY"
done <<< "$FREE_MODELS"

# Config dosyasını güncelle (OpenRouter bölümünü değiştir)
# Awk kullanarak OpenRouter bölümünü bul ve değiştir
awk -v or_section="$OR_SECTION" '
    /# OpenRouter/ { in_or = 1 }
    in_or && /^  - model_name:/ { in_or_block = 1 }
    in_or && in_or_block && /^$/ { 
        print or_section
        in_or = 0; in_or_block = 0
        next
    }
    in_or { next }
    { print }
' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Config dosyası güncellendi: $CONFIG_FILE" >> "$LOG_FILE"

# LiteLLM container'ını yeniden başlat (değişikliklerin etkili olması için)
if docker ps --format '{{.Names}}' | grep -q "ki-enterprise-litellm"; then
    docker restart ki-enterprise-litellm
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LiteLLM container'ı yeniden başlatıldı." >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] UYARI: LiteLLM container'ı çalışmıyor, yeniden başlatma atlandı." >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Model güncelleme tamamlandı." >> "$LOG_FILE"
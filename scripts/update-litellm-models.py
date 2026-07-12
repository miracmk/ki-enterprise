#!/usr/bin/env python3
"""
LiteLLM Model Güncelleme Scripti
Her gün 00:01'de OpenRouter free modellerini günceller.
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from urllib.request import urlopen

CONFIG_FILE = "/opt/ki-enterprise/infrastructure/litellm/config.yaml"
OPENROUTER_API_KEY = "***REMOVED-OPENROUTER-KEY***"
LOG_FILE = "/opt/ki-enterprise/storage/logs/litellm-model-update.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_openrouter_free_models():
    """OpenRouter API'den :free etiketli modelleri çeker."""
    url = "https://openrouter.ai/api/v1/models"
    try:
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        free_models = [
            model["id"]
            for model in data.get("data", [])
            if model.get("id", "").endswith(":free")
        ]
        return sorted(free_models)
    except Exception as e:
        logger.error(f"OpenRouter API hatası: {e}")
        raise


def make_model_name(model_id: str) -> str:
    """Model ID'sinden readable bir model_name oluşturur."""
    base_id = model_id.replace(":free", "")
    name = base_id.replace("/", "-").replace("_", "-").replace(".", "-").lower()
    # Özel karakterleri temizle
    name = re.sub(r'[^a-z0-9-]', '', name)
    # Baştaki ve sondaki tireleri temizle
    name = name.strip("-")
    # Birden fazla tireyi tek tire yap
    name = re.sub(r'-+', '-', name)
    return f"openrouter-{name}"


def generate_openrouter_section(models: list) -> str:
    """OpenRouter bölümünü oluşturur."""
    lines = [
        "  # ============================================================",
        "  # OpenRouter (Free Models Only)",
        "  # ============================================================",
    ]
    for model_id in models:
        model_name = make_model_name(model_id)
        lines.append(f"  - model_name: {model_name}")
        lines.append("    litellm_params:")
        lines.append(f"      model: openrouter/{model_id}")
        lines.append(f"      api_key: {OPENROUTER_API_KEY}")
    return "\n".join(lines)


def update_config(new_or_section: str) -> bool:
    """Config dosyasındaki OpenRouter bölümünü günceller."""
    with open(CONFIG_FILE, "r") as f:
        content = f.read()

    # OpenRouter bölümünün başlangıcını ve bitişini bul
    start_pattern = r"  # ============================================================\n  # OpenRouter"
    end_pattern = r"\n\n  # ============================================================\n  # "

    # OpenRouter bölümünün başlangıcını bul
    start_match = re.search(start_pattern, content)
    if not start_match:
        logger.error("Config dosyasında OpenRouter bölümü bulunamadı!")
        return False

    start_idx = start_match.start()

    # Bir sonraki bölümün başlangıcını bul (bitiş)
    rest = content[start_idx + len(start_match.group()):]
    end_match = re.search(end_pattern, rest)
    if end_match:
        end_idx = start_idx + len(start_match.group()) + end_match.start()
    else:
        # Son bölümse, dosya sonuna kadar
        end_idx = len(content)

    # Eski OpenRouter bölümünü yenisiyle değiştir
    new_content = content[:start_idx] + new_or_section + content[end_idx:]

    with open(CONFIG_FILE, "w") as f:
        f.write(new_content)

    logger.info("Config dosyası güncellendi.")
    return True


def restart_litellm():
    """LiteLLM container'ını yeniden başlatır."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        if "ki-enterprise-litellm" in result.stdout:
            subprocess.run(
                ["docker", "restart", "ki-enterprise-litellm"],
                capture_output=True, timeout=30
            )
            logger.info("LiteLLM container'ı yeniden başlatıldı.")
        else:
            logger.warning("LiteLLM container'ı çalışmıyor, yeniden başlatma atlandı.")
    except Exception as e:
        logger.error(f"Container restart hatası: {e}")


def main():
    logger.info("Model güncelleme başladı...")

    try:
        free_models = get_openrouter_free_models()
        logger.info(f"{len(free_models)} adet free model bulundu.")

        or_section = generate_openrouter_section(free_models)
        if update_config(or_section):
            restart_litellm()

        logger.info("Model güncelleme tamamlandı.")
    except Exception as e:
        logger.error(f"Güncelleme başarısız: {e}")
        sys.exit(1)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    main()
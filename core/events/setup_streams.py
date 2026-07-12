"""
JetStream stream'lerini olusturur/gunceller (idempotent).
Kullanim: ./venv/bin/python setup_streams.py
"""
import asyncio

import nats
from nats.js.api import StreamConfig
from nats.js.errors import APIError

from config import settings
from streams import STREAM_DEFINITIONS, DEFAULT_MAX_AGE_SECONDS, DEFAULT_MAX_MSGS

# JetStream "stream name already in use" hata kodu - bkz. ADR-15 (JSApiStreamNameExistErr)
STREAM_ALREADY_EXISTS_CODE = 10058


async def main():
    nc = await nats.connect(settings.NATS_URL)
    js = nc.jetstream()

    for stream in STREAM_DEFINITIONS:
        cfg = StreamConfig(
            name=stream["name"],
            subjects=stream["subjects"],
            max_age=DEFAULT_MAX_AGE_SECONDS,
            max_msgs=DEFAULT_MAX_MSGS,
            storage="file",
        )
        try:
            await js.add_stream(cfg)
            print(f"  + olusturuldu: {stream['name']} <- {stream['subjects']}")
        except APIError as e:
            if e.err_code == STREAM_ALREADY_EXISTS_CODE:
                await js.update_stream(cfg)
                print(f"  ~ guncellendi: {stream['name']} <- {stream['subjects']}")
            else:
                print(f"  ! HATA ({stream['name']}): [{e.err_code}] {e.description}")
                raise

    await nc.close()
    print("Tum stream'ler hazir.")


if __name__ == "__main__":
    asyncio.run(main())

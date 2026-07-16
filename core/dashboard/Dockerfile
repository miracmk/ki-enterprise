FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" httpx pydantic-settings

COPY main.py config.py static_ui.py ./

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5009"]

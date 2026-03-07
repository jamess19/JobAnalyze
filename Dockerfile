FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt en_core_web_sm-3.8.0-py3-none-any.whl ./
COPY src/ src/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
RUN pip install en_core_web_sm-3.8.0-py3-none-any.whl
RUN playwright install chromium --with-deps

CMD ["python", "-m", "main"]

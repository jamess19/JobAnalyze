FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
COPY src/ src/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e . && python -m spacy download en_core_web_sm
RUN playwright install chromium --with-deps

CMD ["python", "-m", "main"]

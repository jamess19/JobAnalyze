FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
RUN playwright install chromium --with-deps

COPY src/ src/
COPY scrapy.cfg .

CMD ["python", "-m", "main"]

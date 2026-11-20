FROM python:3.11-slim

WORKDIR /app

# System libraries for OpenCV & PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

ARG INSTALL_AI_DEPS=false
RUN if [ "$INSTALL_AI_DEPS" = "true" ]; then \
      pip install --no-cache-dir -r requirements-ai.txt; \
    fi

COPY . .

RUN mkdir -p /app/recordings

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

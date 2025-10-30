FROM python:3.13.1-slim

WORKDIR /app

RUN apt update && \
    apt install -y --no-install-recommends \
    nano \
    libmagic1 \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]

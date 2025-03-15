FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Variabel lingkungan
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

# Variabel lingkungan untuk Supabase dan PostgreSQL akan diisi saat runtime
ENV SUPABASE_URL=""
ENV SUPABASE_KEY=""
ENV SUPABASE_JWT_SECRET=""
ENV DATABASE_URL=""
ENV JWT_SECRET_KEY=""

EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
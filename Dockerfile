FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
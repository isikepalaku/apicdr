# CDR Analyzer API

Aplikasi backend untuk menganalisis data CDR (Call Detail Records) dan menghubungkan entitas terkait, mirip dengan aplikasi i2 Notebook Analyst.

## Fitur

- Autentikasi API key untuk keamanan
- Manajemen session untuk analisis CDR
- Upload file CDR (single atau multiple)
- Analisis data CDR menggunakan NetworkX
- Visualisasi hubungan antar entitas (nomor telepon, IMEI, lokasi)
- Filter data berdasarkan berbagai kriteria
- Penyimpanan data di PostgreSQL

## Teknologi

- FastAPI sebagai framework API
- NetworkX untuk analisis graph
- Pandas untuk pemrosesan data
- PostgreSQL untuk penyimpanan data
- Docker untuk deployment
- Alembic untuk migrasi database

## Struktur Proyek

```
.
├── alembic/                # Migrasi database
├── app/
│   ├── data/               # Direktori untuk menyimpan data
│   ├── models/             # Model data (Pydantic dan SQLAlchemy)
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   ├── utils/              # Utility functions
│   ├── config.py           # Konfigurasi aplikasi
│   ├── database.py         # Koneksi database
│   └── main.py             # Entry point aplikasi
├── Dockerfile              # Konfigurasi Docker
├── docker-compose.yml      # Konfigurasi Docker Compose
├── alembic.ini             # Konfigurasi Alembic
├── .env                    # Variabel lingkungan (tidak di-commit)
└── requirements.txt        # Dependensi Python
```

## Cara Menjalankan

### Persiapan

1. Buat file `.env` berdasarkan `.env.example`:

```bash
cp .env.example .env
```

2. Isi variabel lingkungan di file `.env`:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cdr_analyzer
API_KEY=your-secure-api-key
```

### Menggunakan Docker

1. Clone repository
2. Jalankan dengan Docker Compose:

```bash
docker-compose up -d
```

3. Akses API di http://localhost:8000

### Tanpa Docker

1. Clone repository
2. Buat virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependensi:

```bash
pip install -r requirements.txt
```

4. Jalankan migrasi database:

```bash
alembic upgrade head
```

5. Jalankan aplikasi:

```bash
uvicorn app.main:app --reload
```

6. Akses API di http://localhost:8000

## Autentikasi API Key

Semua endpoint API dilindungi dengan autentikasi API key. Untuk mengakses API, Anda perlu menyertakan header `X-API-Key` dengan nilai yang sesuai dengan konfigurasi `API_KEY` di file `.env`.

Contoh:
```
curl -X GET "http://localhost:8000/api/sessions" -H "X-API-Key: your-secure-api-key"
```

## API Endpoints

### Autentikasi

- `GET /api/auth/users` - Dapatkan daftar semua user

### Session

- `POST /api/sessions` - Buat session baru
- `GET /api/sessions` - Dapatkan daftar session
- `GET /api/sessions/{session_id}` - Dapatkan detail session
- `DELETE /api/sessions/{session_id}` - Hapus session

### CDR

- `POST /api/cdr/upload` - Upload file CDR tunggal
- `POST /api/cdr/upload-multiple` - Upload beberapa file CDR
- `POST /api/cdr/analyze` - Analisis data CDR dan dapatkan data graph

## Format Data CDR

Aplikasi ini mendukung format CDR dengan kolom berikut:

```
CALL_TYPE|ANUMBER|BNUMBER|CNUMBER|DATE|DURATION|LAC_CI|IMEI
```

Contoh:
```
VAS|6285222243707|000|UN|2018-04-14 10:29:02.0|0|09419_47092|356912078685274
Voice MO|6285222243707|628124164478|UN|2018-04-12 21:46:45.0|60|09476_16971|356912078685274
```

## Deployment dengan Coolify

Aplikasi ini dapat dengan mudah di-deploy menggunakan Coolify:

1. Tambahkan repository ke Coolify
2. Konfigurasi deployment dengan Dockerfile
3. Tambahkan variabel lingkungan yang diperlukan
4. Deploy aplikasi

## Lisensi

MIT 
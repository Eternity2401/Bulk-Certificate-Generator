# 📜 Bulk Certificate Generator Backend API

[![CI Pipeline](https://github.com/username/bulk-certificate-generator/actions/workflows/ci.yml/badge.svg)](https://github.com)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-quality, lightweight, and interview-ready **Bulk Certificate Generator Backend API** built with **FastAPI**, **SQLAlchemy 2.0**, **SQLite**, and **ReportLab**.

The system enables organizations to submit bulk certificate generation requests for hundreds of recipients, validates input data, asynchronously renders vector PDF certificates with embedded QR codes, tracks real-time progress, handles individual failures without stopping the batch, and provides single & batch ZIP downloads.

---

## 🌟 Key Features

- **🚀 High-Speed Bulk Generation**: Accepts hundreds of recipients in a single request and returns an immediate `202 Accepted` job receipt.
- **⚡ Asynchronous Background Processing**: Uses non-blocking background workers (`FastAPI BackgroundTasks`) with atomic database state tracking.
- **🛡️ Isolated Fault Tolerance**: If 1 recipient record fails (e.g. malformed data), all other valid certificates are generated successfully. The job finishes with status `COMPLETED_WITH_ERRORS` and logs the exact failure reason per item.
- **📄 Vector PDF Engine**: Custom ReportLab engine producing crisp landscape certificates with gold ornate borders and elegant typography in milliseconds without heavy headless browser binaries.
- **🔍 Public QR Code Verification**: Every certificate embeds a unique verification code and QR code linking directly to `/api/v1/certificates/verify/{certificate_id}`.
- **📦 Batch ZIP Retrieval**: Download all successfully generated certificates in a single compressed ZIP archive with one click.
- **🎨 Interactive Web Dashboard**: Built-in, responsive Jinja2/Vanilla JS frontend with drag-and-drop CSV import, live polling progress bar, and verification portal.
- **☁️ 100% Free Cloud Deployment**: Fully configured for **Render's Free Web Service** with zero external paid dependencies or API keys.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer"]
        UI["Web Dashboard (Vanilla JS / HTML5)"]
        APIClient["API Client / cURL / Postman"]
    end

    subgraph FastAPILayer ["FastAPI Core Application"]
        Router["api/routes.py"]
        Schemas["schemas/certificate.py (Pydantic v2)"]
        BgTasks["FastAPI BackgroundTasks"]
        
        subgraph Services ["Service Layer"]
            CertService["services/certificate_service.py (Orchestrator)"]
            PDFService["services/pdf_service.py (ReportLab Engine)"]
            QRService["services/qr_service.py (QR Generator)"]
        end
    end

    subgraph StorageLayer ["Persistence Layer"]
        DB[(SQLite: jobs & certificate_items)]
        Disk[("certificates/ (PDFs & ZIP Bundles)")]
    end

    UI -->|POST Request / CSV| Router
    APIClient -->|POST /generate| Router
    Router -->|Validate Schema| Schemas
    Router -->|Create Job & Items PENDING| DB
    Router -->|Dispatch Worker| BgTasks
    Router -->|Return 202 job_id immediately| UI

    BgTasks -->|Run Asynchronously| CertService
    CertService -->|Update status: PROCESSING| DB
    CertService -->|Per Recipient Loop| PDFService
    PDFService -->|Generate QR Code| QRService
    PDFService -->|Render Vector PDF| Disk
    CertService -->|Update Item COMPLETED/FAILED| DB
    CertService -->|Aggregate Counters & Final Status| DB

    UI -->|GET /jobs/{id} Polling| Router
    UI -->|GET /jobs/{id}/download-all ZIP| Router
```

---

## 🗄️ Database Design (Strictly 2 Tables)

The schema is intentionally kept minimal, relational, and easy to explain:

### 1. `jobs` Table
Tracks the overarching batch request metadata and completion counters.
- `id` (String UUID, PK)
- `course_name` (String)
- `issue_date` (String)
- `status` (`PENDING` | `PROCESSING` | `COMPLETED` | `COMPLETED_WITH_ERRORS` | `FAILED`)
- `total_count` (Integer)
- `success_count` (Integer)
- `failed_count` (Integer)
- `created_at` (DateTime)
- `completed_at` (DateTime, Nullable)

### 2. `certificate_items` Table
Tracks individual recipient certificate items, file paths, and failure logs.
- `id` (String UUID, PK)
- `job_id` (String UUID, FK -> `jobs.id`)
- `certificate_id` (String, Unique e.g. `CERT-AB12-CD34`)
- `recipient_name` (String)
- `recipient_email` (String, Nullable)
- `status` (`PENDING` | `PROCESSING` | `COMPLETED` | `FAILED`)
- `file_path` (String, Nullable)
- `error_message` (Text, Nullable)
- `created_at` (DateTime)

---

## 📂 Project Structure

```
bulk-certificate-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                     # App factory, CORS, static & template mounts
│   ├── config.py                   # App settings (BASE_URL, STORAGE_DIR)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # REST API endpoints & HTML page routes
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite engine, SessionLocal, get_db dependency
│   │   └── models.py               # Job and CertificateItem SQLAlchemy models + Enums
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── certificate.py          # Pydantic models for request, response, items
│   ├── services/
│   │   ├── __init__.py
│   │   ├── certificate_service.py  # Background job runner & status coordinator
│   │   ├── pdf_service.py          # ReportLab certificate template engine
│   │   └── qr_service.py           # QR code generation with verification URL
│   ├── templates/
│   │   ├── dashboard.html          # Clean Jinja2 web UI for generator demo
│   │   └── verify.html             # Public certificate verification web page
│   └── static/
│       ├── style.css               # Modern, clean CSS
│       └── app.js                  # Vanilla JS for CSV parse, API fetch, progress polling
├── certificates/                   # Directory where generated PDFs/ZIPs are stored
│   └── .gitkeep
├── sample_data/
│   ├── sample_recipients.csv       # Ready-to-test CSV file
│   └── sample_request.json         # Ready-to-test JSON payload
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # In-memory SQLite DB fixture & HTTPX TestClient
│   ├── test_api.py                 # Endpoints: generate, status, download, zip, verify
│   ├── test_generation.py          # PDF & QR generation isolated tests
│   └── test_validation.py          # Pydantic input validation & error tests
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions pytest runner
├── Dockerfile                      # Single-stage Dockerfile
├── render.yaml                     # 1-Click Render Free Deployment Blueprint
├── requirements.txt                # Locked dependencies
├── .gitignore                      # Ignore *.db, __pycache__, certificates/
└── README.md                       # Documentation & Interview Guide
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/your-username/bulk-certificate-generator.git
cd bulk-certificate-generator
```

### 2. Create and activate a virtual environment
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
# Recommended (Universal runner - works from anywhere):
python run.py

# Or directly with Python module:
python -m uvicorn app.main:app --reload --port 8000

# On Windows: you can also simply double-click start.bat
```

- 🌐 **Web Dashboard**: Open [http://localhost:8000](http://localhost:8000)
- 📖 **Interactive Swagger UI**: Open [http://localhost:8000/docs](http://localhost:8000/docs)
- 🔍 **ReDoc Documentation**: Open [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Automated Tests

Run the full automated test suite using `pytest`:

```bash
# Run tests using python module:
python -m pytest

# On Windows: you can also double-click test.bat
```

Expected output:
```
tests/test_api.py::test_create_and_process_job_e2e PASSED
tests/test_api.py::test_individual_failure_isolation PASSED
tests/test_api.py::test_non_existent_job_404 PASSED
tests/test_api.py::test_non_existent_certificate_download_404 PASSED
tests/test_api.py::test_non_existent_certificate_verify_404 PASSED
tests/test_api.py::test_health_check PASSED
tests/test_generation.py::test_qr_code_generation PASSED
tests/test_generation.py::test_pdf_generation_creates_valid_file PASSED
tests/test_generation.py::test_sanitize_filename PASSED
tests/test_validation.py::test_empty_request_body PASSED
tests/test_validation.py::test_missing_course_name PASSED
tests/test_validation.py::test_missing_issue_date PASSED
tests/test_validation.py::test_empty_recipients_list PASSED
tests/test_validation.py::test_empty_recipient_name PASSED
tests/test_validation.py::test_invalid_recipient_email_format PASSED
tests/test_validation.py::test_valid_request_without_email PASSED

======================== 16 passed in 0.55s ========================
```

---

## 📡 REST API Reference

### 1. Submit Bulk Certificate Generation Request
- **Endpoint**: `POST /api/v1/certificates/generate`
- **Status**: `202 Accepted`

#### Request Body:
```json
{
  "course_name": "Full Stack & Cloud Architecture",
  "issue_date": "October 7, 2026",
  "recipients": [
    { "name": "Alice Johnson", "email": "alice@example.com" },
    { "name": "Bob Smith", "email": "bob@example.com" }
  ]
}
```

#### Response:
```json
{
  "job_id": "7f8b9e6c-31a2-4c9f-8d2b-1a9e8f7c6d5e",
  "status": "PENDING",
  "total_count": 2,
  "message": "Certificate generation job accepted and scheduled for background processing."
}
```

#### cURL Example:
```bash
curl -X POST http://localhost:8000/api/v1/certificates/generate \
  -H "Content-Type: application/json" \
  -d @sample_data/sample_request.json
```

---

### 2. Poll Job Status & Item Breakdown
- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}`
- **Status**: `200 OK`

#### Response:
```json
{
  "job_id": "7f8b9e6c-31a2-4c9f-8d2b-1a9e8f7c6d5e",
  "course_name": "Full Stack & Cloud Architecture",
  "issue_date": "October 7, 2026",
  "status": "COMPLETED",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "pending": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T08:00:00",
  "completed_at": "2026-10-07T08:00:02",
  "download_all_url": "/api/v1/certificates/jobs/7f8b9e6c-31a2-4c9f-8d2b-1a9e8f7c6d5e/download-all",
  "items": [
    {
      "id": "e3a89e1a-5b12-4c11-912a-3c5e8f7d9a1b",
      "certificate_id": "CERT-8K2N-9L1P",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "COMPLETED",
      "download_url": "/api/v1/certificates/e3a89e1a-5b12-4c11-912a-3c5e8f7d9a1b/download",
      "error_message": null,
      "created_at": "2026-10-07T08:00:00"
    }
  ]
}
```

---

### 3. Download Individual Certificate PDF
- **Endpoint**: `GET /api/v1/certificates/{item_id}/download`
- **Status**: `200 OK` (`Content-Type: application/pdf`)

```bash
curl -O -J http://localhost:8000/api/v1/certificates/{item_id}/download
```

---

### 4. Download All Certificates as a ZIP
- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}/download-all`
- **Status**: `200 OK` (`Content-Type: application/zip`)

```bash
curl -O -J http://localhost:8000/api/v1/certificates/jobs/{job_id}/download-all
```

---

### 5. Verify Certificate Authenticity
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_id}`
- **Status**: `200 OK`

- When accessed via **Browser / QR code scan**: Renders an authentic Certificate Verification Badge HTML page.
- When accessed via **JSON client / API**: Returns verification payload:

```json
{
  "certificate_id": "CERT-8K2N-9L1P",
  "recipient_name": "Alice Johnson",
  "course_name": "Full Stack & Cloud Architecture",
  "issue_date": "October 7, 2026",
  "status": "VALID",
  "issued_at": "2026-10-07T08:00:00",
  "download_url": "/api/v1/certificates/e3a89e1a-5b12-4c11-912a-3c5e8f7d9a1b/download"
}
```

---

## 🎯 Key Design Decisions & Interview Talking Points

During an interview, you may be asked to justify architectural choices:

### 1. Why FastAPI `BackgroundTasks` instead of Celery + Redis?
> **Answer**: For this application's scope, FastAPI `BackgroundTasks` provides true asynchronous, non-blocking execution with zero external infrastructure overhead (no Redis server, no RabbitMQ broker, no extra worker process daemon). Because all database state updates are transactionally committed to SQLite, client requests are never blocked.  
> Furthermore, because our service layer (`process_certificate_job`) is cleanly decoupled from HTTP routes, scaling to a distributed multi-worker cluster (Celery/Redis/RQ) only requires changing the task invocation without touching any certificate generation or database logic.

### 2. Why ReportLab over Headless Browser HTML-to-PDF (Puppeteer/WeasyPrint)?
> **Answer**: ReportLab renders native vector PDFs directly in Python memory in single-digit milliseconds. Headless browsers require launching heavy Chromium binaries (~300MB RAM per process), often fail or timeout in lightweight serverless/container environments, and introduce font-rendering inconsistencies. ReportLab creates sharp, lightweight, highly reproducible PDF files with minimal CPU and memory footprint.

### 3. How is Partial Failure Handled?
> **Answer**: Inside `process_certificate_job`, each recipient generation is wrapped in an isolated `try-except` block. An individual failure (e.g. invalid name or filesystem error) sets only that item's status to `FAILED` and logs `error_message`, while all remaining valid items continue processing. If at least 1 item succeeded and 1 failed, the overarching job is marked `COMPLETED_WITH_ERRORS`, giving clients complete visibility into what succeeded and what failed.

### 4. Why SQLite?
> **Answer**: SQLite requires zero setup, zero network roundtrips, and stores data in a single file, making it ideal for evaluation, local testing, and free-tier cloud containers. Thanks to SQLAlchemy 2.0 ORM abstraction, switching to PostgreSQL in enterprise production is as simple as updating the `DATABASE_URL` environment variable.

---

## ☁️ Free Cloud Deployment Guide (Render)

This application is 100% ready to deploy on **Render's Free Web Service** with zero billing account or credit card required:

### Option A: 1-Click / Git Push Deploy (Recommended)
1. Push this repository to your **GitHub** account.
2. Sign up / Log in to [Render](https://render.com) (Free account).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the service:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
6. Add Environment Variable:
   - `BASE_URL`: `https://<your-render-subdomain>.onrender.com` (for QR code verification links)
7. Click **Create Web Service**. Your live backend & dashboard will be accessible publicly in ~2 minutes!

> [!NOTE]
> **Free Hosting Considerations**: Render's free tier spins down after 15 minutes of inactivity (taking ~30s on first wakeup) and uses an ephemeral filesystem (files reset on restarts). The application is designed so real-time generation and downloads happen instantly within active sessions.

---

## 🐳 Docker Deployment

To run locally or deploy using Docker:

```bash
# Build the Docker container
docker build -t bulk-certificate-generator .

# Run the container
docker run -p 8000:8000 bulk-certificate-generator
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 📄 License
This project is licensed under the MIT License — feel free to use, modify, and distribute it for academic and professional evaluation.

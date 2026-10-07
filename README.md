# CertiFlow — Bulk Certificate Generator API

[![CI Pipeline](https://github.com/username/bulk-certificate-generator/actions/workflows/ci.yml/badge.svg)](https://github.com)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CertiFlow is a high-performance, lightweight backend API service designed for automated, bulk PDF certificate generation with real-time job progress tracking, fault-tolerant batch processing, and embedded cryptographic QR code verification.

---

## 🌟 Key Features

- **🚀 Bulk Generation**: Accepts hundreds of recipient records in a single API payload and returns an immediate `202 Accepted` job handle.
- **⚡ Asynchronous Processing**: Leverages non-blocking background workers (`FastAPI BackgroundTasks`) with atomic database state tracking.
- **🛡️ Isolated Fault Tolerance**: Individual recipient validation or generation errors do not abort the batch. Valid certificates generate smoothly, while failed items record detailed error logs.
- **📄 Native Vector PDF Engine**: Custom ReportLab layout producing crisp, lightweight landscape certificates with gold and navy ornate borders and typography.
- **🔍 Public QR Code Verification**: Every certificate embeds a unique verification code and QR code linking directly to a public verification portal.
- **📦 Batch ZIP Retrieval**: Allows instant streaming of all successfully generated certificates in a single compressed ZIP archive.
- **🎨 Interactive Web Dashboard**: Built-in Jinja2/Vanilla JS interface featuring CSV file import, live polling progress bar, and instant download buttons.
- **☁️ Cloud-Ready & Containerized**: Ready for containerized deployment via Docker or zero-cost deployment on Render Free Web Service.

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI (Async, OpenAPI/Swagger autodocs)
- **Data Validation**: Pydantic v2
- **ORM & Database**: SQLAlchemy 2.0 with SQLite (PostgreSQL compatible)
- **PDF Generation**: ReportLab
- **QR Code Engine**: qrcode + Pillow
- **Frontend / Templates**: Jinja2 + Vanilla HTML5/CSS3/JavaScript (Fetch API polling)
- **Testing**: Pytest + HTTPX
- **Deployment**: Docker, Render Blueprint (`render.yaml`), GitHub Actions CI

---

## 🏗️ Architecture & Processing Flow

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

### Processing Workflow:
1. **Request Ingestion**: The client sends a `POST /api/v1/certificates/generate` request containing course details, issue date, and an array of recipient objects.
2. **Persistence & Acceptance**: A `Job` record and associated `CertificateItem` records are created in SQLite with `PENDING` status. An immediate `202 Accepted` response with the `job_id` is returned.
3. **Background Execution**: FastAPI `BackgroundTasks` executes the job orchestrator (`process_certificate_job`).
4. **Isolated Rendering**: Each recipient's vector PDF is rendered independently. An embedded QR code pointing to `/api/v1/certificates/verify/{certificate_id}` is generated using the configured `BASE_URL`.
5. **State Aggregation**: Upon completion of all items, the job status transitions to `COMPLETED` (if all succeeded) or `COMPLETED_WITH_ERRORS` (if any items encountered an error).

---

## 🗄️ Database Design

The database schema consists of two normalized tables:

### 1. `jobs` Table
Tracks overarching batch requests and aggregate metrics:
- `id` (String UUID, Primary Key)
- `course_name` (String, Non-nullable)
- `issue_date` (String, Non-nullable)
- `status` (Enum: `PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`)
- `total_count` (Integer, Default: 0)
- `success_count` (Integer, Default: 0)
- `failed_count` (Integer, Default: 0)
- `created_at` (DateTime, Default: UTC Now)
- `completed_at` (DateTime, Nullable)

### 2. `certificate_items` Table
Tracks individual recipient certificate records:
- `id` (String UUID, Primary Key)
- `job_id` (String UUID, Foreign Key $\rightarrow$ `jobs.id`)
- `certificate_id` (String, Unique Index, e.g., `CERT-AB12-CD34`)
- `recipient_name` (String, Non-nullable)
- `recipient_email` (String, Nullable)
- `status` (Enum: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`)
- `file_path` (String, Nullable, Local relative path)
- `error_message` (Text, Nullable, Failure reason)
- `created_at` (DateTime, Default: UTC Now)

---

## 📂 Project Directory Structure

```
bulk-certificate-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application factory, middleware & routing
│   ├── config.py                   # Environment configuration (Pydantic Settings)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # REST API endpoints & HTML template routes
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLAlchemy engine & session dependency
│   │   └── models.py               # ORM models and state Enums
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── certificate.py          # Pydantic v2 request & response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── certificate_service.py  # Background job orchestrator & error isolator
│   │   ├── pdf_service.py          # ReportLab PDF template renderer
│   │   └── qr_service.py           # In-memory QR code generator
│   ├── templates/
│   │   ├── dashboard.html          # Interactive Web UI template
│   │   └── verify.html             # Public certificate verification template
│   └── static/
│       ├── style.css               # Clean, responsive CSS stylesheet
│       └── app.js                  # Vanilla JS frontend logic & polling handler
├── certificates/                   # Storage directory for generated PDF files
│   └── .gitkeep
├── sample_data/
│   ├── sample_recipients.csv       # Sample CSV recipient roster
│   └── sample_request.json         # Sample JSON generation payload
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures & isolated test client
│   ├── test_api.py                 # E2E API and integration test suite
│   ├── test_generation.py          # PDF and QR generation unit tests
│   └── test_validation.py          # Pydantic schema validation tests
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions automated test workflow
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore patterns
├── Dockerfile                      # Production container image definition
├── pytest.ini                      # Pytest configuration
├── render.yaml                     # Render Free Web Service deployment blueprint
├── requirements.txt                # Production and test dependencies
├── run.py                          # Cross-platform application entrypoint
├── start.bat                       # Windows 1-click startup script
├── test.bat                        # Windows 1-click test script
└── README.md                       # Project documentation
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/username/bulk-certificate-generator.git
cd bulk-certificate-generator
```

### 2. Create and Activate Virtual Environment
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
To customize settings, create a `.env` file from the provided template:
```bash
# Linux / macOS
cp .env.example .env

# Windows (CMD / PowerShell)
copy .env.example .env
```

Configurable options in `.env`:
- `BASE_URL`: Base URL used inside embedded QR verification links (e.g. `http://localhost:8000`, `http://192.168.1.9:8000`, or `https://my-app.onrender.com`).
- `DATABASE_URL`: Database connection string (defaults to SQLite: `sqlite:///certificates.db`).

---

## 💻 Running the Application

### Option A: Using the Runner Script (Recommended)
```bash
python run.py
```
*(On Windows, you can also double-click `start.bat`)*

### Option B: Using Uvicorn Directly
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access URLs:
- 🌐 **Interactive Dashboard**: `http://localhost:8000`
- 📖 **Interactive Swagger Docs**: `http://localhost:8000/docs`
- 🔍 **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 🧪 Automated Testing

Execute the test suite using `pytest`:

```bash
python -m pytest
```
*(On Windows, you can also double-click `test.bat`)*

### Test Coverage Highlights:
- Request validation (empty payload, missing fields, malformed email)
- Asynchronous job execution and database status transitions
- Isolated per-recipient error handling
- ReportLab vector PDF rendering and header verification
- Dynamic QR code generation with custom `BASE_URL`
- Single certificate PDF download (`application/pdf`)
- Batch compressed ZIP download (`application/zip`)
- Certificate verification endpoint (JSON and HTML)
- Missing resource handling (HTTP 404)

---

## 📡 REST API Reference

### 1. Submit Generation Request
- **Endpoint**: `POST /api/v1/certificates/generate`
- **Status**: `202 Accepted`

#### Request:
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

---

### 2. Query Job Progress & Results
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
  "created_at": "2026-10-07T12:00:00",
  "completed_at": "2026-10-07T12:00:02",
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
      "created_at": "2026-10-07T12:00:00"
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

### 4. Download Batch ZIP Archive
- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}/download-all`
- **Status**: `200 OK` (`Content-Type: application/zip`)

```bash
curl -O -J http://localhost:8000/api/v1/certificates/jobs/{job_id}/download-all
```

---

### 5. Verify Certificate Authenticity
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_id}`
- **Status**: `200 OK`

- **Web Browser / QR Scan**: Displays the official HTML Verification Badge page.
- **API Clients**: Returns JSON verification payload:

```json
{
  "certificate_id": "CERT-8K2N-9L1P",
  "recipient_name": "Alice Johnson",
  "course_name": "Full Stack & Cloud Architecture",
  "issue_date": "October 7, 2026",
  "status": "VALID",
  "issued_at": "2026-10-07T12:00:00",
  "download_url": "/api/v1/certificates/e3a89e1a-5b12-4c11-912a-3c5e8f7d9a1b/download"
}
```

---

## 🛡️ Error Handling & Fault Isolation

- **Request Validation**: Handled by Pydantic v2 before entering the database. Missing required fields or malformed formats trigger immediate HTTP 422 responses.
- **Recipient Error Isolation**: During background batch generation, each recipient item is processed within an isolated `try-except` block. A failure in one item (e.g. disk write failure or corrupted characters) is logged to `error_message`, and the item is marked `FAILED`. All other valid items continue processing.
- **Job Status Differentiation**:
  - `COMPLETED`: 100% of recipients generated successfully.
  - `COMPLETED_WITH_ERRORS`: Partial success (at least one succeeded, at least one failed).
  - `FAILED`: All items in the batch encountered fatal errors.

---

## ⚙️ Technical Design Decisions

1. **FastAPI BackgroundTasks vs Distributed Brokers**:
   FastAPI `BackgroundTasks` was selected to provide non-blocking asynchronous execution without requiring external dependencies (Redis, RabbitMQ). Because the orchestrator logic (`process_certificate_job`) is decoupled in a dedicated service layer, scaling to Celery/Redis for multi-node distributed clusters requires only adjusting the task dispatcher.
2. **ReportLab Native Vector Generation**:
   Using ReportLab generates native vector PDFs directly in memory in single-digit milliseconds per file, avoiding the high memory overhead (~300MB RAM per worker) and binary dependencies of headless browser rendering engines.
3. **Database Architecture**:
   SQLite with SQLAlchemy 2.0 ORM provides zero-configuration local and containerized execution while maintaining complete schema portability for PostgreSQL via `DATABASE_URL`.

---

## ☁️ Deployment Guide

### Deploying to Render Free Web Service

1. Push this repository to GitHub.
2. In [Render](https://render.com), create a new **Web Service** and connect your repository.
3. Configure the build and start settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Add Environment Variable:
   - `BASE_URL`: `https://<your-service-name>.onrender.com`
5. Click **Create Web Service**.

> **Note on Free Tier Storage**: Render Free Web Services operate on ephemeral storage. Generated PDF files and SQLite records persist throughout active runtime sessions but reset when the instance restarts.

### Deploying with Docker

```bash
# Build Docker image
docker build -t certiflow .

# Run Docker container
docker run -d -p 8000:8000 --name certiflow-app certiflow
```

---

## 🔮 Limitations & Future Scope

- **Template Selection**: Currently uses one standardized landscape certificate design. Future iterations could support customizable template stylesheets.
- **Distributed Queues**: For extremely large batches ($10,000+$ recipients), migrating from in-process background tasks to a Redis/Celery queue with persistent worker nodes would provide horizontal scale.
- **Cloud Object Storage**: Storing generated PDF files in Amazon S3 or Google Cloud Storage would enable persistent storage across stateless serverless instances.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

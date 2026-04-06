# Tech Stack Overview

This document provides a comprehensive overview of the technologies used in the **Help U - Bookkeeper** project.

## 🎨 Frontend (FE)

The frontend is a modern Single Page Application (SPA) built with React and Vite, focusing on performance and developer experience.

- **Framework**: [React 19](https://react.dev/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Language**: JavaScript (JSX/ESNext)
- **Styling**: [Tailwind CSS 4.x](https://tailwindcss.com/) with PostCSS
- **Routing**: [React Router 7](https://reactrouter.com/)
- **HTTP Client**: [Axios](https://axios-http.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **State Management**: React Context API
- **Code Quality**: ESLint
- **Deployment**: Nginx (Dockerized)

## ⚙️ Backend (BE)

The backend is a robust Python-based API server designed for high performance and scalability, handling AI processing, media, and integrations.

- **Language**: [Python 3.10+](https://www.python.org/)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Web Server**: [Uvicorn](https://www.uvicorn.org/)
- **Database**: 
  - [PostgreSQL](https://www.postgresql.org/) (Production via Cloud SQL)
  - [SQLite](https://www.sqlite.org/) (Local development)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication**: JWT (JSON Web Tokens)
- **AI & ML**:
  - [OpenAI API](https://openai.com/) (GPT models for data extraction)
  - [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (High-performance speech-to-text)
- **Media & PDF Processing**:
  - [PyPDF2](https://pypdf2.readthedocs.io/) & [pdf2image](https://github.com/Belval/pdf2image) (PDF handling)
  - [Pillow](https://python-pillow.org/) (Image processing)
  - [ReportLab](https://www.reportlab.com/) (PDF generation)
  - [Pydub](http://pydub.com/) (Audio manipulation)
- **Task Scheduling**: [APScheduler](https://apscheduler.readthedocs.io/)
- **Integrations**:
  - [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/)
  - [Google Drive API](https://developers.google.com/drive) (Cloud storage)
  - [Stripe API](https://stripe.com/docs/api) (Payments & Subscriptions)
- **Testing**: [Pytest](https://docs.pytest.org/)

## 🚀 Infrastructure & DevOps

- **Containerization**: [Docker](https://www.docker.com/)
- **Cloud Platform**: [Google Cloud Platform (GCP)](https://cloud.google.com/)
  - [Cloud Run](https://cloud.google.com/run) (Serverless deployment)
  - [Cloud SQL](https://cloud.google.com/sql) (Managed PostgreSQL)
- **Environment Management**: Python `venv`, `.env`

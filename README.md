# BharatBuild AI Platform

A comprehensive AI-driven platform for academic projects, code automation, product building, and educational management.

## Features

### 🎓 Student Mode
- Full academic project generation
- Automated SRS, UML diagrams, code, reports, presentations
- Viva Q&A preparation
- Multi-agent orchestration for complete project delivery

### 💻 Developer Mode
- Code automation (similar to Bolt.new)
- Real-time code generation
- Multi-framework support
- Instant deployable projects

### 🚀 Founder Mode
- Product ideation and validation
- PRD generation
- Business plan creation
- Go-to-market strategy

### 🏫 College Mode
- Faculty management
- Batch/student tracking
- Project monitoring
- Analytics dashboard

### 🔌 API Partner Mode
- Token-based API access
- Usage tracking
- Flexible pricing
- Developer documentation

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery
- **AI**: Claude 3.5 Haiku & Sonnet
- **Storage**: AWS S3 / MinIO
- **Auth**: JWT + Google OAuth
- **Billing**: Razorpay

### Frontend
- **Framework**: Next.js 14
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **State**: React Context + SWR
- **Forms**: React Hook Form + Zod

### DevOps
- **Containerization**: Docker
- **Orchestration**: Docker Compose
- **Web Server**: Nginx
- **CI/CD**: GitHub Actions
- **Deployment**: AWS ECS / Render

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../.env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev
```

### Docker Setup

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Project Structure

```
BharatBuild_AI/
├── backend/
│   ├── app/
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── projects/
│   │   │   ├── agents/
│   │   │   ├── orchestrator/
│   │   │   ├── billing/
│   │   │   ├── documents/
│   │   │   ├── admin/
│   │   │   └── api_keys/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── hooks/
│   └── package.json
├── docker/
├── docs/
└── docker-compose.yml
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.

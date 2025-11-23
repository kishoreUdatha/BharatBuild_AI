# Quick Start Guide

Get BharatBuild AI running in 5 minutes!

## Prerequisites

- **Docker Desktop** installed ([Download here](https://www.docker.com/products/docker-desktop))
- **Claude API Key** from Anthropic ([Get one here](https://console.anthropic.com/))

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd BharatBuild_AI
```

## Step 2: Configure Environment

### Windows
```bash
copy .env.example .env
notepad .env
```

### macOS/Linux
```bash
cp .env.example .env
nano .env
```

**Add your Claude API key:**
```bash
ANTHROPIC_API_KEY=your-api-key-here
```

## Step 3: Run Setup Script

### Windows
```bash
setup.bat
```

### macOS/Linux
```bash
chmod +x setup.sh
./setup.sh
```

## Step 4: Access the Platform

Once setup is complete:

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Backend**: http://localhost:8000

## Step 5: Create Your First Project

1. Open http://localhost:3000
2. Click "Register" and create an account
3. Login with your credentials
4. Click "New Project"
5. Fill in the details:
   - **Title**: "My E-Commerce Platform"
   - **Mode**: Student
   - **Domain**: Web Development
   - **Description**: "A full-featured e-commerce platform"
6. Click "Create & Execute"
7. Watch the AI generate your complete project!

## Common Commands

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Access Database
```bash
docker-compose exec postgres psql -U bharatbuild -d bharatbuild_db
```

### Access Redis
```bash
docker-compose exec redis redis-cli
```

## Troubleshooting

### Port Already in Use

If port 3000, 8000, or 5432 is already in use:

1. Stop the service using that port, or
2. Edit `docker-compose.yml` to use different ports

### Docker Not Running

Make sure Docker Desktop is running:
- Windows: Check system tray
- Mac: Check menu bar

### Cannot Connect to Services

Wait a bit longer (services take 30-60 seconds to start), then:
```bash
docker-compose ps
```

All services should show "Up" status.

### Database Migration Errors

Reset the database:
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Next Steps

1. **Explore the API**: http://localhost:8000/docs
2. **Read Documentation**: Check `/docs` folder
3. **Try Different Modes**: Student, Developer, Founder
4. **Customize**: Modify the code to fit your needs

## Getting Help

- **Documentation**: `/docs` directory
- **GitHub Issues**: Report bugs
- **Email**: support@bharatbuild.ai

## What You Can Do

### Student Mode
Generate complete academic projects with:
- Software Requirements Specification (SRS)
- UML diagrams
- Full source code
- Project reports
- PowerPoint presentations
- Viva Q&A preparation

### Developer Mode
- Generate production-ready code
- Support for multiple frameworks
- Instant deployable applications

### Founder Mode
- Product idea validation
- PRD generation
- Business plan creation
- Market analysis

### API Partner Mode
- Generate API keys
- Programmatic access
- Token tracking
- Custom integrations

## API Example

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "Test User",
    "role": "student"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }'

# Create Project (use token from login)
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "My Project",
    "description": "Project description",
    "mode": "student",
    "domain": "Web Development"
  }'
```

## Success! 🎉

You now have a fully functional AI-powered project generation platform running locally!

**Happy Building!** 🚀

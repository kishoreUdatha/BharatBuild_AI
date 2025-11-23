#!/bin/bash

# BharatBuild AI Setup Script
# This script sets up the development environment

set -e

echo "========================================="
echo "BharatBuild AI - Setup Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}⚠ IMPORTANT: Edit .env file and add your API keys:${NC}"
    echo "  - ANTHROPIC_API_KEY (required)"
    echo "  - GOOGLE_CLIENT_ID (optional)"
    echo "  - RAZORPAY_KEY_ID (optional)"
    echo ""
    read -p "Press enter to continue after updating .env..."
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

echo ""
echo "Starting services with Docker Compose..."
echo ""

# Pull images
echo "Pulling Docker images..."
docker-compose pull

# Build and start services
echo "Building and starting services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check if backend is ready
echo "Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Backend failed to start${NC}"
        echo "Check logs with: docker-compose logs backend"
        exit 1
    fi
    sleep 2
done

# Run database migrations
echo ""
echo "Running database migrations..."
docker-compose exec -T backend alembic upgrade head
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Check if frontend is ready
echo ""
echo "Checking frontend..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠ Frontend might not be ready yet${NC}"
        break
    fi
    sleep 2
done

echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Your BharatBuild AI platform is now running:"
echo ""
echo "  Frontend:    http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  MinIO:       http://localhost:9001"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "To restart services:"
echo "  docker-compose restart"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Register a new account"
echo "  3. Create your first project"
echo "  4. Check the documentation in /docs"
echo ""
echo "Happy building! 🚀"
echo ""

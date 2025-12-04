#!/bin/bash

# BharatBuild AI - Production Startup Script

echo "========================================="
echo "  BharatBuild AI - Production Mode"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: No .env file found. Please create one from .env.example"
    exit 1
fi

# Check for required environment variables
if ! grep -q "ANTHROPIC_API_KEY=" .env || grep -q "ANTHROPIC_API_KEY=your-" .env; then
    echo "❌ Error: ANTHROPIC_API_KEY not configured in .env"
    exit 1
fi

echo "✓ Environment configured"
echo ""

# Stop any existing containers
echo "🧹 Stopping existing containers..."
docker-compose down

echo ""
echo "🚀 Starting production environment..."
echo ""

# Start services
docker-compose up -d --build

echo ""
echo "========================================="
echo "  ✓ Production environment started!"
echo "========================================="
echo ""
echo "Services:"
echo "  - Frontend:  http://localhost:3000"
echo "  - Backend:   http://localhost:8000"
echo "  - API Docs:  http://localhost:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"
echo ""

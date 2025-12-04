#!/bin/bash

# BharatBuild AI - Development Startup Script

echo "========================================="
echo "  BharatBuild AI - Development Mode"
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
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your ANTHROPIC_API_KEY"
    echo "   Press Enter to continue after updating .env, or Ctrl+C to exit..."
    read
fi

# Stop any existing containers
echo "🧹 Stopping existing containers..."
docker-compose -f docker-compose.dev.yml down

echo ""
echo "🚀 Starting development environment..."
echo ""

# Start services
docker-compose -f docker-compose.dev.yml up --build

echo ""
echo "========================================="
echo "  Development environment stopped"
echo "========================================="

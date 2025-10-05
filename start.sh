#!/bin/bash

# Pipe Organ Pipeline Startup Script

echo "🎵 Pipe Organ Pipeline - Starting up..."
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install Docker Compose."
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data/uploads data/results

echo "📁 Created data directories"
echo "🔨 Building Docker image (this may take a few minutes on first run)..."
docker-compose build

echo "🚀 Starting the application..."
docker-compose up -d

echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is running
if curl -f http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    echo "🌐 Open your browser and go to: http://localhost:5000"
    echo ""
    echo "📋 Useful commands:"
    echo "  - View logs: make docker-logs"
    echo "  - Stop app: make docker-down"
    echo "  - Restart: make docker-restart"
    echo ""
    echo "📁 Your data will be saved to: ./data/"
else
    echo "❌ Application failed to start. Check logs with: make docker-logs"
    exit 1
fi

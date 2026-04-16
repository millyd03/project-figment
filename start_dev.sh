#!/bin/bash
# Development server startup script for Project FIGMENT

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Project FIGMENT - Development Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Could not activate virtual environment${NC}"
    exit 1
fi

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo -e "${BLUE}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠ Please edit .env with your credentials${NC}"
    exit 1
fi

# Create data directory
mkdir -p data

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo -e "${BLUE}Starting services...${NC}"
echo -e "${GREEN}Backend will run on http://localhost:8002${NC}"
echo -e "${GREEN}Frontend will run on http://localhost:8501${NC}"
echo ""

# Run backend in background
python -c "import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8002)" &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Wait a moment for backend to start
sleep 2

# Run frontend
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
# project-figment

Personal AI agent for generating Spotify playlist and replacing Disney Genie on Disney World trips.

## Quick Start

### Option 1: Docker (Recommended)
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials
vi .env

# Start all services
docker-compose up --build

# Access the app
# Backend: http://localhost:8002
# Frontend: http://localhost:8501
```

### Option 2: Local Development

**Windows:**
```powershell
# Double-click start_dev.bat
# OR run manually:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
./start_dev.sh
```

**Manual Setup:**
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Terminal 1: Start backend
python -c "import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8002)"

# Terminal 2: Start frontend
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

## Features

### 🎵 Spotify Playlist Curator
- **Rule-Based Filtering**: Followed-only filter, tiered artist caps
- **Feature Toggles**: Throwback, Fresh, TACNO, Christmas, Clean
- **Token Persistence**: Once authenticated, stay logged in
- **Anti-Batching**: Shuffle tracks to avoid artist clustering

### 🎢 Disney Genie Replacement
- **Real-Time Wait Times**: Live data from ThemeParks.wiki API
- **Smart Recommendations**: Scoring algorithm based on wait times, distance, party composition
- **Nudge Notifications**: Alerts when rides drop in wait time or hit your target

## Configuration

### Environment Variables
Create a `.env` file (copy from `.env.example`):
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
# Optional for PKCE: SPOTIFY_CLIENT_SECRET can be omitted when using the browser-based auth flow.
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8002/callback
GOOGLE_API_KEY=your_google_api_key
ACTIVE_MODEL=gemini-pro  # or ollama-local
OLLAMA_ENDPOINT=http://localhost:11434
```

### Token Encryption (recommended)
You can encrypt stored Spotify refresh tokens at rest using a Fernet key.

1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Generate a Fernet key (script included):
```bash
python scripts/generate_token_key.py
# This prints a 44-char key and an example .env line `TOKEN_ENCRYPTION_KEY=...`
```
3. Add the printed `TOKEN_ENCRYPTION_KEY=...` line to your `.env` file and restart the backend.

When `TOKEN_ENCRYPTION_KEY` is present the app will encrypt refresh tokens before saving them and decrypt them in memory when needed.


## API Endpoints

### Authentication
- `GET /auth/spotify` - Get Spotify authorization URL
- `GET /callback?code=CODE` - Handle OAuth callback
- `GET /auth/status` - Check authentication status

### Spotify
- `POST /create_playlist` - Create playlist (requires auth)
  - Params: `name`, `throwback`, `fresh`, `tacno`, `christmas`, `clean`

### Disney
- `POST /get_next_action` - Get ride recommendations
  - Params: `park_id`, `user_location`, `party_composition`

### System
- `GET /` - Health check
- `GET /docs` - API documentation (Swagger UI)

## Project Structure
```
project-figment/
├── main.py                     # FastAPI app
├── spotify_rule_engine.py      # Spotify logic
├── disney_engine.py            # Disney Genie
├── llm_gateway.py              # LLM integration
├── database.py                 # Database models
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── frontend/
│   ├── app.py                 # Streamlit UI
│   └── manifest.json          # PWA config
├── Dockerfile                 # Backend container
├── Dockerfile.streamlit       # Frontend container
├── docker-compose.yml         # Multi-container setup
└── DEPLOYMENT.md              # Deployment guide
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black .
flake8 .
```

### Database
```bash
# View database
sqlite3 figment.db

# Reset database
rm figment.db  # Will be recreated on startup
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guides:
- Docker & Docker Compose
- Google Cloud Run
- AWS (ECS, Elastic Beanstalk)
- Azure Container Instances
- Heroku

## Troubleshooting

### Port Already in Use
```bash
# Change port in commands (e.g., 8003 instead of 8002)
python -c "import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8003)"
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Docker Issues
```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean rebuild
docker-compose down
docker-compose up --build
```

## TODO
- [ ] Add Redis caching for token persistence
- [ ] Implement Discord notifications
- [ ] Add PWA offline support
- [ ] Build Reflex frontend
- [ ] Add historical wait time analysis
- [ ] Implement mousetools for extended Disney data
- [ ] Add party composition wizard
- [ ] Support multiple parks

## License

MIT License - see LICENSE file

## Contributing

Pull requests welcome! Please follow the code style and add tests for new features.

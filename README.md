# project-figment
Personal AI agent for generating Spotify playlist and replacing Disney Genie. More ideas to come!

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` file with your API keys:
   ```
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   GOOGLE_API_KEY=your_google_api_key
   DISNEY_USERNAME=your_disney_username
   DISNEY_PASSWORD=your_disney_password
   ```
3. Run the backend: `python -c "import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8000)"`
4. Run the frontend: `python -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0`

## API Endpoints
- `GET /` - Welcome message
- `POST /create_playlist` - Create Spotify playlist with rules

## TODO
- Implement Disney engine (fix themeparks import)
- Add authentication
- Complete track fetching for Spotify
- Add PWA icons
- Implement nudge notifications

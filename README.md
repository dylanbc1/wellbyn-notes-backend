# Notes API

A FastAPI-based backend service for audio transcription using AI models.

## Features

- Audio transcription using Hugging Face's Whisper model
- PostgreSQL database for storing transcriptions
- RESTful API with automatic documentation
- File upload support for multiple audio formats
- Transcription history management

## Model

The application uses the **Whisper Base** model running locally. The model (74 MB) is downloaded once and cached for future use. It provides fast and accurate transcription for multiple languages including Spanish.

## Requirements

- Python 3.9 or higher
- PostgreSQL database
- Hugging Face API token

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
HF_TOKEN=your_huggingface_token
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/notes
SECRET_KEY=your-secret-key
PORT=8000
```

## Usage

```bash
# Start the server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload
```

The API will be available at:
- http://localhost:8000
- Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
notes-backend/
├── config.py           # Application configuration
├── database.py         # Database connection setup
├── main.py            # Main application entry point
├── models/            # SQLAlchemy models
├── routers/           # API endpoints
├── schemas/           # Pydantic schemas
└── services/          # Business logic
```

## API Endpoints

- `POST /api/transcriptions/transcribe` - Transcribe audio file
- `GET /api/transcriptions` - List all transcriptions
- `GET /api/transcriptions/{id}` - Get specific transcription
- `DELETE /api/transcriptions/{id}` - Delete transcription
- `GET /api/health` - Health check endpoint

## Supported Audio Formats

- MP3 (audio/mpeg)
- WAV (audio/wav)
- M4A (audio/m4a)
- OGG (audio/ogg)
- FLAC (audio/flac)
- WEBM (audio/webm)

Maximum file size: 25MB

## License

MIT License

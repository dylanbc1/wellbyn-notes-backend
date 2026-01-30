# How to Run Notes Backend

## Prerequisites

1. Python 3.9 or higher
2. PostgreSQL installed and running
3. Hugging Face API token (obtain from https://huggingface.co/settings/tokens)

## Setup Instructions

### 1. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE notes;

# Exit
\q
```

### 2. Set Up Virtual Environment

```bash
# Navigate to the directory
cd notes-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Option 1: Using echo
echo "HF_TOKEN=your_token_here" > .env
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/notes" >> .env
echo "SECRET_KEY=your-secret-key-here" >> .env

# Option 2: Copy and edit the example file
cp .env.example .env
# Then edit .env with your preferred editor
```

Replace `your_token_here` with your actual Hugging Face token.

### 5. Verify Configuration

```bash
python -c "from config import settings; print(f'HF Token: {settings.HF_TOKEN[:10]}...')"
```

## Running the Server

```bash
# Make sure you're in the notes-backend directory with venv activated
python main.py
```

The server will be available at:
- API: http://localhost:8000
- Interactive documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Testing the API

### Health Check

```bash
curl http://localhost:8000/api/health
```

### Transcribe Audio

```bash
curl -X POST "http://localhost:8000/api/transcriptions/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@/path/to/your/audio.mp3"
```

Alternatively, use the interactive documentation at http://localhost:8000/docs

## Troubleshooting

### Error: "HF_TOKEN not configured"
- Verify the `.env` file exists in the project root
- Verify it contains the line `HF_TOKEN=your_actual_token`
- Restart the server after creating/editing `.env`

### Error: "Could not connect to database"
- Verify PostgreSQL is running: `pg_isready`
- Verify the database exists: `psql -U postgres -l | grep notes`
- Check the DATABASE_URL in `.env`

### Error: "Model is loading" (503)
- This is normal the first time you use a model
- Wait 30-60 seconds and retry
- Hugging Face models need to "warm up"

### Port Already in Use
```bash
# Change port in .env
echo "PORT=8001" >> .env

# Or kill the process using port 8000
# On Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

## Model Information

The application uses the **Whisper Base** model running locally. The model (74 MB) is automatically downloaded on first use and cached for future transcriptions. It offers fast and accurate transcription for multiple languages including Spanish.

The first transcription will take longer as the model downloads, but subsequent transcriptions will be much faster.

## Resources

- Hugging Face Token: https://huggingface.co/settings/tokens
- PostgreSQL Download: https://www.postgresql.org/download/
- FastAPI Documentation: https://fastapi.tiangolo.com/

## Next Steps

Once the backend is running, you can start the frontend:
```bash
cd ../notes-frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

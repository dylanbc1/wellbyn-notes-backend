#!/bin/bash
# Script de inicio para Railway

set -e  # Exit on error (pero lo quitaremos antes de exec)

echo "=========================================="
echo "=== Starting Wellbyn Notes Backend ==="
echo "=========================================="
echo "Timestamp: $(date)"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Files in directory:"
ls -la | head -10
echo ""

# Verificar que main.py existe
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    exit 1
fi

# Log de variables de entorno importantes
echo "=== Environment Variables ==="
echo "PORT: ${PORT:-NOT_SET}"
echo "DATABASE_URL: ${DATABASE_URL:0:50}..." 
echo "GEMINI_KEY: ${GEMINI_KEY:+SET}" 
echo "DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:+SET}"
echo "ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-NOT_SET}"
echo ""

# Verificar que PORT esté definido, usar 8000 como fallback
PORT=${PORT:-8000}
export PORT

echo "=== Starting Application ==="
echo "Using PORT: $PORT"
echo "Host: 0.0.0.0"
echo "Health check URL: http://0.0.0.0:$PORT/api/health"
echo "Root URL: http://0.0.0.0:$PORT/"
echo "=========================================="
echo ""

# Verificar que uvicorn está instalado
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "ERROR: uvicorn not installed!"
    pip list | grep uvicorn || echo "uvicorn not in pip list"
    exit 1
fi

echo "uvicorn is installed ✅"
echo "Starting uvicorn..."
echo ""

# Quitar set -e antes de exec para que uvicorn maneje sus propios errores
set +e

# Iniciar la aplicación con logs detallados
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info --access-log

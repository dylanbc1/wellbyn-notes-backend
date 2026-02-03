#!/bin/bash
# Script de inicio para Railway

echo "=== Starting Wellbyn Notes Backend ==="
echo "PORT: ${PORT:-8000}"
echo "Python version: $(python --version)"

# Verificar que PORT esté definido, usar 8000 como fallback
PORT=${PORT:-8000}
export PORT

echo "Starting uvicorn on port $PORT..."
echo "Health check will be available at: http://0.0.0.0:$PORT/api/health"

# Iniciar la aplicación (sin set -e para que no falle si hay warnings)
python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info

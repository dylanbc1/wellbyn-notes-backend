#!/bin/bash
# Script de inicio para Railway

set -e  # Exit on error

echo "=== Starting Wellbyn Notes Backend ==="
echo "PORT: ${PORT:-8000}"
echo "Python version: $(python --version)"

# Verificar que PORT esté definido, usar 8000 como fallback
PORT=${PORT:-8000}
export PORT

echo "Starting uvicorn on port $PORT..."

# Iniciar la aplicación
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT

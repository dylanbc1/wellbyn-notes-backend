# Despliegue en Railway

Esta guía explica cómo desplegar el backend de Wellbyn Notes en Railway.

## Configuración Automática

El proyecto incluye `railway.toml` que configura automáticamente:
- Comando de inicio: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Puerto: Railway proporciona automáticamente la variable `PORT`

## Pasos para Desplegar

### 1. Conectar el Repositorio

1. Ve a [Railway](https://railway.app)
2. Crea un nuevo proyecto
3. Selecciona "Deploy from GitHub repo"
4. Conecta tu repositorio: `dylanbc1/wellbyn-notes-backend`

### 2. Configurar Variables de Entorno

En la pestaña "Variables" de Railway, agrega:

```env
# Base de datos (Railway proporciona DATABASE_URL automáticamente si agregas PostgreSQL)
# Si no, configura manualmente:
DATABASE_URL=postgresql://user:password@host:port/database

# Google Gemini (requerido para generación de notas médicas)
GEMINI_KEY=tu_clave_de_gemini

# Deepgram (recomendado para transcripción en producción)
DEEPGRAM_API_KEY=tu_clave_de_deepgram
DEEPGRAM_MODEL=nova-2

# Configuración de transcripción
TRANSCRIPTION_PROVIDER=deepgram  # o "auto" para usar Deepgram primero, luego Whisper

# CORS - Agrega la URL de tu frontend
ALLOWED_ORIGINS=https://tu-frontend.railway.app,https://tu-dominio.com

# Seguridad
SECRET_KEY=tu-clave-secreta-muy-segura-aqui
```

### 3. Agregar Base de Datos PostgreSQL

1. En Railway, haz clic en "+ New"
2. Selecciona "Database" → "PostgreSQL"
3. Railway creará automáticamente la variable `DATABASE_URL`

### 4. Configurar el Puerto (IMPORTANTE)

**Railway detecta automáticamente el puerto desde:**
- La variable de entorno `PORT` (proporcionada automáticamente por Railway)
- El archivo `railway.toml` que ya está configurado

**Si Railway te pide un "Target Port" al generar el dominio:**

Esto es normal. Railway necesita saber qué puerto está escuchando tu aplicación para enrutar el tráfico. Sin embargo:

1. **El código ya está configurado** para usar `$PORT` automáticamente (ver `config.py` línea 24)
2. **Railway proporciona `PORT` automáticamente** cuando despliegas
3. **Si Railway te pide un "target port":**
   - Puedes usar **8000** como referencia
   - Pero Railway internamente usará su propia variable `PORT` (que puede ser diferente, como 8080, 3000, etc.)
   - El código leerá `$PORT` automáticamente, así que funcionará correctamente

**Resumen:** Si Railway pide un puerto, usa **8000**, pero no te preocupes - Railway y tu código manejarán el puerto correcto automáticamente.

### 5. Generar Dominio Público

1. En "Settings" → "Networking"
2. Activa "Public Networking"
3. Haz clic en "Generate Domain"
4. Railway generará automáticamente un dominio como: `tu-proyecto.up.railway.app`

**Nota:** Si Railway te pide un puerto al generar el dominio:
- El puerto ya está configurado en `railway.toml` usando `$PORT`
- Railway debería detectarlo automáticamente
- Si aún así te pide, puedes dejar el puerto por defecto (8000) pero Railway usará su propio PORT

### 6. Ejecutar Migraciones

Después del primer despliegue, ejecuta las migraciones de la base de datos:

1. Ve a la pestaña "Deployments"
2. Haz clic en el deployment más reciente
3. Abre la terminal
4. Ejecuta:

```bash
python migrate_add_user_tables.py
python migrate_add_role_column.py
python migrate_add_ehr_tables.py
python migrate_add_workflow_columns.py
```

O ejecuta todas las migraciones necesarias según tu versión de la base de datos.

## Verificación

### 1. Health Check

```bash
curl https://tu-proyecto.up.railway.app/api/health
```

Debería responder con:
```json
{"status": "healthy", "version": "1.0.0"}
```

### 2. Documentación de la API

Visita: `https://tu-proyecto.up.railway.app/docs`

## Solución de Problemas

### Error: "Port not specified"

Si Railway no detecta el puerto automáticamente:

1. Verifica que `railway.toml` esté en la raíz del proyecto
2. Verifica que el archivo tenga el formato correcto
3. Como alternativa, puedes especificar el puerto en Railway:
   - Settings → Networking → Target Port: **8000**
   - Pero Railway usará su propia variable `PORT` internamente

### Error: "Database connection failed"

1. Verifica que PostgreSQL esté agregado como servicio
2. Verifica que `DATABASE_URL` esté configurada (Railway la crea automáticamente)
3. Verifica que las migraciones se hayan ejecutado

### Error: "Module not found"

1. Verifica que `requirements.txt` esté en la raíz
2. Verifica que todas las dependencias estén listadas
3. Railway instala automáticamente desde `requirements.txt`

### El dominio no funciona

1. Verifica que "Public Networking" esté activado
2. Verifica que el servicio esté desplegado correctamente
3. Espera unos minutos para que el DNS se propague

## Configuración Recomendada para Producción

### Usar Deepgram en lugar de Whisper

Para producción, se recomienda usar Deepgram (transcripción en la nube) en lugar de Whisper local:

1. Configura `DEEPGRAM_API_KEY` en Railway
2. Configura `TRANSCRIPTION_PROVIDER=deepgram`
3. **Opcional:** Usa `requirements-production.txt` que no incluye whisper (más rápido de instalar)

Para usar `requirements-production.txt`:
- En Railway, Settings → Build → Build Command:
  ```bash
  pip install -r requirements-production.txt
  ```

### Configurar CORS

Asegúrate de agregar la URL de tu frontend en `ALLOWED_ORIGINS`:

```env
ALLOWED_ORIGINS=https://tu-frontend.railway.app,https://tu-dominio.com
```

## Recursos

- [Railway Documentation](https://docs.railway.app)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Railway Discord](https://discord.gg/railway)

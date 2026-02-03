# Checklist de Verificación - Railway Deployment

## ⚠️ Si ves "Application failed to respond" (502 Bad Gateway)

### 1. Verifica los Logs de Despliegue

En Railway:
1. Ve a tu proyecto
2. Click en "Deployments"
3. Selecciona el deployment más reciente
4. Revisa los logs completos

**Busca estos errores comunes:**

#### Error: "ModuleNotFoundError"
- **Causa:** Faltan dependencias en `requirements.txt`
- **Solución:** Verifica que todas las dependencias estén listadas

#### Error: "Database connection failed"
- **Causa:** PostgreSQL no está configurado o `DATABASE_URL` no está definida
- **Solución:** 
  1. Agrega PostgreSQL como servicio en Railway
  2. Verifica que `DATABASE_URL` aparezca automáticamente en Variables

#### Error: "Port already in use" o "Address already in use"
- **Causa:** Conflicto de puertos (raro en Railway)
- **Solución:** Railway maneja los puertos automáticamente, esto no debería pasar

#### Error: "ImportError" o "cannot import"
- **Causa:** Problema con las importaciones
- **Solución:** Verifica que todos los archivos estén en el repositorio

### 2. Verifica las Variables de Entorno

En Railway → Settings → Variables, verifica:

- ✅ `DATABASE_URL` - Debe estar configurada (automática con PostgreSQL)
- ✅ `GEMINI_KEY` - Requerida para generación de notas médicas
- ⚠️ `DEEPGRAM_API_KEY` - Recomendada para transcripción
- ⚠️ `ALLOWED_ORIGINS` - URLs permitidas para CORS (ej: `https://tu-frontend.railway.app`)

### 3. Verifica que PostgreSQL esté Agregado

1. En Railway, verifica que tengas un servicio PostgreSQL
2. Si no lo tienes:
   - Click en "+ New"
   - Selecciona "Database" → "PostgreSQL"
   - Railway creará automáticamente `DATABASE_URL`

### 4. Verifica el Puerto

1. En Railway → Settings → Networking
2. Verifica que "Public Networking" esté activado
3. Si te pide "Target Port", usa **8000**
4. El archivo `railway.toml` ya tiene `port = 8000` configurado

### 5. Verifica el Comando de Inicio

El archivo `railway.toml` tiene:
```toml
startCommand = "bash start.sh"
```

El script `start.sh`:
- Verifica que PORT esté definido
- Inicia uvicorn con el puerto correcto

### 6. Prueba Localmente Primero

Antes de desplegar, prueba localmente:

```bash
# Activa el entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Instala dependencias
pip install -r requirements.txt

# Prueba que la app inicie
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Si funciona localmente pero no en Railway, el problema es de configuración de Railway.

### 7. Verifica el Build

En Railway → Deployments, verifica que el build se complete exitosamente:

- ✅ "Build completed successfully"
- ✅ "Deploying..."
- ❌ Si falla en build, revisa los logs de build

### 8. Comandos de Depuración

Si tienes acceso a Railway CLI:

```bash
# Ver logs en tiempo real
railway logs

# Ver variables de entorno
railway variables

# Ejecutar comando en el contenedor
railway run python -c "from config import settings; print(settings.DATABASE_URL)"
```

### 9. Verificación Post-Deploy

Después de un despliegue exitoso, prueba:

```bash
# Health check
curl https://wellbyn-notes-backend-production.up.railway.app/api/health

# Root endpoint
curl https://wellbyn-notes-backend-production.up.railway.app/

# Deberían responder con JSON
```

### 10. Si Nada Funciona

1. **Revisa los logs completos** en Railway
2. **Copia el error específico** que aparece en los logs
3. **Verifica que el código funcione localmente**
4. **Contacta soporte de Railway** con:
   - Los logs completos
   - El error específico
   - Tu configuración de `railway.toml`

## Checklist Rápido

- [ ] PostgreSQL está agregado como servicio
- [ ] `DATABASE_URL` está en Variables (automática)
- [ ] `GEMINI_KEY` está configurada
- [ ] `railway.toml` está en la raíz del proyecto
- [ ] `start.sh` tiene permisos de ejecución (chmod +x)
- [ ] El build se completa exitosamente
- [ ] El deployment se completa
- [ ] El health check responde: `/api/health`

## Errores Comunes y Soluciones

### "Application failed to respond" inmediatamente
→ Revisa los logs, probablemente hay un error al iniciar la app

### "502 Bad Gateway"
→ La app no está respondiendo, revisa logs y variables de entorno

### "Database connection failed"
→ Agrega PostgreSQL y verifica `DATABASE_URL`

### "Module not found"
→ Verifica `requirements.txt` y que todas las dependencias estén listadas

# ⚠️ CONFIGURACIÓN CRÍTICA DEL PUERTO EN RAILWAY

## El Problema

Railway está deteniendo el contenedor porque hay un **desajuste de puertos**:

- Railway asigna el puerto **8080** (según los logs)
- Pero el "Target Port" en Railway está configurado en **8000** (o diferente)
- Railway hace el health check correctamente (200 OK)
- Pero luego detiene el contenedor porque no puede enrutar el tráfico

## Solución PASO A PASO

### 1. En Railway Dashboard:

1. Ve a tu proyecto en Railway
2. Click en **Settings** → **Networking**
3. En **"Public Networking"**, busca **"Target Port"**
4. **CÁMBIALO A 8080** (debe coincidir EXACTAMENTE con el puerto que Railway está usando)
5. **GUARDA los cambios**

### 2. Verifica que el código use el puerto correcto:

El código ya está configurado para leer `$PORT` automáticamente:
- `start.sh` lee `$PORT` de Railway
- `config.py` lee `PORT` de las variables de entorno
- Todo está correcto en el código

### 3. El archivo `railway.toml`:

**NO debe tener `[networking] port = X`** porque Railway asigna puertos dinámicamente.

El archivo está correcto ahora (sin puerto fijo).

## Verificación

Después de cambiar el Target Port a 8080 en Railway:

1. **Espera a que Railway redespliegue** (o haz un nuevo deploy)
2. **Revisa los logs** - NO deberías ver "Stopping Container" inmediatamente
3. **Prueba el endpoint:**
   ```bash
   curl https://wellbyn-notes-backend-production.up.railway.app/api/health
   ```

## Importante

- El **Target Port en Railway** debe ser **8080** (el puerto que Railway está asignando)
- El código lee `$PORT` automáticamente, así que está bien
- NO necesitas cambiar nada en el código, solo en Railway Dashboard

## Si Railway cambia el puerto

Si Railway asigna un puerto diferente (ej: 3000, 5000, etc.):

1. **Revisa los logs** para ver qué puerto está usando Railway
2. **Actualiza el Target Port en Railway** para que coincida
3. El código se adaptará automáticamente porque lee `$PORT`

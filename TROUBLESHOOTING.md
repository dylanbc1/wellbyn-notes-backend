# Solución de Problemas - Railway Deployment

## Error: "Application failed to respond"

### Pasos de Depuración

1. **Revisa los logs de despliegue:**
   ```bash
   # En Railway:
   # 1. Ve a "Deployments"
   # 2. Selecciona el deployment más reciente
   # 3. Revisa los logs completos
   ```

2. **Verifica las variables de entorno:**
   - `DATABASE_URL` - Debe estar configurada (Railway la crea automáticamente con PostgreSQL)
   - `GEMINI_KEY` - Requerida para generación de notas médicas
   - `DEEPGRAM_API_KEY` - Recomendada para transcripción en producción
   - `ALLOWED_ORIGINS` - URLs permitidas para CORS

3. **Verifica que PostgreSQL esté agregado:**
   - En Railway, verifica que tengas un servicio PostgreSQL
   - La variable `DATABASE_URL` debe aparecer automáticamente

4. **Verifica el puerto:**
   - El archivo `railway.toml` tiene `port = 8000` configurado
   - Cuando Railway pida el puerto, usa **8000**
   - Railway usará su propia variable `PORT` internamente

### Errores Comunes

#### Error: "Database connection failed"

**Causa:** La base de datos no está configurada o no está accesible.

**Solución:**
1. Agrega PostgreSQL como servicio en Railway
2. Verifica que `DATABASE_URL` esté configurada
3. Ejecuta las migraciones después del primer despliegue

#### Error: "Module not found"

**Causa:** Faltan dependencias en `requirements.txt`.

**Solución:**
1. Verifica que `requirements.txt` esté en la raíz del proyecto
2. Revisa los logs de build para ver qué módulo falta
3. Agrega la dependencia faltante a `requirements.txt`

#### Error: "Port already in use"

**Causa:** Conflicto de puertos (raro en Railway).

**Solución:**
- Railway maneja los puertos automáticamente
- Si persiste, verifica que `railway.toml` esté configurado correctamente

#### Error: "Application failed to respond" inmediatamente después del deploy

**Causa más común:** La aplicación no está iniciando correctamente.

**Solución:**
1. Revisa los logs para ver el error específico
2. Verifica que `start.sh` tenga permisos de ejecución (ya está configurado)
3. Verifica que todas las variables de entorno estén configuradas
4. Verifica que la base de datos esté accesible

### Comandos Útiles para Depuración

```bash
# Ver logs en tiempo real (desde Railway terminal)
railway logs

# Verificar variables de entorno
railway variables

# Ejecutar comando en el contenedor
railway run python -c "from config import settings; print(settings.DATABASE_URL)"
```

### Verificación Post-Deploy

1. **Health Check:**
   ```bash
   curl https://tu-proyecto.up.railway.app/api/health
   ```
   Debe responder con `{"status": "healthy", ...}`

2. **Root Endpoint:**
   ```bash
   curl https://tu-proyecto.up.railway.app/api/
   ```
   Debe mostrar información del servicio

3. **Documentación:**
   Visita: `https://tu-proyecto.up.railway.app/docs`

### Checklist Pre-Deploy

- [ ] `railway.toml` está en la raíz del proyecto
- [ ] `requirements.txt` está actualizado
- [ ] `start.sh` tiene permisos de ejecución (chmod +x)
- [ ] PostgreSQL está agregado como servicio
- [ ] `DATABASE_URL` está configurada (automática con PostgreSQL)
- [ ] `GEMINI_KEY` está configurada
- [ ] `DEEPGRAM_API_KEY` está configurada (recomendado)
- [ ] `ALLOWED_ORIGINS` incluye la URL del frontend

### Si Nada Funciona

1. **Revisa los logs completos** en Railway
2. **Verifica que el código funcione localmente:**
   ```bash
   python main.py
   ```
3. **Prueba el build localmente:**
   ```bash
   pip install -r requirements.txt
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. **Contacta soporte de Railway** con los logs completos

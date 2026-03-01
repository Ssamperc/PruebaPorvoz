# Agenda de llamadas automáticas (Python + HTML)

Esta webapp te permite:

1. Registrar un recordatorio (ej. medicamento a las 8:00 PM).
2. Definir el número de teléfono a llamar.
3. Escribir el texto exacto que Twilio debe decir durante la llamada.
4. Hacer la llamada automática a la hora programada.

## Requisitos

- Python 3.10+
- Cuenta de Twilio
- Un número de Twilio con capacidad de voz
- URL pública para que Twilio consulte el endpoint `/voice/<id>` (puedes usar ngrok)

## Instalación

### Linux / macOS (bash)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno

### Linux / macOS (bash)

```bash
export APP_TIMEZONE="America/Mexico_City"
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="tu_token"
export TWILIO_FROM_NUMBER="+1xxxxxxxxxx"
export TWILIO_BASE_URL="https://tu-url-publica.com"
```

### Windows (PowerShell)

```powershell
$env:APP_TIMEZONE = "America/Mexico_City"
$env:TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TWILIO_AUTH_TOKEN = "tu_token"
$env:TWILIO_FROM_NUMBER = "+1xxxxxxxxxx"
$env:TWILIO_BASE_URL = "https://tu-url-publica.com"
```

> `TWILIO_BASE_URL` debe ser accesible desde internet para que Twilio pueda leer el mensaje de voz.

## Ejecutar

```bash
python manage.py runserver
```

Abre `http://127.0.0.1:5000`.

## Alternativa recomendada para ejecutar

Si prefieres un comando estilo framework (similar a Django), usa:

```bash
python manage.py runserver
```

Opciones útiles:

```bash
python manage.py runserver --host 0.0.0.0 --port 5000 --debug
```

## Comandos de verificación (sin errores en PowerShell)

### Verificar sintaxis

```powershell
python -m py_compile app.py
```

### Arrancar app y probar homepage

#### Linux / macOS (bash)

```bash
python manage.py runserver
# en otra terminal
curl http://127.0.0.1:5000
```

#### Windows (PowerShell)

```powershell
# Terminal 1
python manage.py runserver

# Terminal 2
Invoke-WebRequest http://127.0.0.1:5000 | Select-Object -ExpandProperty Content
```

> No uses comandos con `&`, `sleep`, `kill`, `/tmp/...` en PowerShell porque son sintaxis de bash.

## Flujo

- Crea un recordatorio desde el formulario.
- Se guarda en SQLite (`reminders.db`) y se agenda con APScheduler.
- Cuando llega la hora, se ejecuta la llamada vía Twilio.
- Twilio consulta `/voice/<id>` y la app responde con TwiML diciendo tu mensaje.

## Notas

- Si faltan credenciales de Twilio, la llamada se marca con estado `failed_missing_twilio_config`.
- Si la llamada falla por API o red, se marca `failed_call_error`.

# LinkedIn Job Hunter

Monitor automático de ofertas de empleo en LinkedIn con notificaciones por Telegram y, opcionalmente, auto-aplicación a ofertas Easy Apply con revisión humana.

## Qué hace

El proyecto tiene dos piezas principales que trabajan juntas:

| Componente | Qué hace | Cuándo se ejecuta |
|---|---|---|
| **Monitor** (`main.py`) | Busca ofertas en LinkedIn, filtra las nuevas y las envía por Telegram | Manualmente o con un programador de tareas |
| **Bot de aprobación** (`src/approval_bot/bot.py`) | Escucha Telegram y permite aprobar/rechazar candidaturas Easy Apply | Manualmente, debe estar siempre en ejecución |

### Flujo completo

```
LinkedIn (jobspy) → Filtros → SQLite → Telegram (notificación)
                                              ↓
                              [Easy Apply + auto_apply activado]
                                              ↓
                              Cola de revisión → Bot Telegram
                                              ↓
                              Aprobar → Playwright → LinkedIn Easy Apply
```

1. El monitor consulta LinkedIn con [python-jobspy](https://github.com/BunsenMcD/JobSpy) según los criterios definidos en `config.yaml`.
2. Descarta ofertas ya vistas (SQLite en `data/jobs.db`).
3. Envía las nuevas por Telegram con título, empresa, ubicación, salario y preview de la descripción.
4. Si `auto_apply` está activado, las ofertas con Easy Apply entran en cola y el bot pide aprobación con botones inline.
5. Al pulsar **Aplicar**, Playwright abre la oferta, rellena el formulario y envía la candidatura.

## Requisitos

- **Python 3.11+** (recomendado)
- Cuenta de **Telegram** y un bot creado con [@BotFather](https://t.me/BotFather)
- Cuenta de **LinkedIn** (solo necesaria si activas el auto-apply)

## Instalación

### 1. Clonar e instalar dependencias

```powershell
git clone <url-del-repo>
cd "Linkedin Search"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
LINKEDIN_EMAIL=tu@email.com
LINKEDIN_PASSWORD=tu_contraseña
```

| Variable | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot de [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Tu ID numérico de Telegram (obténlo con [@userinfobot](https://t.me/userinfobot)) |
| `LINKEDIN_EMAIL` | Email de LinkedIn (reserva; el login real usa sesión de navegador) |
| `LINKEDIN_PASSWORD` | Contraseña de LinkedIn (reserva; el login real usa sesión de navegador) |

> Las credenciales de LinkedIn en `.env` no se usan directamente en el flujo actual. El auto-apply depende de una sesión guardada en `data/browser_state.json` (ver más abajo).

### 3. Ajustar la búsqueda

Edita `config.yaml` según tus criterios:

```yaml
search:
  keywords:
    - "Python Django"
    - "Java Spring Boot"
  location: "Spain"
  is_remote: true
  results_wanted: 25
  hours_old: 24
  require_keywords_in_title:
    - "python"
    - "backend"
```

Los parámetros más relevantes:

- `keywords`: términos combinados con OR
- `location` y `distance_miles`: área geográfica
- `is_remote`: filtrar solo remoto
- `hours_old`: antigüedad máxima de la oferta
- `exclude_keywords` / `require_keywords_in_title`: filtros post-scraping

## Configurar Telegram

1. Abre [@BotFather](https://t.me/BotFather) en Telegram y crea un bot (`/newbot`).
2. Copia el token a `TELEGRAM_BOT_TOKEN` en `.env`.
3. Obtén tu chat ID con [@userinfobot](https://t.me/userinfobot) y ponlo en `TELEGRAM_CHAT_ID`.
4. **Importante:** inicia una conversación con tu bot (pulsa `/start`) antes de usarlo; si no, no podrá enviarte mensajes.

## Uso básico (solo monitor)

Ejecuta un escaneo manual:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Si hay ofertas nuevas, llegarán a tu Telegram. Los logs se guardan en `logs/jobhunter.log`.

Para automatizar el escaneo, configura un programador de tareas del sistema (cron en Linux/macOS, Programador de tareas en Windows) que ejecute `python main.py` periódicamente.

## Bot de aprobación de LinkedIn

El bot de Telegram es un proceso **persistente** (no se lanza y termina como el monitor). Debe estar corriendo para recibir los botones de Aplicar/Saltar.

### Arrancar el bot manualmente

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.approval_bot.bot
```

### Comandos disponibles

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida |
| `/status` | Estadísticas: ofertas vistas, aplicadas, pendientes |
| `/pending` | Lista ofertas pendientes con botones de acción |

Solo responde al chat cuyo ID coincide con `TELEGRAM_CHAT_ID`.

## Auto-apply (Easy Apply)

> **Advertencia:** el auto-apply puede violar los [Términos de Servicio de LinkedIn](https://www.linkedin.com/legal/user-agreement). Tu cuenta puede ser restringida o bloqueada. Úsalo bajo tu propio riesgo.

### Activar en config.yaml

```yaml
auto_apply:
  enabled: true
  risk_acknowledged: true   # obligatorio si enabled: true
  mode: "human_review"      # human_review | fully_automatic
  approval_timeout_hours: 12
  linkedin:
    headless: true
    slow_mo_ms: 150
    max_applications_per_day: 10
  cv:
    pdf_path: "cv/resume.pdf"
    answers:
      years_experience: 3
      phone_number: "+34 600 000 000"
      work_authorization: "Yes"
      require_sponsorship: "No"
```

Coloca tu CV en `cv/resume.pdf`. Las claves de `answers` se emparejan con las etiquetas de los campos del formulario Easy Apply (por coincidencia parcial de texto).

### Iniciar sesión en LinkedIn (obligatorio para auto-apply)

La primera vez debes guardar la sesión del navegador:

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.auto_apply.session_manager
```

Se abrirá Chromium. Inicia sesión en LinkedIn manualmente y pulsa Enter en la terminal. La sesión queda en `data/browser_state.json`.

Si la sesión caduca, repite este paso.

### Flujo con revisión humana

Con `mode: "human_review"` (recomendado):

1. El monitor detecta una oferta Easy Apply nueva.
2. Te llega un mensaje con botones **Aplicar** / **Saltar**.
3. Si apruebas, Playwright abre la oferta, rellena el formulario paso a paso y envía la candidatura.
4. Recibes confirmación o error por Telegram.

Límite diario configurable con `max_applications_per_day`.

## Estructura del proyecto

```
Linkedin Search/
├── main.py                      # Punto de entrada del monitor
├── config.yaml                  # Criterios de búsqueda y opciones
├── requirements.txt
├── .env                         # Secretos (no se sube al repo)
├── data/
│   ├── .gitkeep
│   ├── jobs.db                  # Base SQLite (generada)
│   └── browser_state.json       # Sesión LinkedIn (generada)
├── logs/                        # Logs de ejecución (generados)
├── cv/                          # Tu CV en PDF (no se sube)
├── src/
│   ├── config.py                # Carga config.yaml + .env con Pydantic
│   ├── scraper.py               # Scraping LinkedIn vía jobspy
│   ├── database.py              # Persistencia SQLite
│   ├── notifier.py              # Notificaciones Telegram
│   ├── approval_bot/
│   │   └── bot.py               # Bot interactivo de aprobación
│   └── auto_apply/
│       ├── apply_bot.py         # Orquestador de candidatura
│       ├── form_filler.py       # Relleno de formularios Easy Apply
│       └── session_manager.py   # Gestión de sesión Playwright
```

## Solución de problemas

### No llegan mensajes de Telegram

- Comprueba que `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` son correctos.
- Asegúrate de haber enviado `/start` al bot.
- Revisa `logs/jobhunter.log` por errores de envío.

### El monitor no encuentra ofertas

- Amplía `hours_old` o relaja `require_keywords_in_title`.
- LinkedIn puede limitar peticiones; jobspy reintenta hasta 3 veces con backoff exponencial.

### El bot de aprobación no responde

- Verifica que el proceso está corriendo.
- Solo responde al chat ID configurado en `.env`.

### Falla el auto-apply

- Repite el login: `python -m src.auto_apply.session_manager`
- Comprueba que `cv/resume.pdf` existe.
- Algunos formularios Easy Apply tienen campos personalizados que `form_filler.py` no reconoce (devuelve `unknown` y aborta).
- Revisa el límite diario en `max_applications_per_day`.

## Licencia

Uso personal. Respeta los términos de servicio de LinkedIn y Telegram.

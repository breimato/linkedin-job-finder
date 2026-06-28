# LinkedIn Job Hunter

Monitor automático de ofertas de empleo en LinkedIn con notificaciones por Telegram y, opcionalmente, auto-aplicación a ofertas Easy Apply con revisión humana.

Repositorio: [github.com/breimato/linkedin-job-finder](https://github.com/breimato/linkedin-job-finder)

## Qué hace

| Componente | Qué hace | Cuándo se ejecuta |
|---|---|---|
| **Monitor** (`main.py`) | Busca ofertas en LinkedIn, filtra las nuevas y las envía por Telegram | Manualmente o con un programador de tareas |
| **Bot de aprobación** (`src/approval_bot/bot.py`) | Escucha Telegram y permite aprobar/rechazar candidaturas Easy Apply | Manualmente, debe estar siempre en ejecución |

```
LinkedIn (jobspy) → Filtros → SQLite → Telegram (notificación)
                                              ↓
                              [Easy Apply + auto_apply activado]
                                              ↓
                              Cola de revisión → Bot Telegram
                                              ↓
                              Aprobar → Playwright → LinkedIn Easy Apply
```

## Empezar desde cero (guía rápida)

Cada persona que use el proyecto necesita **su propia configuración** (`.env`, `config.yaml`, CV). Los secretos y datos personales no se suben a GitHub.

### 1. Clonar e instalar

```powershell
git clone https://github.com/breimato/linkedin-job-finder.git
cd linkedin-job-finder

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1
```

El script `install.ps1` crea el entorno virtual, instala dependencias, Playwright, y genera `.env` y `config.yaml` desde las plantillas.

### 2. Crear tu bot de Telegram

1. Abre [@BotFather](https://t.me/BotFather) y crea un bot con `/newbot`.
2. Copia el token en `.env` → `TELEGRAM_BOT_TOKEN`.
3. Obtén tu chat ID con [@userinfobot](https://t.me/userinfobot) y ponlo en `.env` → `TELEGRAM_CHAT_ID`.
4. **Importante:** abre el bot en Telegram y pulsa `/start` antes de usarlo.

> Cada usuario debe tener **su propio bot** (o al menos su propio `TELEGRAM_CHAT_ID`). Si dos personas comparten el mismo bot y chat ID, recibirían las mismas notificaciones.

### 3. Configurar la búsqueda

Edita `config.yaml` (generado desde `config.example.yaml`):

```yaml
search:
  keywords:
    - "Python Developer"
    - "Backend Engineer"
  location: "Spain"
  is_remote: true
  hours_old: 24
  require_keywords_in_title:
    - "python"
    - "backend"
```

### 4. Probar

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Si hay ofertas nuevas, llegarán a tu Telegram. Los logs se guardan en `logs/jobhunter.log`.

### 5. Automatizar en Windows (opcional)

Abre PowerShell **como administrador** y ejecuta:

```powershell
cd ruta\al\proyecto
.\setup_tasks.ps1
```

Esto crea dos tareas en el Programador de tareas:

| Tarea | Frecuencia | Qué hace |
|---|---|---|
| `JobHunter\Monitor` | Cada 20 minutos | Ejecuta `main.py` en segundo plano |
| `JobHunter\ApprovalBot` | Al iniciar sesión | Arranca el bot de Telegram |

## Instalación manual

Si prefieres no usar `install.ps1`:

```powershell
git clone https://github.com/breimato/linkedin-job-finder.git
cd linkedin-job-finder

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium

copy .env.example .env
copy config.example.yaml config.yaml
```

Luego edita `.env` y `config.yaml` como se indica arriba.

## Variables de entorno (`.env`)

| Variable | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot de [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Tu ID numérico de Telegram ([@userinfobot](https://t.me/userinfobot)) |
| `LINKEDIN_EMAIL` | Reservado; el login real usa sesión de navegador |
| `LINKEDIN_PASSWORD` | Reservado; el login real usa sesión de navegador |

## Bot de aprobación

El bot de Telegram es un proceso **persistente**. Debe estar corriendo para recibir los botones de Aplicar/Saltar.

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.approval_bot.bot
```

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida |
| `/status` | Estadísticas: ofertas vistas, aplicadas, pendientes |
| `/pending` | Lista ofertas pendientes con botones de acción |

Solo responde al chat cuyo ID coincide con `TELEGRAM_CHAT_ID`.

## Auto-apply (Easy Apply)

> **Advertencia:** el auto-apply puede violar los [Términos de Servicio de LinkedIn](https://www.linkedin.com/legal/user-agreement). Tu cuenta puede ser restringida o bloqueada. Úsalo bajo tu propio riesgo.

Actívalo en `config.yaml`:

```yaml
auto_apply:
  enabled: true
  risk_acknowledged: true
  cv:
    pdf_path: "cv/resume.pdf"
    answers:
      phone_number: "+34 600 000 000"
```

1. Coloca tu CV en `cv/resume.pdf`.
2. Guarda la sesión de LinkedIn (solo la primera vez):

```powershell
python -m src.auto_apply.session_manager
```

Se abre Chromium; inicia sesión manualmente y pulsa Enter. La sesión queda en `data/browser_state.json`.

## Qué se sube a GitHub y qué no

| En el repo | Solo en tu PC (gitignore) |
|---|---|
| Código fuente (`src/`) | `.env` (tokens y secretos) |
| `config.example.yaml` | `config.yaml` (tu búsqueda personal) |
| `.env.example` | `data/jobs.db` (ofertas vistas) |
| `install.ps1`, `setup_tasks.ps1` | `data/browser_state.json` (sesión LinkedIn) |
| `requirements.txt` | `cv/` (tu currículum) |
| | `logs/`, `.venv/` |

## Estructura del proyecto

```
linkedin-job-finder/
├── main.py                  # Monitor de ofertas
├── install.ps1              # Instalación automática
├── setup_tasks.ps1          # Tareas programadas de Windows
├── config.example.yaml      # Plantilla de configuración
├── .env.example             # Plantilla de secretos
├── src/
│   ├── scraper.py           # Scraping LinkedIn vía jobspy
│   ├── database.py          # SQLite
│   ├── notifier.py          # Notificaciones Telegram
│   ├── approval_bot/bot.py  # Bot interactivo
│   └── auto_apply/          # Easy Apply con Playwright
├── data/                    # Base de datos (generada)
├── logs/                    # Logs (generados)
└── cv/                      # Tu CV (no se sube)
```

## Solución de problemas

### No llegan mensajes de Telegram

- Comprueba `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`.
- Pulsa `/start` en tu bot antes de usarlo.
- Revisa `logs/jobhunter.log`.

### Error "Windows Script Host" / tarea no encuentra archivo

- Ejecuta `setup_tasks.ps1` como administrador para reconfigurar las tareas.

### El monitor no encuentra ofertas

- Amplía `hours_old` o relaja `require_keywords_in_title` en `config.yaml`.

### Falla el auto-apply

- Repite el login: `python -m src.auto_apply.session_manager`
- Comprueba que existe `cv/resume.pdf`.

## Requisitos

- Python 3.11+
- Windows (para `setup_tasks.ps1`; el monitor funciona en cualquier SO)
- Cuenta de Telegram + bot propio
- Cuenta de LinkedIn (solo si usas auto-apply)

## Licencia

Uso personal. Respeta los términos de servicio de LinkedIn y Telegram.

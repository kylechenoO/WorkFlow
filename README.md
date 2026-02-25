# WorkFlow

**Author:** Kyle · **Version:** 0.0.3 · **License:** MIT

A Python-based **workflow automation platform** built on JSON-defined flows, dynamic module loading, and a full-featured web UI for managing, executing, and monitoring workflows at scale.

> **Clarity first · Correctness always · Complexity last**

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Upgrading](#upgrading)
- [Configuration Reference](#configuration-reference)
- [Web UI](#web-ui)
- [REST API](#rest-api)
- [CLI Reference](#cli-reference)
- [Workflow JSON Format](#workflow-json-format)
- [Module Reference](#module-reference)
- [Database Schema](#database-schema)
- [Security Considerations](#security-considerations)
- [Testing](#testing)
- [Design Principles](#design-principles)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- **JSON-defined workflows** — declare procedures, parameters, and data flow in plain JSON
- **Triple-mode workflow editor** — Form, Visual (drag-and-drop canvas), and JSON modes with bidirectional sync
- **Built-in modules** — Bash, HTTP, SSH, File I/O, MySQL, MongoDB, Kafka, Elasticsearch, Prometheus, Notify, Filter, MultiProcess, and more
- **Cluster failover** — multi-node failover built into MySQL and MongoDB modules (`cluster_connect`, `cluster_query`, etc.)
- **Custom module editor** — write Python procedure modules directly in the browser with version history
- **Run history & step viewer** — per-run execution timeline with step-level timing, results, and errors
- **Version control** — every workflow and module edit is versioned; diff and restore at any point
- **Role-based access control** — granular page + action permissions via Groups and Roles
- **Audit log** — every user action captured with IP, timestamp, and change detail
- **Password policy** — configurable minimum length, complexity requirements (uppercase, lowercase, digit, special character), and password expiry with forced change
- **System admin** — timezone, backup/restore, security (SSL + password policy), services management, API key management, and developer tools
- **Developer tools** — built-in REST client and SQL query tool
- **Backup & restore** — export/import workflows, modules, accounts, and settings as ZIP
- **SSL management** — upload server certificates and trusted CA certificates (under Security tab)
- **Services management** — view, configure, and restart backend/frontend services from the UI
- **SSH key management** — upload a global SSH private key and reference it as `@sys.ssh_key` in workflow procedures
- **System variables (`@sys.`)** — shared variables resolved at execution time with role/group-based permission control
- **Flask REST API** — full programmatic control (port 5001)
- **Django web frontend** — browser-based management UI (port 5002)
- **CLI interface** — manage and run workflows from the command line

---

## Screenshots

### Login
![Login](screenshots/login.png)

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Workflow List
![Workflow List](screenshots/workflow_list.png)

### Workflow Editor — Visual Mode
![Workflow Editor Visual](screenshots/workflow_editor_visual.png)

### Workflow Editor — Form Mode
![Workflow Editor Form](screenshots/workflow_editor_form.png)

### Workflow Editor — JSON Mode
![Workflow Editor JSON](screenshots/workflow_editor_json.png)

### Module Registry
![Modules](screenshots/modules.png)

### Module Editor
![Module Editor](screenshots/module_editor.png)

### Run Log
![Run Log](screenshots/runlog.png)

### System Log
![Syslog](screenshots/syslog.png)

### Audit Log
![Audit Log](screenshots/audit_log.png)

### User Management
![Users](screenshots/users.png)

### Group Management
![Groups](screenshots/groups.png)

### Role Management
![Roles](screenshots/roles.png)

### Profile
![Profile](screenshots/profile.png)

### Timezone Settings
![Timezone](screenshots/timezone.png)

### Version Info
![Version](screenshots/version.png)

### License
![License](screenshots/license.png)

### Backup & Restore
![Backup](screenshots/backup.png)

### OpenAPI Key Management
![OpenAPI](screenshots/openapi.png)

### Developer Tools — REST Client
![Devtool REST](screenshots/devtool_rest.png)

### Developer Tools — SQL Query
![Devtool SQL](screenshots/devtool_sql.png)

### Security — SSL Certs
![Security SSL](screenshots/security_ssl.png)

### Security — Password Policy
![Security Password Policy](screenshots/security_password_policy.png)

### Services Management
![Services](screenshots/services.png)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    WorkFlow.py                       │
│              (CLI + Flask REST API)                  │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │   System Initialization │
          │  Config · Log · MySQL   │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │      Flow Engine        │
          │      lib/Flow.py        │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   Procedure Execution   │
          │  resolve → load → call  │
          │   store result → next   │
          └─────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Django Web Frontend                     │
│  Dashboard · Workflows · Modules · Accounts          │
│  Audit · Syslog · System (port 5002)                │
└──────────────────────┬──────────────────────────────┘
                       │ calls
          ┌────────────▼────────────┐
          │   Flask REST API        │
          │   (port 5001)           │
          └─────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │        MySQL            │
          │   wf_flow · wf_syslog   │
          │  wf_run_history · etc.  │
          └─────────────────────────┘
```

---

## Project Structure

```
WorkFlow/
├── bin/
│   ├── WorkFlow.py              # Entry point: CLI + Flask REST API
│   └── service.sh               # Service manager (start/stop/restart/status)
├── lib/
│   ├── Flow.py                  # Workflow execution engine
│   ├── Config.py                # Configuration loader (JSON5)
│   ├── Log.py                   # Logging: console + file + MySQL
│   ├── MySQL.py                 # MySQL connection & access layer
│   └── ModuleInspector.py       # Module introspection for editor
├── mod/
│   ├── common/
│   │   ├── Bash.py              # Local shell command execution
│   │   ├── Kt.py                # Example/test module
│   │   ├── DataTransformer.py   # Dict list ↔ DataFrame
│   │   ├── Filter.py            # Filter, sort, dedup, select, limit
│   │   ├── Http.py              # HTTP client (GET/POST/PUT/DELETE)
│   │   ├── FileIO.py            # File read/write (CSV/JSON/Excel/YAML)
│   │   ├── Notify.py            # Email (SMTP) + Webhook
│   │   ├── Ssh.py               # SSH commands + SFTP transfer
│   │   └── MultiProcess.py      # Parallel steps + parallel data
│   ├── mysql/
│   │   └── MySQL.py             # MySQL CRUD operations
│   ├── mongodb/
│   │   └── MongoDB.py           # MongoDB CRUD + TLS support
│   ├── kafkaclient/
│   │   └── Kafka.py             # Kafka producer/consumer
│   ├── elasticsearchclient/
│   │   └── ElasticSearch.py     # Elasticsearch CRUD + Search
│   └── prometheus/
│       └── Prometheus.py        # Prometheus metrics push + export
├── web/
│   ├── manage.py
│   ├── wfsite/                  # Django project settings
│   ├── dashboard/               # Home page with stats
│   ├── accounts/                # User / Group / Role management + password policy
│   ├── audit/                   # Audit log viewer
│   ├── syslog_viewer/           # System log viewer
│   ├── workflows/               # Workflow editor + run history
│   ├── modules/                 # Module editor + registry
│   ├── system/                  # System admin (backup, devtool, security, services, API keys)
│   ├── templates/               # Shared base template
│   └── static/                  # CSS + JS assets
├── etc/
│   ├── global.json              # Global configuration (JSON5)
│   └── service.conf             # Gunicorn service settings
├── tools/
│   ├── workflow.ddl.sql         # Database schema
│   ├── initdb.sh                # Database initializer
│   ├── upgrade.sh               # Platform upgrade script
│   └── upgrade.sql              # Incremental DDL for upgrades
├── test/
│   ├── test.md                  # Test cases (335 total)
│   └── screenshots/             # UI screenshots
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- **Linux** — Ubuntu 20.04+ or CentOS 7+
- **miniforge** — Python 3.10+ runtime ([install guide](https://github.com/kylechenoO/miniforge))
- **MySQL 8.0+**

#### Install miniforge

```bash
git clone https://github.com/kylechenoO/miniforge.git
cd miniforge
sudo ./install_miniforge.sh
/opt/miniforge/bin/python -V   # verify
```

#### Create project virtualenv

```bash
cd /path/to/WorkFlow
/opt/miniforge/bin/python -m venv .
source bin/activate
```

### 1. Database Setup

```bash
# Create tables
mysql -u root -p < tools/workflow.ddl.sql

# Or use initdb.sh
./tools/initdb.sh
```

### 2. Configuration

Edit `etc/global.json`:

```json5
{
  db: {
    host: "127.0.0.1",
    port: 3306,
    username: "workflow",
    password: "your_password",      // change this
    database: "workflow",
    charset: "utf8mb4"
  },
  log: {
    path: "log/",
    file: "workflow.log",
    table: "wf_syslog",
    level: "INFO",
    rotate: { max_size: 10485760, backup_count: 5 }
  },
  lib: { path: "lib/" },
  mod: { path: "mod/" },
  flow: { table: "wf_flow" },
  api: { host: "0.0.0.0", port: 5001, debug: false },
  web: { secret_key: "change-me-in-production", debug: false, port: 5002 }
}
```

> **Important:** Change `db.password` and `web.secret_key` before deploying to production. The defaults are development placeholders only.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
cd web && python manage.py migrate
```

### 4. Start Services

**Production (gunicorn):**
```bash
./bin/service.sh start             # Start both backend + frontend
./bin/service.sh start backend     # Flask REST API → http://localhost:5001
./bin/service.sh start frontend    # Django Web UI → http://localhost:5002
./bin/service.sh status            # Check service status
./bin/service.sh restart           # Restart both services
```

**Development:**
```bash
python bin/WorkFlow.py --serve                     # Flask API
cd web && python manage.py runserver 0.0.0.0:5002  # Django UI
```

### 5. First Login

Navigate to `http://localhost:5002` and log in with the admin account created during `migrate`.

---

## Upgrading

### From v0.0.2 to v0.0.3

For existing deployments, use the single-trigger upgrade script:

```bash
bash tools/upgrade.sh
```

The script performs these steps automatically:
1. Stops backend and frontend services
2. Applies incremental database schema changes (`tools/upgrade.sql`)
3. Runs Django migrations for the `accounts` app
4. Seeds `UserProfile` records for all existing users (sets `password_changed_at` to current time — no forced password reset)
5. Starts services and verifies status

> **Note:** The upgrade is idempotent — safe to run multiple times. Default password policy after upgrade is permissive (min 8 chars, no complexity, no expiry) — identical to pre-upgrade behavior.

### Fresh Installation

For new deployments, follow the [Quick Start](#quick-start) guide. The full DDL (`tools/workflow.ddl.sql`) includes all tables.

---

## Configuration Reference

`etc/global.json` uses **JSON5** format (unquoted keys, trailing commas, comments allowed).

| Key | Description |
|-----|-------------|
| `db.host` | MySQL host |
| `db.port` | MySQL port (default: 3306) |
| `db.username` | MySQL username |
| `db.password` | MySQL password |
| `db.database` | Database name |
| `db.charset` | Character set (default: utf8mb4) |
| `log.path` | Log file directory |
| `log.file` | Log filename |
| `log.table` | MySQL log table name |
| `log.level` | Log level: DEBUG / INFO / WARNING / ERROR |
| `log.rotate.max_size` | Max log file size in bytes before rotation |
| `log.rotate.backup_count` | Number of rotated files to keep |
| `lib.path` | Core library path |
| `mod.path` | Procedure module path |
| `flow.table` | Workflow definition table name |
| `api.host` | Flask API bind address |
| `api.port` | Flask API port (default: 5001) |
| `api.debug` | Flask debug mode |
| `web.secret_key` | Django secret key (change in production) |
| `web.debug` | Django debug mode |
| `web.port` | Django port (default: 5002) |

Service settings (`etc/service.conf`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_HOST` | `0.0.0.0` | Flask API bind address |
| `BACKEND_PORT` | `5001` | Flask API port |
| `BACKEND_WORKERS` | `1` | Gunicorn workers (keep at 1 for APScheduler) |
| `BACKEND_THREADS` | `4` | Threads per worker |
| `FRONTEND_HOST` | `0.0.0.0` | Django bind address |
| `FRONTEND_PORT` | `5002` | Django port |
| `FRONTEND_WORKERS` | `4` | Gunicorn workers |
| `FRONTEND_THREADS` | `4` | Threads per worker |

### Changing Ports

**Via Web UI (recommended):**

1. Navigate to **System → Services**
2. Click the pencil icon next to a service's Configuration card
3. Change `BACKEND_PORT` or `FRONTEND_PORT`
4. Click **Save** → click **Restart Now** to apply
5. Both `etc/service.conf` and `etc/global.json` are updated automatically

**Via Console:**

1. Edit `etc/service.conf` — change `BACKEND_PORT` and/or `FRONTEND_PORT`
2. Edit `etc/global.json` — update `api.port` and/or `web.port` to match
3. Restart services:
   ```bash
   ./bin/service.sh restart backend    # restart Flask API
   ./bin/service.sh restart frontend   # restart Django UI
   ```

> **Important:** Both config files must stay in sync. `service.conf` controls gunicorn bind ports; `global.json` controls the Django→Flask connection URL. The web UI auto-syncs both files, but manual edits require updating both.

---

## Web UI

The Django web frontend runs on port **5002** and provides full management of the platform.

### Navigation

The collapsible left sidebar contains:

- **Dashboard** — overview stats
- **Automation:** Modules · Workflows · Runlog · Syslog
- **Admin:** System · OpenAPI · Devtool · Auditlog

Access to each section is controlled by the permission system.

---

### Dashboard (`/`)

- Summary cards: total workflows, enabled/disabled counts
- Recent workflows list (sorted by last updated) with pagination

---

### Workflows (`/workflows/`)

#### Workflow List
- Paginated list with per-workflow status, last run badge, run time, and updated timestamp
- Actions per row: **Edit** · **Run** · **Enable/Disable** · **Runlog** · **Delete**
- Search bar with client-side filtering

#### Workflow Editor (`/workflows/<name>/edit/`)

Three editing modes with **bidirectional sync**:

| Mode | Description |
|------|-------------|
| **Form** | Structured step list — add/remove/reorder procedures with fields for name, module, method, and params |
| **Visual** | Drawflow canvas — drag-and-drop procedure nodes with connection arrows |
| **JSON** | CodeMirror editor — full JSON with syntax highlighting, bracket matching, and validation |

Switching between tabs automatically syncs all three modes.

#### Run History (`/workflows/<name>/runs/` and `/workflows/runs/`)

- Per-workflow and global run history views
- Filters: status · trigger type · date range · text search
- Export to Excel (`.xlsx`)

#### Run Detail (`/workflows/<name>/run/<id>/`)

- Visual canvas showing the flow at execution time (snapshot)
- Step-by-step panel: status badge, duration, result data (expandable JSON), error message
- Run metadata: overall status, trigger, start/end time, duration
- Recent runs sidebar for quick navigation

#### Version History (`/workflows/<name>/versions/`)

- Full version list with timestamps and author
- View, diff (side-by-side), and restore any previous version

---

### Modules (`/modules/`)

#### Module List
- Grouped by category with expandable cards
- Displays: module name, description, method count, last modified
- Core modules (built-in) are protected from deletion
- Actions: **Edit** · **Delete** · **Create Category** · **Rename Category**

#### Module Editor (`/modules/<category>/<name>/edit/`)

- Full-page CodeMirror Python editor with syntax highlighting
- Live introspection sidebar: docstring, method list with signatures
- Save creates a version snapshot automatically

#### Module Version History
- Same version, diff, and restore capabilities as workflows

#### Module API (`/modules/api/registry/`)
- JSON endpoint listing all modules and their methods
- Used by the workflow editor for module/method selection dropdowns

---

### Accounts

#### Users (`/accounts/users/`)
- List all users with active/inactive status
- Create, edit, enable/disable users
- Assign Django Groups and custom Roles

#### Groups (`/accounts/groups/`)
- Create and manage permission groups
- Assign permissions per group using the page + action grid
- Protected groups: `admin`, `user`

#### Roles (`/accounts/roles/`)
- Custom role model extending Django groups
- Assign permissions to roles; assign roles to users
- Protected roles: `admin`, `user`

#### Profile (`/accounts/profile/`)
- View current user info, assigned groups and roles
- Update name/email and change password

#### Permission System

Permissions use a `page.action` format. Available permissions:

| Page | Actions |
|------|---------|
| `dashboard` | view |
| `workflows` | view · create · edit · delete · enable · run |
| `modules` | view · create · edit · delete |
| `users` | view · create · edit · toggle |
| `groups` | view · create · edit · delete |
| `roles` | view · create · edit · delete |
| `audit` | view |
| `syslog` | view |
| `system` | edit |
| `devtool` | use |

---

### Audit Log (`/audit/`)

- Captures every significant user action automatically
- Filters: user · action type · target type · date range · text search
- Logged fields: user, action, target type, target name, IP address, detail (JSON), timestamp
- Action types: `create` · `update` · `delete` · `enable` · `disable` · `run` · `rename` · `login` · `logout`

---

### Syslog Viewer (`/syslog/`)

- View runtime logs written by the workflow engine
- Filters: log level · date range · text search
- Levels: DEBUG · INFO · WARNING · ERROR · CRITICAL

---

### System Admin (`/system/`)

The system section groups administrative settings in a tabbed layout.

#### Timezone (`/system/timezone/`)
- Select system timezone from 80+ curated options grouped by region
- Shows current server time in the selected timezone

#### Backup (`/system/backup/`)
- Create a ZIP backup containing any combination of:
  - Workflow definitions (JSON)
  - Module source files (Python)
  - User/group/role accounts
  - System settings
- Download immediately after creation

#### Restore (`/system/backup/?tab=restore`)
- Upload a previously created backup ZIP to restore selected sections

#### Security (`/system/security/`)

Sub-tabbed layout with **SSL Certs** and **Password Policy** sections.

**SSL Certs** (default sub-tab):
- View HTTPS status (HTTP Only / HTTPS Enabled)
- Upload server certificate and private key (`.crt`/`.pem` + `.key`/`.pem`)
- Manage trusted CA certificates (upload and delete)
- Toggle HTTPS on/off

**Password Policy** (`/system/security/?tab=password-policy`):
- Configure minimum password length (8–32 characters)
- Require uppercase, lowercase, digit, and/or special characters
- Set password expiry (0–365 days; 0 = disabled)
- When expired, users are forced to change their password before accessing any page
- Current Policy summary card shows active rules at a glance

#### Services Management (`/system/services/`)
- View backend (Flask API) and frontend (Django UI) service status
- Start, stop, restart services from the UI
- View and edit service configuration (host, port, workers, threads, timeout)
- Live service log viewer
- Read-only display of `global.json` configuration with masked passwords

#### API Keys (`/system/apis/`)
- Create named API keys for programmatic access to the REST API
- Keys are hashed on creation; the plain key is shown once
- Enable/disable and delete existing keys

#### Developer Tools (`/system/devtool/`)

**RESTFultool** — built-in HTTP client:
- Method dropdown (GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS)
- URL bar with Send · Clear · Export buttons
- Headers and Body fields (JSON)
- Response panel with status badge, duration, and formatted output
- Export response as JSON or text

**SQLtool** — read-only SQL query runner:
- Execute SELECT, SHOW, DESCRIBE statements against the WorkFlow database
- Results capped at 500 rows
- Syntax: Run · Clear · Export buttons
- Export results to Excel (`.xlsx`)

#### Version (`/system/version/`)
- Displays app name, version, author, and email from `pyproject.toml`

#### License (`/system/license/`)
- Displays the full LICENSE file content

---

## REST API

The Flask REST API runs on port **5001** and provides programmatic workflow management.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/flow` | List all workflows |
| `GET` | `/flow/<name>` | Get workflow definition |
| `POST` | `/flow` | Create workflow |
| `PUT` | `/flow/<name>` | Update workflow |
| `DELETE` | `/flow/<name>` | Soft-delete workflow |
| `POST` | `/flow/<name>/run` | Execute workflow |
| `PUT` | `/flow/<name>/enable` | Enable workflow |
| `PUT` | `/flow/<name>/disable` | Disable workflow |
| `PUT` | `/flow/<name>/rename` | Rename workflow |
| `GET` | `/flow/<name>/runs` | List run history for a workflow |
| `GET` | `/run/<run_id>` | Get run details with step results |
| `GET` | `/backup` | Download full backup ZIP (requires `X-Api-Key` header) |

### Authentication

The `/backup` endpoint requires an API key in the `X-Api-Key` header. Keys are managed in the web UI under **System → OpenAPI**.

> **Note:** Most API endpoints are designed for internal use and do not require authentication. Deploy behind a firewall or add an authentication layer for production use. See [Security Considerations](#security-considerations).

---

## CLI Reference

```bash
python bin/WorkFlow.py [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `-f <name>` | Execute workflow by name |
| `-c <json>` | Create workflow from JSON string |
| `-u <json>` | Update workflow definition |
| `-r <json>` | Rename workflow: `{"current":"old","new":"new"}` |
| `-t <name>` | Soft-delete workflow |
| `-e <name>` | Enable workflow |
| `-d <name>` | Disable workflow |
| `-i <name>` | Get workflow info |
| `-l` | List all workflows |
| `-s` | Start Flask REST API server |

---

## Workflow JSON Format

Workflows are stored as JSON in the database. A workflow contains a list of **procedures** (steps) executed sequentially.

```json
{
  "procedures": [
    {
      "name": "fetch",
      "mod": "common.Http",
      "method": "get",
      "params": {
        "url": "https://api.example.com/data",
        "headers": {"Authorization": "Bearer token123"}
      }
    },
    {
      "name": "save",
      "mod": "common.FileIO",
      "method": "write",
      "params": {
        "file_path": "/tmp/output.json",
        "data": "@fetch.data"
      }
    },
    {
      "name": "notify",
      "mod": "common.Notify",
      "method": "webhook",
      "params": {
        "url": "https://hooks.slack.com/...",
        "body": {"text": "Done. Saved @fetch.count rows."}
      }
    }
  ],
  "variables": {
    "env": "production"
  }
}
```

### Parameter Reference Syntax

| Syntax | Resolves to |
|--------|-------------|
| `@step` | Full result dict of `step` |
| `@step.key` | Specific key from `step`'s result |
| `@@value` | Literal string `@value` (escaped) |
| `value` | Literal string as-is |
| `@var.name` | Workflow-level variable |
| `@sys.key` | System variable (e.g. `@sys.ssh_key`) |

### Procedure Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique step name; used as `@name` reference |
| `mod` | Yes | Module path: `category.ClassName` |
| `method` | Yes | Method name to call on the module class |
| `params` | No | Key-value parameters passed to the method |

---

## Module Reference

All procedure modules follow this interface:

```python
class MyModule:
    def __init__(self, logger):
        self.logger = logger

    def my_method(self, context: dict, params: dict) -> dict:
        # params: resolved input parameters
        # context: full execution context (previous step results)
        # returns: dict with at least {"status": True/False}
        ...
```

---

### `common.Bash` — Shell Execution

| Method | Key Params | Returns |
|--------|-----------|---------|
| `run` | `cmd` (str or list), `cwd`, `env` (dict), `timeout` (int), `shell` (bool, default True) | `{"status": True, "exit_code": N, "stdout": "...", "stderr": "..."}` |

> **Security note:** `shell=True` is the default to support piped and compound commands. Avoid passing untrusted user input directly as `cmd`. Use `shell=False` and a list for `cmd` when arguments come from external input.

---

### `common.Kt` — Test/Demo

| Method | Description |
|--------|-------------|
| `prt1` | Log and return `msg` param |
| `prt2` | Log and return `msg` param |

---

### `common.DataTransformer` — DataFrame Conversion

| Method | Key Params | Returns |
|--------|-----------|---------|
| `dicts2df` | `data` (list of dicts) | `{"status": True, "data": DataFrame}` |
| `df2dicts` | `data` (DataFrame) | `{"status": True, "data": [...]}` |

---

### `common.Filter` — Data Transformation

| Method | Key Params | Description |
|--------|-----------|-------------|
| `filter` | `data`, `conditions` | Filter rows by conditions (`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `not_contains`) |
| `select` | `data`, `cols` / `rename` / `drop` | Keep, rename, or drop columns |
| `sort` | `data`, `by`, `ascending` | Sort rows by one or more columns |
| `dedup` | `data`, `cols` | Remove duplicate rows |
| `limit` | `data`, `count`, `offset` | Slice rows with offset |

All methods return `{"status": True, "data": [...], "count": N}`.

---

### `common.Http` — HTTP Client

| Method | Key Params | Returns |
|--------|-----------|---------|
| `get` | `url`, `headers`, `params`, `timeout`, `auth`, `verify_ssl` | `{"status": True, "status_code": N, "data": {...}}` |
| `post` | `url`, `json` / `data`, `headers`, `timeout` | same |
| `put` | `url`, `json` / `data`, `headers`, `timeout` | same |
| `delete` | `url`, `headers`, `timeout` | same |

---

### `common.FileIO` — File I/O

Supported formats: **CSV**, **JSON**, **XLSX**, **YAML** (auto-detected from extension).

| Method | Key Params | Returns |
|--------|-----------|---------|
| `read` | `file_path`, `format`, `encoding`, `sheet` | `{"status": True, "data": [...]}` |
| `write` | `file_path`, `data`, `format`, `encoding`, `sheet` | `{"status": True}` |

---

### `common.Notify` — Notifications

| Method | Key Params | Description |
|--------|-----------|-------------|
| `email` | `smtp_host`, `smtp_port`, `from_addr`, `to_addrs`, `subject`, `body`, `body_type`, `use_tls` | Send email via SMTP |
| `webhook` | `url`, `body`, `method`, `headers`, `timeout` | Send webhook (Slack, Teams, DingTalk, etc.) |

---

### `common.Ssh` — Remote Execution & SFTP

| Method | Key Params | Description |
|--------|-----------|-------------|
| `connect` | `host`, `port`, `username`, `password` / `key_file`, `timeout` | Establish SSH connection |
| `disconnect` | — | Close SSH and SFTP sessions |
| `run` | `cmd`, `timeout` | Execute remote shell command |
| `run_script` | `script_path`, `interpreter`, `args`, `timeout` | Upload and run local script remotely |
| `upload` | `local_path`, `remote_path` | Upload file via SFTP |
| `download` | `remote_path`, `local_path` | Download file via SFTP |

`run` and `run_script` return `{"status": True, "exit_code": N, "stdout": "...", "stderr": "..."}`.

> **Tip:** Use `@sys.ssh_key` as the `key_file` parameter to reference the global SSH key configured in System → Services.

---

### `common.MultiProcess` — Parallel Execution

| Method | Key Params | Description |
|--------|-----------|-------------|
| `parallel_steps` | `steps` (list of step dicts), `processes` | Run independent workflow steps concurrently |
| `parallel_data` | `data`, `data_key`, `mod`, `method`, `params`, `processes` | Split data into chunks and process in parallel |

> **Note:** Worker processes cannot inherit stateful connections (SSH, MySQL, Elasticsearch). Best for stateless operations.

---

### `mongodb.MongoDB` — MongoDB Operations

Connection is stored in context (`__mongodb_con__`, `__mongodb_db__`) to persist across steps.

| Method | Key Params | Description |
|--------|-----------|-------------|
| `connect` | `host`, `port`, `username`, `password`, `database`, `auth_source`, TLS options | Establish connection with optional TLS/SSL |
| `disconnect` | — | Close connection |
| `find` | `collection`, `query`, `projection`, `sort`, `limit` | Query documents |
| `findOne` | `collection`, `query`, `projection` | Get single document |
| `insert` | `collection`, `data` | Insert documents |
| `update` | `collection`, `query`, `data`, `upsert` | Update documents |
| `delete` | `collection`, `query` | Delete documents |
| `count` | `collection`, `query` | Count matching documents |
| `aggregate` | `collection`, `pipeline` | Run aggregation pipeline |

TLS supports cert from local file path, URL, or base64-encoded content.

#### Cluster Methods

Auto-failover to the next node on connection error. Returns `{"status": True, "connected_node": "host:port"}` on connect.

| Method | Key Params | Description |
|--------|-----------|-------------|
| `cluster_connect` | `hosts` (list of {host, port, username, password, database, TLS options}), `retry_on_error`, `timeout` (ms, default 5000), `retry_count` (default 3), `retry_delay` (sec, default 1.0) | Connect to first available node with configurable timeout and retry |
| `cluster_disconnect` | — | Close connection |
| `cluster_find` | `collection`, `query`, `projection`, `sort`, `limit` | Query documents (delegated) |
| `cluster_findOne` | `collection`, `query`, `projection` | Get single document (delegated) |
| `cluster_insert` | `collection`, `data` | Insert documents (delegated) |
| `cluster_update` | `collection`, `query`, `data`, `upsert` | Update documents (delegated) |
| `cluster_delete` | `collection`, `query` | Delete documents (delegated) |
| `cluster_count` | `collection`, `query` | Count documents (delegated) |
| `cluster_aggregate` | `collection`, `pipeline` | Aggregation pipeline (delegated) |

---

### `kafkaclient.Kafka` — Kafka Producer/Consumer

Producer and consumer are stored in context (`__kafka_producer__`, `__kafka_consumer__`).

| Method | Key Params | Description |
|--------|-----------|-------------|
| `connect_producer` | `bootstrap_servers`, `client_id`, `acks`, `retries`, security options | Connect as Kafka producer |
| `connect_consumer` | `bootstrap_servers`, `group_id`, `topics`, `auto_offset_reset`, security options | Connect and subscribe as consumer |
| `send` | `topic`, `data`, `key` | Send JSON message to topic |
| `consume` | `max_messages`, `timeout_ms` | Consume messages from subscribed topics |
| `disconnect` | — | Close producer/consumer |
| `list_topics` | — | List available topics |

Supports PLAINTEXT, SSL, SASL_PLAINTEXT, and SASL_SSL security protocols.

---

### `mysql.MySQL` — MySQL Operations

| Method | Key Params | Description |
|--------|-----------|-------------|
| `connect` | `host`, `port`, `username`, `password`, `database`, `charset` | Establish connection |
| `disconnect` | — | Close connection |
| `query` | `sql`, `params` | Parameterized SELECT |
| `insert` | `table`, `data` | Insert records |
| `update` | `table`, `where`, `data` | Update records |
| `upsert` | `table`, `data`, `update_cols`, `key_cols` | Insert or update on duplicate key |
| `execute` | `sql` | Execute arbitrary SQL |
| `showDatabases` | — | List databases |
| `showTables` | — | List tables |

#### Cluster Methods

Stores MySQLBase instance in context (`__mysqlcluster_mysql__`). Returns `{"status": True, "connected_node": "host:port"}` on connect.

| Method | Key Params | Description |
|--------|-----------|-------------|
| `cluster_connect` | `hosts` (list of {host, port, username, password, database}), `retry_on_error`, `timeout` (ms, default 5000), `retry_count` (default 3), `retry_delay` (sec, default 1.0) | Connect to first available node with configurable timeout and retry |
| `cluster_disconnect` | — | Close connection |
| `cluster_query` | `sql`, `params` | Parameterized SELECT (delegated) |
| `cluster_insert` | `table`, `data` | Insert records (delegated) |
| `cluster_update` | `table`, `where`, `data` | Update records (delegated) |
| `cluster_insertWithUK` | `table`, `data`, `update_cols`, `key_cols` | Upsert on duplicate key (delegated) |

---

### `elasticsearchclient.ElasticSearch` — Elasticsearch

| Method | Description |
|--------|-------------|
| `connect` | Connect with basic auth, API key, or certificate |
| `disconnect` | Close connection |
| `search` | Execute search query |
| `get` | Get document by ID |
| `index` | Index a document |
| `create` | Create a document (fail if exists) |
| `bulk` | Bulk index/update/delete |
| `update` | Update document |
| `delete` | Delete document |
| `createIndex` | Create index with mapping |
| `deleteIndex` | Delete index |
| `health` | Get cluster health |

---

### `prometheus.Prometheus` — Metrics

| Method | Description |
|--------|-------------|
| `connect` | Connect to Pushgateway |
| `disconnect` | Close connection |
| `dicts2prom` | Convert list of dicts to Prometheus metrics |
| `push` | Push metrics to Pushgateway |
| `write` | Write metrics to file (for node_exporter) |

Supported metric types: `gauge`, `counter`, `histogram`, `summary`.

---

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `wf_flow` | Workflow definitions |
| `wf_syslog` | Engine runtime logs |
| `wf_run_history` | Workflow execution records |
| `wf_run_step` | Per-step execution details |
| `wf_version` | Version snapshots for workflows and modules |
| `wf_audit_log` | User action audit trail |
| `wf_role` | Custom roles |
| `wf_user_role` | User ↔ Role mappings |
| `system_setting` | Key-value system configuration |
| `system_api_key` | API access tokens (hashed) |
| `system_devtool_request` | Devtool request history |
| `wf_user_profile` | User password expiry tracking |
| `wf_permission` | Page + action permission definitions |
| `wf_role_permission` | Role ↔ Permission mappings |
| `wf_group_permission` | Group ↔ Permission mappings |

### Key Table Details

#### `wf_flow`

| Column | Description |
|--------|-------------|
| `id` | Primary key |
| `flow_name` | Unique workflow name |
| `flow_procedures` | Workflow JSON definition |
| `enabled` | Enable flag |
| `deleted` | Soft delete flag |
| `created_at` | Creation timestamp |
| `updated_at` | Last update timestamp |

#### `wf_run_history`

| Column | Description |
|--------|-------------|
| `id` | Primary key (run ID) |
| `flow_name` | Workflow name |
| `status` | `running` / `success` / `failed` |
| `trigger_by` | Username or `job:<name>` |
| `start_time` | Execution start |
| `end_time` | Execution end |
| `duration_ms` | Total duration in ms |
| `error_msg` | Error message if failed |

#### `wf_run_step`

| Column | Description |
|--------|-------------|
| `id` | Primary key |
| `run_id` | Foreign key to `wf_run_history` |
| `step_name` | Procedure name |
| `step_order` | Execution order |
| `status` | `running` / `success` / `failed` |
| `duration_ms` | Step duration in ms |
| `result_data` | Step result JSON |
| `error_msg` | Error message if failed |

#### `wf_audit_log`

| Column | Description |
|--------|-------------|
| `id` | Primary key |
| `user_id` | FK to `auth_user` |
| `action` | Action type |
| `target_type` | Entity type (flow, user, module, etc.) |
| `target_name` | Entity name |
| `detail` | JSON detail of the change |
| `ip_address` | Client IP |
| `created_at` | Timestamp |

---

## Security Considerations

WorkFlow is designed as an **internal tool** deployed behind a firewall. The following items should be reviewed before production deployment:

| Area | Default | Recommendation |
|------|---------|----------------|
| **Flask REST API auth** | No authentication on most endpoints | Deploy behind a reverse proxy with auth, or add API key validation |
| **Django ALLOWED_HOSTS** | `['*']` | Restrict to specific hostnames in production |
| **Debug mode** | `true` in `global.json` | Set `api.debug` and `web.debug` to `false` |
| **API bind address** | `0.0.0.0` | Use `127.0.0.1` if the API should not be exposed externally |
| **DB password** | `"pass"` (development default) | Change to a strong password |
| **Django SECRET_KEY** | `"change-me-in-production"` | Generate a random 50+ character key |
| **Error messages** | `str(e)` returned to API clients | Acceptable for internal use; sanitize for public-facing deployments |
| **API keys** | Hashed with bcrypt; plain key shown once at creation | Rotate keys regularly |
| **SQL queries** | All parameterized (no string concatenation) | Safe by design |
| **CSRF protection** | Enabled via Django middleware | Active on all form submissions |
| **Password policy** | Min 8 chars, no complexity, no expiry | Enable complexity requirements and set expiry in System → Security |
| **SSL verification** | `verify_ssl=True` by default in Http module | Do not disable in production |

---

## Testing

All features have been tested across **335 test cases** covering authentication, workflows, modules, run logs, system admin, REST API, and browser UI.

| Metric | Count |
|--------|-------|
| **Total** | 335 |
| **Pass** | 329 |
| **Fail** | 0 |
| **Skip** | 6 |

Test methods include:
- **Browser tests** — end-to-end UI testing across all pages (login, dashboard, workflows, modules, accounts, system admin)
- **API tests** — REST endpoint validation for CRUD operations, workflow execution, and system configuration
- **Integration tests** — cross-module workflows, database operations, service management

The full test report with detailed steps, expected results, and screenshots is available at [`test/test.md`](test/test.md).

---

## Design Principles

1. **Explicit over implicit** — all procedure dependencies declared in JSON; no hidden coupling
2. **Configuration-driven** — workflows stored as JSON in the database, loaded dynamically
3. **Clear separation** — system infrastructure (`lib/`) vs business logic (`mod/`)
4. **Deterministic execution** — sequential procedure execution with predictable ordering
5. **Observability first** — logging at every layer (console, file, database); run history with step-level detail
6. **Fail-safe logging** — logging errors never interrupt workflow execution
7. **Security by default** — SSL verification on, parameterized queries only, audit trail on all actions
8. **Soft deletes** — workflows renamed with timestamp suffix rather than hard deleted
9. **Version everything** — every workflow and module edit creates a restorable snapshot
10. **Extend without modifying** — add new modules under `mod/` without touching the engine

---

## Changelog

### v0.0.3 (2026-02-25)

**New Features**
- **Password policy** — configurable minimum length, complexity requirements (uppercase, lowercase, digit, special character), and password expiry with forced change via System → Security → Password Policy
- **Security tab** — renamed "SSL Certs" tab to "Security" with sub-tabs for SSL Certs and Password Policy
- **Upgrade script** — `tools/upgrade.sh` for single-trigger platform upgrades on existing offline deployments

**Improvements**
- Dynamic password help text on all password forms reflects the current policy
- `UserProfile` model tracks `password_changed_at` for password expiry; existing users seeded with current timestamp during upgrade
- Comprehensive test suite: **335 test cases**

### v0.0.2 (2026-02-22)

**New Features**
- **Triple-mode workflow editor** — Visual (drag-and-drop canvas), Form, and JSON editing modes with bidirectional sync
- **Module editor** — write and edit Python procedure modules directly in the browser with syntax highlighting
- **Version control** — every workflow and module edit is versioned with diff and restore support
- **Cluster failover** — multi-node failover with configurable timeout, retry count, and retry delay built into MySQL and MongoDB modules
- **Kafka module** — producer/consumer operations with SASL/SSL support (`kafkaclient.Kafka`)
- **MongoDB module** — full CRUD, aggregation, TLS support (`mongodb.MongoDB`)
- **Bash module** — execute shell commands with timeout and environment variable support
- **SSL management** — upload and manage server certificates for HTTPS with auto-restart on enable/disable
- **Services management** — view, configure, and restart backend/frontend services from the UI
- **Backup & restore** — export/import workflows, modules, accounts, and settings as ZIP
- **API key management** — create, rotate, and revoke API keys with bcrypt hashing
- **Developer tools** — built-in REST client and SQL query tool in the web UI
- **Audit log** — every user action captured with IP, timestamp, and change detail
- **Role-based access control** — granular page + action permissions via Groups and Roles
- **SSH key management** — upload and manage a global SSH private key from System → Services
- **System variables (`@sys.`)** — shared variables (e.g. `@sys.ssh_key`) resolved at execution time with permission control via Roles/Groups
- **Friendly error pages** — deleted or missing workflows show a clean "Workflow Not Found" page instead of raw 404

**Improvements**
- Service management via unified `bin/service.sh` (start/stop/restart/status for backend and frontend)
- Port configuration auto-sync between `global.json` and `service.conf` via the web UI
- Password verification modal for sensitive system operations

**Bug Fixes**
- Fix visual editor losing double-quoted content in parameter values (e.g. `sudo -u root -c "whoami"` truncated to `sudo -u root -c`)
- Fix visual editor not syncing changes from JSON/Form editors — renaming, reordering, and content edits now reflect correctly across all tabs
- Fix missing connection lines when workflows created via JSON or Form editor are reopened
- Block saving workflows with unconnected nodes in the visual editor to prevent ambiguous execution order
- Fix HTTPS SSL: gunicorn now starts with `--certfile`/`--keyfile` flags; service auto-restarts on enable/disable
- Fix orphan gunicorn worker processes surviving after service stop
- Fix MySQL password handling: remove unnecessary URL encoding
- Fix devtool page failing to load offline (missing `{% load static %}`)

**Security**
- Passwords masked in debug logs
- Security comments added to default configuration
- Expanded `.gitignore` for credential and secret file protection

### v0.0.1 (2025-08-22)

- Initial release
- JSON-defined workflow engine with dynamic module loading
- Flask REST API (port 5001) and Django web frontend (port 5002)
- Core modules: HTTP, SSH, FileIO, MySQL, Elasticsearch, Prometheus, Notify, Filter, DataTransformer, Kt, MultiProcess
- CLI interface for workflow management and execution
- MySQL-backed logging and run history

---

## License

MIT License. See [LICENSE](LICENSE) for details.

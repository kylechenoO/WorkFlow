# Workflow Framework

**Author:** Kyle

**Created:** 20251224

**License:** MIT

**Maintainer:** Kyle

A lightweight Python workflow execution framework based on **JSON-defined flows**, **explicit procedure dependencies**, and **centralized system services**.

This framework is designed to be:

* Clear and predictable
* Explicit in data flow
* Deterministic in execution order
* Easy to extend
* Production-friendly with strong observability

---

## 1. Overview

A **workflow** is a sequence of procedures executed in a predefined order.

Each procedure:

* Receives input parameters
* Executes business logic
* Returns a structured result (`dict`)

Procedures exchange data through a shared **execution context**, which is managed entirely by the workflow engine.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
+--------------------------------------------------+
|                  WorkFlow.py                     |
|               (Program Entry Point)              |
+-------------------------+------------------------+
                          |
                          v
        +-----------------+------------------+
        |   System Initialization            |
        |------------------------------------|
        |  Load configuration                |
        |  Initialize Log Object             |
        |  Initialize Database Connection    |
        |  Attach MySQL Log Handler          |
        +-----------------+------------------+
                          |
                          v
        +-----------------+------------------+
        |            Flow Engine             |
        |           (lib/Flow.py)            |
        +-----------------+------------------+
                          |
                          v
        +-----------------+------------------+
        |              Context               |
        |     (In-memory execution state)    |
        +-----------------+------------------+
                          |
                          v
        +-----------------+------------------+
        |      Procedure Execution Loop      |
        |------------------------------------|
        |  Resolve parameters                |
        |  Execute procedures                |
        |  Store result into context         |
        +------------------------------------+
```

Arrows indicate **control flow and execution order**, not data coupling.

---

## 3. Project Structure

```
WorkFlow/
├── bin/                     # bin path
│   ├── WorkFlow.py          # Program entry point (CLI + REST API)
│   └── service.sh           # Gunicorn service startup script
├── lib/                     # lib path
│   ├── Flow.py              # Workflow execution engine
│   ├── Config.py            # Configuration loader
│   ├── Log.py               # Logging lib
│   └── MySQL.py             # MySQL connection & access layer
├── mod/                     # mod path
│   ├── common/              # common modules
│   │   ├── Kt.py            # Example procedure module
│   │   ├── DataTransformer.py # Dict list ↔ DataFrame conversion
│   │   ├── Filter.py        # Dict list filtering & transformation
│   │   ├── Http.py          # HTTP client (GET/POST/PUT/DELETE)
│   │   ├── FileIO.py        # File read/write (CSV/JSON/Excel/YAML)
│   │   ├── Notify.py        # Email (SMTP) + Webhook notifications
│   │   ├── Ssh.py           # SSH remote commands + SFTP transfer
│   │   └── MultiProcess.py  # Parallel steps + parallel data processing
│   ├── mysql/               # MySQL procedure module
│   │   └── MySQL.py         # MySQL CRUD operations
│   ├── elasticsearch/       # Elasticsearch procedure module
│   │   └── ElasticSearch.py # Elasticsearch CRUD + Search operations
│   └── prometheus/          # Prometheus procedure module
│       └── Prometheus.py    # Prometheus metrics operations
├── web/                     # Django web frontend
│   ├── manage.py            # Django management CLI
│   ├── service_django.sh    # Django dev server startup script
│   ├── wfsite/              # Django project settings
│   ├── dashboard/           # Dashboard app (home page)
│   ├── accounts/            # User/Group/Role management app
│   ├── audit/               # Audit logging app
│   ├── syslog_viewer/       # Syslog viewer app
│   ├── workflows/           # Workflow management + editor app
│   ├── templates/           # Shared templates (base.html)
│   └── static/              # CSS + JS (style.css, flow_editor.js)
├── etc/                     # config path
│   ├── global.json          # Global configuration (JSON5)
│   └── service.conf         # Gunicorn service settings
├── tools/                   # utility scripts
└── README.md
```

---

## 4. System Modules

### 4.1 Program Entry (`WorkFlow.py`)

Responsibilities:

* Load global configuration
* Initialize **Log Object**
* Initialize **database connection**
* Attach MySQL log handler
* Create Flow engine
* Trigger workflow execution (CLI or REST API)

Supports two modes:

* **CLI mode** — execute workflows and manage flows from command line
* **REST API mode** — serve workflows as a web service via Flask + gunicorn

Initialization sequence:

```
Load configuration
    ↓
Initialize Log Object
    ↓
Initialize Database Connection
    ↓
Attach MySQL Log Handler
    ↓
Execute Flow (CLI) or Start API Server (REST)
```

---

### 4.2 Logging System (`lib/Log.py`)

The logging system is encapsulated as a **Log Object**.

Features:

* Console logging
* Rotating file logging
* MySQL logging
* Unified log format

Log format example:

```
2025-12-19 08:39:02.002 DEBUG Flow execFlow start
```

Formatter definition:

```
%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s
```

Design notes:

* Log Object is initialized **before** database connection
* MySQL logging is attached **after** database connection is available
* Logging failures must never interrupt workflow execution

---

### 4.3 Database Access Layer (`lib/MySQL.py`)

Responsibilities:

* Initialize MySQL connections
* Execute SQL statements
* Manage transactions (commit / rollback)
* Provide database access to Flow engine and logging system

Important clarification:

> This module **only initializes database connections**.
> It does **not** create databases or modify table structures.

---

## 5. Core Concepts

### 5.1 Procedures

A **procedures** represents one execution step in a workflow.

Procedures method signature:

```python
def method(self, context: dict, params: dict) -> dict
```

Rules:

* `params` contains resolved input parameters
* `context` represents workflow execution state
* Return value **must be a dict**

---

### 5.2 Context

`context` is an **in-memory execution data store**.

It is used to:

* Store results of completed procedures
* Provide data to downstream procedures
* Maintain runtime state during execution

Example:

```python
context = {
    "step1": {"msg": "hello"},
    "_runtime": {
        "start_time": "2025-12-19T08:39:02"
    }
}
```

Rules:

* `context[procedure_name]` stores procedure output
* Keys starting with `_` are system-reserved
* Pasks should not modify results of other procedures

---

## 6. Flow Definition (JSON)

Flows are defined using **standard JSON** and stored in the database.

### Example Flow JSON

```json
{
  "procedures": [
    {
      "name": "step1",
      "mod": "common.Kt",
      "method": "prt",
      "params": {
        "msg": "hello"
      }
    },
    {
      "name": "step2",
      "mod": "common.Kt",
      "method": "prt",
      "params": {
        "msg": "@step1.msg"
      }
    }
  ]
}
```

---

## 7. Data Flow Between Procedures

### Execution Example

```
step1 returns {"msg": "hello"}

Stored as:
context["step1"]["msg"]

Resolved reference:
@step1.msg

Passed to step2 as:
{"msg": "hello"}
```

Key points:

* Procedures do not directly depend on each other
* All dependencies are declared in flow JSON
* The Flow engine resolves dependencies centrally

---

## 8. Parameter Reference Rules

| Syntax      | Meaning                          |
| ----------- | -------------------------------- |
| `@step`     | Reference full procedure result  |
| `@step.key` | Reference a specific key         |
| `@@value`   | Literal string starting with `@` |
| `value`     | Normal literal value             |

Example:

```json
{
  "params": {
    "msg": "@step1.msg",
    "email": "kk@gmail.com",
    "raw": "@@example"
  }
}
```

Resolved parameters:

```python
{
    "msg": "hello",
    "email": "kk@gmail.com",
    "raw": "@example"
}
```

---

## 9. Procedure Implementation Example

```python
class Kt:
    def __init__(self, logger) -> None:
        self.logger = logger

    def prt(self, context: dict, params: dict) -> dict:
        msg = params["msg"]
        self.logger.info("msg=%s", msg)
        return {"msg": msg}
```

---

## 10. Database Design

### 10.1 Database Overview

The database contains **independent tables** serving different purposes.

There are **no foreign key relationships** between these tables.

---

#### Workflow Definition Table

```
+----------------------+
|   wf_flow            |
|----------------------|
| Flow configuration   |
| Enable / Disable     |
| Soft delete          |
+----------------------+
```

Purpose:

* Store workflow definitions
* Act as the configuration source for the Flow engine

---

#### System Log Table

```
+----------------------+
|  wf_syslog           |
|----------------------|
| System logs          |
| Execution logs       |
| Audit & debug        |
+----------------------+
```

Purpose:

* Store runtime logs
* Support observability and troubleshooting
* Written by the logging system

---

### 10.2 Table Details

#### `wf_flow`

| Column     | Description                |
| ---------- | -------------------------- |
| id         | Primary key                |
| flow_name  | Unique workflow name       |
| flow_json  | Workflow definition (JSON) |
| enabled    | Enable flag                |
| deleted    | Soft delete flag           |
| created_at | Creation time              |
| updated_at | Update time                |

---

#### `wf_syslog`

| Column      | Description                  |
| ----------- | ---------------------------- |
| id          | Primary key                  |
| created_at  | Log timestamp                |
| level       | Log level                    |
| logger_name | Logger name                  |
| message     | Log message                  |

---

#### `wf_role`

| Column      | Description                  |
| ----------- | ---------------------------- |
| id          | Primary key                  |
| name        | Unique role name             |
| description | Role description             |
| created_at  | Creation time                |

Purpose:

* Custom role definitions for workflow access control
* Extends beyond Django's built-in Group model

---

#### `wf_audit_log`

| Column      | Description                  |
| ----------- | ---------------------------- |
| id          | Primary key                  |
| user_id     | Foreign key to auth_user     |
| action      | Action type (create, update, delete, enable, disable, run, login, logout) |
| target_type | Target entity type (flow, user, group, role) |
| target_name | Target entity name           |
| detail      | Additional details (JSON)    |
| ip_address  | Client IP address            |
| created_at  | Log timestamp                |

Purpose:

* Track every user action across the web frontend
* Support security auditing and compliance
* Auto-captured by AuditMiddleware + explicit logging in views

---

## 11. Execution Lifecycle

```
Start Program
    ↓
Load Configuration
    ↓
Initialize Log Object
    ↓
Initialize Database Connection
    ↓
Attach MySQL Log Handler
    ↓
Load Flow Definition
    ↓
Execute Procedures Sequentially
    ↓
Write Logs
    ↓
End
```

---

## 12. Error Handling

* Parameter resolution errors:

  * Logged
  * Workflow stops immediately
* Procedure execution errors:

  * Logged
  * Exception propagated
* Logging errors never interrupt workflow execution

---

## 13. Design Principles

* Explicit over implicit
* Configuration-driven execution
* Clear separation of system and business logic
* Deterministic execution order
* Observability as a first-class concern

---

## 14. Available Modules

| Module | Path | Description |
| ------ | ---- | ----------- |
| Kt | `mod/common/Kt.py` | Example procedure module for testing and reference |
| DataTransformer | `mod/common/DataTransformer.py` | Dict list ↔ pandas DataFrame conversion |
| Filter | `mod/common/Filter.py` | Dict list filtering, sorting, dedup, select, limit |
| Http | `mod/common/Http.py` | HTTP client (GET/POST/PUT/DELETE) with auth support |
| FileIO | `mod/common/FileIO.py` | File read/write (CSV, JSON, Excel, YAML) |
| Notify | `mod/common/Notify.py` | Email (SMTP) + Webhook notifications |
| Ssh | `mod/common/Ssh.py` | SSH remote commands, scripts, SFTP file transfer |
| MultiProcess | `mod/common/MultiProcess.py` | Parallel steps + parallel data chunk processing |
| MySQL | `mod/mysql/MySQL.py` | MySQL database CRUD operations |
| ElasticSearch | `mod/elasticsearch/ElasticSearch.py` | Elasticsearch 8.x CRUD + Search operations |
| Prometheus | `mod/prometheus/Prometheus.py` | Prometheus metrics conversion, push and export |

Each module has its own `README.md` with usage instructions and workflow JSON samples. See the respective `mod/<module>/README.md` for details.

---

## 15. REST API

WorkFlow exposes a Flask REST API for managing and executing workflows as a web service.

### Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `GET` | `/flow` | List all workflows |
| `GET` | `/flow/<name>` | Get workflow info |
| `POST` | `/flow` | Create workflow |
| `PUT` | `/flow/<name>` | Update workflow |
| `DELETE` | `/flow/<name>` | Delete workflow (soft) |
| `POST` | `/flow/<name>/run` | Execute workflow |
| `PUT` | `/flow/<name>/enable` | Enable workflow |
| `PUT` | `/flow/<name>/disable` | Disable workflow |
| `PUT` | `/flow/<name>/rename` | Rename workflow |

### Running the Service

**Production (gunicorn):**

```bash
./bin/service.sh
```

Settings are loaded from `etc/service.conf`:

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Listen port |
| `WORKERS` | `4` | Gunicorn worker processes |
| `PROCESSES` | `4` | Threads per worker |
| `TIMEOUT` | `120` | Worker request timeout (seconds) |
| `LOG_LEVEL` | `info` | Gunicorn log level |
| `ACCESS_LOG` | `-` | Access log path (`-` for stdout) |
| `ERROR_LOG` | `-` | Error log path (`-` for stderr) |

**Development (Flask built-in server):**

```bash
python3 bin/WorkFlow.py --serve
```

---

## 16. Web Frontend

A Django-based web frontend provides a browser interface for managing workflows, users, and system logs.

### Architecture

* **Framework:** Django 4.2 + Bootstrap 5 (CDN) + CodeMirror 5 (CDN)
* **Database:** Shares the same MySQL database via `etc/global.json` (uses `pymysql.install_as_MySQLdb()`)
* **Integration:** Direct DB reads for listing data, Flask REST API calls for mutations
* **Port:** 8000 (default), configurable in `etc/global.json` `web` section

### Django Apps

| App | Description |
| --- | ----------- |
| `dashboard` | Home page with summary cards (workflow counts, user stats, recent audit activity) |
| `accounts` | User, Group, and Role CRUD + login/logout |
| `audit` | Auto-capture audit middleware + filterable audit log page |
| `syslog_viewer` | Workflow syslog viewer with level/date/search filters |
| `workflows` | Workflow list, actions (enable/disable/delete/rename/run), dual-mode editor |

### Workflow Editor

The workflow editor (`/workflows/<name>/edit/`) provides two editing modes:

* **Form mode** — dynamic form with add/remove procedure steps, each with name/mod/method/params fields
* **JSON mode** — CodeMirror editor with syntax highlighting, bracket matching, and validation

Switching between tabs automatically syncs data bidirectionally.

### URL Structure

| URL Pattern | Description |
| ----------- | ----------- |
| `/` | Dashboard |
| `/accounts/login/` | Login |
| `/accounts/logout/` | Logout |
| `/accounts/users/` | User list (create/edit/enable/disable) |
| `/accounts/groups/` | Group list (create/edit/delete) |
| `/accounts/roles/` | Role list (create/edit/delete) |
| `/audit/` | Audit log (filter by user/action/target/date) |
| `/syslog/` | Syslog viewer (filter by level/date/search) |
| `/workflows/` | Workflow list (edit/enable/disable/delete/rename/run) |
| `/workflows/create/` | Create new workflow |
| `/workflows/<name>/edit/` | Edit workflow (form + JSON editor) |

### Running the Web Frontend

**Setup:**

```bash
pip install Django
cd web && python manage.py migrate
python manage.py createsuperuser
```

**Development:**

```bash
./web/service_django.sh
```

Or manually:

```bash
cd web && python manage.py runserver 0.0.0.0:8000
```

**Note:** The Flask REST API backend must be running on port 5000 for workflow mutations to work.

### Configuration

Web frontend settings are in `etc/global.json`:

```json5
web: {
    secret_key: "change-me-in-production",
    debug: true,
    port: 8000,
},
```

---

## 17. Summary

This framework provides:

* Clear and explicit workflow orchestration
* Structured data flow between procedures
* Centralized logging and persistence
* Predictable execution behavior
* A solid foundation for future extensions

The design goal is:

**Clarity first · Correctness always · Complexity last**

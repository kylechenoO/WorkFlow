# Workflow Framework

**Author:** Kyle

**Created:** 20251224

**License:** MIT

**Maintainer:** Kyle

A lightweight Python workflow execution framework based on **JSON-defined flows**, **explicit task dependencies**, and **centralized system services**.

This framework is designed to be:

* Clear and predictable
* Explicit in data flow
* Deterministic in execution order
* Easy to extend
* Production-friendly with strong observability

---

## 1. Overview

A **workflow** is a sequence of tasks executed in a predefined order.

Each task:

* Receives input parameters
* Executes business logic
* Returns a structured result (`dict`)

Tasks exchange data through a shared **execution context**, which is managed entirely by the workflow engine.

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
        |        Task Execution Loop         |
        |------------------------------------|
        |  Resolve parameters                |
        |  Execute task                      |
        |  Store result into context         |
        +------------------------------------+
```

Arrows indicate **control flow and execution order**, not data coupling.

---

## 3. Project Structure

```
WorkFlow/
├── bin/                     # bin path
│   └── WorkFlow.py          # Program entry point
├── lib/                     # lib path
│   ├── Flow.py              # Workflow execution engine
│   ├── Log.py               # Logging lib
│   └── MySQL.py             # MySQL connection & access layer
├── mod/                     # mod path
│   └── common/              # common package path, only for example
│       └── Kt.py            # Example task module
├── etc/                     # config path
│   └── global.json          # Global configuration (JSON)
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
* Trigger workflow execution

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
Execute Flow
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

### 5.1 Task

A **task** represents one execution step in a workflow.

Task method signature:

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

* Store results of completed tasks
* Provide data to downstream tasks
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

* `context[task_name]` stores task output
* Keys starting with `_` are system-reserved
* Tasks should not modify results of other tasks

---

## 6. Flow Definition (JSON)

Flows are defined using **standard JSON** and stored in the database.

### Example Flow JSON

```json
{
  "tasks": [
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

## 7. Data Flow Between Tasks

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

* Tasks do not directly depend on each other
* All dependencies are declared in flow JSON
* The Flow engine resolves dependencies centrally

---

## 8. Parameter Reference Rules

| Syntax      | Meaning                          |
| ----------- | -------------------------------- |
| `@step`     | Reference full task result       |
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

## 9. Task Implementation Example

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
Execute Tasks Sequentially
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
* Task execution errors:

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

## 14. Summary

This framework provides:

* Clear and explicit workflow orchestration
* Structured data flow between tasks
* Centralized logging and persistence
* Predictable execution behavior
* A solid foundation for future extensions

The design goal is:

**Clarity first · Correctness always · Complexity last**

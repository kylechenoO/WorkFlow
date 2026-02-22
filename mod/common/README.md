# Common Modules

Common utility modules for the WorkFlow engine.

---

## Kt

**Module Path:** `common.Kt`

A simple example procedure module for demonstration and testing purposes.

### Methods

#### prt1

Log a message and return a result payload.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| msg | str | Yes | Message to log |

**Returns:**

```python
{
    'status': 0,
    'msg': 'ret from <msg>'
}
```

#### prt2

Log a message and return a result payload.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| msg | str | Yes | Message to log |

**Returns:**

```python
{
    'status': 0,
    'msg': 'ret from <msg>'
}
```

### Sample Workflow JSON

```json
{
  "procedures": [
    {
      "name": "step1",
      "mod": "common.Kt",
      "method": "prt1",
      "params": {
        "msg": "hello world"
      }
    },
    {
      "name": "step2",
      "mod": "common.Kt",
      "method": "prt2",
      "params": {
        "msg": "@step1.msg"
      }
    }
  ]
}
```

---

## DataTransformer

**Module Path:** `common.DataTransformer`

Convert between list of dicts and pandas DataFrame.

### Methods

#### dicts2df

Convert a list of dicts to a pandas DataFrame.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts to convert |

**Returns:**

```python
{
    'status': True,
    'data': <pandas.DataFrame>
}
```

#### df2dicts

Convert a pandas DataFrame to a list of dicts.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | DataFrame | Yes | pandas DataFrame to convert |

**Returns:**

```python
{
    'status': True,
    'data': [list of dicts]
}
```

---

## Filter

**Module Path:** `common.Filter`

Dict list filtering and transformation. Supports filtering by conditions, column selection, sorting, deduplication, and slicing.

### Methods

#### filter

Filter rows by conditions. All conditions are evaluated with AND logic.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts to filter |
| conditions | list | Yes | List of `{"col", "op", "value"}` dicts |

**Supported operators:**

| Operator | Description |
| -------- | ----------- |
| eq | Equal |
| ne | Not equal |
| gt | Greater than |
| gte | Greater than or equal |
| lt | Less than |
| lte | Less than or equal |
| in | Value in list |
| not_in | Value not in list |
| contains | String contains |
| not_contains | String does not contain |

**Returns:**

```python
{
    'status': True,
    'data': [...],
    'count': 5
}
```

---

#### select

Select, rename, or drop columns. Only one operation at a time. Priority: `cols` > `rename` > `drop`.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts |
| cols | list | No | Columns to keep (whitelist) |
| rename | dict | No | Column rename mapping `{old: new}` |
| drop | list | No | Columns to remove |

**Returns:**

```python
{
    'status': True,
    'data': [...],
    'count': 10
}
```

---

#### sort

Sort by one or more columns. Uses pandas for multi-key sort support.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts |
| by | str/list | Yes | Column name(s) to sort by |
| ascending | bool/list | No | Sort direction(s), default `true` |

**Returns:**

```python
{
    'status': True,
    'data': [...],
    'count': 10
}
```

---

#### dedup

Remove duplicate rows. Preserves first occurrence.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts |
| cols | list | No | Columns to check for duplicates (all if omitted) |

**Returns:**

```python
{
    'status': True,
    'data': [...],
    'count': 8
}
```

---

#### limit

Slice rows with offset and count.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts |
| count | int | Yes | Number of rows to return |
| offset | int | No | Starting offset, default `0` |

**Returns:**

```python
{
    'status': True,
    'data': [...],
    'count': 5
}
```

### Sample Workflow JSON

> **Note:** The `data` parameter accepts any list of dicts — it can come from any upstream workflow step (e.g. MySQL query, Elasticsearch search, API call, file read, etc.) via `@step_name.result`.

#### Filter, sort, and limit data from any upstream step

```json
{
  "procedures": [
    {
      "name": "filter_active",
      "mod": "common.Filter",
      "method": "filter",
      "params": {
        "data": "@prev_step.data",
        "conditions": [
          {"col": "status", "op": "eq", "value": "active"},
          {"col": "score", "op": "gte", "value": 80}
        ]
      }
    },
    {
      "name": "sort_result",
      "mod": "common.Filter",
      "method": "sort",
      "params": {
        "data": "@filter_active.data",
        "by": ["score", "name"],
        "ascending": [false, true]
      }
    },
    {
      "name": "top_10",
      "mod": "common.Filter",
      "method": "limit",
      "params": {
        "data": "@sort_result.data",
        "count": 10
      }
    }
  ]
}
```

#### Select columns and deduplicate

```json
{
  "procedures": [
    {
      "name": "pick_cols",
      "mod": "common.Filter",
      "method": "select",
      "params": {
        "data": "@prev_step.data",
        "cols": ["host", "region", "status"]
      }
    },
    {
      "name": "dedup_hosts",
      "mod": "common.Filter",
      "method": "dedup",
      "params": {
        "data": "@pick_cols.data",
        "cols": ["host"]
      }
    }
  ]
}
```

---

## Http

**Module Path:** `common.Http`

HTTP client module. Stateless — no connect/disconnect needed.

**Dependencies:** `requests>=2.32.0` (already included)

### Methods

#### get

Send an HTTP GET request.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| url | str | Yes | — | Target URL |
| headers | dict | No | `{}` | Request headers |
| params | dict | No | `{}` | Query string parameters |
| timeout | int | No | `30` | Request timeout in seconds |
| auth | dict | No | `null` | Basic auth `{"username": "...", "password": "..."}` |
| verify_ssl | bool | No | `true` | SSL certificate verification |

**Returns:**

```python
{
    'status': True,
    'status_code': 200,
    'data': {...},       ## JSON parsed, or text string as fallback
    'headers': {...}
}
```

---

#### post

Send an HTTP POST request.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| url | str | Yes | — | Target URL |
| headers | dict | No | `{}` | Request headers |
| params | dict | No | `{}` | Query string parameters |
| json | dict | No | `null` | JSON request body |
| data | dict | No | `null` | Form data request body |
| timeout | int | No | `30` | Request timeout in seconds |
| auth | dict | No | `null` | Basic auth `{"username": "...", "password": "..."}` |
| verify_ssl | bool | No | `true` | SSL certificate verification |

**Returns:** Same as `get`.

---

#### put

Send an HTTP PUT request.

**cfgs:** Same as `post`.

**Returns:** Same as `get`.

---

#### delete

Send an HTTP DELETE request.

**cfgs:** Same as `get`.

**Returns:** Same as `get`.

### Sample Workflow JSON

#### GET request with basic auth

```json
{
  "procedures": [
    {
      "name": "fetch_data",
      "mod": "common.Http",
      "method": "get",
      "params": {
        "url": "https://api.example.com/v1/users",
        "headers": {
          "Accept": "application/json"
        },
        "auth": {
          "username": "admin",
          "password": "secret"
        },
        "timeout": 60
      }
    }
  ]
}
```

#### POST JSON data from upstream step

```json
{
  "procedures": [
    {
      "name": "send_data",
      "mod": "common.Http",
      "method": "post",
      "params": {
        "url": "https://api.example.com/v1/records",
        "headers": {
          "Content-Type": "application/json",
          "Authorization": "Bearer <token>"
        },
        "json": "@prev_step.data"
      }
    }
  ]
}
```

---

## FileIO

**Module Path:** `common.FileIO`

File read/write module supporting CSV, JSON, Excel (xlsx), YAML, and plain text formats. Auto-detects format from file extension.

**Dependencies:** `openpyxl>=3.1.0`, `PyYAML>=6.0.0`, `pandas>=2.0.0` (all included)

### Methods

#### read

Read a file and return data as a list of dicts (or raw string for txt format).

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| file_path | str | Yes | — | Path to input file |
| format | str | No | auto-detect | `csv`, `json`, `xlsx`, `yaml`, `txt` |
| encoding | str | No | `utf-8` | File encoding |
| sheet | str | No | first sheet | Excel sheet name |

**Supported extensions:** `.csv`, `.json`, `.xlsx`, `.yaml`, `.yml`, `.txt`, `.log`, `.md`, `.conf`, `.ini`, `.cfg`

**Returns:**

```python
## Structured formats (csv, json, xlsx, yaml)
{
    'status': True,
    'data': [list of dicts]
}

## Text formats (txt, log, md, conf, ini, cfg)
{
    'status': True,
    'data': 'raw string content'
}
```

---

#### write

Write data to a file (list of dicts for structured formats, or string/list for txt).

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| file_path | str | Yes | — | Path to output file |
| data | list/str | Yes | — | List of dicts (structured) or string/list (txt) |
| format | str | No | auto-detect | `csv`, `json`, `xlsx`, `yaml`, `txt` |
| encoding | str | No | `utf-8` | File encoding |
| sheet | str | No | `Sheet1` | Excel sheet name |

> **Note:** For txt format, if `data` is a list, each item is written as a line. If `data` is a string, it is written as-is.

**Returns:**

```python
{
    'status': True
}
```

### Sample Workflow JSON

> **Note:** The `data` parameter accepts any list of dicts from any upstream workflow step via `@step_name.result`.

#### Read CSV, filter, and write to Excel

```json
{
  "procedures": [
    {
      "name": "read_csv",
      "mod": "common.FileIO",
      "method": "read",
      "params": {
        "file_path": "/data/input/servers.csv"
      }
    },
    {
      "name": "filter_active",
      "mod": "common.Filter",
      "method": "filter",
      "params": {
        "data": "@read_csv.data",
        "conditions": [
          {"col": "status", "op": "eq", "value": "active"}
        ]
      }
    },
    {
      "name": "write_xlsx",
      "mod": "common.FileIO",
      "method": "write",
      "params": {
        "file_path": "/data/output/active_servers.xlsx",
        "data": "@filter_active.data",
        "sheet": "ActiveServers"
      }
    }
  ]
}
```

#### Write upstream data to JSON

```json
{
  "procedures": [
    {
      "name": "save_json",
      "mod": "common.FileIO",
      "method": "write",
      "params": {
        "file_path": "/data/output/report.json",
        "data": "@prev_step.data"
      }
    }
  ]
}
```

#### Read and write text files

```json
{
  "procedures": [
    {
      "name": "read_config",
      "mod": "common.FileIO",
      "method": "read",
      "params": {
        "file_path": "/etc/app/config.conf"
      }
    },
    {
      "name": "write_log",
      "mod": "common.FileIO",
      "method": "write",
      "params": {
        "file_path": "/data/output/report.txt",
        "data": "@read_config.data"
      }
    }
  ]
}
```

---

## Notify

**Module Path:** `common.Notify`

Email and webhook notification module. Stateless — no connect/disconnect needed.

**Dependencies:** `smtplib` (stdlib), `requests>=2.32.0` (already included)

### Methods

#### email

Send an email via SMTP.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| smtp_host | str | Yes | — | SMTP server hostname |
| smtp_port | int | Yes | — | SMTP server port |
| username | str | No | `null` | SMTP login username |
| password | str | No | `null` | SMTP login password |
| from_addr | str | Yes | — | Sender email address |
| to_addrs | list | Yes | — | Recipient email addresses |
| subject | str | Yes | — | Email subject |
| body | str | Yes | — | Email body content |
| body_type | str | No | `plain` | Body MIME type: `plain` or `html` |
| cc | list | No | `[]` | CC email addresses |
| use_tls | bool | No | `true` | Use STARTTLS |

**Returns:**

```python
{
    'status': True
}
```

---

#### webhook

Send a webhook notification to any URL (Slack, Teams, DingTalk, etc.).

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| url | str | Yes | — | Webhook URL |
| method | str | No | `POST` | HTTP method |
| headers | dict | No | `{}` | Request headers |
| body | dict | Yes | — | JSON request body |
| timeout | int | No | `30` | Request timeout in seconds |

**Returns:**

```python
{
    'status': True
}
```

### Sample Workflow JSON

#### Send email notification after workflow step

```json
{
  "procedures": [
    {
      "name": "send_email",
      "mod": "common.Notify",
      "method": "email",
      "params": {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "username": "alerts@example.com",
        "password": "smtp_password",
        "from_addr": "alerts@example.com",
        "to_addrs": ["admin@example.com", "ops@example.com"],
        "subject": "Workflow Report",
        "body": "<h1>Report Ready</h1><p>Processing completed.</p>",
        "body_type": "html",
        "use_tls": true
      }
    }
  ]
}
```

#### Send Slack webhook notification

```json
{
  "procedures": [
    {
      "name": "slack_notify",
      "mod": "common.Notify",
      "method": "webhook",
      "params": {
        "url": "https://hooks.slack.com/services/T00/B00/xxxx",
        "body": {
          "text": "Workflow completed successfully",
          "channel": "#ops-alerts"
        }
      }
    }
  ]
}
```

---

## Ssh

**Module Path:** `common.Ssh`

SSH remote command execution and SFTP file transfer. Stateful — uses `connect` / `disconnect` like MySQL and Elasticsearch modules.

**Dependencies:** `paramiko>=3.4.0` (already included)

### Methods

#### connect

Establish an SSH connection to a remote server.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| host | str | Yes | — | Remote server hostname or IP |
| port | int | No | `22` | SSH port |
| username | str | Yes | — | SSH username |
| password | str | No | `null` | SSH password |
| key_file | str | No | `null` | Path to private key file |
| timeout | int | No | `30` | Connection timeout in seconds |

**Returns:**

```python
{
    'status': True
}
```

---

#### disconnect

Close SSH and SFTP connections. Safe to call multiple times.

**cfgs:** None required.

**Returns:**

```python
{
    'status': True
}
```

---

#### run

Execute a remote shell command.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| cmd | str | Yes | — | Shell command to execute |
| timeout | int | No | `30` | Command timeout in seconds |

**Returns:**

```python
{
    'status': True,          ## True if exit_code == 0
    'exit_code': 0,
    'stdout': '...',
    'stderr': '...'
}
```

---

#### run_script

Run a local script on a remote server without uploading. Reads local script content and feeds it to the remote interpreter via stdin.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| script_path | str | Yes | — | Local path to script file |
| interpreter | str | No | `bash` | Remote interpreter (`bash`, `python3`, `sh`, etc.) |
| args | str | No | `""` | Arguments to pass to the script |
| timeout | int | No | `30` | Command timeout in seconds |

**Returns:**

```python
{
    'status': True,          ## True if exit_code == 0
    'exit_code': 0,
    'stdout': '...',
    'stderr': '...'
}
```

---

#### upload

Upload a local file to the remote server via SFTP.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| local_path | str | Yes | Local file path |
| remote_path | str | Yes | Remote destination path |

**Returns:**

```python
{
    'status': True
}
```

---

#### download

Download a remote file to the local machine via SFTP.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| remote_path | str | Yes | Remote file path |
| local_path | str | Yes | Local destination path |

**Returns:**

```python
{
    'status': True
}
```

### Sample Workflow JSON

#### Run remote command and download log file

```json
{
  "procedures": [
    {
      "name": "ssh_connect",
      "mod": "common.Ssh",
      "method": "connect",
      "params": {
        "host": "192.168.1.100",
        "username": "deploy",
        "key_file": "/home/deploy/.ssh/id_rsa",
        "timeout": 10
      }
    },
    {
      "name": "check_disk",
      "mod": "common.Ssh",
      "method": "run",
      "params": {
        "cmd": "df -h",
        "timeout": 10
      }
    },
    {
      "name": "get_log",
      "mod": "common.Ssh",
      "method": "download",
      "params": {
        "remote_path": "/var/log/app/error.log",
        "local_path": "/data/logs/remote_error.log"
      }
    },
    {
      "name": "ssh_close",
      "mod": "common.Ssh",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

#### Run local script on remote server

```json
{
  "procedures": [
    {
      "name": "ssh_connect",
      "mod": "common.Ssh",
      "method": "connect",
      "params": {
        "host": "192.168.1.100",
        "username": "deploy",
        "password": "deploy_pass"
      }
    },
    {
      "name": "run_deploy",
      "mod": "common.Ssh",
      "method": "run_script",
      "params": {
        "script_path": "/opt/scripts/deploy.sh",
        "interpreter": "bash",
        "args": "--env production",
        "timeout": 120
      }
    },
    {
      "name": "run_python",
      "mod": "common.Ssh",
      "method": "run_script",
      "params": {
        "script_path": "/opt/scripts/healthcheck.py",
        "interpreter": "python3",
        "timeout": 30
      }
    },
    {
      "name": "ssh_close",
      "mod": "common.Ssh",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

---

## MultiProcess

**Module Path:** `common.MultiProcess`

Parallel execution module using Python multiprocessing. Supports running multiple independent workflow steps concurrently, or splitting data into chunks and processing in parallel.

**Dependencies:** `multiprocessing` (stdlib)

**Caveat:** Workers run in separate processes with fresh module instances. Stateful connections (from `connect()`) are lost. Best for stateless/self-contained operations.

### Methods

#### parallel_steps

Execute multiple independent workflow steps in parallel. Each step runs in its own process with a fresh module instance.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| steps | list | Yes | — | List of step dicts, each with `name`, `mod`, `method`, `params` |
| processes | int | No | `len(steps)` | Number of worker processes |

**Step dict format:**

```python
{
    "name": "step_a",
    "mod": "common.Http",
    "method": "get",
    "params": {"url": "https://api.example.com/data"}
}
```

**Returns:**

```python
{
    'status': True,
    'results': {
        'step_a': {...},
        'step_b': {...}
    },
    'errors': []
}
```

---

#### parallel_data

Split data into chunks and process each chunk in parallel using the same module method. Results are merged into a single flat list.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| data | list | Yes | — | List of dicts to split |
| data_key | str | Yes | — | Key name in params where each chunk is placed |
| mod | str | Yes | — | Target module path |
| method | str | Yes | — | Target method name |
| params | dict | No | `{}` | Additional params for target method |
| processes | int | No | `4` | Number of workers / chunks |

**Returns:**

```python
{
    'status': True,
    'data': [...],       ## flat merged list from all chunks
    'errors': []
}
```

### Sample Workflow JSON

> **Note:** The `data` and `steps` parameters accept any list from any upstream workflow step via `@step_name.result`.

#### Run multiple HTTP requests in parallel

```json
{
  "procedures": [
    {
      "name": "parallel_fetch",
      "mod": "common.MultiProcess",
      "method": "parallel_steps",
      "params": {
        "steps": [
          {
            "name": "api_users",
            "mod": "common.Http",
            "method": "get",
            "params": {"url": "https://api.example.com/users"}
          },
          {
            "name": "api_orders",
            "mod": "common.Http",
            "method": "get",
            "params": {"url": "https://api.example.com/orders"}
          },
          {
            "name": "api_products",
            "mod": "common.Http",
            "method": "get",
            "params": {"url": "https://api.example.com/products"}
          }
        ],
        "processes": 3
      }
    }
  ]
}
```

#### Process large dataset in parallel chunks

```json
{
  "procedures": [
    {
      "name": "parallel_process",
      "mod": "common.MultiProcess",
      "method": "parallel_data",
      "params": {
        "data": "@prev_step.data",
        "data_key": "records",
        "mod": "common.Filter",
        "method": "filter",
        "params": {
          "conditions": [
            {"col": "status", "op": "eq", "value": "active"}
          ]
        },
        "processes": 4
      }
    }
  ]
}
```

---

## Bash

**Module Path:** `common.Bash`

Local shell command executor. Stateless — no connect/disconnect needed.

### Methods

#### run

Execute a shell command and return stdout, stderr, and exit code.

**cfgs:**

| Parameter | Type | Required | Default | Description |
| --------- | ---- | -------- | ------- | ----------- |
| cmd | str/list | Yes | — | Command to execute. String for shell commands (pipes, redirects). List for safe argument passing with `shell=false`. |
| cwd | str | No | `/` | Working directory |
| env | dict | No | `null` | Environment variables merged with current environment |
| timeout | int | No | `60` | Timeout in seconds |
| shell | bool | No | `true` | Use shell interpretation. Set to `false` when passing cmd as a list with untrusted arguments. |

**Returns:**

```python
{
    'status': True,          ## True if exit_code == 0
    'exit_code': 0,
    'stdout': '...',
    'stderr': '...'
}
```

### Sample Workflow JSON

#### Run a shell command

```json
{
  "procedures": [
    {
      "name": "check_disk",
      "mod": "common.Bash",
      "method": "run",
      "params": {
        "cmd": "df -h",
        "cwd": "/",
        "timeout": 30
      }
    }
  ]
}
```

#### Run with custom environment variables

```json
{
  "procedures": [
    {
      "name": "run_with_env",
      "mod": "common.Bash",
      "method": "run",
      "params": {
        "cmd": "echo $MY_VAR",
        "env": {"MY_VAR": "hello_world"}
      }
    }
  ]
}
```

#### Safe argument passing (shell=false)

```json
{
  "procedures": [
    {
      "name": "safe_ls",
      "mod": "common.Bash",
      "method": "run",
      "params": {
        "cmd": ["ls", "-la", "/tmp"],
        "shell": false
      }
    }
  ]
}
```

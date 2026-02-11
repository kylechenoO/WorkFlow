# MySQL Module

**Module Path:** `mysql.MySQL`

MySQL database procedure module for CRUD operations within workflows.

**Dependencies:** `PyMySQL`, `pandas`

---

## Methods

### connect

Establish a connection to the MySQL database.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| host | str | Yes | MySQL server hostname or IP |
| port | str | Yes | MySQL server port |
| username | str | Yes | Database username |
| password | str | Yes | Database password |
| database | str | Yes | Database name |
| charset | str | Yes | Character encoding (e.g. `utf8mb4`) |

**Returns:**

```python
{
    'status': True
}
```

---

### disconnect

Close the active cursor and database connection.

**cfgs:** None required

**Returns:**

```python
{
    'status': True
}
```

---

### showDatabases

Retrieve all databases available on the MySQL server.

**cfgs:** None required

**Returns:**

```python
{
    'status': True,
    'databases': ['db1', 'db2', ...]
}
```

---

### query

Execute a SELECT query and return results as a list of dicts.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| sql | str | Yes | SQL query string |

**Returns:**

```python
{
    'status': True,
    'result': [
        {'col1': 'val1', 'col2': 'val2'},
        {'col1': 'val3', 'col2': 'val4'}
    ]
}
```

---

### insert

Insert multiple rows into a table in a single SQL statement.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts to insert |
| table | str | Yes | Target table name |
| cols | list | Yes | Column names to insert |

**Returns:**

```python
{
    'status': True
}
```

---

### insertWithUK

Insert or update records using ON DUPLICATE KEY UPDATE. Processes data in batches.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts to insert |
| table | str | Yes | Target table name |
| cols | list | Yes | Column names to insert |
| uniq_key | str | Yes | Unique key column name |
| batch_size | int | Yes | Number of rows per batch |

**Returns:**

```python
{
    'status': True
}
```

---

### update

Update records in a table using a WHERE clause.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | dict | Yes | Data dict with update values |
| table | str | Yes | Target table name |
| cols | list | Yes | Column names to update |
| where | str | Yes | SQL WHERE condition |

**Returns:**

```python
{
    'status': True
}
```

---

## Sample Workflow JSON

> **Note:** The `data` parameter in insert/update methods accepts any list of dicts — it can come from any upstream workflow step (e.g. MySQL query, Elasticsearch search, API call, file read, etc.) via `@step_name.result`.

### Query and insert results to another table

```json
{
  "procedures": [
    {
      "name": "db_connect",
      "mod": "mysql.MySQL",
      "method": "connect",
      "params": {
        "host": "172.18.0.7",
        "port": "3306",
        "username": "root",
        "password": "pass",
        "database": "mydb",
        "charset": "utf8mb4"
      }
    },
    {
      "name": "fetch_users",
      "mod": "mysql.MySQL",
      "method": "query",
      "params": {
        "sql": "SELECT id, name, email FROM users WHERE active = 1"
      }
    },
    {
      "name": "insert_report",
      "mod": "mysql.MySQL",
      "method": "insert",
      "params": {
        "data": "@fetch_users.result",
        "table": "user_report",
        "cols": ["id", "name", "email"]
      }
    },
    {
      "name": "db_close",
      "mod": "mysql.MySQL",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `db_connect` establishes a MySQL connection
2. `fetch_users` runs a SELECT query and returns result as list of dicts
3. `insert_report` takes `@fetch_users.result` (the query result list) and inserts into `user_report` table
4. `db_close` closes the connection

### Upsert with unique key

```json
{
  "procedures": [
    {
      "name": "db_connect",
      "mod": "mysql.MySQL",
      "method": "connect",
      "params": {
        "host": "172.18.0.7",
        "port": "3306",
        "username": "root",
        "password": "pass",
        "database": "mydb",
        "charset": "utf8mb4"
      }
    },
    {
      "name": "upsert_data",
      "mod": "mysql.MySQL",
      "method": "insertWithUK",
      "params": {
        "data": "@prev_step.result",
        "table": "daily_metrics",
        "cols": ["metric_date", "metric_name", "metric_value"],
        "uniq_key": "metric_date",
        "batch_size": 500
      }
    },
    {
      "name": "db_close",
      "mod": "mysql.MySQL",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `db_connect` establishes a MySQL connection
2. `upsert_data` inserts data from a previous step into `daily_metrics`, updating existing rows if `metric_date` already exists
3. `db_close` closes the connection

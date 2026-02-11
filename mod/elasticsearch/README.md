# ElasticSearch Module

**Module Path:** `elasticsearch.ElasticSearch`

Elasticsearch 8.x procedure module for CRUD and search operations within workflows.

**Dependencies:** `elasticsearch>=8.0.0,<9.0.0`

---

## Methods

### connect

Establish a connection to an Elasticsearch cluster.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| hosts | list | Yes | List of ES host URLs (e.g. `["https://localhost:9200"]`) |
| basic_auth | dict | No | Dict with `username` and `password` keys |
| api_key | str | No | Elasticsearch API key |
| verify_certs | bool | No | Enable SSL certificate verification (default: `False`) |
| ca_certs | str | No | File path to CA certificate bundle |

**Returns:**

```python
{
    'status': True
}
```

---

### disconnect

Close the Elasticsearch client connection.

**cfgs:** None required

**Returns:**

```python
{
    'status': True
}
```

---

### health

Check if the Elasticsearch cluster is healthy.

**cfgs:** None required

**Returns:**

```python
{
    'status': True,
    'result': {
        'cluster_name': 'my-cluster',
        'status': 'green',
        'number_of_nodes': 3,
        ...
    }
}
```

---

### search

Execute a search query on an index.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| query | dict | Yes | Elasticsearch query DSL |
| size | int | No | Number of results (default: `10`) |
| from_ | int | No | Offset for pagination (default: `0`) |
| sort | list | No | Sort criteria |

**Returns:**

```python
{
    'status': True,
    'total': 42,
    'result': [
        {'_id': '1', '_source': {...}},
        {'_id': '2', '_source': {...}}
    ]
}
```

---

### get

Retrieve a single document by ID.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| id | str | Yes | Document ID |

**Returns:**

```python
{
    'status': True,
    'result': {'_id': '1', '_source': {...}}
}
```

---

### index

Index (create or overwrite) a document. If `id` is provided and exists, the document is overwritten.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| document | dict | Yes | Document body |
| id | str | No | Document ID (auto-generated if omitted) |

**Returns:**

```python
{
    'status': True,
    'result': {'_id': '1', 'result': 'created'}
}
```

---

### create

Create a document with a specified ID. Skips if the ID already exists.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| document | dict | Yes | Document body |
| id | str | Yes | Document ID |

**Returns:**

```python
{
    'status': True,
    'result': {'_id': '1', 'result': 'created'}
}
```

---

### bulk

Bulk create documents. Uses `_op_type: create` to skip existing IDs.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| data | list | Yes | List of dicts to index |
| id | str | Yes | Field name in each dict to use as document `_id` |

**Returns:**

```python
{
    'status': True,
    'success': 100,
    'errors': []
}
```

---

### update

Update a document by ID.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| id | str | Yes | Document ID |
| doc | dict | Yes | Partial document with fields to update |

**Returns:**

```python
{
    'status': True,
    'result': {'_id': '1', 'result': 'updated'}
}
```

---

### delete

Delete a document by ID.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Target index name |
| id | str | Yes | Document ID |

**Returns:**

```python
{
    'status': True,
    'result': {'_id': '1', 'result': 'deleted'}
}
```

---

### createIndex

Create a new Elasticsearch index with optional mappings and settings.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Index name to create |
| mappings | dict | No | Index field mappings |
| settings | dict | No | Index settings |

**Returns:**

```python
{
    'status': True,
    'result': {'acknowledged': True}
}
```

---

### deleteIndex

Delete an Elasticsearch index.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| index | str | Yes | Index name to delete |

**Returns:**

```python
{
    'status': True,
    'result': {'acknowledged': True}
}
```

---

## Sample Workflow JSON

> **Note:** The `data` and `document` parameters accept any dict or list of dicts — they can come from any upstream workflow step (e.g. MySQL query, API call, file read, etc.) via `@step_name.result`.

### Bulk index data from any upstream step

Data source can be any previous workflow step that returns a list of dicts (e.g. MySQL query, API call, file read, etc.).

```json
{
  "procedures": [
    {
      "name": "es_connect",
      "mod": "elasticsearch.ElasticSearch",
      "method": "connect",
      "params": {
        "hosts": ["https://localhost:9200"],
        "basic_auth": {
          "username": "elastic",
          "password": "changeme"
        },
        "verify_certs": false
      }
    },
    {
      "name": "es_health",
      "mod": "elasticsearch.ElasticSearch",
      "method": "health",
      "params": {}
    },
    {
      "name": "es_bulk",
      "mod": "elasticsearch.ElasticSearch",
      "method": "bulk",
      "params": {
        "index": "users",
        "data": "@prev_step.result",
        "id": "id"
      }
    },
    {
      "name": "es_close",
      "mod": "elasticsearch.ElasticSearch",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `es_connect` connects to Elasticsearch with basic auth
2. `es_health` verifies the cluster is healthy
3. `es_bulk` takes `@prev_step.result` (list of dicts from any upstream step) and bulk indexes all documents into the `users` index, using the `id` field as document `_id`
4. `es_close` closes the Elasticsearch connection

### Search and create index

```json
{
  "procedures": [
    {
      "name": "es_connect",
      "mod": "elasticsearch.ElasticSearch",
      "method": "connect",
      "params": {
        "hosts": ["https://localhost:9200"],
        "api_key": "my-api-key"
      }
    },
    {
      "name": "create_idx",
      "mod": "elasticsearch.ElasticSearch",
      "method": "createIndex",
      "params": {
        "index": "logs-2025",
        "mappings": {
          "properties": {
            "timestamp": {"type": "date"},
            "level": {"type": "keyword"},
            "message": {"type": "text"}
          }
        },
        "settings": {
          "number_of_shards": 1,
          "number_of_replicas": 1
        }
      }
    },
    {
      "name": "search_logs",
      "mod": "elasticsearch.ElasticSearch",
      "method": "search",
      "params": {
        "index": "logs-2025",
        "query": {
          "bool": {
            "must": [
              {"match": {"level": "error"}}
            ]
          }
        },
        "size": 50,
        "sort": [{"timestamp": "desc"}]
      }
    },
    {
      "name": "es_close",
      "mod": "elasticsearch.ElasticSearch",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `es_connect` connects using API key authentication
2. `create_idx` creates a new index with field mappings and settings
3. `search_logs` searches for error-level logs, sorted by timestamp descending, returns up to 50 results
4. `es_close` closes the connection

### Connect with SSL certificate

```json
{
  "procedures": [
    {
      "name": "es_connect",
      "mod": "elasticsearch.ElasticSearch",
      "method": "connect",
      "params": {
        "hosts": ["https://es-prod.example.com:9200"],
        "basic_auth": {
          "username": "elastic",
          "password": "secret"
        },
        "verify_certs": true,
        "ca_certs": "/etc/ssl/certs/es-ca.pem"
      }
    }
  ]
}
```

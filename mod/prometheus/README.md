# Prometheus Module

**Module Path:** `prometheus.Prometheus`

Prometheus procedure module for converting dict list data to Prometheus metrics, with support for Pushgateway and file export.

**Dependencies:** `prometheus_client>=0.20.0`

---

## Methods

### connect

Create a fresh Prometheus CollectorRegistry and optionally store Pushgateway URL.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| gateway | str | No | Pushgateway URL (e.g. `"http://localhost:9091"`) |
| job | str | Yes | Prometheus job label |

**Returns:**

```python
{
    'status': True
}
```

---

### disconnect

Clear the Prometheus registry and gateway.

**cfgs:** None required

**Returns:**

```python
{
    'status': True
}
```

---

### dicts2prom

Convert a list of dicts to Prometheus metrics. Supports gauge, counter, histogram, and summary types.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| data | list | Yes | List of dicts from upstream workflow step |
| metric_name | str | Yes | Prometheus metric name |
| metric_desc | str | Yes | Prometheus metric description |
| metric_type | str | Yes | One of: `gauge`, `counter`, `histogram`, `summary` |
| value_col | str | Yes | Field name in each dict to use as metric value |
| label_cols | list | No | Field names from dict to use as dynamic labels |
| static_labels | dict | No | Fixed labels applied to all rows |
| buckets | list | No | Histogram bucket boundaries (only for `histogram` type) |

**Metric type behavior:**

| Type | Method | Description |
| ---- | ------ | ----------- |
| gauge | `.set(value)` | Set a value that can go up or down |
| counter | `.inc(value)` | Increment by value |
| histogram | `.observe(value)` | Observe a value into buckets |
| summary | `.observe(value)` | Observe a value for quantile calculation |

**Returns:**

```python
{
    'status': True,
    'metrics_count': 100
}
```

---

### push

Push all registered metrics to Prometheus Pushgateway. Requires `gateway` to be set in `connect`.

**cfgs:** None required

**Returns:**

```python
{
    'status': True
}
```

---

### write

Write all registered metrics to a text file in Prometheus exposition format.

**cfgs:**

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| file_path | str | Yes | Output file path (e.g. `"/tmp/metrics.prom"`) |

**Returns:**

```python
{
    'status': True
}
```

---

## Sample Workflow JSON

> **Note:** The `data` parameter accepts any list of dicts — it can come from any upstream workflow step (e.g. MySQL query, Elasticsearch search, API call, file read, etc.) via `@step_name.result`.

### Convert dict list to gauge metrics and push to Pushgateway

Data source can be any previous workflow step that returns a list of dicts (e.g. MySQL query, API call, file read, etc.).

Assume `@prev_step.result` returns data like:
```python
[
    {"host": "web01", "cpu_usage": 75.2, "mem_usage": 62.1},
    {"host": "web02", "cpu_usage": 42.8, "mem_usage": 55.3}
]
```

```json
{
  "procedures": [
    {
      "name": "prom_connect",
      "mod": "prometheus.Prometheus",
      "method": "connect",
      "params": {
        "gateway": "http://localhost:9091",
        "job": "server_monitor"
      }
    },
    {
      "name": "convert_cpu",
      "mod": "prometheus.Prometheus",
      "method": "dicts2prom",
      "params": {
        "data": "@prev_step.result",
        "metric_name": "server_cpu_usage",
        "metric_desc": "CPU usage percentage per server",
        "metric_type": "gauge",
        "value_col": "cpu_usage",
        "label_cols": ["host"],
        "static_labels": {
          "env": "production",
          "team": "infra"
        }
      }
    },
    {
      "name": "convert_mem",
      "mod": "prometheus.Prometheus",
      "method": "dicts2prom",
      "params": {
        "data": "@prev_step.result",
        "metric_name": "server_mem_usage",
        "metric_desc": "Memory usage percentage per server",
        "metric_type": "gauge",
        "value_col": "mem_usage",
        "label_cols": ["host"],
        "static_labels": {
          "env": "production",
          "team": "infra"
        }
      }
    },
    {
      "name": "push_metrics",
      "mod": "prometheus.Prometheus",
      "method": "push",
      "params": {}
    },
    {
      "name": "prom_close",
      "mod": "prometheus.Prometheus",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `prom_connect` creates a registry and stores the Pushgateway URL with job name `server_monitor`
2. `convert_cpu` converts CPU data from `@prev_step.result` to gauge metrics with dynamic label `host` and static labels `env`/`team`
3. `convert_mem` converts memory data from `@prev_step.result` to gauge metrics with the same labels
4. `push_metrics` pushes all metrics to Pushgateway
5. `prom_close` clears the registry

### Write metrics to file (for node_exporter textfile collector)

```json
{
  "procedures": [
    {
      "name": "prom_connect",
      "mod": "prometheus.Prometheus",
      "method": "connect",
      "params": {
        "job": "batch_job"
      }
    },
    {
      "name": "convert_histogram",
      "mod": "prometheus.Prometheus",
      "method": "dicts2prom",
      "params": {
        "data": "@prev_step.result",
        "metric_name": "request_duration_seconds",
        "metric_desc": "HTTP request duration in seconds",
        "metric_type": "histogram",
        "value_col": "duration",
        "label_cols": ["method", "endpoint"],
        "buckets": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
      }
    },
    {
      "name": "write_file",
      "mod": "prometheus.Prometheus",
      "method": "write",
      "params": {
        "file_path": "/var/lib/node_exporter/textfile/batch_metrics.prom"
      }
    },
    {
      "name": "prom_close",
      "mod": "prometheus.Prometheus",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `prom_connect` creates a registry (no gateway needed for file export)
2. `convert_histogram` converts data from a previous step to histogram metrics with custom buckets, using `method` and `endpoint` as dynamic labels
3. `write_file` writes all metrics to a `.prom` file in Prometheus exposition format, ready for `node_exporter` textfile collector
4. `prom_close` clears the registry

### Counter metrics with static labels only

```json
{
  "procedures": [
    {
      "name": "prom_connect",
      "mod": "prometheus.Prometheus",
      "method": "connect",
      "params": {
        "gateway": "http://pushgateway:9091",
        "job": "error_counter"
      }
    },
    {
      "name": "convert_errors",
      "mod": "prometheus.Prometheus",
      "method": "dicts2prom",
      "params": {
        "data": "@error_query.result",
        "metric_name": "app_errors_total",
        "metric_desc": "Total application errors",
        "metric_type": "counter",
        "value_col": "error_count",
        "static_labels": {
          "app": "myapp",
          "env": "staging"
        }
      }
    },
    {
      "name": "push_errors",
      "mod": "prometheus.Prometheus",
      "method": "push",
      "params": {}
    },
    {
      "name": "prom_close",
      "mod": "prometheus.Prometheus",
      "method": "disconnect",
      "params": {}
    }
  ]
}
```

**Execution flow:**

1. `prom_connect` creates registry with Pushgateway URL
2. `convert_errors` converts error count data to counter metrics using only static labels (no dynamic labels from dict fields)
3. `push_errors` pushes to Pushgateway
4. `prom_close` clears the registry

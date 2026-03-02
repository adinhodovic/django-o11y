# Demo images

Local Grafana base URL: `http://localhost:3000`

## Screenshot placeholders

### Metrics

[![Metrics dashboard placeholder](images/demo/metrics-dashboard.png)](http://localhost:3000/d/django-overview-jkwq/django-overview)

### Traces

[![Traces dashboard placeholder](images/demo/traces-dashboard.png)](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22tempo%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)

### Logs

[![Logs dashboard placeholder](images/demo/logs-dashboard.png)](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22loki%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)

### Profiles

[![Profiles dashboard placeholder](images/demo/profiles-dashboard.png)](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22pyroscope%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)

## Grafana drilldowns

- Metrics Explore (Prometheus): [Open](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22prometheus%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)
- Traces Explore (Tempo): [Open](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22tempo%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)
- Logs Explore (Loki): [Open](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22loki%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)
- Profiles Explore (Pyroscope): [Open](http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22%3A%20%22pyroscope%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%7D%5D%7D)

## Imported dashboards

These are imported from Grafana.com when you run `o11y stack start`.

> These screenshots are from the library's own local test project (`tests/`): a minimal Django app that runs one Celery task every 5 seconds. Traffic is low and most panels will be sparse or empty.

- Celery / Tasks / Overview
  - Local: [Open](http://localhost:3000/d/celery-tasks-overview-32s3/celery-tasks-overview)
  - Grafana.com: [17509](https://grafana.com/grafana/dashboards/17509-celery-tasks-overview/)
  - [![Celery Tasks Overview](images/demo/celery-tasks-overview.png)](http://localhost:3000/d/celery-tasks-overview-32s3/celery-tasks-overview)
- Celery / Tasks / By Task
  - Local: [Open](http://localhost:3000/d/celery-tasks-by-task-32s3/celery-tasks-by-task)
  - Grafana.com: [17508](https://grafana.com/grafana/dashboards/17508-celery-tasks-by-task/)
  - [![Celery Tasks By Task](images/demo/celery-tasks-by-task.png)](http://localhost:3000/d/celery-tasks-by-task-32s3/celery-tasks-by-task)
- Django / Overview
  - Local: [Open](http://localhost:3000/d/django-overview-jkwq/django-overview)
  - Grafana.com: [17617](https://grafana.com/grafana/dashboards/17617-django-overview/)
  - [![Django Overview](images/demo/django-overview.png)](http://localhost:3000/d/django-overview-jkwq/django-overview)
- Django / Requests / Overview
  - Local: [Open](http://localhost:3000/d/django-requests-jkwq/django-requests-overview)
  - Grafana.com: [17616](https://grafana.com/grafana/dashboards/17616-django-requests-overview/)
  - [![Django Requests Overview](images/demo/django-requests-overview.png)](http://localhost:3000/d/django-requests-jkwq/django-requests-overview)
- Django / Requests / By View
  - Local: [Open](http://localhost:3000/d/django-requests-by-view-jkwq/django-requests-by-view)
  - Grafana.com: [17613](https://grafana.com/grafana/dashboards/17613-django-requests-by-view/)
  - [![Django Requests By View](images/demo/django-requests-by-view.png)](http://localhost:3000/d/django-requests-by-view-jkwq/django-requests-by-view)
- Django / Models / Overview
  - Local: [Open](http://localhost:3000/d/django-model-overview-jkwq/django-models-overview)
  - Grafana.com: [24933](https://grafana.com/grafana/dashboards/24933-django-models-overview/)
  - [![Django Models Overview](images/demo/django-models-overview.png)](http://localhost:3000/d/django-model-overview-jkwq/django-models-overview)

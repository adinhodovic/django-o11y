#!/bin/sh
# Import Grafana dashboards from Grafana.com by ID

set -e

GRAFANA_URL="${GRAFANA_URL:-http://grafana:3000}"

# Dashboard IDs to import (gnetId:name)
DASHBOARDS="
17509:celery-tasks-overview
17508:celery-tasks-by-task
17617:django-overview
17616:django-requests-overview
17613:django-requests-by-view
24933:django-models-overview
"

echo "Waiting for Grafana to be ready..."
until curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1; do
	sleep 2
done

echo "Grafana is ready. Importing dashboards..."

echo "$DASHBOARDS" | while IFS=: read -r gnet_id name; do
	[ -z "$gnet_id" ] && continue

	echo "Importing dashboard: ${name} (gnetId: ${gnet_id})"

	# Download dashboard JSON from Grafana.com
	dashboard_json=$(curl -sf "https://grafana.com/api/dashboards/${gnet_id}/revisions/latest/download")

	# Prepare import payload
	import_payload=$(echo "$dashboard_json" | jq \
		'{
      dashboard: .,
      overwrite: true,
      inputs: [
        {
          name: "DS_PROMETHEUS",
          pluginId: "prometheus",
          type: "datasource",
          value: "Prometheus"
        }
      ],
      folderId: 0
    }')

	# Import to Grafana
	response=$(curl -sf -X POST \
		-H "Content-Type: application/json" \
		-d "$import_payload" \
		"${GRAFANA_URL}/api/dashboards/import" 2>&1) || {
		echo "✗ Failed to import ${name}"
		continue
	}

	echo "✓ Imported ${name}"
done

echo "All dashboards imported successfully!"

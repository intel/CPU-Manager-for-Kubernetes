#!/bin/bash
curl --header "Content-Type:application/json-patch+json" \
        --request PATCH \
        --data '[{"op": "remove", "path": "/status/capacity/pod.alpha.kubernetes.io~1opaque-int-resource-kcm"}]' \
        http://localhost:8080/api/v1/nodes/$1/status

"""Example metrics server to expose in-process audit metrics via Prometheus.

Run this while the service is running to expose metrics at http://localhost:8000/metrics

This is intentionally a small example - in a real deployment you'd wire this into your
application startup and proper lifecycle management.
"""
import time
from prometheus_client import start_http_server

from core import audit


def main(host: str = '0.0.0.0', port: int = 8000):
    # Try to enable Prometheus metrics in the audit module
    enabled = audit.enable_prometheus_metrics()
    if not enabled:
        print('prometheus_client is not available or metrics could not be enabled')
    else:
        print('Prometheus audit metrics enabled')

    # Start the simple HTTP server that serves /metrics
    start_http_server(port, addr=host)
    print(f'Metrics server running at http://{host}:{port}/metrics')

    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Metrics server stopped')


if __name__ == '__main__':
    main()

from __future__ import annotations

from prometheus_client import Counter, start_http_server

SCHEDULER_TICKS = Counter("scheduler_ticks_total", "Scheduler ticks", ["status"])
SCHEDULER_ERRORS = Counter("scheduler_errors_total", "Scheduler tick errors", ["error_type"])
REMINDERS_SENT = Counter("reminders_sent_total", "Reminders sent", ["type"])
BROADCAST_SENT = Counter("broadcast_sent_total", "Broadcast messages sent", ["status"])
ERROR_HANDLER_ERRORS = Counter("error_handler_errors_total", "Errors caught by global handler", ["error_type"])
WEBHOOK_REQUESTS = Counter("webhook_requests_total", "Webhook requests", ["status"])


def start_metrics(port: int = 9090) -> None:
    start_http_server(port)

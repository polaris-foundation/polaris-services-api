from typing import Any, Dict

import kombu_batteries_included
from she_logging import logger


def audit_message(event_type: str, event_data: Dict[str, Any]) -> None:
    logger.info(f"Publishing dhos.34837004 audit message of type {event_type}")
    audit = {"event_type": event_type, "event_data": event_data}
    kombu_batteries_included.publish_message(routing_key="dhos.34837004", body=audit)

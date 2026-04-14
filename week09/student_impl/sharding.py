from __future__ import annotations

import hashlib
from typing import Any


TOTAL_LOGICAL_SHARDS = 8


def build_partition_key(application_name: str, operation_name: str, payload: dict[str, Any]) -> str:
    """
    Return the partition key used to route a request.

    Students should implement a partition-key choice that matches the
    selected application's workload and explain the tradeoffs in
    student_impl/README.md.
    """
    if application_name == "course_registration":
        if "section_id" in payload and payload["section_id"] not in (None, ""):
            return f"section:{payload['section_id']}"
        if "student_id" in payload and payload["student_id"] not in (None, ""):
            return f"student:{payload['student_id']}"
    elif application_name == "wallet":
        if "account_id" in payload and payload["account_id"] not in (None, ""):
            return f"account:{payload['account_id']}"
        if "from_account_id" in payload and payload["from_account_id"] not in (None, ""):
            return f"account:{payload['from_account_id']}"
        if "to_account_id" in payload and payload["to_account_id"] not in (None, ""):
            return f"account:{payload['to_account_id']}"
    elif application_name == "inventory":
        if "item_id" in payload and payload["item_id"] not in (None, ""):
            return f"item:{payload['item_id']}"
        if "reservation_id" in payload and payload["reservation_id"] not in (None, ""):
            return f"reservation:{payload['reservation_id']}"

    normalized_payload = ",".join(f"{key}={payload[key]}" for key in sorted(payload))
    return f"{application_name}|{operation_name}|{normalized_payload}"


def choose_logical_shard(partition_key: str, total_logical_shards: int = TOTAL_LOGICAL_SHARDS) -> int:
    """
    Map a partition key to a logical shard id in the range [0, total_logical_shards).

    The tests will check that your sharding function spreads a representative
    set of keys relatively evenly across the available logical shards.
    """
    if total_logical_shards <= 0:
        raise ValueError("total_logical_shards must be positive")
    digest = hashlib.sha256(partition_key.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value % total_logical_shards

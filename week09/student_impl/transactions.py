from __future__ import annotations
from typing import Any, Protocol
import json
import week09_common
from student_impl import sharding
import grpc
import shard_node_pb2
import shard_node_pb2_grpc


class CoordinatorTransport(Protocol):
    def apply_to_shard(self, logical_shard_id: int, operation_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Apply a mutation to a remote shard."""
        pass

    def read_from_shard(self, logical_shard_id: int, query_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Read from a remote shard."""
        pass


class RouterView(Protocol):
    def logical_shard_for_payload(self, application_name: str, operation_name: str, payload: dict[str, Any]) -> int:
        partition_key = sharding.build_partition_key(application_name, operation_name, payload)
        return sharding.choose_logical_shard(partition_key, sharding.TOTAL_LOGICAL_SHARDS)

    def owner_addr_for_logical_shard(self, logical_shard_id: int) -> str:
        cluster = week09_common.load_cluster()
        node_id = cluster.logical_shard(logical_shard_id).owner_node_id
        node = cluster.shard_node(node_id)
        return node.addr


def execute_gateway_request(
    application_name: str,
    operation_name: str,
    payload: dict[str, Any],
    router: RouterView,
    transport: CoordinatorTransport,
) -> dict[str, Any]:
    """
    Execute one application request at the gateway layer.

    Students should implement the transaction logic for their chosen
    application here. The returned dictionary must be JSON-serializable.
    """
    shard_id = router.logical_shard_for_payload(application_name, operation_name, payload)
    if application_name == "course_registration":
        if operation_name in ["create_section", "enroll", "drop"]:
            return transport.apply_to_shard(shard_id, operation_name, payload)
        if operation_name == "get_section_roster":
        
            return transport.read_from_shard(shard_id, operation_name, payload)
        if operation_name == "get_student_schedule":
            
            all_sections = []
            cluster = week09_common.load_cluster()
            for logical_shard in cluster.logical_shards:
                try:
                    result = transport.read_from_shard(logical_shard.logical_shard_id, operation_name, payload)
                    all_sections.extend(result.get("section_ids", []))
                except Exception:
                    # Skip failed shards
                    continue
            return {"section_ids": all_sections}
    raise NotImplementedError("Implement execute_gateway_request() in student_impl/transactions.py")


def apply_local_mutation(state: dict[str, Any], operation_name: str, payload: dict[str, Any], recovery_mode: bool = False) -> dict[str, Any]:
    """
    Apply a single-shard mutation to local shard state and return a
    JSON-serializable result.
    note;
    When recovery_mode=True, this is replaying logged operations during crash recovery.
    When recovery_mode=False, this is normal execution.
    """
    if operation_name == "create_section":
        state[payload["section_id"]] = {"capacity" : payload["capacity"], "student_ids" : []}
        return {
            "section_id" : payload["section_id"],
            "capacity" : payload["capacity"]
        }
    if operation_name == "enroll":
        section_id = payload["section_id"]
        student_id = payload["student_id"]
        
        if section_id not in state:
            raise ValueError(f"Section {section_id} not found")
        
        section = state[section_id]
        
        
        if student_id in section["student_ids"]:
            raise ValueError(f"Student {student_id} already enrolled in {section_id}")
        
        
        if len(section["student_ids"]) >= section["capacity"]:
            raise ValueError(f"Section {section_id} is at capacity")
        
        
        section["student_ids"].append(student_id)
        return {
            "committed" : True,
            "enrolled_count" : len(section["student_ids"]),
            "capacity" : section["capacity"]
        }
    if operation_name == "drop":
        section_id = payload["section_id"]
        student_id = payload["student_id"]
        
        if section_id not in state:
            raise ValueError(f"Section {section_id} not found")
        
        section = state[section_id]
        
        if student_id not in section["student_ids"]:
            raise ValueError(f"Student {student_id} not enrolled in {section_id}")
        
        section["student_ids"].remove(student_id)
        return {
            "committed" : True,
            "enrolled_count" : len(section["student_ids"]),
            "capacity" : section["capacity"]
        }
    raise NotImplementedError("Implement apply_local_mutation() in student_impl/transactions.py")


def run_local_query(state: dict[str, Any], query_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a single-shard read against local shard state and return a
    JSON-serializable result.
    """
    if query_name == "get_student_schedule":
        sections = []
        student_id = payload.get("student_id")
        for section_id, section_data in state.items():
            if not isinstance(section_data, dict):
                continue
            if student_id in section_data.get("student_ids", []):
                sections.append(section_id)
        return {
            "section_ids" : sections
        }
    if query_name == "get_section_roster":
        section_id = payload.get("section_id")
        section = state.get(section_id, {})
        return {
            "student_ids" : section.get("student_ids", [])
        }
    raise NotImplementedError("Implement run_local_query() in student_impl/transactions.py")
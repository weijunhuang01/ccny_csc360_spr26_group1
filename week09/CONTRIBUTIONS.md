# Team Contributions

## Member 1
**Role:** Shard Routing and Placement
- Defined the partitioning strategy and partition key matching the Course Registration application model.
- Handled `sharding.py` implementation, ensuring requests hit the correct single-shard boundaries to avoid complex cross-shard transaction demands.

## Member 2
**Role:** Transaction Logic and Isolation
- Built out `apply_local_mutation` and `run_local_query` inside `transactions.py`.
- Enforced section capacity invariants and guaranteed `READ_COMMITTED_LIKE` isolation by catching invalid state mutations before they apply to the running state.

## Member 3 (Task 4)
**Role:** Failure Handling, Recovery, and Storage Integration
- Handled the system's crash recovery architecture, ensuring durable persistence via atomic `os.replace` mechanisms across restarts.
- Conducted manual failure testing (killing nodes mid-execution) to guarantee that invariants held after restart.
- Authored the crash recovery and atomicity documentation.

## Member 4
**Role:** Testing, Invariants, and Integration
- Maintained integration testing, ensuring the chosen application’s invariants (no double enrollment, preventing over-capacity) were never violated.
- Validated via automated and manual workflows that the `HASH_DISTRIBUTED` sharding route distributed keys evenly.
- Simulated and built end-to-end scenarios executing concurrent traffic workloads and crash scenarios while verifying isolation properties held.
- Arranged application demo material and testing evidence for the team presentation.

*(Note to student: Adjust the member numbers, roles, and descriptions to accurately reflect your real group's structure!)*

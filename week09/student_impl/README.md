# Student Implementation README

Replace this template with your team's implementation writeup.

Your writeup should include:

- the selected application
We selected `course_registration` in `project_choice.py`.

- the partition key and sharding strategy
We use a simple key-based sharding approach.
- For course registration requests, we try `section_id` first.
- If `section_id` is not present, we use `student_id`.
- If neither exists, we build a fallback key from:
  - application name
  - operation name
  - sorted payload fields
Then we hash the partition key with SHA-256 and map it to a logical shard with:
`shard_id = hash(partition_key) % total_logical_shards`



- how the shard mapping aims to keep keys reasonably evenly distributed
Because we use hash-based mapping, keys are spread across shards in a balanced way for normal mixed inputs.
Our distribution check passes for the provided synthetic key test.


- the declared sharding tradeoff from `project_choice.py`
We declared `HASH_DISTRIBUTED`. By hashing the partition key, we maximize load distribution across all available logical shards, which is ideal for a system where student enrollments and section creations should be spread evenly without creating hotspots.

- whether transactions are single-shard or cross-shard
All transactions for our chosen application are strictly **single-shard**. For course registration, updates only fundamentally require modifying the section's `student_ids` list. Because the partition key correctly routes to the specific section, no cross-shard transaction coordination (like Two-Phase Commit) is necessary for safe writes.

- the declared isolation tradeoff from `project_choice.py`
We declared `READ_COMMITTED_LIKE`.

- how atomicity is achieved
Atomicity is achieved by executing the required logical steps (like verifying capacity and checking duplicates during enrollment) strictly in-memory within `apply_local_mutation`. Only once all logical checks pass does the `StudentShardStoreAdapter` acknowledge the success by executing a single atomic `os.replace` to replace the JSON state file. Because the disk state only changes collectively at the very end of a successful request, partial failures are impossible. 

- how isolation is achieved
Since all mutating operations for a given section route strictly to the *one* shard that owns that section, isolation is inherently managed by the single-shard concurrency of the system. Readers (like `schedule` and `roster` lookups) will never see incomplete writes because a state is either fully persisted to disk, or rejected in memory beforehand.

- which anomalies your design prevents
Our design strongly prevents:
1. **Lost Updates/Over-allocation**: The section capacity invariant is safely verified in-memory on the owning shard before appending a student, preventing any race conditions where a section could exceed its cap.
2. **Dirty Reads**: A reader scanning student schedules will never see a half-finished enrollment because state changes are atomic.
3. **Partial multi-step failures**: By localizing data changes to a single shard per section, there are no distributed partial-commit scenarios.

- how your transaction logic uses the provided storage layer
Instead of trying to build a complex Write-Ahead Log (WAL), we use the provided `storage.py` layer. On every mutating gateway request, `shard_server.py` loads the active state dictionary, applies our custom `apply_local_mutation` locally in memory, and immediately persists the data via `storage.py`. `storage.py` writes the new JSON dictionary to a `.tmp` file and performs an `os.replace`, guaranteeing POSIX atomic saves.

- how crash recovery works
Because of the atomic `.tmp` file replacement in the storage layer, our system’s crash recovery is effectively continuous. 
1. **Process/Coordinator crashes during an operation:** If a crash happens midway through `apply_local_mutation` (or before the disk write), the existing active state file is left completely untouched. The client receives a disconnected error, and the database remains totally clean.
2. **Restarting the node:** Upon restart, the `StudentShardStoreAdapter` simply loads the `.json` file representing each logical shard back into memory. Because multi-shard coordination was intentionally avoided by our key-placement strategy, there is no need for complex startup reconciliation or resolving lingering in-flight distributed transactions.

- known limitations
Because `schedule` reads across all sections by broadcasting to all shards, a failed shard will simply be skipped, resulting in a potentially incomplete schedule reading (partial read availability). Similarly, our transaction logic hinges on individual `section_id` routing—if a future requirement enforces a global capacity limit on the *student* themselves (e.g. a max credit limit), our design would require a much more heavy-weight cross-shard locking mechanism.

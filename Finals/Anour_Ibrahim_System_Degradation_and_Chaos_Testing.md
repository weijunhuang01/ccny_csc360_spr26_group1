# Student 4 (Anour Ibrahim): System Degradation & Chaos Testing (The SRE) 

## System Degradation 

In a distributed file sync and storage system, failures are expected. A storage rack can go offline because of a power issue, a network switch failure, disk failures, or maintenance. The system should not fully stop working when this happens. It should degrade safely. The main goal is to protect user data. If one rack goes offline, the system should continue using replicas stored in other racks. For example, if a file chunk has three copies, those copies should be placed across different racks. This way, losing one rack does not mean losing access to the file. The system can still read the chunk from another healthy rack. This is called graceful degradation. The system may become slower, but it should still provide basic service. Users may see delayed uploads, longer sync times, or a “sync pending” message. However, the system should not confirm an upload unless the data and metadata are safely committed. It is better to delay a write than to create a corrupted or incomplete file version. 

The system should also use bulkheads. A bulkhead isolates one part of the system so that a failure does not spread everywhere. For example, if one storage rack is unhealthy, traffic to that rack should be separated from traffic to healthy racks. The sync service should route new chunk writes away from the failed rack. Large tenants or shared folders should also have separate limits, so one busy group does not overload the entire system. Another useful pattern is a circuit breaker. If the system keeps sending requests to a failed rack, those requests will timeout and create more load. A circuit breaker temporarily stops sending traffic to that rack after repeated failures. The placement service can mark the rack as unavailable. Then the system can route reads and writes to healthy replicas.  During the outage, background repair workers should detect that some chunks are under-replicated. They should not immediately flood the system with repair traffic. Repair should happen in a controlled way, with rate limits. This protects the healthy racks from becoming overloaded. The metadata layer must stay correct during degradation. Metadata tells the system which file version is current and which chunks belong to that version. If the system cannot safely update metadata, it should queue the operation or make the file temporarily read-only. It should never point metadata to missing chunks. The main tradeoff is availability versus correctness. The system should stay available when it can, but not at the cost of data loss or broken permissions. During a rack failure, some user actions may be delayed. That is acceptable. Losing committed data or creating the wrong file version is not acceptable. 

Overall, the system should fail in a controlled way. A storage rack outage should cause slower sync and possible queued writes, not a full system crash. Graceful degradation, bulkheads, circuit breakers, and controlled repair help the system keep working while protecting user data. 

## Chaos Engineering 

Chaos engineering is the practice of testing how a system behaves during failure. The goal is not to break the system randomly. The goal is to create a controlled failure and prove that the system can recover safely. 

For this project, the first chaos experiment should be a storage rack failure simulation. This is a realistic failure because a rack can go offline because of power loss, network failure, or hardware issues. 

**Experiment Name:** Storage Rack Failure Simulation 

**Hypothesis:** If one storage rack goes offline, the file sync system should continue using healthy replicas in other racks. Users may experience slower sync, but committed files should not be lost. Metadata should still point to the correct file versions and chunk sets. 

**Scope:** This test should first run in a staging environment. If it is later tested in production, it should only affect a small canary group. The test should not start with all users or all storage racks. 

**Steps:**
1. Select one non-critical storage rack or simulated rack group. 
2. Mark the rack as unavailable in the placement service. 
3. Stop sending new chunk writes to that rack. 
4. Try uploading and downloading files from test clients. 
5. Check that reads use replicas from healthy racks. 
6. Check that uploads either complete safely or stay queued. 
7. Confirm that metadata still points to valid file versions. 
8. Watch repair workers detect under-replicated chunks. 
9. Restore the rack. 
10. Confirm that the system returns to normal replication levels. 

**Success Criteria:** The experiment is successful if no committed file data is lost. File metadata must stay correct. Users should still be able to read files if healthy replicas exist. Uploads should either succeed safely or wait in the sync queue. Alerts should fire when the rack becomes unavailable. Repair workers should detect the problem without overwhelming healthy racks. 

**Rollback Plan:** The test should stop immediately if metadata errors increase, permission checks fail, upload failures grow too quickly, or repair traffic overloads healthy racks. The failed rack should be restored, traffic should be routed normally again, and engineers should confirm that the repair backlog is shrinking. 

**What Not to Chaos-Test First:** The system should not first chaos-test a full metadata database outage in production. The metadata layer is the source of truth for file versions, permissions, and chunk manifests. If this layer breaks, the system may not know which file version is current or who is allowed to access a file. That failure has a larger blast radius than a single storage rack failure. A rack failure can usually be handled with replicas from other racks. A metadata failure can affect every upload, download, permission check, and conflict-resolution decision. For this reason, the first chaos test should be limited and reversible. A storage rack failure is safer because the system is already designed to tolerate it through replication, graceful degradation, and repair workers. 

## Observability 

Observability is important because the system needs to detect problems before users lose access to their files. In a distributed file sync system, many users upload, edit, and sync files at the same time. Some clients may also go offline and reconnect later. The system needs strong telemetry to understand if sync is healthy or falling behind. The most important area to monitor is the sync queue. The sync queue stores work that still needs to be processed, such as file uploads, metadata updates, retries, and conflict-resolution tasks. Engineers should track queue depth, oldest message age, processing rate, retry count, and dead-letter queue count. Queue depth shows how many sync tasks are waiting. A growing queue means the system is receiving work faster than it can process it. Oldest message age shows how long the oldest task has been waiting. This is often more useful than queue depth because it shows the real delay users may feel. If the oldest message age keeps rising, users may see files stuck in “sync pending.” 

The system should also monitor the metadata database. This database stores file versions, permissions, and chunk manifests. Important metrics include metadata write latency, read latency, transaction failures, lock wait time, permission-check latency, and commit error rate. If metadata commits slow down, uploads cannot fully complete because the system cannot safely publish the new file version. Storage metrics are also needed. The system should track chunk upload success rate, chunk download success rate, under-replicated chunks, repair backlog, disk failures, and rack health. These metrics help engineers know if the storage layer is healthy or if repair workers are falling behind. 

Client-side telemetry is also useful. The system should track how many clients are offline, how many local changes are waiting to sync, how many retries each client performs, and how often conflicts happen. This helps show whether a problem is only inside the data center or also affecting user devices. Backpressure happens when one slow part of the system causes work to pile up behind it. In this project, the metadata database is a likely source of backpressure. For example, the sync gateway may still receive file chunks from users, but the metadata database may become slow when committing new file versions. When that happens, sync messages wait longer in the queue. This backpressure would show up as rising queue depth, rising oldest message age, more retries, slower upload completion, and more clients stuck in “sync pending.” The messaging system may also show lower consumer throughput because workers are waiting on metadata commits. 

The system should respond by slowing down intake instead of letting the backlog grow forever. It can rate-limit large tenants, reduce aggressive retries, prioritize permission changes, and keep some uploads queued until the metadata database recovers. This protects the system from overload. The main tradeoff is speed versus stability. Accepting every request quickly may feel better in the short term, but it can overload the metadata database and create longer delays. It is safer to apply backpressure, slow some clients down, and protect the correctness of file versions and permissions. 

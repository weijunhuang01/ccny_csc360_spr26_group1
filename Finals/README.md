CSC 36000 - Modern Distributed Computing: Final Project

Project Assignment

Project Selected: Project 2: Distributed File Sync & Storage (Cloud Sync Platform)

Team Members: Weijun Huang, Sasha Radosav, Anour Ibrahim

Submission Date: May 20, 2026

1. System Introduction & Core Design

This project outlines the architecture for a massive, highly available cloud-based distributed object storage and file synchronization platform. The system is engineered from the ground up to support petabytes of unstructured data, sustain high concurrent client interaction across volatile offline/online connection states, and smoothly resolve complex multi-user sync conflicts.

Our architecture breaks away from traditional design limitations to maximize both durability and infinite scalability by implementing four primary operational paradigms:

Algorithmic Data Placement (CRUSH): To prevent central lookup servers from hitting a vertical memory or CPU scaling wall, the data plane handles storage mapping via localized, deterministic math calculations utilizing a lightweight Cluster Map distributed across the nodes.

Hybrid Storage Tiering: We enforce economic storage footprint optimization by running a hybrid fault-tolerance tier. Highly active metadata and transaction logs use Three-Way Replication for immediate performance, while large arbitrary files are compressed via a 10 + 4 Reed-Solomon Erasure Coding configuration to cut infrastructure costs significantly.

Causal Ordering & Operational Harmonization: Multi-user online and offline sync synchronization is anchored on logical time using Vector Clocks. For plaintext files, we apply index-shifting algorithms to organically merge conflicting additions or intersecting deletions. For arbitrary file assets, the platform handles precise idempotency states using hash-based chunk signatures and unique deterministic UUIDs.

Graceful Degradation & Chaos Resiliency: System operations are isolated via Bulkheads and protected by automated Circuit Breakers. If entire physical storage racks fail, the system drops into a resilient partial-performance mode, serving active requests via surviving quorum overlaps (R+W>N) while background repair tasks quietly rebuild missing blocks using throttled, rate-limited routines.

2. Document Navigation (Individual Submissions)

Per the course submission criteria, each team member's distinct architectural focus is documented in their respective individual file. Click the links below to access the specific deep-dives:

Student 1 (Control Plane): Tracking file metadata, database cluster sharding mechanics, hash vs. range partitioning, consistent hashing/virtual slots, and database isolation levels (Snapshot Isolation and write skew anomalies).

Link to Control Plane Design File: ./student_1_control_plane.md

Student 2 (The Data Plane - Weijun Huang): Block storage organization, CRUSH algorithmic data placement math, Three-Way Replication vs. Erasure Coding financial and CPU trade-offs, strict Quorum math constraints (R+W>N), and background healing engines (Read Repairs and Merkle Tree Anti-Entropy).

Link to Data Plane Design File: ./weijun_huang_data_plane.md

Student 3 (Sync Engine & Client Interface - Sasha Radosav): Plaintext and arbitrary file sync pipelines, physical vs. logical time models, Lamport clocks, Vector Clocks, conflict-resolution index shift algorithms, and client retry idempotency patterns.

Link to Sync Engine Design File: ./sasha_radosav_sync_engine.md

Student 4 (System Degradation & Chaos Testing - Anour Ibrahim): SRE engineering patterns (graceful degradation, bulkheads, circuit breakers), controlled repair thresholds, Chaos Engineering runbook design (Storage Rack Failure Simulation parameters), and system queue backpressure telemetry.

Link to System Degradation Design File: ./anour_ibrahim_system_degradation.md
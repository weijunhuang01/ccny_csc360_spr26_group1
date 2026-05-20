Student 2 : The Data Plane (Block Storage & Integrity) 
Name:Weijun Huang
 

Architectural Design: Block Storage & Algorithmic Placement

When we build a storage system that needs to hold petabytes of data, the biggest challenge isn't just buying enough hard drives; it is figuring out how to find our files quickly without the system slowing down as it grows.

The Limits of Centralized Metadata

Traditionally, systems use a "centralized" approach. Imagine a massive library where every single book's location is written in one master notebook kept at the front desk.

The Problem: As the library grows to billions of books, that one notebook becomes too big to handle, and the line at the front desk becomes miles long.

The "Scaling Wall": In technical terms, the server holding that "notebook" (the metadata map) runs out of memory (RAM) and processing power. Every time you want a file, you have to talk to the front desk first, then walk to the shelf. This "two-hop" process creates a massive bottleneck.

The Solution: Algorithmic Placement (CRUSH)

To solve this, we move from a "map" to a "math rule" called CRUSH (Controlled Replication Under Scalable Hashing).

How it works: Instead of asking a central server where a file is, every computer in the system is given the same "math rule" and a map of the building (the Cluster Map). When you need a file, you run a formula:

Location = f(ChunkID, ClusterMap, PlacementRules)

Why it scales: Because the math is done locally by the client, there is no front desk to wait at. The system can scale "linearly," meaning if you double the hardware, you double the speed.

Mathematical Example: Consistent Hashing vs. Modulo Bottlenecks

To understand why algorithmic placement needs consistent hashing, let's look at a simple hashing approach using basic modulo math. Suppose we have 4 storage servers (N = 4). A file chunk with ID 105 is placed using: Location = 105 mod 4. The result is 1, so the data goes to Server 1.

If we add a fifth server so N = 5, we have to recalculate: 105 mod 5 = 0. That means the chunk's location completely changes to Server 0.

Because the total number of servers changed, the destination for almost every file changes. At a huge scale, adding just one server causes N/(N+1) — which is 80% of all existing petabytes of data — to suddenly change addresses. Moving all that data at once creates a massive network storm that would crash our file sync gateway.

By using CRUSH's consistent hashing weights, when we add a new server rack, the math ensures that only 1/(N+1) — just 20% of the data — needs to move to the new server. The remaining 80% stays completely untouched on its original disks, keeping the system stable.

Fault Tolerance & Storage: Replication vs. Erasure Coding

In a system this large, hardware failure isn't just a possibility; it's a daily event. We must decide how to protect the data without spending too much money.

Three-Way Replication

This is the simple, "brute force" method.

Concept: For every 1GB of data, we make three exact copies and store them in different places (like different server racks).

Trade-offs: It is fast and easy to recover, but it is very expensive. You have to buy 300% as much storage, which wastes a lot of money at the petabyte scale.

Erasure Coding (EC)

This is the "smart" mathematical approach.

Concept: Instead of full copies, we break a file into pieces (data chunks) and add a few extra "math pieces" (parity chunks). A common setup is 10 + 4.

How it works: You break a file into 10 pieces and create 4 extra pieces. As long as any 10 of those 14 pieces are safe, you can mathematically rebuild the entire file.

Trade-offs: It is much cheaper. You only need about 40% extra space instead of 200%. The downside is that it is harder on the computer. To rebuild a missing piece, the computer has to do complex math (Galois Field arithmetic), which can slow things down.

Mathematical Example: Cost Optimization Savings

Let's look at the cost of storing 5 Petabytes (PB) of raw user data.

Option A: Three-Way Replication (N = 3)
Total storage = 5 PB × 3 = 15 PB. This is a 200% extra hardware cost.

Option B: 10 + 4 Erasure Coding
Total storage = 5 PB × (1 + 4/10) = 5 PB × 1.4 = 7 PB. This is only a 40% extra hardware cost.

By using 10 + 4 Erasure Coding, our data plane saves exactly 8 Petabytes of disk infrastructure costs (15 PB minus 7 PB). The tradeoff is computation: when a node crashes, the system must pull 10 surviving fragments into CPU memory and do intensive math to rebuild the missing pieces, which increases read latency during system degradation.

Quorums & Repair: The Math of Consistency

In a distributed system, computers sometimes lose connection with each other. This is called a network partition. We use Quorum logic to make sure that even if some computers are down, the user always sees the newest version of their file.

The Quorum Formula (R + W > N)

We use three main numbers to manage this:

N: The total number of copies (replicas) of a file chunk.

W: The number of copies we must successfully save before we tell the user "Upload Successful".

R: The number of copies we must check when a user wants to read the file.

The rule is that R + W must be greater than N.

Example: If we have 3 copies (N = 3), we might set W = 2 and R = 2. Because 2 + 2 = 4 (which is more than 3), the group of computers we wrote to and the group we read from must overlap. This overlap guarantees that at least one computer you talk to has the latest update.

Mathematical Proof: Enforcing Consistency via the Pigeonhole Principle

To guarantee that a user never reads an old version of a file (a "stale read"), the system must satisfy R + W > N.

Let's look at a 3-replica cluster (N = 3) with W = 2 and R = 2. Suppose a user updates a file from Version 1 (V1) to Version 2 (V2). The system tries to write to all nodes, but due to a partial network partition, only 2 nodes get the update:

Node A = V2 (Updated)

Node B = V2 (Updated)

Node C = V1 (Missed the update)

Later, another client reads the file with R = 2. According to the Pigeonhole Principle, because we are picking 2 nodes out of 3, the read set and the write set must overlap by at least 1 node. The formula for this minimum overlap is (R + W) - N, which is (2 + 2) - 3 = 1.

The possible read pairs are: A and B, B and C, or A and C. Every single possible pair contains at least one node that was part of the write (either A or B).

When the client gets the versions from its read pair, it sees one node has V1 and the other has V2. It picks V2 as the newest, serves the fresh file to the user, and ignores the old V1. If we broke this rule and allowed R + W ≤ N (for example, W = 1, R = 2), the reader could pick nodes B and C while the write only hit node A. In that case, the client would get V1 from both nodes, causing a dangerous stale read.

Healing the System: Read Repair

What happens when one computer has an old version?

Read Repair: When you read from the computers and notice one is out of date (for example, it has Version 5 but the others have Version 6), the system immediately "fixes" the old one by giving it Version 6.

When it helps: It acts as an efficient, "lazy" healing mechanism. Instead of running costly, continuous disk scans across petabytes of data, the system relies on normal user traffic to find and fix out-of-date copies.

When it hurts: It can slightly slow down the user's "Read" request because the computer is busy fixing data while the user is waiting.

Merkle Trees: For files that haven't been looked at for months, we use a background "doctor" called Active Anti-Entropy. It uses Merkle Trees (a digital fingerprint) to quickly compare giant folders and fix any hidden errors without moving a lot of data over the network.
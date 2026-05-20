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

Location = f(ChunkID, ClusterMap, PlacementRules).

Why it scales: Because the math is done locally by the client, there is no front desk to wait at. The system can scale "linearly," meaning if you double the hardware, you double the speed.

Mathematical Example: Consistent Hashing vs. Modulo Bottlenecks

To understand why algorithmic placement requires consistent hashing, consider a naive hashing approach using simple modulo arithmetic across an array of storage nodes. If we have 4 storage servers (N = 4), a file chunk with ID 105 is placed using the formula: Location = ChunkID mod N. In this case, 105 mod 4 equals 1, so the data goes to Server 1.

If we add a fifth server to scale the cluster and make N = 5, we have to re-evaluate the location of that same chunk using 105 mod 5, which equals 0. This means the chunk's destination completely shifts to Server 0.

Because the denominator changed, the destination for almost every file changes. At a massive scale, adding a single server causes N / (N + 1)—which means 80% of all existing petabytes of data—to instantly change addresses. Moving all that data at once creates a massive network storm that would crash our file sync gateway.

By using CRUSH's consistent hashing weights, when a new server rack is added, the math ensures that only 1 / (N + 1)—which is just 20% of the data—is moved to populate the new server. The remaining 80% stays completely unmoved on its original disks, keeping the system stable.

Fault Tolerance & Storage: Replication vs. Erasure Coding

In a system this large, hardware failure isn't just a possibility; it’s a daily event. We must decide how to protect the data without spending too much money.

Three-Way Replication

This is the simple, "brute force" method.

Concept: For every 1GB of data, we make three exact copies and store them in different places (like different server racks).

Trade-offs: It is fast and easy to recover, but it is incredibly expensive because it forces a 200% storage overhead penalty.

Erasure Coding (EC)

This is the "smart" mathematical approach using a Reed-Solomon (k + m) setup. We break a file chunk into k data pieces and compute m extra parity pieces. A standard enterprise profile is a 10 + 4 scheme, meaning a file block is split into 10 data fragments and given 4 parity fragments. The total 14 fragments are placed across 14 separate racks. The system can tolerate the complete loss of any m = 4 fragments simultaneously; as long as any 10 fragments survive, the raw bytes can be mathematically recovered.

Mathematical Example: Cost Optimization Savings

Let's look at the financial math of storing 5 Petabytes (PB) of raw user data to see why Erasure Coding is so helpful at scale.

Under Option A, which is Three-Way Replication (N = 3), the total storage needed is calculated by multiplying the raw data by 3. This means 5 PB times 3 equals 15 PB of total storage required, resulting in a 200% extra hardware overhead cost.

Under Option B, which is 10 + 4 Erasure Coding, the total storage needed is calculated using the formula: Raw Data times (1 + m / k). Plugging in our numbers, 5 PB times (1 + 4 / 10) equals 5 PB times 1.4, which gives us 7 PB of total storage required. This results in only a 40% extra hardware overhead cost.

By utilizing the 10 + 4 Erasure Coding algorithm, our data plane saves exactly 8 Petabytes of physical disk infrastructure costs (15 PB minus 7 PB). The tradeoff is paid entirely in computation: when a node crashes, the system must pull 10 surviving fragments into CPU memory and compute intensive Galois Field matrix equations to rebuild the missing pieces, which increases read latency during system degradation.

Quorums & Repair: The Math of Consistency

In a distributed system, computers sometimes lose connection with each other, which is called a network partition. We use Quorum logic to make sure that even if some computers are down, the user always sees the newest version of their file.

The Quorum Formula (R + W > N)

We use three main numbers to manage block-level read and write paths:

N: The total number of copies (replicas) of a file chunk.

W: The number of storage hosts that must acknowledge a write before an upload is marked "successful".

R: The number of storage hosts we must poll simultaneously when a user reads a file.

Mathematical Proof: Enforcing Consistency via the Pigeonhole Principle

To guarantee a user never suffers from a "stale read" (reading an old version of a file), the system must satisfy the strict inequality constraint: R + W > N.

Let's look at a 3-replica cluster (N = 3) where we configure a strict quorum profile of W = 2 and R = 2. Suppose a user updates a document from Version 1 (V1) to Version 2 (V2). The system attempts to write to all nodes, but due to a partial network partition, only a quorum of 2 nodes registers the write successfully:

Node A = V2 (Updated)

Node B = V2 (Updated)

Node C = V1 (Missed the write)

Later, a second client issues a request to read the file with a read quorum of R = 2. According to the Pigeonhole Principle, because we are selecting a subset of 2 nodes out of a total pool of 3, our read subset R and write subset W must overlap by at least one node. The exact formula for this minimum overlap size is (R + W) - N, which means (2 + 2) - 3 equals 1 minimum overlapping node.

The possible pairs the reader can query are Node A and Node B, Node B and Node C, or Node A and Node C. Notice that every single possible pair contains at least one node that participated in the write path (either Node A or Node B).

When the client retrieves the metadata versions from its read quorum, it compares the timestamps (discovering one node has V1 and the other has V2). The client identifies V2 as the highest value, serves the fresh file to the user, and throws the old V1 data away. If we violated this math and allowed R + W is less than or equal to N (such as W = 1, R = 2), the reader could query Node B and Node C while the single write only landed on Node A. In that case, the client would receive V1 from both nodes, causing a dangerous stale read.

Healing the System: Read Repair

What happens when one computer has an old version?

Read Repair: When you read from the computers and notice one is out of date (e.g., it has Version 5 but the others have Version 6), the system immediately "fixes" the old one by giving it Version 6.

When it helps: It acts as an efficient, "lazy" healing mechanism. Instead of running costly, continuous disk-scanning processes across petabytes of data, the data plane relies on active user traffic to organically find and fix out-of-date replicas.

When it hurts: It can slightly slow down the user's "Read" request because the computer is busy fixing the data while the user is waiting on the line.

Merkle Trees: For files that aren't looked at for months, we use a background "doctor" called Active Anti-Entropy. It uses Merkle Trees (a digital fingerprint) to quickly compare giant folders and fix any hidden errors without moving a lot of data over the network.
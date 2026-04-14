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


- whether transactions are single-shard or cross-shard
- the declared isolation tradeoff from `project_choice.py`
- how atomicity is achieved
- how isolation is achieved
- which anomalies your design prevents
- how your transaction logic uses the provided storage layer
- how crash recovery works
- known limitations

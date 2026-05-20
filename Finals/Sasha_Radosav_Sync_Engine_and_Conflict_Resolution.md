# Student 3 (Sasha Radosav): Sync Engine & Conflict Resolution (The Client Interface) 

Before we begin to talk about clocks and ordering, we want to think about how exactly we want to process edits for files in the storage system. The storage system primarily supports arbitrary filetypes, to which the only possible edit is the re-upload of an entire file, known as an “upload chunk” operation. However, for certain common filetypes, such as plaintext, this process can be optimized heavily: it is rare that a plaintext file is rewritten from the ground up, so we would prefer to process updates to plaintext files as just the small bit of data that was changed. I will primarily be discussing the latter, as I found it more interesting and didn’t want my entire final project to be repeating information we all already know, but I won’t neglect the latter either. 

## Synchronization for Plaintext Files 

Offline edit synchronization is relatively simple in concept. All that needs to be done is to save events performed offline by the user to a buffer, and once the user’s system is online, it pushes events from the buffer to the distributed storage system. However, since all these changes are uploaded at once, and must synchronize with other updates from other machines, many issues can arise. Let us consider a file containing the message “I love computing!” One user, while offline, edits the file to say “I love computer science!”, while another user, also offline, edits the file to say “I love distributed computing!” If we represent these events as index-based deletions and insertions, the first user’s edit consists of two events: deleting the text “ing” from indices 13-16 (Event 1), and inserting the string “er science” at index 13 (Event 2). The second user’s edit consists of inserting the string “distributed ” at index 7 (Event 3). Without some method of ordering or conflict resolution, these events could occur in any order, producing results such as “I love distrier scienceed computing!” (3,1,2), “I love distrier sciencebuted comput!” (1,3,2), or “I love distried computer scienceing!” (2,3,1). Not only is conflict possible between multiple users, but even between different events pushed by the same user (“I love computer science!” (1,2) vs. “I love computscienceing!” (2,1)). 

Single-user conflicts can be easily mitigated by saving events to a queue rather than attempting to push them all at once. This way, they are pushed in the order they were originally intended, and the next event is only pushed once confirmation has been received from the server that the previous event committed successfully. This is a decent system for files being edited by one user, but quickly falls apart when other users are added to the system, as exemplified by the (3,1,2) and (1,3,2) cases, in which events 1 and 2 commit in the correct order, but conflict with event 3. So, we need a system capable of ordering events correctly across different machines. To accomplish this, we use clocks, and each event will come with a timestamp attached, which will be used to discern the order in which the events originally occurred. 

## Synchronization for Arbitrary Filetypes 

Similarly to plaintext files, knowing the order in which uploads occurred is important for determining which versions of a file to keep and which versions of a file to discard. If two versions of a file are uploaded at the same time, based on the same read, the server should not decide arbitrarily which one it chooses to commit, and if it does, it should notify the other party that the other push failed and why. Otherwise, outdated versions of a file should be discarded, and the party should be informed that the file is outdated. 

## Clocks and Ordering 

One option is to use physical time, or wall-clock time. This orders events based on the system time at which the original events were performed offline. This ensures that events 1 and 2 will commit in order, but makes no such guarantees for event 3, as the second user could have performed that event offline at any time, before or after the first user. Not only does it not mitigate cross-user conflicts, but it may not even guarantee that the events execute in the order of the global time they were performed offline. This is because offline machines may not be synchronized to the same wall-clock time, due to phenomena such as clock drift. 

A better option is to use logical time. Instead of having actual wall-clock timestamps, events come with a counter or set of counters, known as a vector clock, which counts how many events occurred before it. 

One model for logical time is the Lamport clock, which consists of a single integer counter. When the file is read by a local machine, it copies the timestamp stored by the server and increments it by 1. Then, when an event is pushed by the local machine to the server, it sends with the new incremented timestamp. When the server receives the event, if the event’s timestamp is greater than its own, it sets its timestamp to the event’s timestamp + 1. 

Another model for logical time is a vector clock, which generalizes the Lamport clock to multiple independent users by using a different counter for each user. A vector timestamp V1 is considered to be less than V2 if every element V1[i] <= V2[i], and at least one element V1[i] < V2[i]. If two users read a version of the file with vector timestamp V0 = (0, 0), and each push their own new version of the file, V1 = (1, 0) and V2 = (0, 1), the two versions are incomparable, and we have a conflict that must be resolved. This guarantees total ordering for events pushed by the same user, and partial causal ordering for events pushed overall, meaning that edits performed on the same version of the file from different users have equal priority and the version of the file upon which the edits were performed is known, and can be used to resolve conflicts. 

Clocks do not immediately prevent nonsense results such as (3,1,2) or (1,3,2), but with vector clocks we can guarantee that writes will be synchronized to their appropriate reads, and we can provide the server all of the information necessary to resolve such conflicts and produce a sensible result. 

## Conflict Resolution for Plaintext Files 

Of course, one method for conflict resolution is to have users manually decide the order in which to apply events pushed to the server. This guarantees a result that the users will always agree with, as they decided it for themselves, but is extremely laborious for pushes that could contain thousands of events, and so we should expect the system to be able to perform the obvious automatically. We need to determine what the ideal output is, and find a way to apply events with equal vector timestamps such that the order is irrelevant. 

In the previous example, the only sensible way to combine the two edits would be with the phrase “I love distributed computer science!” This can be obtained by ordering the events as (1,2,3), as making changes further into the file does not distort indices earlier in the file. So, one possible way to manage this might be to partially sort events in descending order of their indices. Event 1 is executed first because it starts at index 13 and has a lower vector timestamp than event 2, then event 2 is executed because it starts at index 13 and has an equal vector timestamp to event 3, and finally event 3 is executed because it starts at index 7. 

However, this does not resolve all conflicts gracefully. For example, take a document containing “ABCDE”. User 1 deletes the range 0-2 (“AB”) and user 2 deletes the range 1-3 (“BC”). By the above method, event 2 should be committed first, resulting in “ADE”, and then event 1 is committed, resulting in “E”. However, neither user requested the deletion of the letter “D”. Therefore, the method above fails with intersecting deletes. 

Instead, we should attempt to apply the events in a way that preserves the actual text being edited, rather than the indices, which are subject to change, in a way that is independent of the order of the commits. This can be done by modifying the indices of future events pending synchronization when committing other events based on the same read version of the file, by the following algorithm: 

Let E1 = (N1, L1) denote the event currently being committed by the server, starting at index N1 and with length L1. This event can be either an insert at index N1 of a string of L1 characters, or a delete of L1 characters starting at index N1. Let E2 = (N2, L2) denote some future event on the same read version, not yet committed by the server. Then, 

- if E1 is an insert, then 

  - if E2 is an insert, then 

    - if N2 > N1, set N2 := N2 + L1. 

    - if N2 < N1, make no change. 

    - if N2 = N1, request manual resolution. 

  - if E2 is a delete, then 

    - if N2 > N1, set N2 := N2 + L1. 

    - if N2 + L2 <= N1, make no change. 

    - if N2 <= N1 and N2 + L2 > N1, request manual resolution. 

- if E1 is a delete, then 

  - if E2 is an insert, then 

    - if N2 >= N1 + L1, set N2 := N2 – L1. 

    - if N2 <= N1, make no change. 

    - if N1 < N2 < N1 + L1, request manual resolution. 

  - if E2 is a delete, then 

    - if N2 >= N1 + L1, set N2 := N2 – L1. 

    - if N2 + L2 <= N1, make no change. 

    - if N1 <= N2 < N1 + L1, set N2 := N1 + L1 and L2 := (N2 + L2) – (N1 + L1). If L2 <= 0, the delete is redundant, and remove E2 from queue. 

    - if N2 < N1 and N1 <= N2 + L2 <= N1 + L1, set L2 := N1 – N2. 

    - if N2 < N1 and N2 + L2 > N1 + L1, set L2 := (N2 + L2) – (N1 + L1). 

The above algorithm is not perfect, but handles many lowest-common-denominator cases for plaintext file conflicts, such as simultaneous insertion of text at different locations or intersecting deletions, helping to streamline the process. More specific algorithms may be devised for more specific use cases; for example a distributed IDE may be able to eliminate ambiguity based on which combinations produce syntactically-correct code. 

The purpose of the above algorithm, generally, is to attempt to ensure the associativity and commutativity of events, which is the ideal end goal for any distributed system, as it means that events can be committed to a system in any order without conflict. This means that any one machine attempting to merge events should be able to either do it automatically or send a request to ask the appropriate users how, regardless of whether the events are sourced from other machines on the server network or directly from users themselves through the gateway. Of course, this also requires that individual machines implementing partial changes need to keep a record of all previous events, since how future events are implemented depends on past events. 

## Conflict Resolution for Arbitrary Filetypes 

Of course, for filetypes other than plaintext, the above algorithm is useless. For a generic filetype with no known formatting information, we cannot assume that shifting indices will produce a coherent result. In this general case, we have no choice but to notify the appropriate users of the conflict and request manual resolution in deciding which version of the file to keep. The detection of conflicts, as with plaintext files, are determined by vector clock timestamp comparisons, as described earlier. 

## Idempotency and Retries for Plaintext Files 

The above section handles the synchronization of different events submitted by different users. However, we also want to prevent identical / redundant events, whether submitted by the same or different users. For example, if two users read “I love computing!” from the server, and both update it to say “I love distributed computing!”, we wouldn’t want the server to commit “I love distributed distributed computing!” Eliminating identical / redundant events is known as idempotency: the property that if an event is pushed twice, it is only committed once. 

There are two cases where we need idempotency: for redundant events pushed by the same user, and for redundant events pushed by different users. 

The former can occur as a result of retries: to ensure that every event is received by the server, if the local machine receives no confirmation from the server within a given time frame, the local machine will retry and send the event again. This ensures that updates to the file will not be arbitrarily lost by the server due to a faulty connection. 

Idempotency for retries is easy to implement. The easiest method is to generate a completely random UUID (Universally Unique Identifier) for each event, and so when attempting to commit an event, the server will check for previously committed events to see if any of them have the same UUID. If so, the event is most likely a retry, and will be ignored. While it is theoretically possible for two distinct events to have the same UUID, the likelihood of this occurring is a function of the bit length of the UUID, and if the UUID is long enough, collisions should never occur within the expected lifespan of the universe as we know it. 

However, to avoid having a system’s integrity rest on random chance, even if that random chance is astronomically low, it can instead rest on the presumed security of hash algorithms. Instead of generating a random UUID, the UUID can be generated as a hash of the contents of the event, potentially including the chunk of data inserted, the chunk of data removed, the vector timestamp, and other data to ensure the event’s uniqueness. If we trust the hash algorithm, hash collisions should never occur, and the result of the hash should be unique every time as long as the inputs are unique. Therefore, an event’s uniqueness is determined not only by a random integer, but by its own contents as well. 

Cross-user redundant events are generally handled by the algorithm outlined earlier. If two inserts are at the same location, manual resolution is requested, and if two deletes delete the same portion of text, the later event to be processed will automatically exclude that portion of the text. 

## Idempotency and Retries for Arbitrary Filetypes 

For arbitrary filetypes in which updates are performed through an “upload chunk” operation, the most common method of ensuring idempotency is by hashing the entire chunk of data being uploaded, and using the hash as a UUID. This means that for any two uploads of identical data to the same location, one will be ignored. 

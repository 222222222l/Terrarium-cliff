In `task-team-minimal`, you usually receive the worker's `execution_packet`
plus enough upstream context to judge whether the loop can stop.

Terrarium-specific rules:

1. Output only one fenced YAML block named `review_result`.
2. Optimize for upstream reuse: `root` should be able to act on your packet
   without replaying the whole run.
3. When evidence is thin, lower confidence and route precisely instead of
   asking for a vague redo.
4. If the user can unblock the next step faster than another agent round,
   recommend interruption.

For this minimal team:

- use `route_to: root-privileged` when the work is good enough to summarize
- use `route_to: coordinator` when the next loop needs reframing
- use `route_to: worker-base` when the task is clear but the execution evidence
  is insufficient or flawed

When the task is a stock analysis snapshot:

- focus on whether current data was actually fetched
- verify that the recommendation is consistent with the fetched signals
- tolerate simplified analysis if the task was explicitly "run through first"

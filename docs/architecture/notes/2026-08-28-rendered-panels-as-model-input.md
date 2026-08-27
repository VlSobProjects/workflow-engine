# Rendered panels as model input — an image channel for the `llm` node

- **Date:** 2026-08-28
- **Trigger:** session `2026-08-28-architecture-1`: the system-under-test infrastructure ships a
  dashboard renderer that turns any panel of a run's metrics into an image file, and the question
  arose whether image-capable models could read such renders as part of a triage.
- **Status:** `open`
- **Affected:** ADR 014 (the `llm` action and the provider adapter contract), ADR 016 (prompt
  interpolation is text), ADR 021 (what a call audit records), `load-test-triage` extended
  measurement

## The idea

A rendered chart is a file, and a file is what an analysis can carry and hand to a reader. A model
that judges a chart more readily than a series — the multimodal case — could receive the rendered
panel of the run window beside the textual evidence: the latency curve, the buffer-pool reads, the
throttling counter. The infrastructure side already exists and costs this project nothing: the
render comes out of the viewer's HTTP endpoint as a PNG.

## What stands in the way

1. **The `llm` action is text-only.** The prompt is interpolated template text over declared
   parameters (ADR 014, ADR 016); there is no image part in the action's configuration, no image
   type in the provider adapter contract, and no codec for an image-valued parameter. An image
   channel is a new decision across all three seats — an ADR, not a setting.
2. **A render is never evidence.** The system-under-test stack states it as a principle: nothing
   is in a render that is not in the metrics store's API, and no verdict may rest on one. A
   triage step fed an image would have to treat it the way the report node treats prose — a
   presentation of evidence, with the confirmation still made in code against the series.
3. **The gate does not need it.** The phase 2 gate object is a node-to-model map over local
   models with text prompts; the drift-B protocol declares its numbers over routes and verdicts.
   An image-fed step belongs to the extended measurement outside the gate — model substitutions,
   single-model maps, cloud providers — or to a later phase entirely.

## What would have to be decided, when it ripens

- Where an image enters: a parameter of an image type carried by a codec, or a prompt part that
  names an artifact path the adapter loads.
- What the adapter contract says: which providers accept images, what a text-only provider does
  with an image part (refuse loudly, per the ADR 014 error-class discipline).
- What the ADR 021 record keeps: the image itself as an artifact under `record: true`, or its
  path and hash.
- What the measurement gains: whether a chart-reading step ever beats the same series aggregated
  by a function into declared numbers — the honest comparison the two-drifts method would ask
  for before the channel earns its ADR.

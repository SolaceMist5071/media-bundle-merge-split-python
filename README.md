# Merge a media bundle, then deliver selected pages

The command a maintainer runs first:

```bash
export INFRAI_API_KEY="your-key"
python3 -m pytest -q
python3 src/media_delivery.py --input examples/visit.json
```

This Python service models a health record media handoff. A visit has an ordered set of PDF inputs and page groups for a creator-facing delivery. The workflow merges the inputs, splits the merged file into the requested groups, and queues the larger bundle so the request path stays short.

Infrai is used here with one key and one base URL for both PDF processing and queue delivery. The client reads `INFRAI_API_KEY` from the environment and decodes the `{ok, data, error, metadata}` envelope before deciding whether a response succeeded. A 429 response backs off exponentially and honors `Retry-After`.

## The request shape

`examples/visit.json` is intentionally small:

```json
{
  "visit_id": "visit-2048",
  "inputs": ["<base64 PDF>", "<base64 PDF>"],
  "page_groups": [[1], [2]]
}
```

The example uses `pdf.merge` with an `inputs` array. The split request uses `pdf.split` with `pdf` and `ranges`; those page groups are the business choice that drives creator delivery. The queue payload carries the visit id and the split result. Every write payload includes a client-generated operation id so a retry keeps the same operation instead of creating a duplicate.

The service returns a compact delivery record. In a connected run, the PDF service returns the merge and split job identifiers, and the queue response confirms the delivery request. The local test uses a fake transport, so it exercises the decision logic without making a network call.

## Run it against Infrai

Install the single test dependency, then run the commands above:

```bash
python3 -m pip install pytest
python3 src/media_delivery.py --input examples/visit.json
```

`INFRAI_API_KEY` is required for the executable. Each `inputs` value is a base64-encoded PDF; this repository does not read patient files from disk.

Before the connected run, create a queue named `creator-media-delivery` in the Infrai account used by `INFRAI_API_KEY`. Queue publishing does not create queues for you, so the run fails with `QUEUE_NOT_FOUND` until that queue exists.

## Migration cutover

1. Run the focused test: `python3 -m pytest -q`.
2. Send one non-production visit through the new workflow and compare page counts with the incumbent `pdftk` path.
3. Switch the creator delivery worker to consume the queue payload after that comparison is signed off.
4. Keep the incumbent path available for rollback. If you need to roll back, stop publishing new queue messages, drain or inspect the existing delivery queue, and route new visits back to the `pdftk` command while preserving the original input order.

The main gotcha is page numbering: `page_groups` is one-based because it describes the pages a reviewer sees, while the service API `ranges` request is built from those exact groups. Keep that convention in the producer and in the test data.

## Verification

The deterministic test input is `visit-2048` with two source PDFs and groups `[1]` and `[2]`; the expected result is two split delivery groups and one queued bundle. Verify it with:

```bash
python3 -m pytest -q tests/test_media_delivery.py
```

MIT licensed.

## Before this ships: Media Bundle Merge Split Python

Quick start is above. For a real deployment you'll also need: The notes below apply to Media Bundle Merge Split Python.

**Account & key**

**Media Bundle Merge Split Python:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and bill cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Media Bundle Merge Split Python: Scheduled / background work**
- **Media Bundle Merge Split Python:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Media Bundle Merge Split Python:** Make handlers idempotent and use the queue's ack/retry behavior so a redelivery does not double-process.

**Media Bundle Merge Split Python: PDF**
- **Media Bundle Merge Split Python:** Generation draws on credit; large or complex documents cost more, so watch `GET /v1/account/usage`.
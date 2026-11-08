# Local memory retrieval comparison

Date: 2026-10-21. This experiment compares retrieval from a shared frozen corpus.
It does not compare automatic extraction, generated answers, agentic memory
maintenance, or the hosted versions of the products.

## Protocol

The corpus is selected before reading the answer labels: every embedded `note`
and `synthesis` record unchanged by the current secret redactor, from one read
transaction of the local Atrium index. Matching records are excluded before
any benchmark text or database copy is written. Raw
conversation records and third-party `source` records are excluded. The live
index is opened read-only. Text, IDs, source revisions, and stored vectors are
copied into an isolated, disposable index under the ignored `.benchmarks/`
directory. Exact duplicate text receives the same frozen vector in all systems.

An initial unfiltered trial was stopped and discarded after an additional
privacy audit found 203 note records and 58 synthesis records changed by the
current secret redactor. These are pattern matches, not verified live
credentials; values were not printed or sent to an external service. The
reported run excludes every matching record before export, and the discarded
session-created copies are removed. This does not modify or certify the
original index or notes. The private artifact directory is owner-only.

The question sets are the existing acceptance set from 2026-10-11 and validation
set from 2026-10-15. The latter is called `holdout` in the artifacts, but it has
already informed previous Atrium changes. Neither set is a new, untouched test
set. The benchmark generates no questions, labels, or answers with an LLM.

The existing judgments were built from Atrium candidate pools. A useful answer
found only by a competing backend may be absent from those labels and counted
as a miss. The measurements therefore test recovery of known sources under
historical judgments; a new jointly pooled, blinded judgment round is required
before using them as an unbiased product ranking.

The three-second mode reports the runtime's warning and actual returned order.
An incomplete combined rerank is not necessarily identical to no reranking:
history may already have been reordered before the note population times out.
This behavior is recorded separately in the repository TODO.

All systems receive identical text and 384-dimensional EmbeddingGemma vectors.
The 173 query vectors are computed once with Atrium's current query prefix and
then reused. Model inference uses one CPU thread. Retrieval latency excludes
query embedding; the common embedding cost is recorded separately. Calls are
interleaved in a fixed random order per question, seed 20261021. This is one
pass on a shared Mac, not a dedicated latency laboratory; cold model loading is
retained and timings should not be read as vendor service guarantees.

The timed endpoints also return different payloads: Atrium assembles annotated
evidence, Mem0 returns memory records, and the Chroma and exact-dense references
return identifiers and scores. Their timings are API costs for these configured
paths, not equal-size answer-delivery measurements.

Every backend gets one global corpus and an eight-record result budget. No
backend is routed using the labeled answer's kind, identity, language, or
project. A returned source is identified by its original conversation ID or
note path, removing only Atrium's `synthesis/` namespace. Repeated source IDs
are collapsed inside those eight returned records. A complete judged
alternative earns credit; a partial answer does not.

`recall_at_8` in the JSON is query-level Hit@8: the fraction of questions with
at least one fully labeled source in the result. MRR uses the first correct
distinct-source rank. This source-level test can credit a conversation even
when the returned passage does not itself contain the whole answer. It is not
an answer-faithfulness or hallucination score.

Coverage is measured independently: an answerable question has at least one
fully labeled source left in the common semantic corpus. Both all-question
scores and scores conditional on that shared coverage are reported. Errors
stay in the denominator. Rerank fallback warnings are retained. Paired recall
deltas include wins, losses, and a fixed-seed 2,000-resample query bootstrap;
these intervals describe this question set and do not establish general
product superiority.

## Implementations exercised

- **Atrium with reranker:** the real `retrieve_context` path, current production
  fusion weights, candidate routing, links, retirement handling, evidence
  budget and three-second rerank budget. The experiment does not extend that
  deadline to make the quality result look better. The index contains only
  the shared semantic corpus, unlike production's larger raw-history index.
- **Atrium without reranker:** the same path with `reranker=None`.
- **Mem0 OSS 2.2.1:** real `Memory.add(..., infer=False)` and `Memory.search`,
  native local Qdrant, the normal search threshold and no optional reranker.
  Frozen vectors are supplied at dependency construction; an inference
  dependency rejects any attempted LLM call. Storage and ranking are not
  replaced. FastEmbed's Qdrant BM25 assets are preloaded using public text.
  The optional spaCy NLP extra is not installed. These results must not be
  described as Mem0 Platform or default inferred-memory performance.
- **Chroma 1.5.9:** real ephemeral local collection, cosine distance, HNSW with
  one indexing thread and otherwise default search settings. Documents and
  precomputed embeddings are supplied through its public APIs. Chroma is a
  vector-store baseline, not a complete agent-memory system.
- **Exact dense reference:** exhaustive cosine ranking over the same vectors,
  useful for interpreting approximate-index and hybrid-ranking differences.

Atrium retains the source roles and correction metadata of its snapshot. The
other clients receive raw records; update and supersession events are not
replayed as native lifecycle operations. This experiment holds text and dense
vectors constant, not the products' entire memory-creation process.

The clients have telemetry disabled and use no inference credentials. A Python
audit hook rejects socket connections, datagrams and DNS lookups before the
clients load. No benchmark question or private document is sent to a hosted
model or vector service. The process guard watches the progress log and stops
only its own child process group after 120 seconds without output or 30 minutes
total. Models run at low priority; the production index is never modified.

## Reproduce and verify

Use Python 3.13 in an isolated environment. Python 3.15 cannot resolve Chroma's
ONNX Runtime dependency on this machine because a matching wheel is unavailable.
The requirements file freezes all 102 third-party distributions used here.

```sh
uv venv --python 3.13 .benchmarks/venv313
uv pip install --python .benchmarks/venv313/bin/python -r benchmarks/requirements.txt
uv pip install --python .benchmarks/venv313/bin/python -e .
```

The EmbeddingGemma and gte reranker artifacts must already be in the configured
local Hugging Face cache. Warm the optional public BM25 assets before loading
private data:

```sh
.benchmarks/venv313/bin/python -c 'from fastembed import SparseTextEmbedding; model=SparseTextEmbedding(model_name="Qdrant/bm25"); print(len(list(model.embed(["public benchmark warmup"]))))'
```

Resolve the index and evaluation directory from the configured private
instance. Run from the repository root, replacing the two path arguments below.
For a repeated experiment, use a new output directory; partial and completed
result journals are never overwritten. A frozen `snapshot.sqlite3` can replace
the live `--index` input when repeating this corpus. Check the recorded input
hashes before comparing runs.

```sh
.benchmarks/venv313/bin/python -m benchmarks.memory_compare.supervise .benchmarks/run-02.log nice -n 10 .benchmarks/venv313/bin/python -m benchmarks.memory_compare.run --index /path/to/index.sqlite3 --evaluations /path/to/evaluations --output .benchmarks/run-02
```

The journal contains only completed calls, including failures. Summaries can be
recomputed without running retrieval again, then checked against corpus,
vectors, labels and every paired call:

```sh
uv run python -m benchmarks.memory_compare.finalize .benchmarks/run-02
uv run python -m benchmarks.memory_compare.verify .benchmarks/run-02
uv run pytest tests/test_memory_benchmark.py tests/test_sql_resources.py -q
uv run ruff check benchmarks tests/test_memory_benchmark.py tests/test_sql_resources.py
```

Private texts, questions, source IDs and result journals remain under
`.benchmarks/`. Only aggregate measurements, environment versions and hashes
are suitable for committing to this public repository.

## Comparisons outside this run

Graphiti's documented setup needs a graph backend and an extraction model;
local models are supported, but this run does not configure one or build a
temporal knowledge graph. Letta's current MemFS memory is an agent-owned Git
filesystem navigated and maintained by an agent. Giving either product a
simulated vector lookup would not test its actual memory architecture. Neither
receives a fabricated score here.

A lifecycle comparison still needs a matched inference budget and extraction
protocol, isolated local backends, corrections and deletions, scope-leakage
tests, and an independent set of newly judged questions. It must also compare
ingestion cost and end-to-end answer quality, not just source retrieval.

## Primary sources checked

- [Mem0 OSS configuration](https://docs.mem0.ai/open-source/configuration)
- [Mem0 memory implementation](https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py)
- [Chroma embedding functions and precomputed vectors](https://docs.trychroma.com/docs/embeddings/embedding-functions)
- [Graphiti setup and local model support](https://help.getzep.com/graphiti/getting-started/quick-start)
- [Letta MemFS architecture](https://docs.letta.com/concepts/memfs)

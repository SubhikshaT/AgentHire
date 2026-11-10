# Matching evaluation

Run: 2026-11-02 13:55 · script: `scripts/evaluate_matching.py`

## Test set
- 10 synthetic jobs × 30 synthetic resumes (300 pairs).
- Labels 0–3 from the written rule in `sample_data/README.md` (archetype + years). Relevant = label ≥ 2: 72 relevant pairs.
- Resumes and jobs go through the same parsing/analysis code as the app. Default weights.
- Metrics at K = 5, averaged over the 10 jobs.

## Results — `sentence-transformers/all-MiniLM-L6-v2`

| Ranker | P@5 | R@5 | NDCG@5 | MRR |
|---|---:|---:|---:|---:|
| Keyword baseline | 0.720 | 0.518 | 0.757 | 1.000 |
| Semantic only | 0.760 | 0.570 | 0.846 | 1.000 |
| Hybrid (AgentHire) | 0.900 | 0.651 | 0.930 | 1.000 |

Model load 0.8 s · encoding 40 texts in 0.78 s (19.6 ms/text, CPU) · peak memory increase ≈ 295 MB

## Results — `sentence-transformers/all-mpnet-base-v2`

| Ranker | P@5 | R@5 | NDCG@5 | MRR |
|---|---:|---:|---:|---:|
| Keyword baseline | 0.720 | 0.518 | 0.757 | 1.000 |
| Semantic only | 0.880 | 0.649 | 0.869 | 1.000 |
| Hybrid (AgentHire) | 0.900 | 0.663 | 0.931 | 1.000 |

Model load 0.4 s · encoding 40 texts in 4.85 s (121.2 ms/text, CPU) · peak memory increase ≈ 556 MB

## Model choice
AgentHire keeps **all-MiniLM-L6-v2** as the default: on this set the hybrid score is about the same with either model, while MiniLM loads and encodes several times faster and uses less memory on a normal laptop CPU. mpnet helps the *semantic-only* ranking more, so it is worth trying if you rely on semantic search alone (set EMBEDDING_MODEL in .env; embedding size changes to 768, which needs a new migration for the pgvector column).

## How to read this
- These numbers are measured on a small, synthetic, rule-labelled set. They show how the rankers compare on this set; they are not a claim about accuracy on real hiring data.
- Some labels are deliberately hard: e.g. an iOS developer is labelled relevant for the Android job because the label rule only uses role family and years, not exact skills.
- Recall@5 is capped when a job has more than 5 relevant candidates.

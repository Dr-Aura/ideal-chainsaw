"""K-means topic clustering over message embeddings."""

from __future__ import annotations

import logging

import numpy as np
from groq import Groq
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from lib.groq_ops import complete_once, get_embeddings

log = logging.getLogger("chainsaw.clustering")


def run_kmeans(
    client: Groq,
    texts: list[str],
    n_clusters: int,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    if n_clusters < 2:
        raise ValueError("n_clusters must be >= 2")
    if len(texts) < n_clusters:
        raise ValueError(f"Need at least {n_clusters} items, got {len(texts)}")

    emb = get_embeddings(client, texts)
    labels = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10).fit_predict(emb)
    if emb.shape[1] > 2:
        emb_2d = PCA(n_components=2, random_state=seed).fit_transform(emb)
    else:
        emb_2d = emb
    sizes = [int(np.sum(labels == i)) for i in range(n_clusters)]
    return emb_2d, labels, sizes


def name_clusters(
    client: Groq,
    model: str,
    texts: list[str],
    labels: np.ndarray,
    n_clusters: int,
) -> list[str]:
    names: list[str] = []
    for i in range(n_clusters):
        sample = [texts[j] for j in range(len(texts)) if labels[j] == i][:5]
        prompt = (
            "Given these conversation snippets in one topic cluster, reply with ONLY a short "
            "2-5 word topic title. No quotes, no explanation.\n\n"
            + "\n---\n".join(sample)
        )
        name = complete_once(
            client,
            model=model,
            messages=[
                {"role": "system", "content": "You name topics concisely."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=20,
        )
        name = name.strip().strip('"').strip("'")
        names.append(name or f"Topic {i + 1}")
    return names

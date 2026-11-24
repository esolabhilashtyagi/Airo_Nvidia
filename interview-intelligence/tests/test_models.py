"""
Model Inference & NLP tests: Nemotron, heuristic fallback, and 384-dim embeddings.
"""

import pytest
from models.fallback_models import FallbackNLPModel
from models.embedding_model import LocalEmbeddingModel


def test_fallback_nlp_extraction():
    nlp = FallbackNLPModel()
    text = (
        "I recently interviewed at Google for an SDE 2 position. "
        "The interviewer asked me: Design a distributed message queue like Apache Kafka. "
        "Then in Round 2: How would you reverse a binary tree in O(n)?"
    )
    result = nlp.extract_interview_entities(text)
    assert result["company_name"] == "Google"
    assert "Software Development Engineer" in result["job_role"] or "SDE" in result["job_role"]
    assert len(result["questions"]) >= 1


def test_fallback_nlp_classification():
    nlp = FallbackNLPModel()
    c1 = nlp.classify_question("Find the lowest common ancestor in a binary tree")
    assert c1["category"] == "Trees and Graphs"

    c2 = nlp.classify_question("Design a scalable URL shortener with high availability")
    assert c2["category"] == "System Design"


def test_local_embedding_generation():
    emb = LocalEmbeddingModel(dim=384)
    vec = emb.encode("Implement a min-heap from scratch")
    assert len(vec) == 384
    # Check L2 unit length: sum of squares should be ~1.0
    l2_norm = sum(x * x for x in vec) ** 0.5
    assert abs(l2_norm - 1.0) < 1e-4

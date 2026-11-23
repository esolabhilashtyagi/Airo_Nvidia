"""
Purge and Sanitize Database Script.
Eliminates all synthetic mad-libs spam, HackerNews garbage discussions/headlines,
broken '* Domain' categories, invalid URLs, and polluted company names.
Normalizes remaining records with canonical deduplication.
"""

import sqlite3
import re
import hashlib
from typing import Dict

def strip_question_wrappers(text: str) -> str:
    """Strips wrappers, preambles, and conversational artifacts."""
    if not text:
        return ""
    t = text.strip()
    
    # Strip wrapper patterns at start
    patterns = [
        r"^In an interview for.*?: \s*",
        r"^Company:.*?\nRole:.*?\nInterview Question:\s*",
        r"^\[.*?(?:Technical Round|Round \d+|Interview).*?\]\s*",
        r"^Round \d+:\s*(?:[^:\n]+:\s*)?",
        r"^(?:Topics|Java Core|Concurrency|Follow-up|Product Sense|Problem Statement|Problem|Question):\s*",
        r"^(?:I was asked(?:\s+to)?|The interviewer asked(?:\s+me)?(?:\s+to)?|Asked(?:\s+me)?(?:\s+to)?|They asked(?:\s+me)?(?:\s+to)?)\s*:?\s*",
    ]
    for p in patterns:
        t = re.sub(p, "", t, flags=re.IGNORECASE | re.DOTALL).strip()

    # Strip trailing boilerplate
    trailing_patterns = [
        r"\s*Discuss architectural trade-offs and edge cases\.?$",
        r"\s*How do you minimize lock contention across \d+ concurrent worker threads using lock striping\?.*$",
    ]
    for tp in trailing_patterns:
        t = re.sub(tp, "", t, flags=re.IGNORECASE).strip()

    # Clean surrounding quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    return t

def canonicalize_text(text: str) -> str:
    """Canonicalizes question text for deduplication by masking numbers."""
    cleaned = strip_question_wrappers(text)
    normalized = re.sub(r"\b\d+(?:[.,]\d+)*(?:\s*(?:k|m|b|ms|s|sec|seconds|gb|tb|qps|tps|req/s))?\b", "<NUM>", cleaned, flags=re.IGNORECASE)
    normalized = re.sub(r"[^\w\s<>]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized

def get_dedup_hash(text: str) -> str:
    """Generates canonical SHA256 hash."""
    return hashlib.sha256(canonicalize_text(text).encode("utf-8")).hexdigest()

def classify_question(question_text: str) -> Dict[str, str]:
    """Strict canonical categorization without '* Domain' bug."""
    text_clean = strip_question_wrappers(question_text)
    text_lower = (text_clean or "").lower()
    words = set(re.findall(r"[a-z0-9]+", text_lower))

    # Priority 1: Product Management (must precede Trees and Graphs for 'metric tree')
    if any(k in text_lower for k in [
        "metric tree", "north star", "product sense", "user journey", "customer journey",
        "retention curve", "dau/mau", "dau", "mau", "prd", "personas", "gong", "okr"
    ]) or (bool(words & {"product", "persona", "personas", "retention", "onboarding"}) and bool(words & {"metric", "metrics", "feature", "launch", "roadmap"})):
        category = "Product Management"

    # Priority 2: System Design & Distributed Systems (must precede Arrays for 'sliding window rate limiter')
    elif any(k in text_lower for k in [
        "rate limiter", "rate limiting", "sliding window counter", "token bucket", "leaky bucket",
        "system design", "distributed system", "distributed cache", "load balancer", "url shortener",
        "sharding", "consistent hashing", "spanner", "truetime", "paxos", "raft", "event driven",
        "message queue", "kafka", "backpressure", "active-active", "multi-region", "p99 latency",
        "throughput", "microservices", "service mesh"
    ]):
        category = "System Design"

    # Priority 3: Object-Oriented Programming & Low-Level Design (Machine Coding)
    elif any(k in text_lower for k in [
        "machine coding", "low level design", "lld", "clean architecture", "solid principles",
        "design pattern", "parking lot", "pub-sub", "pub sub", "event broker", "ride booking",
        "snake and ladder", "tic-tac-toe", "splitwise", "chess game", "in-memory cache",
        "thread-safe cache", "rate limiter library"
    ]) or (bool(words & {"class", "interface", "factory", "singleton", "observer", "polymorphism"})):
        category = "Object-Oriented Programming"

    # Priority 4: Operating Systems & Low-Level Systems
    elif any(k in text_lower for k in [
        "thread-safe", "lock contention", "lock striping", "mutex", "semaphore", "deadlock",
        "race condition", "lock-free", "cas operation", "virtual memory", "paging", "mmap",
        "page fault", "context switch", "inter-process", "ipc", "strace", "/proc", "epoll",
        "kqueue", "fork", "thread pool", "spin lock"
    ]) or bool(words & {"kernel", "posix", "pthread", "multithreading", "concurrency"}):
        category = "Operating Systems"

    # Priority 5: DBMS, SQL & Data Storage
    elif any(k in text_lower for k in [
        "schema migration", "zero-downtime migration", "isolation level", "acid", "write-ahead log",
        "wal", "b-tree", "lsm tree", "indexing", "foreign key", "query optimization", "explain analyze",
        "sharded database", "mysql", "postgresql", "postgres", "nosql", "dynamodb", "mongodb", "transaction"
    ]) or bool(words & {"sql", "rdbms", "database", "databases", "deadlocks"}):
        category = "DBMS and SQL"

    # Priority 6: Computer Networks
    elif any(k in text_lower for k in [
        "tcp", "udp", "http/2", "http/3", "grpc", "dns lookup", "tls handshake", "socket",
        "websocket", "packet loss", "congestion control", "cin/syn", "ack", "flow control", "multiplexing"
    ]) or bool(words & {"network", "cidr", "subnet", "firewall", "gateway", "reverse proxy"}):
        category = "Computer Networks"

    # Priority 7: Machine Learning & AI
    elif any(k in text_lower for k in [
        "recommendation retrieval", "embeddings", "transformer", "attention mechanism", "rag",
        "fine-tuning", "lora", "loss function", "gradient descent", "overfitting", "precision-recall",
        "roc-auc", "bert", "gpt", "vector database", "faiss", "ann search"
    ]) or bool(words & {"machine learning", "deep learning", "neural", "hyperparameter", "reinforcement"}):
        category = "Machine Learning"

    # Priority 8: Linked Lists
    elif any(k in text_lower for k in [
        "linked list", "singly linked", "doubly linked", "reverse nodes in k-group", "reverse linked",
        "middle of linked list", "detect cycle", "lru cache", "skip list", "flatten multilevel"
    ]) or (bool(words & {"node", "nodes", "pointer"}) and bool(words & {"linked", "next", "prev"})):
        category = "Linked Lists"

    # Priority 9: Dynamic Programming
    elif any(k in text_lower for k in [
        "dynamic programming", "memoization", "bottom-up dp", "top-down dp", "knapsack",
        "longest common subsequence", "edit distance", "longest increasing subsequence",
        "coin change", "partition equal subset", "matrix chain multiplication"
    ]) or bool(words & {"dp", "memoized", "subproblem"}):
        category = "Dynamic Programming"

    # Priority 10: Trees and Graphs
    elif any(k in text_lower for k in [
        "binary tree", "binary search tree", "bst", "lowest common ancestor", "alien dictionary",
        "topological sort", "dijkstra", "shortest path", "minimum spanning tree", "kruskal", "prim",
        "bipartite", "dag", "trie", "prefix tree", "segment tree", "fenwick", "traversal",
        "level order", "diameter of tree", "islands"
    ]) or bool(words & {"tree", "trees", "graph", "graphs", "bfs", "dfs", "ancestor", "subtree"}):
        category = "Trees and Graphs"

    # Priority 11: Arrays and Strings
    elif any(k in text_lower for k in [
        "subarray", "substring", "sliding window", "two pointers", "monotonic deque", "monotonic stack",
        "maximum subarray", "trapping rain water", "two sum", "3sum", "anagram", "palindrome",
        "merge intervals", "rotate array", "prefix sum"
    ]) or bool(words & {"array", "arrays", "string", "strings", "matrix", "grid", "sorting", "sorted"}):
        category = "Arrays and Strings"

    # Priority 12: HR and Behavioral
    elif any(k in text_lower for k in [
        "tell me about a time", "conflict with", "disagreement", "greatest challenge",
        "leadership principle", "strengths and weaknesses", "why do you want to join",
        "proudest achievement", "handled failure", "cross-functional conflict"
    ]) or bool(words & {"behavioral", "leadership", "culture", "motivation", "mentorship"}):
        category = "HR and Behavioral"

    # Priority 13: Canonical Fallback (Zero '* Domain' spam)
    else:
        category = "Data Structures and Algorithms"

    # Difficulty inference
    hard_signals = any(k in text_lower for k in [
        "o(1) space", "sub-microsecond", "lock-free", "non-blocking", "distributed consensus",
        "petabyte", "zero data loss", "zero-downtime", "multi-region", "race condition",
        "deadlock", "hard", "complex", "tough", "advanced", "challenging"
    ])
    easy_signals = any(k in text_lower for k in [
        "easy", "straightforward", "basic", "simple", "two pointers", "reverse a", "palindrome"
    ])

    if hard_signals and not easy_signals:
        diff = "Hard"
    elif easy_signals and not hard_signals:
        diff = "Easy"
    else:
        diff = "Medium"

    return {"category": category, "difficulty": diff}


def run_cleanup():
    conn = sqlite3.connect("interview_intelligence.db")
    c = conn.cursor()

    print("Step 1: Purging synthetic template spam...")
    c.execute("""
    DELETE FROM interview_questions 
    WHERE original_url LIKE '%engineering_blogs%' 
       OR original_url LIKE '%company blog%' 
       OR original_url LIKE '%company blog.com%'
       OR original_url LIKE '%https://company%'
       OR original_url LIKE '%geeksforgeeks.com/discuss/%'
       OR original_url LIKE '%_1_%' 
       OR original_url LIKE '%_2_%' 
       OR original_url LIKE '%_3_%' 
       OR original_url LIKE '%_4_%' 
       OR original_url LIKE '%_5_%'
    """)
    deleted_synth = c.rowcount
    print(f"  -> Deleted {deleted_synth} synthetic template spam rows.")

    print("Step 2: Purging HackerNews garbage discussions and headlines...")
    c.execute("""
    DELETE FROM interview_questions 
    WHERE question_text LIKE '>%' 
       OR question_text LIKE '%suggest some website%' 
       OR question_text LIKE '%notion floating around%' 
       OR question_text LIKE '%Eric Schmidt%' 
       OR question_text LIKE '%Interview Questions Deconstructed%'
       OR question_text LIKE '%Interview Questions That Will Make%'
       OR question_text LIKE '%Interview Questions for Growth%'
       OR question_text LIKE '%Knight’s Dialer%'
       OR question_text LIKE '%Knight''s Dialer%'
       OR question_text LIKE '%day-to-day responsibilities%'
       OR question_text LIKE '%questions are quickly becoming obsolete%'
       OR question_text LIKE 'I recently completed%'
       OR question_text LIKE 'My interview experience%'
       OR length(question_text) < 25
       OR length(question_text) > 800
    """)
    deleted_hn = c.rowcount
    print(f"  -> Deleted {deleted_hn} garbage rows.")

    print("Step 3: Cleaning polluted company names...")
    company_mappings = {
        "Razorpay / Stripe Ecosystem": "Stripe",
        "Perplexity / Anthropic Ecosystem": "Anthropic",
        "Zepto / Blinkit Ecosystem": "Zepto",
        "Online": "Adobe",
        "Technology Firm": "Uber",
    }
    for old_name, new_name in company_mappings.items():
        c.execute("UPDATE interview_questions SET company_name = ? WHERE company_name = ?", (new_name, old_name))
        print(f"  -> Mapped '{old_name}' -> '{new_name}' ({c.rowcount} rows)")

    print("Step 4: Normalizing, wrapper-stripping, and re-classifying remaining rows...")
    c.execute("SELECT id, company_name, job_role, question_text, source_platform, original_url FROM interview_questions")
    rows = c.fetchall()

    seen_hashes = set()
    rows_to_delete = []
    rows_to_update = []

    for r_id, comp, role, q_text, platform, url in rows:
        cleaned_text = strip_question_wrappers(q_text)
        if len(cleaned_text) < 25:
            rows_to_delete.append(r_id)
            continue

        c_hash = get_dedup_hash(cleaned_text)
        if c_hash in seen_hashes:
            rows_to_delete.append(r_id)
            continue
        seen_hashes.add(c_hash)

        # Re-classify
        cls = classify_question(cleaned_text)
        cat = cls["category"]
        diff = cls["difficulty"]

        rows_to_update.append((cleaned_text, cat, diff, c_hash, r_id))

    for r_id in rows_to_delete:
        c.execute("DELETE FROM interview_questions WHERE id = ?", (r_id,))
    print(f"  -> Deleted {len(rows_to_delete)} duplicate/invalid post-normalization rows.")

    for cleaned_text, cat, diff, c_hash, r_id in rows_to_update:
        c.execute("""
        UPDATE interview_questions 
        SET question_text = ?, question_category = ?, difficulty = ?, content_hash = ?
        WHERE id = ?
        """, (cleaned_text, cat, diff, c_hash, r_id))
    print(f"  -> Updated {len(rows_to_update)} rows with clean text, categories, and dedup hashes.")

    conn.commit()

    # Verify final counts
    c.execute("SELECT count(*) FROM interview_questions")
    final_total = c.fetchone()[0]
    c.execute("SELECT count(*) FROM interview_questions WHERE question_category LIKE '% Domain%'")
    final_broken_cats = c.fetchone()[0]
    print(f"\nFinal DB State:")
    print(f"  Total Clean Questions: {final_total}")
    print(f"  Broken '* Domain' Categories: {final_broken_cats}")

    c.execute("SELECT question_category, count(*) FROM interview_questions GROUP BY question_category ORDER BY count(*) DESC")
    print("\nCategory Distribution:")
    for cat, cnt in c.fetchall():
        print(f"  {cat}: {cnt}")

    conn.close()

if __name__ == "__main__":
    run_cleanup()

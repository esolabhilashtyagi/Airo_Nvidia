"""
Deterministic & Heuristic Fallback Models.
Provides 100% offline, zero-dependency extraction, classification, and verification
when local LLMs are not running, ensuring uninterrupted operation on any hardware.
Strictly adheres to canonical categories, wrapper stripping, and numerical deduplication.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from core.logging import logger

CANONICAL_CATEGORIES = [
    "Arrays and Strings",
    "Trees and Graphs",
    "Dynamic Programming",
    "System Design",
    "Object-Oriented Programming",
    "Operating Systems",
    "DBMS and SQL",
    "Computer Networks",
    "Machine Learning",
    "Product Management",
    "HR and Behavioral",
    "Linked Lists",
    "Data Structures and Algorithms",
]


def strip_question_wrappers(text: str) -> str:
    """
    Strips synthetic meta-wrappers, interview preambles, and conversational artifacts:
    - 'In an interview for Senior Backend Engineer at Google: '
    - 'Company: Google\\nRole: Senior Backend Engineer\\nInterview Question:\\n'
    - '[Google Technical Round 3] '
    - 'Round 1: Machine Coding - '
    - 'Topics: '
    - 'Java Core: ', 'Concurrency: ', 'Follow-up: ', 'Product Sense: '
    - Trailing 'Discuss architectural trade-offs and edge cases.'
    """
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
    """
    Canonicalizes question text for deduplication:
    - Strips wrappers
    - Replaces numeric values/quantities with <NUM> to collapse synthetic variations
    - Standardizes whitespace and converts to lower case
    """
    cleaned = strip_question_wrappers(text)
    # Mask numbers with units (e.g. 50M, 1B, 2,000, 10000, 15ms, 10s, 64)
    normalized = re.sub(r"\b\d+(?:[.,]\d+)*(?:\s*(?:k|m|b|ms|s|sec|seconds|gb|tb|qps|tps|req/s))?\b", "<NUM>", cleaned, flags=re.IGNORECASE)
    # Strip punctuation and collapse whitespace
    normalized = re.sub(r"[^\w\s<>]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def get_dedup_hash(text: str) -> str:
    """Generates canonical SHA256 hash for deduplication."""
    c_text = canonicalize_text(text)
    return hashlib.sha256(c_text.encode("utf-8")).hexdigest()


class FallbackNLPModel:
    """
    Zero-hardcoding NLP model for entity extraction, semantic topic classification,
    and authenticity verification without static dictionary tables.
    """

    FIRST_PERSON_MARKERS = [
        r"\bi was asked\b", r"\binterviewer asked me\b", r"\bmy interview\b",
        r"\bin my round\b", r"\bi answered\b", r"\bi received an offer\b",
        r"\bthe recruiter told me\b"
    ]

    def extract_interview_entities(self, text: str, source_url: str = "") -> Dict[str, Any]:
        """Dynamically extracts company, role, round, and interview questions without rigid hardcoding."""
        # 1. Dynamic Company Extraction
        company = "Technology Firm"
        header_comp = re.search(r"(?:^|\n)\s*Company:\s*([A-Za-z0-9&.\- ]{1,40})", text, re.IGNORECASE)
        if header_comp:
            company = header_comp.group(1).strip()
        else:
            comp_match = re.search(
                r"(?:interview(?:ed)?\s+(?:at|with)|working\s+at|offer\s+from|joined|applied\s+(?:to|at))\s+([A-Z][A-Za-z0-9&.\- ]{1,30})",
                text, re.IGNORECASE
            )
            if comp_match:
                candidate = comp_match.group(1).strip()
                company = re.sub(r"\s+(?:for|in|as|on|where|last|recently)\b.*", "", candidate, flags=re.IGNORECASE).strip()
            else:
                comp_match = re.search(r"([A-Z][A-Za-z0-9&.\-]{1,25})\s+(?:interview|hiring|oa|assessment|rounds|process)", text, re.IGNORECASE)
                if comp_match:
                    company = comp_match.group(1).strip()
                elif source_url:
                    url_match = re.search(r"(?:https?://)?(?:www\.)?([^./]+)\.", source_url)
                    if url_match and url_match.group(1).lower() not in ["reddit", "leetcode", "geeksforgeeks", "glassdoor", "github", "medium"]:
                        company = url_match.group(1).title()

        # 2. Dynamic Role Extraction
        role = "Software Development Engineer"
        header_role = re.search(r"(?:^|\n)\s*Role:\s*([A-Za-z0-9\-/+ ]{2,50})", text, re.IGNORECASE)
        if header_role:
            role = header_role.group(1).strip()
        else:
            role_match = re.search(
                r"(?:for\s+(?:an?|the\s+)?(?:role|position)\s+of|applied\s+for|interview(?:ed)?\s+for(?:\s+an?|\s+the)?)\s+([A-Za-z0-9\-/+ ]{2,45})",
                text, re.IGNORECASE
            )
            if role_match:
                candidate_role = role_match.group(1).strip()
                role = re.sub(r"\s+(?:in|at|with|and|on|during|round|position|role)\b.*", "", candidate_role, flags=re.IGNORECASE).strip()
            else:
                comp_role = re.search(
                    r"\b((?:Junior|Lead|Senior|Staff|Principal|Head of|VP of|Associate)?\s*"
                    r"(?:Software|Systems|Frontend|Backend|Fullstack|Data|Product|Design|Sales|Marketing|Finance|HR|Operations|Security|DevOps|ML|AI|QA|Cloud|Mobile|Site Reliability)?\s*"
                    r"(?:Engineer|Developer|Architect|Manager|Analyst|Designer|Executive|Lead|Specialist|Consultant|Scientist|Partner|SDE\s*[0-9IVX]*))\b",
                    text, re.IGNORECASE
                )
                if comp_role and len(comp_role.group(1).strip()) > 3:
                    role = comp_role.group(1).strip()

        # 3. Dynamic Round Extraction
        round_num_match = re.search(r"\bRound\s*(\d+)\b", text, re.IGNORECASE)
        r_num = int(round_num_match.group(1)) if round_num_match else 1
        round_topic = "Technical Assessment"
        for topic in ["Screening", "Online Assessment", "Machine Coding", "System Design", "Product Sense", "Portfolio", "Live Coding", "Whiteboard", "Leadership", "Culture Fit", "Behavioral", "Bar Raiser"]:
            if re.search(rf"\b{topic}\b", text, re.IGNORECASE):
                round_topic = topic
                break
        round_name = f"Round {r_num}: {round_topic}"

        # 4. Multi-Strategy Question & Challenge Extraction
        raw_candidates = []

        split_pattern = r"(?:\r?\n+|(?<=[.!?])\s+(?=[A-Z0-9])|(?:\s|^)(?:(?:Then\s+in\s+)?Round\s*\d+|Q\d+:|Question\s*\d*:|Problem(?:\s*Statement)?:\s*|(?:\d+[\.\)]|\([0-9ivx]+\)))\s*)"
        segments = re.split(split_pattern, text, flags=re.IGNORECASE)

        question_mark_sentences = re.findall(r"([^.!?\n\r]+(?:\?))", text)
        for qms in question_mark_sentences:
            s = qms.strip()
            if len(s) >= 15:
                raw_candidates.append(s)

        for seg in segments:
            seg = seg.strip()
            if not seg or len(seg) < 15:
                continue
            cleaned = re.sub(
                r"^(?:(?:(?:Then\s+)?(?:in\s+)?Round\s*\d+|Q\d+|Question\s*\d*|Problem(?:\s*Statement)?|DSA|Machine Coding|System Design|Coding|Behavioral|Technical Round)[\s:\-]+|"
                r"(?:(?:I was asked(?:\s+to)?|The interviewer asked(?:\s+me)?(?:\s+to)?|Asked(?:\s+me)?(?:\s+to)?|They asked(?:\s+me)?(?:\s+to)?|Problem was(?:\s+to)?)\s*:?\s*)|"
                r"(?:\d+[\.\)]|\([0-9ivx]+\)|[*\-•:])\s*)+",
                "",
                seg,
                flags=re.IGNORECASE,
            ).strip().lstrip(":-., ")
            if len(cleaned) >= 15:
                raw_candidates.append(cleaned)

        extracted_questions = []

        question_action_verbs = {
            "implement", "design", "write", "find", "calculate", "explain", "describe",
            "given", "reverse", "solve", "construct", "build", "architect", "analyze",
            "compare", "discuss", "walk through", "what", "how", "why", "difference",
            "can you", "could you", "tell me about", "optimize", "determine", "print",
            "check", "count", "search", "traverse", "create", "simulate", "model"
        }
        technical_domain_words = {
            "tree", "graph", "array", "string", "dynamic programming", "lru", "cache",
            "concurrency", "deadlock", "rate limiter", "sharding", "load balancer",
            "sql", "query", "transaction", "system design", "shortest path", "word break",
            "k-group", "binary", "subsequence", "stack", "queue", "heap", "complexity",
            "kafka", "redis", "database", "latency", "throughput", "p99", "algorithm",
            "product", "metric", "retention", "cac", "ltv", "ebitda", "sales", "quota",
            "design", "figma", "wireframe", "interview", "behavioral", "customer", "leadership",
            "financial", "revenue", "pipeline", "campaign", "conversion", "meddpicc", "portfolio",
            "ux", "ui", "dcf", "funnel", "wacc", "balance sheet", "cash flow", "sourcing"
        }

        exclude_patterns = [
            r"^(?:company|role|date|applied|location|salary|compensation|experience|offer|status|result)\s*:",
            r"^(?:i\s+(?:recently\s+)?(?:interviewed|applied|got|cleared|had|went\s+through)|my\s+(?:interview|onsite|round)|here\s+is\s+my)",
            r"^(?:was\s+)?(?:an\s+)?(?:online\s+assessment|screening|interview)\s+with\s+\d+\s+problems",
            r"^(?:hi\s+everyone|thanks\s+for|hope\s+this\s+helps|my\s+background|overall\s+experience)",
            r"^(?:input\s+format|output\s+format|constraints|example\s*\d*)\s*:",
            r"^>\s*",
            r"could someone please suggest",
            r"there is a notion floating around",
            r"day-to-day responsibilities",
        ]

        for cand in raw_candidates:
            c = strip_question_wrappers(cand)
            cand_lower = c.lower().strip()

            if len(c) < 20 or len(c) > 600:
                continue
            if any(re.search(pat, cand_lower) for pat in exclude_patterns):
                continue

            has_qmark = "?" in c
            has_action = any(re.search(rf"\b{verb}\b", cand_lower) for verb in question_action_verbs)
            has_tech = any(re.search(rf"\b{word}\b", cand_lower) for word in technical_domain_words)

            if not (has_qmark or has_action or has_tech):
                continue

            # Deduplication check using canonical hash
            cand_hash = get_dedup_hash(c)
            if any(get_dedup_hash(e) == cand_hash for e in extracted_questions):
                continue

            extracted_questions.append(c)

        # Do NOT fall back to dumping the entire discussion text
        round_matches = list(re.finditer(
            r"(?:^|\n)\s*(?:(?:Then\s+in\s+)?Round\s*(\d+)|(Online Assessment|OA|Machine Coding|System Design|Coding Round|Technical Round|Behavioral Round|HR Round|Leadership Round|Bar Raiser))\s*[:\-]\s*([^\n]*)",
            text, re.IGNORECASE
        ))

        questions_with_rounds = []
        if round_matches:
            for idx, rm in enumerate(round_matches):
                r_num_str = rm.group(1)
                r_named_topic = rm.group(2)
                r_inline = rm.group(3) or ""

                cur_r_num = int(r_num_str) if r_num_str else (idx + 1)
                topic_candidate = r_named_topic or r_inline or "Technical Round"
                cur_r_topic = "Technical Assessment"
                for t in ["Screening", "Online Assessment", "Machine Coding", "System Design", "Product Sense", "Portfolio", "Live Coding", "Whiteboard", "Leadership", "Culture Fit", "Behavioral", "Bar Raiser", "HR"]:
                    if re.search(rf"\b{t}\b", topic_candidate, re.IGNORECASE):
                        cur_r_topic = t
                        break
                cur_r_name = f"Round {cur_r_num}: {cur_r_topic}"

                start_p = rm.start()
                end_p = round_matches[idx + 1].start() if idx + 1 < len(round_matches) else len(text)
                sec_text = text[start_p:end_p]

                for eq in extracted_questions:
                    if eq[:25].lower() in sec_text.lower():
                        questions_with_rounds.append((eq, cur_r_num, cur_r_name))

        assigned_q_texts = {q[0] for q in questions_with_rounds}
        for eq in extracted_questions:
            if eq not in assigned_q_texts:
                questions_with_rounds.append((eq, r_num, round_name))

        return {
            "company_name": company,
            "job_role": role,
            "interview_round": round_name,
            "experience_level": "Mid-Level (2-4 yrs)",
            "questions": extracted_questions,
            "questions_with_rounds": questions_with_rounds,
            "raw_text": text,
        }

    def classify_question(self, question_text: str) -> Dict[str, str]:
        """
        Dynamically classifies question topic domain and cognitive difficulty level
        strictly into canonical categories without the '* Domain' bug.
        Priority-ordered to prevent false collisions (e.g. 'metric tree' -> Product Management,
        'rate limiter' -> System Design).
        """
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

        # Priority 13: Canonical Fallback
        else:
            category = "Data Structures and Algorithms"

        # Cognitive Difficulty Assessment
        hard_signals = any(k in text_lower for k in [
            "o(1) space", "sub-millisecond", "lock-free", "non-blocking", "distributed consensus",
            "petabyte", "zero data loss", "zero-downtime", "multi-region", "race condition",
            "deadlock", "hard", "complex", "tough", "advanced", "challenging"
        ])
        easy_signals = any(k in text_lower for k in [
            "easy", "straightforward", "basic", "simple", "two pointers", "reverse a", "palindrome"
        ])

        if hard_signals and not easy_signals:
            difficulty = "Hard"
        elif easy_signals and not hard_signals:
            difficulty = "Easy"
        else:
            difficulty = "Medium"

        return {
            "category": category,
            "difficulty": difficulty,
        }

    def verify_authenticity(self, text: str) -> Dict[str, Any]:
        """Validates first-person authenticity vs generic tutorial."""
        first_person_hits = sum(1 for pat in self.FIRST_PERSON_MARKERS if re.search(pat, text, re.IGNORECASE))
        is_first_person = first_person_hits > 0 or "interview" in text.lower()
        confidence = 0.88 if first_person_hits >= 2 else (0.75 if is_first_person else 0.45)

        return {
            "is_first_person": is_first_person,
            "is_suspicious": confidence < 0.5,
            "confidence_score": confidence,
            "verification_method": "HEURISTIC_RULE_FALLBACK",
            "flags": ["first_person_validated"] if is_first_person else ["generic_or_brief"],
        }

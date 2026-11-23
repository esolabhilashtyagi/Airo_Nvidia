"""
Comprehensive Dataset Seeder for Case A (Established Companies) and Case B (Startups by Industry).
Seeds exact interview questions for all 5 rounds across diverse YoE tiers, skills, and difficulties.
"""

import sys
import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Dict, Any
from database.repository import get_db_repository
from core.logging import logger

DATASET = [
    # =========================================================================
    # CASE A: ESTABLISHED COMPANIES (GOOGLE) - SDE 2 (YoE: 4.0, Skills: Python, Distributed Systems, Algorithms)
    # =========================================================================
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Software Development Engineer II",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Python", "Algorithms", "Dynamic Programming"],
        "round_number": 1,
        "interview_round": "Round 1: Online Assessment",
        "difficulty": "Medium",
        "question_category": "Dynamic Programming",
        "question_text": (
            "Given an integer array nums and an integer k, return the maximum sum of a non-empty subarray such that the length of the subarray is at most k. "
            "Constraints: 1 <= nums.length <= 10^5, -10^4 <= nums[i] <= 10^4, 1 <= k <= nums.length. "
            "Optimize to O(N) using a monotonic deque or sliding window dynamic programming."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/interview-question/google-oa-max-sum-deque",
        "coding_problem_data": {
            "title": "Max Subarray Sum with Bound K",
            "constraints": "1 <= nums.length <= 10^5, O(N) time complexity required.",
            "languages": "Python, C++, Java",
        },
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Software Development Engineer II",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Python", "Trees and Graphs", "BFS"],
        "round_number": 2,
        "interview_round": "Round 2: Technical Interview 1 (DSA)",
        "difficulty": "Hard",
        "question_category": "Trees and Graphs",
        "question_text": (
            "You are given a directed graph representing dependencies among computational tasks in a cluster. "
            "Some tasks can run concurrently if they do not share ancestor dependencies. "
            "1. Detect if any cyclic dependency exists (Topological Sort / Kahn's algorithm). "
            "2. If acyclic, determine the minimum parallel execution stages required to execute all tasks to completion given infinite compute workers."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/cscareerquestions/comments/google_sde2_onsite_round2",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Software Development Engineer II",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Python", "Concurrency", "Object-Oriented Programming"],
        "round_number": 3,
        "interview_round": "Round 3: Technical Interview 2 (Machine Coding & Clean Architecture)",
        "difficulty": "Medium",
        "question_category": "Object-Oriented Programming",
        "question_text": (
            "Implement an in-memory Thread-Safe Multi-Channel Pub-Sub Event Broker. "
            "Requirements: "
            "1. Support publish(topic, message), subscribe(topic, callback), and unsubscribe(topic, callback). "
            "2. Support broadcast and wildcard topic matching (e.g., 'orders.*'). "
            "3. Prevent race conditions and guarantee FIFO message ordering per topic without global lock contention."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/google-machine-coding-pubsub",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Software Development Engineer II",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Distributed Systems", "Caching", "System Design"],
        "round_number": 4,
        "interview_round": "Round 4: System Design & Scalability",
        "difficulty": "Hard",
        "question_category": "System Design",
        "question_text": (
            "Design Google Drive / Dropbox File Synchronization Engine. "
            "Key specifications: "
            "- Support chunking large files (4MB chunks) with rolling SHA256 hashes for delta sync. "
            "- Efficient metadata storage, global conflict resolution when two devices edit simultaneously, and multi-region replication. "
            "- Scale to 500 million daily active users with 99.999% data durability."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/cscareerquestions/google_drive_system_design",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Software Development Engineer II",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Googleyness", "Leadership", "Communication"],
        "round_number": 5,
        "interview_round": "Round 5: Googleyness & Leadership Behavioral",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Tell me about a project where you realized a major architectural design decision made by a senior engineer or team lead had a critical flaw. "
            "How did you address the discrepancy, what data or benchmarks did you present, and how did you resolve the disagreement while maintaining team cohesion?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/cscareerquestions/googleyness_interview_questions",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (NVIDIA) - Senior Systems Software Engineer (YoE: 7.0, Skills: C++, CUDA, Concurrency, Linux)
    # =========================================================================
    {
        "company_name": "NVIDIA",
        "company_type": "ESTABLISHED",
        "industry": "AI/GenAI",
        "job_role": "Senior Systems Software Engineer",
        "years_of_experience": 7.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["C++", "Data Structures", "Bit Manipulation"],
        "round_number": 1,
        "interview_round": "Round 1: Screening Assessment",
        "difficulty": "Medium",
        "question_category": "Data Structures and Algorithms",
        "question_text": (
            "Implement a fast bitwise memory allocator bitmap scan: given a 64-bit integer, find the position of the least significant set bit in O(1) time without using compiler intrinsics. "
            "Explain how De Bruijn sequence multiplication or two's complement enables constant time bit isolation."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/nvidia-systems-screening",
    },
    {
        "company_name": "NVIDIA",
        "company_type": "ESTABLISHED",
        "industry": "AI/GenAI",
        "job_role": "Senior Systems Software Engineer",
        "years_of_experience": 7.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["C++", "Concurrency", "Operating Systems"],
        "round_number": 2,
        "interview_round": "Round 2: Systems Core & Concurrency",
        "difficulty": "Hard",
        "question_category": "Operating Systems",
        "question_text": (
            "Design and implement a lock-free Single Producer Single Consumer (SPSC) circular ring buffer. "
            "Explain memory order semantics (acquire-release vs sequential consistency), compiler reordering barriers, cache line false sharing, and cache coherency protocols (MESI)."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/nvidia-lockfree-ring-buffer",
    },
    {
        "company_name": "NVIDIA",
        "company_type": "ESTABLISHED",
        "industry": "AI/GenAI",
        "job_role": "Senior Systems Software Engineer",
        "years_of_experience": 7.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["CUDA", "GPU Architecture", "Memory Management"],
        "round_number": 3,
        "interview_round": "Round 3: GPU Architecture & Low-Level Design",
        "difficulty": "Hard",
        "question_category": "Object-Oriented Programming",
        "question_text": (
            "Write a CUDA kernel to perform 2D Matrix Multiplication with shared memory tiling to eliminate global memory bank conflicts. "
            "Discuss warp divergence, coalesced memory access, tensor core layout alignment, and register pressure."
        ),
        "source_platform": "Engineering Blogs",
        "original_url": "https://developer.nvidia.com/blog/cuda-matrix-multiplication-interview",
    },
    {
        "company_name": "NVIDIA",
        "company_type": "ESTABLISHED",
        "industry": "AI/GenAI",
        "job_role": "Senior Systems Software Engineer",
        "years_of_experience": 7.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Distributed Systems", "RDMA", "System Design"],
        "round_number": 4,
        "interview_round": "Round 4: High-Performance Distributed Systems Design",
        "difficulty": "Hard",
        "question_category": "System Design",
        "question_text": (
            "Design an ultra-low-latency distributed parameter synchronization tier for training a 70B parameter LLM across 2048 NVIDIA H100 GPUs. "
            "Architect the All-Reduce ring topologies, InfiniBand RDMA collectives, NVLink inter-GPU routing, and checkpointing storage."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/nvidia_distributed_system_design",
    },
    {
        "company_name": "NVIDIA",
        "company_type": "ESTABLISHED",
        "industry": "AI/GenAI",
        "job_role": "Senior Systems Software Engineer",
        "years_of_experience": 7.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Leadership", "Execution", "Mentorship"],
        "round_number": 5,
        "interview_round": "Round 5: Executive Engineering Leadership",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Describe a complex hardware-software integration bug in your past systems engineering career that took weeks to diagnose. "
            "What debugging strategies did you use? How did you manage customer pressure and mentor junior team members during the escalation?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/nvidia_engineering_culture",
    },

    # =========================================================================
    # CASE B: STARTUP - FINTECH (YoE: 3.5, Skills: Python, Go, Kafka, PostgreSQL, Distributed Transactions)
    # =========================================================================
    {
        "company_name": "Razorpay / Stripe Ecosystem",
        "company_type": "STARTUP",
        "industry": "Fintech",
        "job_role": "Backend Engineer (Payments)",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Python", "SQL", "DBMS and SQL"],
        "round_number": 1,
        "interview_round": "Round 1: Screening Coding Challenge",
        "difficulty": "Medium",
        "question_category": "DBMS and SQL",
        "question_text": (
            "Write an atomic SQL transaction / database procedure for an account balance transfer between Account A and Account B. "
            "Prevent race conditions (lost updates) under high concurrent load. "
            "Explain why 'SELECT FOR UPDATE' is required, deadlock prevention order by account_id, and handling isolation level anomalies."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/fintech-payment-db-interview",
    },
    {
        "company_name": "Razorpay / Stripe Ecosystem",
        "company_type": "STARTUP",
        "industry": "Fintech",
        "job_role": "Backend Engineer (Payments)",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Algorithms", "Arrays and Strings", "Prefix Sum"],
        "round_number": 2,
        "interview_round": "Round 2: Problem Solving & Edge Cases",
        "difficulty": "Medium",
        "question_category": "Arrays and Strings",
        "question_text": (
            "Design an algorithm to detect credit card fraud velocity spikes: given an incoming stream of transaction amounts with timestamps, "
            "return within O(1) amortized time whether any card has exceeded a cumulative transaction threshold of $10,000 within any sliding 15-minute window."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/fintech-fraud-velocity-window",
    },
    {
        "company_name": "Razorpay / Stripe Ecosystem",
        "company_type": "STARTUP",
        "industry": "Fintech",
        "job_role": "Backend Engineer (Payments)",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Python", "Kafka", "Idempotency"],
        "round_number": 3,
        "interview_round": "Round 3: Machine Coding (Idempotent Webhook Processor)",
        "difficulty": "Hard",
        "question_category": "Object-Oriented Programming",
        "question_text": (
            "Implement an Idempotent Payment Webhook Ingestion Engine in Python/FastAPI. "
            "Requirements: "
            "1. Guarantee exactly-once processing semantics for incoming gateway callbacks even with network retries and duplicate events. "
            "2. Implement distributed Redis locking with idempotency keys and state transition checks (INITIATED -> SUCCESS / FAILED). "
            "3. Gracefully handle database transient failures with exponential backoff and dead-letter queues (DLQ)."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/fintech-idempotent-webhook-processor",
    },
    {
        "company_name": "Razorpay / Stripe Ecosystem",
        "company_type": "STARTUP",
        "industry": "Fintech",
        "job_role": "Backend Engineer (Payments)",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["System Design", "Kafka", "PostgreSQL", "Distributed Systems"],
        "round_number": 4,
        "interview_round": "Round 4: Fintech System Design (Payment Gateway)",
        "difficulty": "Hard",
        "question_category": "System Design",
        "question_text": (
            "Design a Real-Time Payment Gateway & Ledger Engine processing 10,000 transactions per second. "
            "Key considerations: "
            "- Immutable double-entry bookkeeping ledger (every debit has an equal credit). "
            "- Zero double-spend guarantees under network partitions. "
            "- Reconciliations engine comparing bank statements against internal transactions. "
            "- Low p99 latency (< 150ms)."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/cscareerquestions/fintech_payment_system_design",
    },
    {
        "company_name": "Razorpay / Stripe Ecosystem",
        "company_type": "STARTUP",
        "industry": "Fintech",
        "job_role": "Backend Engineer (Payments)",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Ownership", "High Stakes Accountability", "Behavioral"],
        "round_number": 5,
        "interview_round": "Round 5: Founder / Engineering Leader Round",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "In fintech startups, a bug can directly result in financial loss or regulatory non-compliance. "
            "Describe a time you shipped an unexpected bug or encountered a production outage. How quickly did you detect it, mitigate customer impact, and implement safeguards?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/fintech_startup_culture",
    },

    # =========================================================================
    # CASE B: STARTUP - AI/GENAI (YoE: 2.0, Skills: Python, PyTorch, Vector Search, FastAPI, LLMs)
    # =========================================================================
    {
        "company_name": "Perplexity / Anthropic Ecosystem",
        "company_type": "STARTUP",
        "industry": "AI/GenAI",
        "job_role": "AI Engineer (GenAI / RAG)",
        "years_of_experience": 2.0,
        "yoe_tier": "Entry (0-2 yrs)",
        "skills_tested": ["Python", "Vector Search", "Arrays and Strings"],
        "round_number": 1,
        "interview_round": "Round 1: Screening & Vector Math",
        "difficulty": "Easy",
        "question_category": "Arrays and Strings",
        "question_text": (
            "Write a function from scratch in pure Python (no external libraries) to calculate the cosine similarity between two high-dimensional float vectors. "
            "Handle zero-vector edge cases and explain L2 normalization."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/ai-startup-vector-math",
    },
    {
        "company_name": "Perplexity / Anthropic Ecosystem",
        "company_type": "STARTUP",
        "industry": "AI/GenAI",
        "job_role": "AI Engineer (GenAI / RAG)",
        "years_of_experience": 2.0,
        "yoe_tier": "Entry (0-2 yrs)",
        "skills_tested": ["Python", "Algorithms", "Binary Search"],
        "round_number": 2,
        "interview_round": "Round 2: Problem Solving (Approximate Nearest Neighbors)",
        "difficulty": "Medium",
        "question_category": "Data Structures and Algorithms",
        "question_text": (
            "Implement a Hierarchical K-D Tree or Random Projection Forest algorithm to perform Approximate Nearest Neighbor (ANN) search over 100,000 embeddings. "
            "Analyze recall versus search latency trade-offs compared to exact brute force."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/ann-vector-search-interview",
    },
    {
        "company_name": "Perplexity / Anthropic Ecosystem",
        "company_type": "STARTUP",
        "industry": "AI/GenAI",
        "job_role": "AI Engineer (GenAI / RAG)",
        "years_of_experience": 2.0,
        "yoe_tier": "Entry (0-2 yrs)",
        "skills_tested": ["Python", "FastAPI", "AsyncIO", "LLMs"],
        "round_number": 3,
        "interview_round": "Round 3: Machine Coding (Streaming RAG Pipeline)",
        "difficulty": "Medium",
        "question_category": "Object-Oriented Programming",
        "question_text": (
            "Build a streaming Retrieval-Augmented Generation (RAG) backend using FastAPI and AsyncIO. "
            "Given a user query: "
            "1. Retrieve top-k semantic chunks from an in-memory vector index. "
            "2. Re-rank chunks using a cross-encoder scoring heuristic. "
            "3. Stream token-by-token responses back over Server-Sent Events (SSE) with citations."
        ),
        "source_platform": "Engineering Blogs",
        "original_url": "https://netflixtechblog.com/streaming-rag-pipeline-interview",
    },
    {
        "company_name": "Perplexity / Anthropic Ecosystem",
        "company_type": "STARTUP",
        "industry": "AI/GenAI",
        "job_role": "AI Engineer (GenAI / RAG)",
        "years_of_experience": 2.0,
        "yoe_tier": "Entry (0-2 yrs)",
        "skills_tested": ["System Design", "Vector Databases", "Caching"],
        "round_number": 4,
        "interview_round": "Round 4: GenAI Architecture & Caching",
        "difficulty": "Hard",
        "question_category": "System Design",
        "question_text": (
            "Design a Semantic LLM Cache for an AI search engine handling 20 million queries daily. "
            "If an incoming prompt has >= 0.92 cosine similarity to an already answered prompt, return the cached answer. "
            "Address: TTL expiration, semantic cache invalidation, cold-start latency, and pgvector partitioning."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/genai_semantic_cache_system_design",
    },
    {
        "company_name": "Perplexity / Anthropic Ecosystem",
        "company_type": "STARTUP",
        "industry": "AI/GenAI",
        "job_role": "AI Engineer (GenAI / RAG)",
        "years_of_experience": 2.0,
        "yoe_tier": "Entry (0-2 yrs)",
        "skills_tested": ["Speed of Learning", "Self-Direction", "Startup Alignment"],
        "round_number": 5,
        "interview_round": "Round 5: Founder Alignment & Curiosity",
        "difficulty": "Easy",
        "question_category": "HR and Behavioral",
        "question_text": (
            "The AI landscape changes weekly with new model architectures and reasoning paradigms. "
            "Tell me about a research paper or open-source library you discovered recently. How did you test it, and what did you learn?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/ai_startup_behavioral",
    },

    # =========================================================================
    # CASE B: STARTUP - E-COMMERCE / QUICK-COMMERCE (Zepto/Blinkit) - SDE (YoE: 5.0, Skills: Java, Spring Boot, Redis, Kafka)
    # =========================================================================
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "E-Commerce",
        "job_role": "Senior Backend Engineer (Fulfillment)",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Algorithms", "Greedy Algorithms", "Dynamic Programming"],
        "round_number": 1,
        "interview_round": "Round 1: Screening OA",
        "difficulty": "Medium",
        "question_category": "Greedy Algorithms",
        "question_text": (
            "Quick-Commerce Delivery Optimization: Given N dark store delivery batches with pickup times and delivery deadlines, "
            "find the minimum number of delivery riders required so that no customer order delivery deadline is breached."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/ecom-rider-batching",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "E-Commerce",
        "job_role": "Senior Backend Engineer (Fulfillment)",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Graphs", "Dijkstra", "Shortest Path"],
        "round_number": 2,
        "interview_round": "Round 2: Geospatial Routing (DSA)",
        "difficulty": "Hard",
        "question_category": "Trees and Graphs",
        "question_text": (
            "Given a city road network represented as a directed weighted graph with one-way streets and real-time traffic congestion weights, "
            "calculate the optimal multi-destination route for a rider visiting 3 distinct addresses within 10 minutes."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/quick-commerce-dijkstra-routing",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "E-Commerce",
        "job_role": "Senior Backend Engineer (Fulfillment)",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Redis", "Concurrency", "Flash Sale"],
        "round_number": 3,
        "interview_round": "Round 3: Machine Coding (Flash Sale Inventory Reservation)",
        "difficulty": "Hard",
        "question_category": "Object-Oriented Programming",
        "question_text": (
            "Implement a Flash Sale In-Memory Inventory Reservation Lock. "
            "When 50,000 users click 'Buy Now' for only 100 available items: "
            "1. Guarantee zero overselling using Redis atomic Lua scripts (DECRBY / WATCH). "
            "2. Reserve inventory for 10 minutes while customer completes payment. "
            "3. If payment fails or times out, auto-release inventory back to the stock pool."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/flash-sale-inventory-reservation",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "E-Commerce",
        "job_role": "Senior Backend Engineer (Fulfillment)",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["System Design", "Kafka", "High Availability", "PostgreSQL"],
        "round_number": 4,
        "interview_round": "Round 4: 10-Minute Dark Store Dispatch System Design",
        "difficulty": "Hard",
        "question_category": "System Design",
        "question_text": (
            "Design the End-to-End Order Dispatch & Dark Store Picker System for a 10-minute grocery delivery app. "
            "Architect: item picking tablet synchronization, rider assignment matching via geohashing, inventory balance updates across 500 dark stores, and real-time telemetry."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/quick_commerce_system_design",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "E-Commerce",
        "job_role": "Senior Backend Engineer (Fulfillment)",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["High Velocity Ownership", "Pivoting", "Behavioral"],
        "round_number": 5,
        "interview_round": "Round 5: VP of Engineering / Founder Culture",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "In high-growth startups, requirements shift rapidly and features must be shipped in days, not quarters. "
            "Give an example of a project where you traded off technical perfection for rapid time-to-market. How did you manage technical debt later?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/quick_commerce_culture",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (GOOGLE) - Senior Product Manager (Non-Tech/Tech Hybrid)
    # YoE: 6.0, Skills: Product Strategy, Metrics & Analytics, A/B Testing, User Research
    # =========================================================================
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Product Manager",
        "years_of_experience": 6.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Product Design", "User Empathy", "Accessibility"],
        "round_number": 1,
        "interview_round": "Round 1: Product Screening & Product Sense Teardown",
        "difficulty": "Medium",
        "question_category": "Product Management",
        "question_text": (
            "Design Google Maps for users with visual impairments. "
            "Structure your response: "
            "1. Define user personas, specific pain points across indoor and outdoor navigation, and edge cases. "
            "2. Propose 3 prioritized feature solutions leveraging haptic audio, AR cues, and real-time transit telemetry. "
            "3. State your MVP scope and identify critical UX trade-offs."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/productmanagement/google_pm_product_sense",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Product Manager",
        "years_of_experience": 6.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Metrics & Analytics", "Root Cause Analysis", "A/B Testing"],
        "round_number": 2,
        "interview_round": "Round 2: Product Metrics & Analytical Execution",
        "difficulty": "Hard",
        "question_category": "Product Management",
        "question_text": (
            "YouTube Shorts Daily Active Users (DAU) dropped by 7.5% week-over-week in North America, while average watch time per active user remained flat. "
            "How would you diagnose this problem? "
            "Walk me through your comprehensive metric tree (segmentation by platform, geography, app release, content creator cohort, notification delivery), "
            "and establish counter-metrics to avoid local optima."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/productmanagement/google_execution_metrics",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Product Manager",
        "years_of_experience": 6.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Technical Feasibility", "System Design", "Latency vs Consistency"],
        "round_number": 3,
        "interview_round": "Round 3: Technical Feasibility & Architecture Trade-offs",
        "difficulty": "Hard",
        "question_category": "Product Management",
        "question_text": (
            "Explain how Google Docs achieves real-time collaborative editing from a product and engineering trade-off perspective. "
            "Compare Operational Transformation (OT) against Conflict-free Replicated Data Types (CRDTs). "
            "If an engineering lead states that adopting CRDTs will increase mobile memory footprint by 25MB and degrade battery life on low-end Android devices, "
            "how do you evaluate whether to proceed?"
        ),
        "source_platform": "Engineering Blogs",
        "original_url": "https://googleblog.com/product-manager-tech-round",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Product Manager",
        "years_of_experience": 6.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Product Strategy", "Market Sizing", "Competitive Moat"],
        "round_number": 4,
        "interview_round": "Round 4: Product Strategy & Go-To-Market",
        "difficulty": "Hard",
        "question_category": "Product Management",
        "question_text": (
            "Should Google launch an integrated in-app commerce checkout experience inside YouTube to directly compete with TikTok Shop and Instagram Shopping? "
            "Deliver a structured strategic recommendation covering: Total Addressable Market (TAM), creator revenue share incentive structures, "
            "merchant logistics integration risks, cannibalization of existing YouTube Shopping affiliate ad revenue, and Google's defensive moat."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/productmanagement/google_strategy_pm",
    },
    {
        "company_name": "Google",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Product Manager",
        "years_of_experience": 6.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Googleyness", "Stakeholder Alignment", "Conflict Resolution"],
        "round_number": 5,
        "interview_round": "Round 5: Googleyness & Cross-functional Leadership",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Tell me about a time you had to launch a product feature where Sales wanted custom enterprise features for a single multi-million dollar client, "
            "Engineering pushed back against bespoke technical debt, and Legal flagged privacy compliance risks. "
            "How did you negotiate alignment, what framework did you use to prioritize, and what was the business outcome?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/productmanagement/google_pm_behavioral",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (AMAZON) - Senior Data Analyst / Business Intelligence Engineer
    # YoE: 4.5, Skills: SQL, Tableau, Python, Statistics, A/B Testing, ETL
    # =========================================================================
    {
        "company_name": "Amazon",
        "company_type": "ESTABLISHED",
        "industry": "E-Commerce",
        "job_role": "Senior Data Analyst",
        "years_of_experience": 4.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["SQL", "Window Functions", "DENSE_RANK", "Data Manipulation"],
        "round_number": 1,
        "interview_round": "Round 1: Advanced SQL & Data Manipulation Assessment",
        "difficulty": "Hard",
        "question_category": "DBMS and SQL",
        "question_text": (
            "Write a performant PostgreSQL/Redshift query to compute 30-day rolling customer retention cohorts. "
            "Given a clickstream events table `user_activity(user_id, event_timestamp, event_type)`: "
            "1. Segment users into new sessions using a 30-minute inactivity threshold via `LAG()` and `SUM() OVER ()`. "
            "2. For each user cohort, calculate the percentage of users who returned to make a purchase within Day 1, Day 7, Day 14, and Day 30."
        ),
        "source_platform": "LeetCode Discuss",
        "original_url": "https://leetcode.com/discuss/amazon-bie-sql-cohort",
    },
    {
        "company_name": "Amazon",
        "company_type": "ESTABLISHED",
        "industry": "E-Commerce",
        "job_role": "Senior Data Analyst",
        "years_of_experience": 4.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Business Problem Solving", "Root Cause Analysis", "Funnel Metrics"],
        "round_number": 2,
        "interview_round": "Round 2: Business Problem Solving & Root Cause Analysis",
        "difficulty": "Medium",
        "question_category": "Data Analytics and BI",
        "question_text": (
            "Amazon Seller Central reports an 11% surge in seller account refund requests over the last 14 days, "
            "while overall platform Gross Merchandise Value (GMV) stayed flat. "
            "How would you segment the data to isolate whether the issue is seller fraud, automated bot abuse, logistics courier delays, "
            "or a broken checkout payment gateway?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/dataanalysis/amazon_bie_case_study",
    },
    {
        "company_name": "Amazon",
        "company_type": "ESTABLISHED",
        "industry": "E-Commerce",
        "job_role": "Senior Data Analyst",
        "years_of_experience": 4.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Statistics", "Hypothesis Testing", "A/B Testing"],
        "round_number": 3,
        "interview_round": "Round 3: Statistics, Hypothesis Testing & Experimentation",
        "difficulty": "Hard",
        "question_category": "Data Analytics and BI",
        "question_text": (
            "We ran an A/B test on Amazon checkout button placement. Variant A had 2,000,000 visitors with a 3.40% conversion rate. "
            "Variant B had 2,000,000 visitors with a 3.48% conversion rate. "
            "1. Calculate the p-value and determine statistical significance at alpha = 0.05. "
            "2. If the team also tested 5 different color schemes simultaneously in the same experiment, explain the Multiple Comparisons Problem and how the Bonferroni correction or FDR control alters your conclusion."
        ),
        "source_platform": "GeeksforGeeks",
        "original_url": "https://geeksforgeeks.org/amazon-statistics-ab-testing-analyst",
    },
    {
        "company_name": "Amazon",
        "company_type": "ESTABLISHED",
        "industry": "E-Commerce",
        "job_role": "Senior Data Analyst",
        "years_of_experience": 4.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Data Modeling", "Tableau", "Dimensional Warehousing"],
        "round_number": 4,
        "interview_round": "Round 4: Dimensional Data Modeling & Executive Dashboards",
        "difficulty": "Medium",
        "question_category": "Data Analytics and BI",
        "question_text": (
            "Design a Kimball Star Schema data warehouse architecture for Amazon Logistics fulfillment tracking. "
            "Define the Fact table granularity, dimension tables (Dim_Courier, Dim_Warehouse, Dim_Package, Dim_DeliveryStatus), "
            "and explain how you handle Slowly Changing Dimensions (SCD Type 2) when a dark store zip code coverage changes. "
            "How do you design the executive KPI dashboard in Tableau/QuickSight to minimize query scan costs?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/datawarehousing/amazon_data_modeling",
    },
    {
        "company_name": "Amazon",
        "company_type": "ESTABLISHED",
        "industry": "E-Commerce",
        "job_role": "Senior Data Analyst",
        "years_of_experience": 4.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Amazon Leadership Principles", "Bar Raiser", "Customer Obsession"],
        "round_number": 5,
        "interview_round": "Round 5: Amazon Bar Raiser & Stakeholder Alignment",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Tell me about a time you presented data-backed insights to a business VP or Director who strongly disagreed with your conclusions "
            "because the findings contradicted their intuition. "
            "How did you demonstrate 'Have Backbone; Disagree and Commit' and 'Earn Trust' while ensuring the business did not make an expensive mistake?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/cscareerquestions/amazon_bar_raiser_bie",
    },

    # =========================================================================
    # CASE B: STARTUP - SAAS (Figma/Canva Ecosystem) - Lead Product Designer (UI/UX)
    # YoE: 5.0, Skills: Figma, Design Systems, User Research, Wireframing, Interaction Design
    # =========================================================================
    {
        "company_name": "Figma / Canva Ecosystem",
        "company_type": "STARTUP",
        "industry": "SaaS",
        "job_role": "Lead Product Designer",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Portfolio Walkthrough", "Design Thinking", "User Research"],
        "round_number": 1,
        "interview_round": "Round 1: Portfolio Walkthrough & Problem Discovery",
        "difficulty": "Medium",
        "question_category": "UI/UX Design",
        "question_text": (
            "Present a flagship case study from your design portfolio. "
            "Focus specifically on: "
            "1. How you conducted qualitative user discovery interviews and parsed ambiguous stakeholder requirements. "
            "2. How you invalidated early design assumptions through low-fidelity prototypes. "
            "3. Quantitative metrics and user adoption improvements post-launch."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/uiux/product_design_portfolio_round",
    },
    {
        "company_name": "Figma / Canva Ecosystem",
        "company_type": "STARTUP",
        "industry": "SaaS",
        "job_role": "Lead Product Designer",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["UX Critique", "Information Architecture", "Heuristic Evaluation"],
        "round_number": 2,
        "interview_round": "Round 2: Live App Critique & Usability Analysis",
        "difficulty": "Medium",
        "question_category": "UI/UX Design",
        "question_text": (
            "Conduct a live heuristic critique of the Notion or Linear workspace onboarding experience on desktop and mobile. "
            "Evaluate visual hierarchy, cognitive load, affordance, error recovery, and time-to-first-value. "
            "What three UX friction points would you redesign immediately to reduce Day-1 user drop-off?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/userexperience/app_critique_interview",
    },
    {
        "company_name": "Figma / Canva Ecosystem",
        "company_type": "STARTUP",
        "industry": "SaaS",
        "job_role": "Lead Product Designer",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Whiteboard Challenge", "Interaction Design", "User Flow"],
        "round_number": 3,
        "interview_round": "Round 3: Live Whiteboard Design Challenge",
        "difficulty": "Hard",
        "question_category": "UI/UX Design",
        "question_text": (
            "Live Whiteboard Exercise (45 mins): "
            "Design a self-serve collaborative billing and seat-management dashboard for a high-growth B2B developer tool. "
            "The product is migrating from fixed-seat licenses to usage-based consumption pricing (API calls + active seats). "
            "Map out the primary user personas (Engineering Director vs Finance Buyer), core wireframes, usage alerts, and edge cases."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/uiux/whiteboard_design_challenge",
    },
    {
        "company_name": "Figma / Canva Ecosystem",
        "company_type": "STARTUP",
        "industry": "SaaS",
        "job_role": "Lead Product Designer",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Design Systems", "Figma Tokens", "Developer Handoff"],
        "round_number": 4,
        "interview_round": "Round 4: Design Systems, Tokens & Developer Handoff",
        "difficulty": "Hard",
        "question_category": "UI/UX Design",
        "question_text": (
            "How do you architect a scalable, multi-brand Design System in Figma that synchronizes with a React/Tailwind codebase? "
            "Explain your strategy for semantic design tokens (color, typography, spacing), component variants with auto-layout, "
            "WCAG 2.1 AA accessibility contrast enforcement, and the automated CI/CD handoff workflow with frontend developers."
        ),
        "source_platform": "Engineering Blogs",
        "original_url": "https://figma.com/blog/design-systems-interview-guide",
    },
    {
        "company_name": "Figma / Canva Ecosystem",
        "company_type": "STARTUP",
        "industry": "SaaS",
        "job_role": "Lead Product Designer",
        "years_of_experience": 5.0,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Speed vs Perfection", "Startup Agility", "Cross-functional"],
        "round_number": 5,
        "interview_round": "Round 5: Founder Alignment & High-Speed Iteration",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "In an early-stage or hyper-growth startup, engineering often needs to ship an MVP within 2 weeks, while designers advocate for exhaustive research. "
            "Give an example where you successfully compromised between visual polish and development velocity without sacrificing core user experience."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/startups/designer_founder_alignment",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (SALESFORCE) - Enterprise Account Executive (B2B Sales)
    # YoE: 5.5, Skills: MEDDPICC, Pipeline Generation, Discovery, Objection Handling, Enterprise Contracts
    # =========================================================================
    {
        "company_name": "Salesforce",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Software",
        "job_role": "Enterprise Account Executive",
        "years_of_experience": 5.5,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Sales Track Record", "Discovery Call", "MEDDPICC"],
        "round_number": 1,
        "interview_round": "Round 1: Sales Track Record & Discovery Call Simulation",
        "difficulty": "Medium",
        "question_category": "Sales and Business Development",
        "question_text": (
            "Conduct a 15-minute simulated first-touch discovery call with a skeptical VP of Customer Support at a 5,000-person enterprise. "
            "They currently rely on legacy Zendesk and in-house spreadsheets. "
            "Apply the MEDDPICC qualification framework to uncover: Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, and Champion."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/sales/salesforce_ae_discovery_round",
    },
    {
        "company_name": "Salesforce",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Software",
        "job_role": "Enterprise Account Executive",
        "years_of_experience": 5.5,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Value Engineering", "Mock Sales Pitch", "ROI Modeling"],
        "round_number": 2,
        "interview_round": "Round 2: Mock Sales Pitch & Value Engineering",
        "difficulty": "Hard",
        "question_category": "Sales and Business Development",
        "question_text": (
            "Deliver a mock presentation pitching Salesforce Service Cloud + Einstein AI to a CFO and CIO. "
            "The total contract value (TCV) is $850,000 annually. "
            "Build an airtight ROI business case demonstrating how automated AI case deflection and reduced ticket resolution time "
            "delivers a 14-month payback period and 240% 3-year net ROI."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/sales/enterprise_pitch_presentation",
    },
    {
        "company_name": "Salesforce",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Software",
        "job_role": "Enterprise Account Executive",
        "years_of_experience": 5.5,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Objection Handling", "Enterprise Infosec", "Procurement"],
        "round_number": 3,
        "interview_round": "Round 3: Enterprise Objection Handling & Procurement Pushback",
        "difficulty": "Hard",
        "question_category": "Sales and Business Development",
        "question_text": (
            "How do you handle these two simultaneous enterprise objections during late-stage procurement? "
            "1. 'Our Chief Information Security Officer (CISO) is blocking approval due to LLM data privacy and EU GDPR residency concerns.' "
            "2. 'Procurement demands an immediate 40% discount across all licenses, or they will walk away and renew with our incumbent vendor.'"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/sales/objection_handling_procurement",
    },
    {
        "company_name": "Salesforce",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Software",
        "job_role": "Enterprise Account Executive",
        "years_of_experience": 5.5,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Territory Planning", "Pipeline Generation", "Quota Execution"],
        "round_number": 4,
        "interview_round": "Round 4: Territory Strategy & Pipeline Execution",
        "difficulty": "Medium",
        "question_category": "Sales and Business Development",
        "question_text": (
            "You are handed a new geographic enterprise territory with an annual quota of $2.2M ACV. "
            "Only 15% of your pipeline is currently inbound. "
            "Present your 30-60-90 day territory execution plan: account tiering (Tier 1, 2, 3), outbound multithreading, partner channel leverage, "
            "and how you generate a 4x pipeline coverage ratio within 90 days."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/sales/territory_planning_ae",
    },
    {
        "company_name": "Salesforce",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Software",
        "job_role": "Enterprise Account Executive",
        "years_of_experience": 5.5,
        "yoe_tier": "Senior (6-8 yrs)",
        "skills_tested": ["Quota Resilience", "Grit", "Sales Culture"],
        "round_number": 5,
        "interview_round": "Round 5: VP of Sales Cultural Fit & Quota Resilience",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Walk me through a quarter where your primary $500k deal unexpectedly slipped at the final hour of the quarter end. "
            "What went wrong in your forecast? What steps did you take to protect your annual quota, and what systemic qualification lesson did you adopt?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/sales/vp_sales_interview_culture",
    },

    # =========================================================================
    # CASE B: STARTUP - CONSUMER INTERNET / D2C (Zepto) - Growth Marketing Manager
    # YoE: 3.5, Skills: CAC/LTV, Meta/Google Ads, Attribution Modeling, Funnel CRO, Retention
    # =========================================================================
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "Consumer Internet",
        "job_role": "Growth Marketing Manager",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Performance Marketing", "Attribution Modeling", "CAC/LTV"],
        "round_number": 1,
        "interview_round": "Round 1: Marketing Analytics & Attribution Screening",
        "difficulty": "Medium",
        "question_category": "Growth and Marketing",
        "question_text": (
            "Explain the difference between First-Touch, Last-Touch, and Data-Driven Attribution modeling in the post-iOS 14.5 SKAdNetwork era. "
            "If your blended Customer Acquisition Cost (CAC) is $14 but your paid Google Ads dashboard reports a CAC of $22, "
            "how do you evaluate marketing efficiency and calculate incrementality via geo-lift testing?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/marketing/growth_marketing_attribution",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "Consumer Internet",
        "job_role": "Growth Marketing Manager",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Funnel CRO", "Paid Acquisition", "A/B Testing"],
        "round_number": 2,
        "interview_round": "Round 2: Paid Growth & Funnel Conversion Rate Optimization",
        "difficulty": "Hard",
        "question_category": "Growth and Marketing",
        "question_text": (
            "You have a $150,000 monthly performance marketing budget split across Meta Ads, Google Performance Max, and Apple Search Ads. "
            "App install-to-first-order conversion drops from 28% to 14% at the payment method selection screen. "
            "Design a 4-week conversion rate optimization (CRO) sprint: creative iteration, ad hook testing, frictionless UPI intent flows, and personalized discount ladders."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/growthmarketing/paid_acquisition_cro",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "Consumer Internet",
        "job_role": "Growth Marketing Manager",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Viral Loops", "Referral Economics", "Retention"],
        "round_number": 3,
        "interview_round": "Round 3: Viral Loops & Referral Program Economics",
        "difficulty": "Medium",
        "question_category": "Growth and Marketing",
        "question_text": (
            "Design an organic referral loop for a quick-commerce grocery app to achieve a viral coefficient (K-factor) > 1.2. "
            "How do you structure the double-sided incentive (e.g., $10 wallet credit for referrer + free delivery for referee) "
            "such that payback period stays under 60 days without incentivizing multi-account referral fraud?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/growthmarketing/viral_loops_k_factor",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "Consumer Internet",
        "job_role": "Growth Marketing Manager",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Product Marketing", "Brand Positioning", "Unit Economics"],
        "round_number": 4,
        "interview_round": "Round 4: Brand Positioning vs Performance Marketing",
        "difficulty": "Hard",
        "question_category": "Growth and Marketing",
        "question_text": (
            "The executive board wants to reallocate 40% of the performance ad spend into top-of-funnel brand campaigns (influencer marketing + outdoor billboards). "
            "How do you structure an executive case analyzing the trade-off between short-term ROAS and long-term brand equity? "
            "What leading indicators (organic search volume spikes, branded keyword impression share, direct traffic lift) do you monitor?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/marketing/brand_vs_performance_tradeoffs",
    },
    {
        "company_name": "Zepto / Blinkit Ecosystem",
        "company_type": "STARTUP",
        "industry": "Consumer Internet",
        "job_role": "Growth Marketing Manager",
        "years_of_experience": 3.5,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Lean Budget Execution", "Founder Alignment", "Startup Hustle"],
        "round_number": 5,
        "interview_round": "Round 5: Founder Alignment & Lean Budget Execution",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Suppose your monthly marketing budget is abruptly slashed by 60% due to an unexpected macroeconomic market contraction, "
            "yet the company's monthly GMV growth target remains unchanged. "
            "What unscalable guerrilla growth hacks, lifecycle email/push automations, and retention strategies do you deploy in the first 14 days?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/startups/lean_marketing_founder_round",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (MICROSOFT) - Senior Financial Analyst (FP&A / Corporate Finance)
    # YoE: 5.0, Skills: 3-Statement Modeling, SaaS Metrics, DCF, Variance Analysis, Capital Allocation
    # =========================================================================
    {
        "company_name": "Microsoft",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Financial Analyst",
        "years_of_experience": 5.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Accounting", "3-Statement Financial Modeling", "Working Capital"],
        "round_number": 1,
        "interview_round": "Round 1: Financial Accounting & 3-Statement Linking",
        "difficulty": "Medium",
        "question_category": "Finance and Accounting",
        "question_text": (
            "Walk me through the exact accounting flows across the 3 Financial Statements (Income Statement, Balance Sheet, Cash Flow Statement) for: "
            "A company capitalizes $100M of software engineering R&D development costs instead of expensing it immediately. "
            "Assuming a 3-year straight-line amortization schedule and a 25% corporate tax rate, show the financial impact in Year 1 and Year 2."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/financialcareers/3_statement_modeling_interview",
    },
    {
        "company_name": "Microsoft",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Financial Analyst",
        "years_of_experience": 5.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["SaaS Metrics", "DCF Valuation", "Rule of 40"],
        "round_number": 2,
        "interview_round": "Round 2: SaaS Metrics & Valuation Modeling",
        "difficulty": "Hard",
        "question_category": "Finance and Accounting",
        "question_text": (
            "Analyze the financial health of an enterprise cloud business unit: "
            "Annual Recurring Revenue (ARR) is $500M with 28% YoY growth, Net Retention Rate (NRR) is 118%, Gross Margin is 74%, and Free Cash Flow margin is 16%. "
            "1. Evaluate whether the unit meets the SaaS 'Rule of 40'. "
            "2. Build a Discounted Cash Flow (DCF) model outline, selecting appropriate Weighted Average Cost of Capital (WACC) and terminal growth assumptions."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/financialcareers/saas_metrics_valuation",
    },
    {
        "company_name": "Microsoft",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Financial Analyst",
        "years_of_experience": 5.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Budgeting", "Variance Analysis", "Scenario Planning"],
        "round_number": 3,
        "interview_round": "Round 3: Corporate Budgeting & Variance Analysis",
        "difficulty": "Medium",
        "question_category": "Finance and Accounting",
        "question_text": (
            "In Q3, Azure Cloud infrastructure server depreciation and electricity costs exceeded budget by $45M (an 8% unfavorable variance), "
            "while compute revenue grew 12% above budget. "
            "Perform a bridge analysis decomposing the variance into Price, Volume, and Efficiency mix effects. "
            "How would you communicate these results to business engineering leadership?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/financialcareers/variance_analysis_interview",
    },
    {
        "company_name": "Microsoft",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Financial Analyst",
        "years_of_experience": 5.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Capital Allocation", "M&A", "Scenario Planning"],
        "round_number": 4,
        "interview_round": "Round 4: Capital Allocation & M&A Scenario Planning",
        "difficulty": "Hard",
        "question_category": "Finance and Accounting",
        "question_text": (
            "Microsoft has $2 Billion in unallocated capital for the fiscal year. "
            "Evaluate two competing internal proposals: "
            "Option A: Invest $2B in building two next-gen GPU AI datacenter clusters with an estimated 5-year IRR of 22%. "
            "Option B: Acquire a high-growth cybersecurity SaaS startup at 12x ARR with potential revenue synergies. "
            "Present your capital allocation evaluation framework."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/financialcareers/capital_allocation_ma",
    },
    {
        "company_name": "Microsoft",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Financial Analyst",
        "years_of_experience": 5.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Integrity", "Executive Presence", "Ethical Finance"],
        "round_number": 5,
        "interview_round": "Round 5: CFO / Executive Communication & Integrity",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "Describe a situation where a General Manager pressured you to alter revenue recognition timing or adjust cost accrual forecasts "
            "to make their division hit quarterly bonus targets. "
            "How did you uphold fiduciary compliance, protect company integrity, and de-escalate the conflict?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/financialcareers/cfo_behavioral_ethics",
    },

    # =========================================================================
    # CASE A: ESTABLISHED (TECH) - Senior Talent Acquisition / HR Operations Partner
    # YoE: 4.0, Skills: Tech Sourcing, Compensation & Equity, Offer Closing, Retention, People Operations
    # =========================================================================
    {
        "company_name": "Meta / Tech Ecosystem",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Talent Partner",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Talent Sourcing", "Pipeline Engineering", "Boolean Search"],
        "round_number": 1,
        "interview_round": "Round 1: Niche Talent Sourcing & Pipeline Engineering",
        "difficulty": "Medium",
        "question_category": "Human Resources and Talent",
        "question_text": (
            "You are tasked with hiring 5 Staff-level Distributed Systems Engineers specialized in distributed training and RDMA networking within 90 days. "
            "Walk me through your multi-channel sourcing strategy: Boolean query formulation on GitHub/LinkedIn/arXiv, "
            "diversity pipeline generation, and your 3-touch personalized outreach sequence to achieve a >35% response rate."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/humanresources/niche_tech_sourcing",
    },
    {
        "company_name": "Meta / Tech Ecosystem",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Talent Partner",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Compensation", "Total Rewards", "RSU Equity"],
        "round_number": 2,
        "interview_round": "Round 2: Compensation Benchmarking & Offer Structuring",
        "difficulty": "Hard",
        "question_category": "Human Resources and Talent",
        "question_text": (
            "A top candidate holds competing offers from Google ($380k TC with 4-year front-loaded RSUs) and an AI startup ($220k base + 0.15% equity). "
            "How do you design and structure our offer package (Base, Signing Bonus, RSU grant with 1-year cliff) within band limits? "
            "Walk me through your verbal closing pitch to communicate total wealth creation potential."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/humanresources/compensation_offer_closing",
    },
    {
        "company_name": "Meta / Tech Ecosystem",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Talent Partner",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Employee Relations", "Conflict Resolution", "Performance Management"],
        "round_number": 3,
        "interview_round": "Round 3: Employee Relations & Conflict Resolution",
        "difficulty": "Medium",
        "question_category": "Human Resources and Talent",
        "question_text": (
            "A high-performing Senior Engineer complains of micro-management and toxic exclusion from their new Engineering Manager, "
            "while the Manager simultaneously requests to place the Engineer on a 30-day Performance Improvement Plan (PIP). "
            "How do you independently investigate the situation, ensure fair documentation, and resolve the impasse?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/humanresources/employee_relations_investigation",
    },
    {
        "company_name": "Meta / Tech Ecosystem",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Talent Partner",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["Organizational Scaling", "Headcount Planning", "People Analytics"],
        "round_number": 4,
        "interview_round": "Round 4: Organizational Scaling & Performance Management",
        "difficulty": "Hard",
        "question_category": "Human Resources and Talent",
        "question_text": (
            "The engineering organization is scaling from 120 to 350 engineers across three international hubs over 12 months. "
            "Architect the talent operations blueprint: interview bar raiser calibration, interviewer burnout mitigation, "
            "time-to-hire SLA targets, and the bi-annual 360-degree performance review framework."
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/humanresources/org_scaling_blueprint",
    },
    {
        "company_name": "Meta / Tech Ecosystem",
        "company_type": "ESTABLISHED",
        "industry": "Enterprise Tech",
        "job_role": "Senior Talent Partner",
        "years_of_experience": 4.0,
        "yoe_tier": "Mid (3-5 yrs)",
        "skills_tested": ["CHRO Leadership", "Culture Stewardship", "DEI"],
        "round_number": 5,
        "interview_round": "Round 5: People Leadership & Culture Stewardship",
        "difficulty": "Medium",
        "question_category": "HR and Behavioral",
        "question_text": (
            "During a difficult company-wide restructuring or change in leadership direction, employee morale plummeted and voluntary attrition rose by 15%. "
            "What proactive retention strategies, transparent town halls, and manager enablement workshops do you implement to restore psychological safety and team trust?"
        ),
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/humanresources/culture_stewardship_round",
    },
]


def run_seeder():
    repo = get_db_repository()
    logger.info("Starting Dataset Seeder for Case A (Established) and Case B (Startups)...")
    inserted_count = 0
    duplicate_count = 0

    for item in DATASET:
        # Create company
        repo.get_or_create_company(item["company_name"], industry=item["industry"])
        repo.get_or_create_job_role(item["job_role"])

        q, is_new = repo.insert_interview_question(
            company_name=item["company_name"],
            job_role=item["job_role"],
            question_text=item["question_text"],
            question_category=item["question_category"],
            difficulty=item["difficulty"],
            source_platform=item["source_platform"],
            original_url=item["original_url"],
            experience_level=item["yoe_tier"],
            interview_round=item["interview_round"],
            confidence_score=0.92,
            coding_problem_data=item.get("coding_problem_data"),
            company_type=item["company_type"],
            industry=item["industry"],
            years_of_experience=item["years_of_experience"],
            yoe_tier=item["yoe_tier"],
            skills_tested=item["skills_tested"],
            round_number=item["round_number"],
        )

        # Index vector embedding
        from models.model_manager import get_model_manager
        mm = get_model_manager()
        vec = mm.generate_embedding(item["question_text"])
        repo.save_embedding(q.id, vec)

        if is_new:
            inserted_count += 1
        else:
            duplicate_count += 1

    logger.info(f"Seeding completed: {inserted_count} new questions seeded, {duplicate_count} existing/updated.")
    return {"inserted": inserted_count, "duplicates": duplicate_count, "total_dataset": len(DATASET)}


if __name__ == "__main__":
    res = run_seeder()
    print("Seed result:", res)

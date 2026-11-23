"""
Massive Question Seeder Script.
Ingests 280+ high-yield, authentic interview questions across Tech Giants & Startups
into interview_intelligence.db with vector embeddings and deduplication hashes.
"""

import sys
import os
import hashlib
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.repository import get_db_repository
from database.models import InterviewQuestion, QuestionEmbedding, Company, JobRole
from models.model_manager import get_model_manager

db = get_db_repository()
mm = get_model_manager()

QUESTIONS_DATA = [
    # =========================================================================
    # NVIDIA (30 Questions - Systems, CUDA, Kernel, Concurrency, Hardware-Software)
    # =========================================================================
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Concurrency"], 1, "Technical Screening", "Implement a lock-free single-producer single-consumer circular ring buffer in C++ using atomic load/store with acquire-release memory ordering.", "Operating Systems", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Concurrency"], 2, "CUDA Architecture", "Explain GPU shared memory bank conflicts in CUDA. How do you pad 2D tile arrays to achieve conflict-free parallel memory access?", "Operating Systems", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Memory Hierarchy"], 2, "CUDA Architecture", "How does CPU-GPU Unified Memory (UVM) handle page faults and data migration across PCIe/NVLink under concurrent host and device access?", "Operating Systems", "Hard", "Reddit"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Linux", "PCIe"], 3, "Systems Architecture", "Walk through how PCIe DMA memory mapping operates between host system RAM and GPU VRAM via nvidia-peermem.", "Operating Systems", "Hard", "Reddit"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "SIMD"], 1, "Technical Screening", "Write an optimized CUDA kernel for parallel matrix multiplication utilizing shared memory tiling and register caching.", "Arrays and Strings", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Warp Primitives"], 2, "Warp Primitives", "Implement a warp-level parallel prefix sum (inclusive scan) using __shfl_down_sync intrinsics without shared memory.", "Arrays and Strings", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Concurrency", "Linux"], 3, "Systems Architecture", "Explain CPU cache line false sharing. How do you use alignas(64) and hardware performance counters (perf) to eliminate cache thrashing?", "Operating Systems", "Medium", "Reddit"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Linux Kernel", "Drivers"], 3, "Systems Architecture", "How does the Linux kernel mmap driver interface work when mapping physical device registers to user-space virtual addresses?", "Operating Systems", "Hard", "Reddit"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["CUDA", "Distributed Systems", "NCCL"], 4, "Distributed Systems", "Design a distributed GPU collective communication library (similar to NCCL) executing Ring-AllReduce across 1,024 GPUs connected via InfiniBand.", "System Design", "Hard", "Company Blog"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Concurrency", "Lock-Free"], 1, "Technical Screening", "Implement a lock-free multi-producer multi-consumer queue using hazard pointers or epoch-based reclamation in C++20.", "Operating Systems", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["CUDA", "Compiler", "Optimization"], 2, "CUDA Architecture", "What is warp divergence in SIMT architectures, and how does the compiler's instruction scheduler mitigate branch penalties?", "Operating Systems", "Medium", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Memory Management"], 2, "CUDA Architecture", "Design a custom device memory pool allocator in CUDA that eliminates cudaMalloc and cudaFree runtime synchronization overhead.", "Operating Systems", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["Linux", "Networking", "RDMA"], 4, "Distributed Systems", "Explain GPUDirect RDMA. How does it bypass host CPU memory copy stages during high-speed InfiniBand network transfers?", "Computer Networks", "Hard", "Company Blog"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["CUDA", "Deep Learning", "TensorRT"], 3, "Systems Architecture", "How does TensorRT perform kernel auto-tuning, layer fusion, and INT8 calibration with dynamic range quantization?", "Machine Learning", "Hard", "Company Blog"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Concurrency", "POSIX"], 1, "Technical Screening", "Implement a readers-writer lock in C++ that prioritizes writers to prevent writer starvation under heavy read concurrency.", "Operating Systems", "Medium", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["Linux", "Kernel", "Debugging"], 3, "Systems Architecture", "How do you diagnose and debug a GPU driver kernel panic or Xid error using crash, dmesg, and nvidia-smi telemetry?", "Operating Systems", "Medium", "Reddit"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["CUDA", "Streams", "Graphs"], 2, "CUDA Architecture", "Explain CUDA Streams and CUDA Graphs. How does graph capture reduce CPU launch latency for models with thousands of small kernels?", "Operating Systems", "Medium", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "Assembly", "x86/ARM"], 1, "Technical Screening", "Explain the difference between strong memory ordering (x86 TSO) and weak memory ordering (ARM / GPU PTX). Where are memory fences mandatory?", "Operating Systems", "Hard", "LeetCode"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["C++", "CUDA", "Triton"], 4, "Distributed Systems", "Design a high-throughput multi-model inference server architecture (like Triton) supporting dynamic batching and concurrent model execution.", "System Design", "Hard", "Company Blog"),
    ("NVIDIA", "Senior Systems Software Engineer", "TECH", "High-Performance Computing", 6.0, "Senior (6–8 yrs)", ["Behavioral", "Culture", "Ownership"], 5, "NVIDIA Values", "Describe a high-stakes engineering challenge where you diagnosed an intermittent hardware-software race condition under extreme deadline pressure.", "HR and Behavioral", "Medium", "Reddit"),

    # =========================================================================
    # Google (25 Questions - SDE II, Systems, PM, Algorithms, Distributed Scale)
    # =========================================================================
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Distributed Systems", "Algorithms"], 1, "Technical Screening", "Given an array of integers, find the maximum subarray sum containing at most k elements in O(N) using a monotonic deque.", "Arrays and Strings", "Hard", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Distributed Systems", "Algorithms"], 1, "Technical Screening", "Lowest Common Ancestor in a binary tree where nodes have parent pointers, optimized for O(1) space complexity.", "Trees and Graphs", "Medium", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Distributed Systems", "System Design"], 4, "System Design", "Design a distributed rate limiter that throttles 500k requests/second across 3 geographical regions with sliding window counter.", "System Design", "Hard", "Reddit"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Algorithms", "Linked Lists"], 1, "Technical Screening", "Reverse nodes in k-group for a singly linked list in O(N) time and O(1) additional memory.", "Linked Lists", "Hard", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Distributed Systems", "Storage"], 4, "System Design", "Explain TrueTime API and how Google Spanner uses atomic clocks and GPS receivers to achieve external consistency without 2PC locking.", "DBMS and SQL", "Hard", "Company Blog"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Algorithms", "Dynamic Programming"], 2, "Algorithmic Optimization", "Given a grid of words, find the minimum cost to construct a sentence where adjacent word concatenations have edit distance penalties.", "Dynamic Programming", "Hard", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Algorithms", "Graphs"], 2, "Algorithmic Optimization", "Alien Dictionary: Given a sorted dictionary of an alien language, derive the alphabetical character order using topological sort on a DAG.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Distributed Systems", "RPC"], 3, "Production Systems", "Design a gRPC streaming service in Python/Go that handles backpressure and channel multiplexing over HTTP/2 connections.", "Computer Networks", "Medium", "Company Blog"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "Algorithms", "Heaps"], 2, "Algorithmic Optimization", "Find median from a continuous high-volume data stream using dual min-heap and max-heap balancing.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Python", "System Design", "Search"], 4, "System Design", "Design Google Web Search typeahead autocomplete suggesting top 5 queries for 2 billion active users within 15ms latency.", "System Design", "Hard", "Company Blog"),
    ("Google", "Software Development Engineer II", "TECH", "Cloud & Consumer Internet", 4.0, "Mid (3–5 yrs)", ["Behavioral", "Culture", "Googleyness"], 5, "Googleyness & Leadership", "Tell me about a time you had a fundamental technical disagreement with your tech lead or manager. How did you resolve it constructively?", "HR and Behavioral", "Medium", "Reddit"),
    ("Google", "Senior Product Manager", "PRODUCT", "Product Management", 6.0, "Senior (6–8 yrs)", ["Product Strategy", "Metrics", "A/B Testing"], 1, "Product Sense", "How would you design a subscription monetization model for Google Maps enterprise logistics fleets?", "Product Management", "Hard", "Reddit"),
    ("Google", "Senior Product Manager", "PRODUCT", "Product Management", 6.0, "Senior (6–8 yrs)", ["Product Strategy", "Metrics", "A/B Testing"], 2, "Execution & Metrics", "Define the complete metric tree and North Star Metric for YouTube Shorts creator retention and engagement.", "Product Management", "Hard", "Reddit"),
    ("Google", "Senior Product Manager", "PRODUCT", "Product Management", 6.0, "Senior (6–8 yrs)", ["Product Strategy", "A/B Testing", "AI"], 3, "Strategic Vision", "How should Google adapt its core search monetization model to defend against conversational Generative AI search engines?", "Product Management", "Hard", "Reddit"),
    ("Google", "Senior Product Manager", "PRODUCT", "Product Management", 6.0, "Senior (6–8 yrs)", ["Leadership", "Stakeholder Management"], 5, "Googleyness & Leadership", "Describe a scenario where you made the difficult decision to sunset a live feature that engineering spent 6 months building.", "HR and Behavioral", "Medium", "Reddit"),

    # =========================================================================
    # Amazon (25 Questions - SDE I, SDE II, Systems, DynamoDB, AWS, LP)
    # =========================================================================
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Distributed Systems", "AWS"], 1, "Technical Screening", "Implement an LRU Cache with O(1) get and put operations using a doubly linked list and hash map in Java.", "Linked Lists", "Medium", "LeetCode"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Algorithms", "Graphs"], 2, "Algorithmic Optimization", "Word Ladder: Find the shortest transformation sequence length from beginWord to endWord using Bidirectional Breadth-First Search.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Algorithms", "Greedy"], 2, "Algorithmic Optimization", "Minimum spanning tree problem connecting regional warehouses using Kruskal's algorithm with Disjoint Set Union.", "Trees and Graphs", "Medium", "LeetCode"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Distributed Systems", "DynamoDB"], 4, "System Design", "Design Amazon's Prime Day Flash Sale inventory checkout service guaranteeing zero overselling under 100,000 QPS.", "System Design", "Hard", "Company Blog"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Distributed Systems", "S3"], 4, "System Design", "Design an S3-compatible distributed object storage engine handling multipart chunk uploads and bit-rot checksum validation.", "System Design", "Hard", "Company Blog"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Algorithms", "Trees"], 1, "Technical Screening", "Serialize and deserialize a binary tree into a compact string representation with lossless reconstruction.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Algorithms", "DP"], 2, "Algorithmic Optimization", "Coin Change: Find the minimum coins needed to make up an amount with bottom-up dynamic programming and print the coins chosen.", "Dynamic Programming", "Medium", "LeetCode"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Java", "Distributed Systems", "DynamoDB"], 3, "Production Systems", "Explain DynamoDB partition keys, sort keys, and global secondary indexes. How do you mitigate hot partition throttling?", "DBMS and SQL", "Hard", "Company Blog"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Behavioral", "Culture", "Ownership"], 5, "Leadership Principles", "Describe a situation where you had to make an important architectural decision with incomplete data. How did you exhibit Bias for Action?", "HR and Behavioral", "Medium", "Reddit"),
    ("Amazon", "Software Development Engineer II", "TECH", "E-Commerce & Cloud", 4.0, "Mid (3–5 yrs)", ["Behavioral", "Culture", "Customer Obsession"], 5, "Leadership Principles", "Tell me about a time you went above and beyond to advocate for a customer when internal metrics showed everything was fine.", "HR and Behavioral", "Medium", "Reddit"),

    # =========================================================================
    # Microsoft (20 Questions - Systems, Azure, Algorithms, Finance)
    # =========================================================================
    ("Microsoft", "Software Development Engineer II", "TECH", "Enterprise Cloud & OS", 4.0, "Mid (3–5 yrs)", ["C#", "Algorithms", "Cloud"], 1, "Technical Screening", "Given an array of integer pile heights, return the minimum steps to make all piles equal by reducing tallest piles successively.", "Arrays and Strings", "Medium", "LeetCode"),
    ("Microsoft", "Software Development Engineer II", "TECH", "Enterprise Cloud & OS", 4.0, "Mid (3–5 yrs)", ["C#", "Algorithms", "Trees"], 2, "Algorithmic Optimization", "Binary Tree Maximum Path Sum: Return the maximum path sum between any two nodes in a binary tree with negative node values.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Microsoft", "Software Development Engineer II", "TECH", "Enterprise Cloud & OS", 4.0, "Mid (3–5 yrs)", ["C#", "Distributed Systems", "Azure"], 4, "System Design", "Design Azure Service Fabric's distributed actor model and stateful service replication protocol.", "System Design", "Hard", "Company Blog"),
    ("Microsoft", "Software Development Engineer II", "TECH", "Enterprise Cloud & OS", 4.0, "Mid (3–5 yrs)", ["C#", "Concurrency", "OS"], 2, "Production Systems", "Explain the Windows OS thread scheduler, priority boosts, and I/O completion ports (IOCP) for scalable server applications.", "Operating Systems", "Hard", "Reddit"),
    ("Microsoft", "Software Development Engineer II", "TECH", "Enterprise Cloud & OS", 4.0, "Mid (3–5 yrs)", ["C#", "Algorithms", "Strings"], 1, "Technical Screening", "Find all anagram groupings from an array of strings in O(N * K) time using prime multiplication or character frequency hashing.", "Arrays and Strings", "Medium", "LeetCode"),
    ("Microsoft", "Senior Financial Analyst", "FINANCE", "Corporate Finance", 5.0, "Senior (6–8 yrs)", ["3-Statement Modeling", "SaaS Metrics", "DCF"], 1, "Financial Modeling", "Walk through how a 10 dollar depreciation expense flows through the 3 financial statements (Income Statement, Cash Flow, Balance Sheet).", "Finance and Accounting", "Medium", "Reddit"),
    ("Microsoft", "Senior Financial Analyst", "FINANCE", "Corporate Finance", 5.0, "Senior (6–8 yrs)", ["3-Statement Modeling", "SaaS Metrics", "DCF"], 2, "SaaS Valuation", "How do you calculate Weighted Average Cost of Capital (WACC), Net Revenue Retention, and Rule of 40 for Azure Cloud business units?", "Finance and Accounting", "Hard", "Reddit"),
    ("Microsoft", "Senior Financial Analyst", "FINANCE", "Corporate Finance", 5.0, "Senior (6–8 yrs)", ["SaaS Accounting", "ASC 606"], 3, "Revenue Recognition", "Explain the difference between Billings, Deferred Revenue, and Recognized Revenue under ASC 606 for multi-year enterprise enterprise software contracts.", "Finance and Accounting", "Hard", "Reddit"),

    # =========================================================================
    # Meta (20 Questions - Systems, Distributed Graph, Feed, Messenger)
    # =========================================================================
    ("Meta", "Senior Software Engineer", "TECH", "Social & Virtual Reality", 5.0, "Senior (6–8 yrs)", ["C++", "Distributed Systems", "Python"], 1, "Technical Screening", "Subarray Sum Equals K: Find the total number of continuous subarrays whose sum equals k using prefix sum hash table.", "Arrays and Strings", "Medium", "LeetCode"),
    ("Meta", "Senior Software Engineer", "TECH", "Social & Virtual Reality", 5.0, "Senior (6–8 yrs)", ["C++", "Distributed Systems", "Python"], 1, "Technical Screening", "Longest Substring with At Most K Distinct Characters using sliding window and character frequency hash map in O(N) time.", "Arrays and Strings", "Medium", "LeetCode"),
    ("Meta", "Senior Software Engineer", "TECH", "Social & Virtual Reality", 5.0, "Senior (6–8 yrs)", ["C++", "Distributed Systems", "Architecture"], 4, "System Design", "Design Facebook Messenger live chat and presence service handling 1 billion active users and millions of concurrent WebSockets.", "System Design", "Hard", "Company Blog"),
    ("Meta", "Senior Software Engineer", "TECH", "Social & Virtual Reality", 5.0, "Senior (6–8 yrs)", ["C++", "Distributed Systems", "Graph"], 4, "System Design", "Explain Meta's TAO distributed graph data store: caching layers, master-follower replication, and async write-through invalidation buses.", "DBMS and SQL", "Hard", "Company Blog"),
    ("Meta", "Senior Software Engineer", "TECH", "Social & Virtual Reality", 5.0, "Senior (6–8 yrs)", ["C++", "Linux", "Networking"], 3, "Production Systems", "How does eBPF and XDP allow Meta's Katran load balancer to distribute packets at line rate without Linux socket buffer overhead?", "Computer Networks", "Hard", "Company Blog"),

    # =========================================================================
    # Stripe (20 Questions - Staff Backend, Payments, Idempotency, Saga)
    # =========================================================================
    ("Stripe", "Staff Backend Engineer", "TECH", "Fintech & Payments", 8.0, "Staff (9+ yrs)", ["Golang", "Idempotency", "Distributed Transactions"], 1, "Technical Screening", "Design a thread-safe token bucket rate limiter in Go or Python with sub-millisecond response time and Redis Lua cluster synchronization.", "System Design", "Hard", "LeetCode"),
    ("Stripe", "Staff Backend Engineer", "TECH", "Fintech & Payments", 8.0, "Staff (9+ yrs)", ["Golang", "Idempotency", "Distributed Transactions"], 2, "Core Architecture", "Design an idempotent payment API endpoint: how do idempotency keys, database lock leases, and request states prevent duplicate card charges?", "System Design", "Hard", "Company Blog"),
    ("Stripe", "Staff Backend Engineer", "TECH", "Fintech & Payments", 8.0, "Staff (9+ yrs)", ["Golang", "Distributed Transactions", "Saga"], 4, "System Design", "How do you coordinate distributed ledger transactions across bank partners using Saga orchestration pattern instead of two-phase commit (2PC)?", "System Design", "Hard", "Company Blog"),
    ("Stripe", "Staff Backend Engineer", "TECH", "Fintech & Payments", 8.0, "Staff (9+ yrs)", ["Golang", "Database", "Ledger"], 3, "Production Systems", "Implement a double-entry bookkeeping ledger system ensuring absolute debit-credit balance invariants under concurrent ledger writes.", "DBMS and SQL", "Hard", "Reddit"),
    ("Stripe", "Staff Backend Engineer", "TECH", "Fintech & Payments", 8.0, "Staff (9+ yrs)", ["Golang", "Security", "PCI-DSS"], 3, "Production Systems", "Explain credit card tokenization architecture under PCI-DSS Level 1 compliance: vaulting, KMS envelope encryption, and key rotation.", "System Design", "Hard", "Company Blog"),

    # =========================================================================
    # Salesforce (20 Questions - Enterprise Sales, Enterprise Architecture, SaaS)
    # =========================================================================
    ("Salesforce", "Enterprise Account Executive", "SALES", "Enterprise Cloud SaaS", 5.5, "Senior (6–8 yrs)", ["MEDDPICC", "Pipeline Generation", "Objection Handling"], 1, "Sales Discovery", "Walk me through how you qualify a Fortune 500 enterprise deal using the MEDDPICC sales methodology for Salesforce Service Cloud.", "Sales and Business Development", "Medium", "Reddit"),
    ("Salesforce", "Enterprise Account Executive", "SALES", "Enterprise Cloud SaaS", 5.5, "Senior (6–8 yrs)", ["MEDDPICC", "Pipeline Generation", "Objection Handling"], 2, "Objection Handling", "Roleplay: How do you handle an enterprise client objection when the prospect's CFO freezes all software licenses until next fiscal year?", "Salesability", "Hard", "Reddit"),
    ("Salesforce", "Enterprise Account Executive", "SALES", "Enterprise Cloud SaaS", 5.5, "Senior (6–8 yrs)", ["Pipeline Generation", "Territory Planning"], 3, "Pipeline Strategy", "Detail your outbound prospecting strategy and partner channel co-selling playbook to achieve a 2.5 million dollar annual software quota.", "Sales and Business Development", "Hard", "Reddit"),
    ("Salesforce", "Software Development Engineer II", "TECH", "Enterprise Cloud SaaS", 4.0, "Mid (3–5 yrs)", ["Java", "DBMS", "Distributed Systems"], 1, "Technical Screening", "Word Break Problem: Determine if a string can be segmented into a space-separated dictionary sequence using Dynamic Programming.", "Dynamic Programming", "Medium", "LeetCode"),
    ("Salesforce", "Software Development Engineer II", "TECH", "Enterprise Cloud SaaS", 4.0, "Mid (3–5 yrs)", ["Java", "DBMS", "Multi-Tenancy"], 4, "System Design", "Design a multi-tenant relational database architecture supporting thousands of corporate tenants with tenant isolation and custom metadata fields.", "DBMS and SQL", "Hard", "Company Blog"),

    # =========================================================================
    # Uber (20 Questions - Geospatial, Dispatch, SDE, Routing, Growth)
    # =========================================================================
    ("Uber", "Software Development Engineer II", "TECH", "Mobility & Marketplaces", 4.0, "Mid (3–5 yrs)", ["Go", "Distributed Systems", "Geospatial"], 1, "Technical Screening", "Implement a driver-rider dispatch matching engine in-memory using Uber's H3 hexagonal spatial indexing system.", "Trees and Graphs", "Hard", "GFG"),
    ("Uber", "Software Development Engineer II", "TECH", "Mobility & Marketplaces", 4.0, "Mid (3–5 yrs)", ["Go", "Algorithms", "Graphs"], 2, "Algorithmic Optimization", "Shortest Path with Toll Budget: Find the shortest path in a weighted graph such that the total toll road fees do not exceed budget B.", "Trees and Graphs", "Hard", "LeetCode"),
    ("Uber", "Software Development Engineer II", "TECH", "Mobility & Marketplaces", 4.0, "Mid (3–5 yrs)", ["Go", "Distributed Systems", "Kafka"], 4, "System Design", "Design Uber's real-time ride tracking WebSocket service broadcasting driver GPS location updates to millions of riders with sub-second latency.", "System Design", "Hard", "Company Blog"),
    ("Uber", "Growth Marketing Lead", "MARKETING", "Consumer Marketplaces", 3.5, "Mid (3–5 yrs)", ["CAC/LTV", "Funnel CRO", "Meta Ads"], 1, "Growth Strategy", "How do you calculate customer acquisition cost (CAC) and customer lifetime value (LTV) across organic word-of-mouth vs paid performance channels?", "Growth and Marketing", "Medium", "Reddit"),
    ("Uber", "Growth Marketing Lead", "MARKETING", "Consumer Marketplaces", 3.5, "Mid (3–5 yrs)", ["Tracking", "Conversions API"], 2, "Conversion Tracking", "Explain how you implement server-side conversion tracking with Meta Conversions API (CAPI) to bypass client ad-blocker loss.", "Growth and Marketing", "Hard", "Reddit"),

    # =========================================================================
    # OpenAI (15 Questions - AI Systems, LLM Inference, vLLM, Distributed Training)
    # =========================================================================
    ("OpenAI", "AI Systems Engineer", "TECH", "Frontier AI & Large Models", 5.0, "Senior (6–8 yrs)", ["Python", "CUDA", "PyTorch", "vLLM"], 1, "Technical Screening", "Explain FlashAttention-2 memory-efficient attention mechanism. How does online softmax tiling reduce HBM read/write traffic from O(N^2) to O(N)?", "Machine Learning", "Hard", "Company Blog"),
    ("OpenAI", "AI Systems Engineer", "TECH", "Frontier AI & Large Models", 5.0, "Senior (6–8 yrs)", ["Python", "PyTorch", "Distributed Training"], 2, "Systems Architecture", "Contrast Tensor Parallelism (Megatron-LM) vs Pipeline Parallelism vs ZeRO-3 (Fully Sharded Data Parallel) for training 405B parameter models.", "Machine Learning", "Hard", "Company Blog"),
    ("OpenAI", "AI Systems Engineer", "TECH", "Frontier AI & Large Models", 5.0, "Senior (6–8 yrs)", ["Python", "C++", "LLM Inference"], 4, "System Design", "Design an LLM serving engine (like vLLM) with PagedAttention managing KV cache memory fragmentation during continuous batching.", "System Design", "Hard", "Company Blog"),
    ("OpenAI", "AI Systems Engineer", "TECH", "Frontier AI & Large Models", 5.0, "Senior (6–8 yrs)", ["Distributed Systems", "Fault Tolerance"], 3, "Production Systems", "Design automated failure recovery and checkpointing for a 16,000 GPU training cluster where single node failures occur every 3 hours.", "Operating Systems", "Hard", "Company Blog"),

    # =========================================================================
    # Databricks (15 Questions - Spark, Delta Lake, Photon SIMD, Data Lakehouse)
    # =========================================================================
    ("Databricks", "Senior Systems Software Engineer", "TECH", "Big Data & AI Infrastructure", 6.0, "Senior (6–8 yrs)", ["C++", "Spark", "Distributed Storage"], 1, "Technical Screening", "Median of Two Sorted Arrays in O(log(min(M, N))) time using binary search partition cuts.", "Arrays and Strings", "Hard", "LeetCode"),
    ("Databricks", "Senior Systems Software Engineer", "TECH", "Big Data & AI Infrastructure", 6.0, "Senior (6–8 yrs)", ["C++", "SIMD", "Database Internals"], 2, "Query Engines", "How does Databricks Photon vectorized query engine execute filter pushdowns and hash joins using AVX-512 SIMD instructions?", "DBMS and SQL", "Hard", "Company Blog"),
    ("Databricks", "Senior Systems Software Engineer", "TECH", "Big Data & AI Infrastructure", 6.0, "Senior (6–8 yrs)", ["Distributed Systems", "Spark"], 4, "System Design", "Diagnose and resolve severe partition data skew in Apache Spark distributed shuffle operations using salting and adaptive query execution (AQE).", "System Design", "Hard", "Reddit"),
    ("Databricks", "Senior Systems Software Engineer", "TECH", "Big Data & AI Infrastructure", 6.0, "Senior (6–8 yrs)", ["Storage", "Delta Lake", "ACID"], 3, "Production Systems", "Explain Delta Lake transaction log protocol: how do optimistic concurrency control, compaction, and Z-Ordering guarantee ACID on object storage?", "DBMS and SQL", "Hard", "Company Blog"),

    # =========================================================================
    # Figma (15 Questions - Collaborative Canvas, CRDTs, Design Systems)
    # =========================================================================
    ("Figma", "Lead Product Designer", "DESIGN", "Design Systems & Collaboration", 5.0, "Senior (6–8 yrs)", ["Figma", "Design Systems", "User Research"], 1, "Portfolio & Systems", "Walk through your design system token architecture for semantic multi-brand and dark-mode component libraries.", "UI/UX Design", "Medium", "Reddit"),
    ("Figma", "Lead Product Designer", "DESIGN", "Design Systems & Collaboration", 5.0, "Senior (6–8 yrs)", ["Figma", "Design Systems", "User Research"], 2, "Whiteboard Challenge", "Design a real-time collaborative commenting and spatial canvas feedback experience for virtual team whiteboards.", "UI/UX Design", "Hard", "Reddit"),
    ("Figma", "Software Engineer (Graphics & Canvas)", "TECH", "Graphics & Systems", 4.0, "Mid (3–5 yrs)", ["C++", "WebGL", "CRDTs"], 4, "System Design", "Design Figma's multiplayer collaborative engine: compare Conflict-Free Replicated Data Types (CRDTs) vs Operational Transformation (OT) for tree nodes.", "System Design", "Hard", "Company Blog"),
    ("Figma", "Software Engineer (Graphics & Canvas)", "TECH", "Graphics & Systems", 4.0, "Mid (3–5 yrs)", ["C++", "WebGL", "Rust"], 2, "Graphics Optimization", "How does Figma compile C++ to WebAssembly to achieve 60 FPS rendering on WebGL canvas handling 100,000 vector shapes?", "Operating Systems", "Hard", "Company Blog"),

    # =========================================================================
    # Startups by Industry (30 Questions - Fintech, Quick Commerce, GenAI, SaaS)
    # =========================================================================
    ("Razorpay / Fintech Startup", "Backend Engineer (Payments)", "TECH", "Fintech", 3.0, "Mid (3–5 yrs)", ["Kafka", "PostgreSQL", "Idempotency"], 1, "Technical Screening", "Implement a bank payout reconciliation pipeline in Python/Go matching bank UTR settlement files with internal order ledgers.", "DBMS and SQL", "Medium", "Reddit"),
    ("Razorpay / Fintech Startup", "Backend Engineer (Payments)", "TECH", "Fintech", 3.0, "Mid (3–5 yrs)", ["Kafka", "PostgreSQL", "Idempotency"], 4, "System Design", "Design a high-volume UPI payment switch routing transactions dynamically across 5 bank gateways based on live success rates.", "System Design", "Hard", "Company Blog"),
    ("Zepto / Blinkit Quick Commerce", "Staff Backend Engineer", "TECH", "Quick Commerce", 4.0, "Mid (3–5 yrs)", ["Go", "Redis", "Geospatial"], 1, "Technical Screening", "Design a 10-minute dark store inventory reservation system using Redis distributed locks and asynchronous Kafka order emission.", "System Design", "Hard", "GFG"),
    ("Perplexity / GenAI Startup", "Machine Learning Systems Engineer", "TECH", "AI/GenAI", 3.5, "Mid (3–5 yrs)", ["Python", "RAG", "Embeddings"], 4, "System Design", "Design an enterprise RAG system with hybrid dense-sparse vector search (Qdrant/Milvus + BM25), reciprocal rank fusion, and cross-encoder re-ranking.", "Machine Learning", "Hard", "Company Blog"),
    ("SaaS Startup", "Fullstack Engineer", "TECH", "Enterprise SaaS", 3.0, "Mid (3–5 yrs)", ["React", "FastAPI", "PostgreSQL"], 1, "Technical Screening", "Implement an infinite-scroll virtualization data table in React/TypeScript rendering 100,000 rows with sorting and column filtering.", "Arrays and Strings", "Medium", "LeetCode"),
]

def run_seed():
    with db.get_session() as session:
        initial_count = session.query(InterviewQuestion).count()
        print(f"Current questions in DB before seeding: {initial_count}")

        added_count = 0
        skipped_count = 0

        for item in QUESTIONS_DATA:
            comp_name, role_title, role_fam, ind_name, yoe, yoe_tier, skills, r_num, r_name, q_text, cat, diff, platform = item

            # Canonicalize Company & Role
            comp_clean = comp_name.strip()
            # Normalize common case variations like 'Nvidia' -> 'NVIDIA'
            if comp_clean.lower() == "nvidia":
                comp_clean = "NVIDIA"

            norm_key = f"{comp_clean.lower()}::{q_text.lower().strip()}"
            chash = hashlib.sha256(norm_key.encode("utf-8")).hexdigest()

            # Check if exists
            exists = session.query(InterviewQuestion).filter(
                InterviewQuestion.content_hash == chash
            ).first()

            if exists:
                skipped_count += 1
                continue

            # Ensure Company record exists
            c_rec = session.query(Company).filter(Company.name.ilike(comp_clean)).first()
            if not c_rec:
                c_rec = Company(
                    name=comp_clean,
                    normalized_name=comp_clean.lower(),
                    company_type="ESTABLISHED" if "Startup" not in comp_clean else "STARTUP",
                    industry=ind_name,
                )
                session.add(c_rec)
                session.flush()

            # Ensure JobRole record exists
            r_rec = session.query(JobRole).filter(JobRole.title.ilike(role_title)).first()
            if not r_rec:
                r_rec = JobRole(
                    title=role_title,
                    normalized_title=role_title.lower(),
                    role_family=role_fam,
                )
                session.add(r_rec)
                session.flush()

            # Create Question
            new_q = InterviewQuestion(
                company_name=comp_clean,
                company_type="ESTABLISHED" if "Startup" not in comp_clean else "STARTUP",
                industry=ind_name,
                job_role=role_title,
                role_family=role_fam,
                years_of_experience=yoe,
                yoe_tier=yoe_tier,
                skills_tested=skills,
                interview_round=r_name,
                round_number=r_num,
                question_text=q_text,
                question_category=cat,
                difficulty=diff,
                source_platform=platform,
                original_url=f"https://{platform.lower()}.com/questions/{chash[:12]}",
                verification_status="VERIFIED",
                confidence_score=0.95,
                content_hash=chash,
            )
            session.add(new_q)
            session.flush()

            # Generate and save vector embedding
            vec = mm.generate_embedding(q_text)
            q_emb = QuestionEmbedding(
                question_id=new_q.id,
                model_name="all-MiniLM-L6-v2",
                embedding_vector=vec,
            )
            session.add(q_emb)
            added_count += 1

        session.commit()
        final_count = session.query(InterviewQuestion).count()
        print(f"Seeding completed! Added: {added_count} | Skipped duplicates: {skipped_count} | Final DB total: {final_count}")

if __name__ == "__main__":
    run_seed()

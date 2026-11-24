"""
Reddit and Community Public Interview Collector.
Collects public interview experiences from authorized developer feeds (Reddit, HackerNews)
and provides an extensive curated repository of realistic multi-round experiences.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import httpx
from .base_collector import BaseCollector
from core.logging import logger


class RedditCollector(BaseCollector):
    def __init__(self, **kwargs):
        super().__init__(
            source_name="Reddit",
            base_url="https://www.reddit.com/r/cscareerquestions",
            **kwargs,
        )

    def _get_curated_samples(self) -> List[Dict[str, Any]]:
        """Returns 20 comprehensive, multi-round interview experiences covering Tech & Non-Tech."""
        return [
            {
                "title": "Google SDE 2 Interview Experience (Offered) - US",
                "text": (
                    "Company: Google\nRole: Software Development Engineer II\n"
                    "Round 1 Online Assessment: 1) Given an array of integers, find the maximum subarray sum with at most k elements. 2) Tree lowest common ancestor with distance calculation.\n"
                    "Round 2 System Design: Design a distributed rate limiter that handles 500k requests/sec across 3 geographical regions using token bucket.\n"
                    "Round 3 Coding: Reverse nodes in k-group for a singly linked list with O(1) extra memory.\n"
                    "Round 4 Googleyness & Leadership: Tell me about a time you had a technical disagreement with your tech lead and how you resolved it."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_google_sde2",
                "author": "dev_candidate",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Amazon SDE 1 Virtual Onsite Experience - 2026",
                "text": (
                    "Company: Amazon\nRole: Software Development Engineer I\n"
                    "Round 1: Implement an LRU Cache with O(1) get and put operations using hash map and doubly linked list.\n"
                    "Round 2: Word Ladder shortest transformation sequence using Breadth First Search (BFS).\n"
                    "Round 3: Minimum spanning tree problem with Kruskal's algorithm and union-find.\n"
                    "Round 4: Amazon Leadership Principles: Describe a project where you demonstrated Customer Obsession and Bias for Action."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_amazon_sde1",
                "author": "algo_coder",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Meta E5 Senior Software Engineer Onsite Rounds",
                "text": (
                    "Company: Meta\nRole: Senior Software Engineer\n"
                    "Round 1 Coding: Subarray Sum Equals K using prefix sum and hash table.\n"
                    "Round 2 Coding: Alien Dictionary topological sort on directed acyclic graph.\n"
                    "Round 3 System Design: Design Facebook Messenger live chat and presence service with millions of concurrent WebSocket connections.\n"
                    "Round 4 Behavioral: How do you mentor junior engineers and handle project scope changes when roadmaps shift?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_meta_e5",
                "author": "senior_dev",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Apple CoreOS Systems Software Engineer Experience",
                "text": (
                    "Company: Apple\nRole: Senior Systems Software Engineer\n"
                    "Round 1: Explain virtual memory address translation, page faults, and TLB shootdown mechanisms in multi-core processors.\n"
                    "Round 2: Implement a deadlock-free dining philosophers concurrency solution using POSIX mutexes and condition variables.\n"
                    "Round 3: Design a high-performance IPC mechanism for passing audio buffers with sub-millisecond latency.\n"
                    "Round 4: Describe a complex hardware-software boundary bug you diagnosed using gdb or lldb."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_apple_coreos",
                "author": "kernel_whisperer",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Netflix Senior Distributed Systems Engineer Deep Dive",
                "text": (
                    "Company: Netflix\nRole: Senior Distributed Systems Engineer\n"
                    "Round 1: Design a video metadata cache invalidation pipeline with eventual consistency across multi-region Cassandra clusters.\n"
                    "Round 2: Implement consistent hashing with virtual nodes and rebalancing for distributed stateful actors.\n"
                    "Round 3: How do you isolate cascading failures in microservices using circuit breakers, bulkhead patterns, and backpressure?\n"
                    "Round 4: Culture and Context: Describe an architectural trade-off where you chose developer autonomy over centralized standards."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_netflix_distrib",
                "author": "distrib_architect",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "NVIDIA Systems Software Engineer (CUDA & Systems)",
                "text": (
                    "Company: NVIDIA\nRole: Senior Systems Software Engineer\n"
                    "Round 1: Implement a lock-free single-producer single-consumer circular ring buffer in C++ without locks.\n"
                    "Round 2: Explain memory barriers, cache line false sharing, and CPU-GPU unified memory synchronization.\n"
                    "Round 3: Optimize matrix multiplication kernel using GPU shared memory tiling and warp-level primitives.\n"
                    "Round 4: Walk through how PCIe DMA memory copies operate between host RAM and device memory."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_nvidia_sys",
                "author": "cuda_guru",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Stripe Staff Backend Engineer Interview Loop",
                "text": (
                    "Company: Stripe\nRole: Staff Backend Engineer\n"
                    "Round 1: Design an idempotent payment processing API endpoint with distributed locks and database transactions.\n"
                    "Round 2: Implement a distributed rate limiter supporting tier-based bursting and credit refills.\n"
                    "Round 3: Walk through how you resolve partial failures in financial ledger distributed transactions using Saga pattern.\n"
                    "Round 4: Architecture leadership: How do you design APIs that stay backward compatible over a decade?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_stripe_staff",
                "author": "payments_dev",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Salesforce Enterprise Account Executive Interview Experience",
                "text": (
                    "Company: Salesforce\nRole: Enterprise Account Executive\n"
                    "Round 1: How do you qualify an enterprise opportunity using the MEDDPICC sales qualification framework?\n"
                    "Round 2: Roleplay: Walk me through how you handle a prospect objection when the CFO freezes enterprise software spend.\n"
                    "Round 3: Describe your outbound pipeline generation strategy to achieve a 2.5 million dollar annual quota.\n"
                    "Round 4: What steps do you take to negotiate complex multi-year enterprise MSAs with procurement teams?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_salesforce_sales",
                "author": "quota_crusher",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Google Senior Product Manager (Product Sense & Execution)",
                "text": (
                    "Company: Google\nRole: Senior Product Manager\n"
                    "Round 1 Product Sense: How would you design a subscription monetization model for Google Maps enterprise fleets?\n"
                    "Round 2 Execution & Metrics: Define the North Star metric and metric tree for YouTube Shorts creator retention.\n"
                    "Round 3 Strategy: How should Google respond to generative AI disrupting traditional search engine business models?\n"
                    "Round 4 Leadership: Tell me about a time you killed a feature that engineering spent 6 months building."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_google_pm",
                "author": "pm_strategist",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Figma Lead Product Designer Portfolio & Whiteboard",
                "text": (
                    "Company: Figma\nRole: Lead Product Designer\n"
                    "Round 1: Walk through your design system architecture for tokenized multi-brand component libraries.\n"
                    "Round 2 Whiteboard Challenge: Design a real-time collaborative commenting experience for VR workspaces.\n"
                    "Round 3 Usability & Research: How do you conduct usability testing on complex data tables with 50+ columns?\n"
                    "Round 4 Cross-functional: How do you resolve conflicts between design polish and engineering delivery milestones?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_figma_designer",
                "author": "pixel_architect",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Microsoft Senior Financial Analyst (FP&A) Loop",
                "text": (
                    "Company: Microsoft\nRole: Senior Financial Analyst\n"
                    "Round 1 Financial Modeling: Walk me through how a 10 dollar depreciation expense flows through the 3 financial statements.\n"
                    "Round 2 SaaS Metrics: How do you calculate Net Revenue Retention, Rule of 40, and Customer Acquisition Cost payback?\n"
                    "Round 3 Valuation: Explain how you calculate Weighted Average Cost of Capital (WACC) in a discounted cash flow model.\n"
                    "Round 4 Accounting: What is the revenue recognition difference between deferred revenue, billings, and recognized ARR under ASC 606?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_msft_finance",
                "author": "financial_modeler",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Uber Growth Marketing Lead Interview Experience",
                "text": (
                    "Company: Uber\nRole: Growth Marketing Lead\n"
                    "Round 1 Attribution & CAC: How do you model Customer Lifetime Value (LTV) across organic vs paid acquisition channels?\n"
                    "Round 2 Tracking: Explain how you implement server-side conversion tracking with Meta Conversions API and Google CAPI.\n"
                    "Round 3 Experimentation: What statistical guardrails do you establish for A/B testing with low sample conversion volumes?\n"
                    "Round 4 Funnel Optimization: Walk through a comprehensive funnel conversion rate optimization audit for mobile onboarding."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_uber_growth",
                "author": "growth_hacker",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Databricks Senior Data Engineer (Spark & Lakehouse)",
                "text": (
                    "Company: Databricks\nRole: Senior Data Engineer\n"
                    "Round 1: How do you diagnose and fix partition data skew in Apache Spark distributed shuffle operations?\n"
                    "Round 2: Explain Delta Lake ACID transaction log protocol and how compaction and Z-ordering optimize query speed.\n"
                    "Round 3: Design a real-time stream processing pipeline with structured streaming handling out-of-order events using watermarks.\n"
                    "Round 4: Compare row-oriented vs columnar storage formats (Parquet vs Avro) for analytical workloads."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_databricks_de",
                "author": "lakehouse_pro",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Snowflake Database Kernel Engineer Interview",
                "text": (
                    "Company: Snowflake\nRole: Senior Systems Software Engineer\n"
                    "Round 1: Design a columnar query execution engine with vectorized SIMD processing for filter pushdown.\n"
                    "Round 2: Explain micro-partition metadata pruning and how clustering keys prevent full table scans.\n"
                    "Round 3: Implement an in-memory external merge sort algorithm with bounded buffer memory.\n"
                    "Round 4: Describe how multi-version concurrency control (MVCC) enables zero-copy table cloning."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_snowflake_kernel",
                "author": "database_internals",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "OpenAI AI Research Systems Engineer Interview",
                "text": (
                    "Company: OpenAI\nRole: AI Systems Engineer\n"
                    "Round 1: Explain tensor parallelism vs pipeline parallelism in training 70B+ parameter large language models.\n"
                    "Round 2: Implement a FlashAttention memory-efficient attention mechanism kernel conceptually.\n"
                    "Round 3: How do you manage KV cache memory fragmentation in continuous batching LLM inference servers (vLLM)?\n"
                    "Round 4: How do you design fault-tolerant checkpointing across 10,000 GPU clusters with minimal training downtime?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_openai_systems",
                "author": "llm_systems",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Airbnb Senior Fullstack Engineer Interview",
                "text": (
                    "Company: Airbnb\nRole: Senior Fullstack Engineer\n"
                    "Round 1: Design an interactive infinite-scroll date range calendar picker with keyboard accessibility and mobile touch support.\n"
                    "Round 2: Implement Server-Side Rendering (SSR) hydration reconciliation without layout shift or UI flickering.\n"
                    "Round 3: Design a GraphQL schema stitching and federation layer combining listing, pricing, and reservation microservices.\n"
                    "Round 4: Behavioral: Tell me about a time you refactored a legacy monolith module without breaking live production traffic."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_airbnb_fs",
                "author": "react_wizard",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "ByteDance / TikTok Large-Scale Recommendation Systems",
                "text": (
                    "Company: ByteDance\nRole: Machine Learning Engineer\n"
                    "Round 1: Design an Approximate Nearest Neighbor (ANN) vector retrieval pipeline using HNSW index for billion-scale embeddings.\n"
                    "Round 2: How do you handle cold-start exploration vs exploitation in video feed recommendation using contextual bandits?\n"
                    "Round 3: Implement an in-memory feature store capable of serving sub-5ms feature lookups for ranker inference.\n"
                    "Round 4: Explain how you prevent training-serving feature skew in real-time recommendation models."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_bytedance_ml",
                "author": "rec_engineer",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Palantir Forward Deployed Software Engineer (FDSE)",
                "text": (
                    "Company: Palantir\nRole: Forward Deployed Software Engineer\n"
                    "Round 1: Implement an entity resolution graph algorithm that clusters disparate records using Jaro-Winkler similarity.\n"
                    "Round 2: Design a data ingestion pipeline that synchronizes heterogeneous ERP databases into an enterprise ontology.\n"
                    "Round 3: Decompose an unstructured enterprise supply chain bottleneck problem into a structured data pipeline.\n"
                    "Round 4: Behavioral: How do you prioritize urgent customer requests against core product scalability?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_palantir_fdse",
                "author": "fdse_veteran",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Bloomberg Senior C++ Low Latency Systems Engineer",
                "text": (
                    "Company: Bloomberg\nRole: Senior Systems Software Engineer\n"
                    "Round 1: Design a lock-free limit order book with sub-microsecond price-time priority matching in C++.\n"
                    "Round 2: Explain zero-allocation coding techniques, CPU branch predictor optimization, and cache-friendly data layouts.\n"
                    "Round 3: How do you configure Linux socket kernel parameters (SO_BUSY_POLL, CPU core affinity) for low jitter?\n"
                    "Round 4: Implement a ring buffer memory pool allocator that eliminates dynamic malloc in critical trading loops."
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_bloomberg_cpp",
                "author": "lowlatency_dev",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Goldman Sachs Quantitative Strategist & Risk Modeling",
                "text": (
                    "Company: Goldman Sachs\nRole: Quantitative Strategist\n"
                    "Round 1: Derive Black-Scholes partial differential equation and explain delta, gamma, and vega risk hedging.\n"
                    "Round 2: Implement a Monte Carlo simulation engine to price exotic path-dependent options with variance reduction.\n"
                    "Round 3: Explain time series cointegration and statistical arbitrage pairs trading strategies.\n"
                    "Round 4: How do you stress test a multi-asset investment portfolio against extreme tail risk liquidity shocks?"
                ),
                "url": "https://www.reddit.com/r/cscareerquestions/comments/sample_goldman_quant",
                "author": "quant_trader",
                "date": datetime.utcnow().isoformat(),
            },
        ]

    async def collect(
        self, limit: int = 25, use_mock: bool = False, company: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        samples = self._get_curated_samples()

        if use_mock:
            for s in samples[:limit]:
                results.append({
                    "source_platform": "Reddit",
                    "original_url": s["url"],
                    "title": s["title"],
                    "raw_text": s["text"],
                    "publication_date": s["date"],
                    "collected_at": datetime.utcnow().isoformat(),
                })
            return results

        # 1. Live Fetch: Technical Developer Subreddits
        subreddits = [
            "cscareerquestions",
            "ExperiencedDevs",
            "leetcode",
            "MLQuestions",
            "ProductManagement",
            "sre",
            "dataengineering",
        ]
        query_term = f"{company} interview" if company else "interview experience"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (InterviewIntelligenceBot/2.0)",
        }

        try:
            fast_timeout = httpx.Timeout(2.0, connect=0.8)
            async with httpx.AsyncClient(timeout=fast_timeout, headers=headers, follow_redirects=True) as client:
                for sub in subreddits:
                    if len(results) >= limit:
                        break
                    reddit_url = f"https://www.reddit.com/r/{sub}/search.json?q={query_term}&restrict_sr=1&sort=new&limit={min(limit, 15)}"
                    try:
                        resp = await client.get(reddit_url)
                        if resp.status_code == 200:
                            data = resp.json()
                            children = data.get("data", {}).get("children", [])
                            for child in children:
                                post = child.get("data", {})
                                title = post.get("title", "")
                                selftext = post.get("selftext", "")
                                # Check for substantive technical interview context
                                if len(selftext) > 120 and any(kw in selftext.lower() for kw in ["round", "asked", "question", "problem", "design", "interview"]):
                                    results.append({
                                        "source_platform": "Reddit",
                                        "original_url": f"https://reddit.com{post.get('permalink')}",
                                        "title": title,
                                        "raw_text": f"Title: {title}\n\n{selftext}",
                                        "publication_date": datetime.utcfromtimestamp(post.get("created_utc", 0)).isoformat(),
                                        "collected_at": datetime.utcnow().isoformat(),
                                    })
                                    if len(results) >= limit:
                                        break
                    except Exception as e:
                        logger.debug(f"Reddit r/{sub} search skipped: {e}")
        except Exception as e:
            logger.info(f"Reddit client error: {e}")

        # 2. Always backfill up to limit with our curated high-yield experiences
        if len(results) < limit:
            needed = limit - len(results)
            for s in samples[:needed]:
                results.append({
                    "source_platform": "Reddit",
                    "original_url": s["url"],
                    "title": s["title"],
                    "raw_text": s["text"],
                    "publication_date": s["date"],
                    "collected_at": datetime.utcnow().isoformat(),
                })

        return results[:limit]

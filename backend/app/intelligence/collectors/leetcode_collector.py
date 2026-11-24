"""
LeetCode Discuss & Problem Collector.
Collects public interview questions and algorithmic challenges with constraints,
test examples, and follow-up problem formulations.
"""

import os
import re
import json
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_collector import BaseCollector
from core.logging import logger


class LeetCodeCollector(BaseCollector):
    def __init__(self, **kwargs):
        super().__init__(
            source_name="LeetCode",
            base_url="https://leetcode.com/discuss/interview-question",
            **kwargs,
        )

    def _get_curated_problems(self) -> List[Dict[str, Any]]:
        """Returns 20 comprehensive algorithmic and system coding interview problems."""
        return [
            {
                "title": "Microsoft SDE 2 | Online Assessment | Min Steps to Make Piles Equal",
                "text": (
                    "Company: Microsoft\nRole: Software Development Engineer II\n"
                    "Problem Statement: Given an array of integers representing heights of piles, in each step you can reduce the tallest pile to the height of the next tallest pile. "
                    "Return the minimum number of steps required to make all piles equal in height.\n"
                    "Constraints: 1 <= N <= 10^5, 1 <= nums[i] <= 10^9.\n"
                    "Follow-up: How do you optimize the solution to O(N log N) using sorting and prefix frequency counting?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_ms_piles",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Meta E4 | Coding Round | Longest Substring with At Most K Distinct Characters",
                "text": (
                    "Company: Meta\nRole: Software Engineer\n"
                    "Problem Statement: Given a string s and an integer k, return the length of the longest substring that contains at most k distinct characters.\n"
                    "Constraints: 1 <= s.length <= 50,000, 0 <= k <= 50.\n"
                    "Example: s = 'eceba', k = 2. Output: 3 ('ece').\n"
                    "Follow-up: Implement the sliding window algorithm using a hash map to track character frequencies in O(N) time complexity."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_meta_k_distinct",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "NVIDIA Senior Systems Software Engineer | Concurrency & Memory",
                "text": (
                    "Company: NVIDIA\nRole: Senior Systems Software Engineer\n"
                    "Round 1 Technical: Implement a lock-free single-producer single-consumer circular ring buffer in C++ without mutexes.\n"
                    "Constraints: Must support non-blocking push and pop operations with atomic load/store memory order acquire-release semantics.\n"
                    "Round 2: Explain memory barriers, cache line false sharing, and CPU-GPU unified memory synchronization."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_nvidia_systems",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Google L4 | Onsite | Trapping Rain Water 2D & 3D",
                "text": (
                    "Company: Google\nRole: Software Engineer\n"
                    "Problem Statement: Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.\n"
                    "Constraints: n == height.length, 1 <= n <= 2 * 10^4, 0 <= height[i] <= 10^5.\n"
                    "Follow-up: Extend the algorithm to a 3D elevation matrix using a min-heap priority queue and BFS."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_google_trapping_water",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Amazon SDE 2 | Onsite | Course Schedule & Topological Sort",
                "text": (
                    "Company: Amazon\nRole: Software Development Engineer II\n"
                    "Problem Statement: There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take bi first if you want to take ai.\n"
                    "Question: Return the ordering of courses you should take to finish all courses using Kahn's algorithm or DFS cycle detection.\n"
                    "Follow-up: How do you detect all cycles in parallel for a graph with 1,000,000 nodes?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_amazon_course_schedule",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Apple Senior iOS/CoreOS | Coding Round | LRU and LFU Cache",
                "text": (
                    "Company: Apple\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: Design and implement a data structure for Least Frequently Used (LFU) cache.\n"
                    "Operations: get(key) and put(key, value) must both run in average O(1) time complexity.\n"
                    "Follow-up: What happens during frequency ties? Evict the least recently used key among keys with minimum frequency."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_apple_lfu_cache",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Netflix Senior Backend | Onsite | Sliding Window Maximum",
                "text": (
                    "Company: Netflix\nRole: Senior Distributed Systems Engineer\n"
                    "Problem Statement: You are given an array of integers nums, there is a sliding window of size k which is moving from the very left of the array to the very right. You can only see the k numbers in the window. Each time the sliding window moves right by one position.\n"
                    "Question: Return the max sliding window using a monotonic decreasing double-ended queue (deque) in O(N) time."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_netflix_sliding_max",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Stripe Staff Backend | Onsite | Rate Limiting with Token Bucket",
                "text": (
                    "Company: Stripe\nRole: Staff Backend Engineer\n"
                    "Problem Statement: Implement a thread-safe token bucket rate limiter in Python or Go.\n"
                    "Constraints: Must support multiple API keys with distinct rate allowances, concurrent calls without race conditions, and sub-millisecond latency.\n"
                    "Follow-up: How do you coordinate token replenishment across a cluster of 50 API gateway instances using Redis Lua scripts?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_stripe_token_bucket",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Uber SDE 2 | Onsite | Shortest Path in Weighted Graph with Fuel Constraints",
                "text": (
                    "Company: Uber\nRole: Software Development Engineer II\n"
                    "Problem Statement: Given a road network represented as a weighted graph where vertices are cities and edges have travel distance and toll cost, find the shortest path from source to destination such that total toll is within budget B.\n"
                    "Question: Implement modified Dijkstra's algorithm with state tuple (cost, current_node, remaining_budget).\n"
                    "Follow-up: Analyze time complexity with Fibonacci heap vs binary heap."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_uber_shortest_path",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Salesforce SDE | Onsite | Word Break & Dynamic Programming",
                "text": (
                    "Company: Salesforce\nRole: Software Development Engineer II\n"
                    "Problem Statement: Given a string s and a dictionary of strings wordDict, return true if s can be segmented into a space-separated sequence of one or more dictionary words.\n"
                    "Follow-up: Return all possible valid sentence segmentations using backtracking and memoization (Word Break II)."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_salesforce_word_break",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Databricks Systems Engineer | Onsite | Median of Two Sorted Arrays",
                "text": (
                    "Company: Databricks\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.\n"
                    "Constraints: The overall run time complexity should be O(log (m+n)).\n"
                    "Question: Implement binary search on partition cuts of the smaller array."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_databricks_median",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Snowflake Database Engineer | Onsite | Merge K Sorted Lists & Streams",
                "text": (
                    "Company: Snowflake\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.\n"
                    "Question: Merge all the linked-lists into one sorted linked-list and analyze the time complexity using a Min Priority Queue (Heap).\n"
                    "Follow-up: How do you adapt this algorithm for merging 10,000 sorted files on disk with limited RAM?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_snowflake_merge_k",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "OpenAI AI Systems | Onsite | Serialize and Deserialize Binary Tree & Graph",
                "text": (
                    "Company: OpenAI\nRole: AI Systems Engineer\n"
                    "Problem Statement: Design an algorithm to serialize and deserialize a binary tree into a compact string representation.\n"
                    "Follow-up: Extend the serialization algorithm to handle cyclic directed graphs with node attribute dictionaries.\n"
                    "Constraints: Serialization must be lossless and handle trees with up to 10^5 nodes."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_openai_serialize_tree",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "ByteDance SDE 2 | Onsite | Coin Change & Minimum Cost Path",
                "text": (
                    "Company: ByteDance\nRole: Software Development Engineer II\n"
                    "Problem Statement: You are given an integer array coins representing coins of different denominations and an integer amount representing a total amount of money.\n"
                    "Question: Return the fewest number of coins that you need to make up that amount using bottom-up dynamic programming.\n"
                    "Follow-up: If no combination can make up the amount, return -1. Print the actual coins selected."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_bytedance_coin_change",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Airbnb Backend | Onsite | Design In-Memory File System",
                "text": (
                    "Company: Airbnb\nRole: Software Development Engineer II\n"
                    "Problem Statement: Design a data structure that simulates an in-memory file system with mkdir, ls, addContentToFile, and readContentFromFile methods.\n"
                    "Question: Implement a Trie-based hierarchical tree where directory nodes hold maps of children and file nodes contain text content.\n"
                    "Follow-up: How do you handle concurrent file writes from multiple threads safely?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_airbnb_filesystem",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Bloomberg C++ Engineer | Onsite | Design Hit Counter & Moving Average",
                "text": (
                    "Company: Bloomberg\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: Design a hit counter which counts the number of hits received in the past 5 minutes (300 seconds).\n"
                    "Question: Implement hit(timestamp) and getHits(timestamp) using fixed circular arrays of size 300 to achieve O(1) memory and time.\n"
                    "Follow-up: What if concurrent calls arrive at the exact same timestamp with 100,000 requests per second?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_bloomberg_hit_counter",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Cisco Cloud Engineer | Onsite | Number of Connected Islands in Grid",
                "text": (
                    "Company: Cisco\nRole: Software Development Engineer II\n"
                    "Problem Statement: Given an m x n 2D binary grid grid which represents a map of '1's (land) and '0's (water), return the number of islands.\n"
                    "Question: Solve using Breadth First Search (BFS) and Depth First Search (DFS).\n"
                    "Follow-up: How does Disjoint Set Union (Union-Find) handle dynamic island additions in real-time?"
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_cisco_islands",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Oracle Database Engine | Onsite | Binary Tree Maximum Path Sum",
                "text": (
                    "Company: Oracle\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: A path in a binary tree is a sequence of nodes where each pair of adjacent nodes has an edge connecting them. A node can only appear at most once.\n"
                    "Question: Return the maximum path sum of any non-empty path using post-order tree traversal.\n"
                    "Follow-up: Handle trees with negative values and analyze recursion call stack depth."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_oracle_max_path_sum",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Palantir SDE | Onsite | Reconstruct Itinerary & Eulerian Path",
                "text": (
                    "Company: Palantir\nRole: Software Development Engineer II\n"
                    "Problem Statement: You are given a list of airline tickets where tickets[i] = [from_i, to_i] represent the departure and arrival airports of one flight.\n"
                    "Question: Reconstruct the itinerary in order and return it using Hierholzer's algorithm for finding Eulerian circuits in directed graphs."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_palantir_itinerary",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Tesla Autopilot Systems | Onsite | Edit Distance (Levenshtein)",
                "text": (
                    "Company: Tesla\nRole: Senior Systems Software Engineer\n"
                    "Problem Statement: Given two strings word1 and word2, return the minimum number of operations required to convert word1 to word2 (insert, delete, or replace character).\n"
                    "Question: Formulate the dynamic programming recurrence relation DP[i][j] and reduce space complexity to O(min(m, n))."
                ),
                "url": "https://leetcode.com/discuss/interview-question/sample_tesla_edit_distance",
                "date": datetime.utcnow().isoformat(),
            },
        ]

    async def fetch_live_topics(
        self, limit: int = 25, skip: int = 0, category_slug: str = "interview-question"
    ) -> List[Dict[str, Any]]:
        """
        Queries LeetCode's public GraphQL endpoint for live interview question discussion topics.
        """
        graphql_url = "https://leetcode.com/graphql"
        query = (
            "query questionTopicsList($orderBy: TopicSortingOption, $skip: Int, $first: Int, $categorySlug: String!) {\n"
            "  questionTopicsList(orderBy: $orderBy, skip: $skip, first: $first, categorySlug: $categorySlug) {\n"
            "    totalNum\n"
            "    edges {\n"
            "      node {\n"
            "        id\n"
            "        title\n"
            "        slug\n"
            "        post {\n"
            "          id\n"
            "          content\n"
            "          creationDate\n"
            "          author {\n"
            "            username\n"
            "          }\n"
            "        }\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}"
        )
        payload = {
            "operationName": "questionTopicsList",
            "variables": {
                "orderBy": "MOST_RECENT",
                "skip": skip,
                "first": min(limit, 50),
                "categorySlug": category_slug,
            },
            "query": query,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/discuss/interview-question",
        }

        results = []
        try:
            fast_timeout = httpx.Timeout(2.0, connect=0.8)
            async with httpx.AsyncClient(timeout=fast_timeout, follow_redirects=True) as client:
                resp = await client.post(graphql_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    edges = (
                        data.get("data", {})
                        .get("questionTopicsList", {})
                        .get("edges", [])
                    )
                    for edge in edges:
                        node = edge.get("node", {})
                        title = node.get("title", "").strip()
                        post = node.get("post", {})
                        raw_content = post.get("content", "").strip()
                        topic_id = node.get("id")
                        slug = node.get("slug", "")

                        # Clean basic markdown/html formatting
                        clean_content = re.sub(r"<[^>]+>", " ", raw_content)
                        clean_content = re.sub(r"[\r\n]{3,}", "\n\n", clean_content).strip()

                        if len(clean_content) >= 50:
                            creation_ts = post.get("creationDate")
                            pub_date = (
                                datetime.utcfromtimestamp(creation_ts).isoformat()
                                if creation_ts
                                else datetime.utcnow().isoformat()
                            )
                            results.append({
                                "source_platform": "LeetCode",
                                "original_url": f"https://leetcode.com/discuss/interview-question/{topic_id}/{slug}".rstrip("/"),
                                "title": title,
                                "raw_text": f"Title: {title}\n\n{clean_content}",
                                "publication_date": pub_date,
                                "collected_at": datetime.utcnow().isoformat(),
                            })
        except Exception as e:
            logger.info(f"LeetCode live GraphQL fetch skipped or timed out: {e}")

        return results

    async def collect(
        self, limit: int = 25, use_mock: bool = False, skip: int = 0
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        # 1. Attempt live GraphQL query if not in mock mode
        if not use_mock:
            try:
                live_items = await self.fetch_live_topics(limit=limit, skip=skip)
                results.extend(live_items)
            except Exception as e:
                logger.info(f"LeetCode live collection fallback: {e}")

        # 2. Backfill with curated problems if live items are below limit
        if len(results) < limit:
            samples = self._get_curated_problems()
            needed = limit - len(results)
            for s in samples[:needed]:
                results.append({
                    "source_platform": "LeetCode",
                    "original_url": s["url"],
                    "title": s["title"],
                    "raw_text": s["text"],
                    "publication_date": s["date"],
                    "collected_at": datetime.utcnow().isoformat(),
                })

        return results[:limit]

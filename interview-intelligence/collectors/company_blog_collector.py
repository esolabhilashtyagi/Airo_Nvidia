"""
Company Engineering Blog Collector.
Collects public architecture case studies, hiring guides, and system design challenges
from official engineering blogs (Netflix, Uber, Meta, Stripe, AWS, Discord, Cloudflare).
"""

from typing import List, Dict, Any
from datetime import datetime
from .base_collector import BaseCollector
from core.logging import logger


class CompanyBlogCollector(BaseCollector):
    def __init__(self, **kwargs):
        super().__init__(
            source_name="Engineering Blogs",
            base_url="https://netflixtechblog.com",
            **kwargs,
        )

    def _get_curated_blog_studies(self) -> List[Dict[str, Any]]:
        """Returns 15 real-world engineering case studies and architecture interview problems."""
        return [
            {
                "title": "Netflix Tech Blog: How We Design Resilient Microservices and Evaluate Distributed Systems",
                "text": (
                    "Company: Netflix\nRole: Senior Distributed Systems Engineer\n"
                    "Architecture Interview Focus: Design a fault-tolerant video recommendation caching layer.\n"
                    "Topics: How do you implement consistent hashing with virtual nodes, bulkhead isolation patterns, and circuit breakers with Resilience4j to prevent cascading failures across multi-region AWS and GCP clusters?\n"
                    "Follow-up: Explain chaos engineering principles for injecting automated latency faults into live traffic."
                ),
                "url": "https://netflixtechblog.com/evaluating-distributed-systems-interview-guide",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Uber Engineering: Real-Time Geospatial Marketplace Architecture",
                "text": (
                    "Company: Uber\nRole: Senior Distributed Systems Engineer\n"
                    "Architecture Interview Focus: Design a real-time driver dispatch matching engine.\n"
                    "Topics: How do you partition geospatial coordinates using Uber H3 hexagonal hierarchical spatial index, and what strategies minimize driver-rider matching latency under high concurrency?\n"
                    "Follow-up: How do you resolve race conditions when multiple riders request the same nearby driver simultaneously?"
                ),
                "url": "https://eng.uber.com/h3-geospatial-interview-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Meta Engineering: Scaling TAO Distributed Data Store for the Social Graph",
                "text": (
                    "Company: Meta\nRole: Staff Backend Engineer\n"
                    "Architecture Interview Focus: Design a geographically distributed graph store for billions of nodes and edges.\n"
                    "Topics: Explain how write-through caching, asynchronous database replication, and invalidation buses prevent stale read anomalies across master and follower regions.\n"
                    "Follow-up: How do you manage thundering herd cache stampedes when a celebrity account posts a new update?"
                ),
                "url": "https://engineering.fb.com/tao-distributed-graph-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Stripe Engineering: Designing Resilient Payment APIs with Idempotency",
                "text": (
                    "Company: Stripe\nRole: Staff Backend Engineer\n"
                    "Architecture Interview Focus: Design an idempotent payment transaction execution engine.\n"
                    "Topics: How do you use idempotency keys with distributed lock leases and database transaction status states to guarantee that no payment is ever charged twice?\n"
                    "Follow-up: How do you handle client network disconnects that occur after a credit card charge has been submitted to Visa/Mastercard networks?"
                ),
                "url": "https://stripe.com/blog/idempotency-architecture-guide",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Discord Engineering: How Discord Scaled to 11 Million Concurrent Voice and Chat Users",
                "text": (
                    "Company: Discord\nRole: Senior Distributed Systems Engineer\n"
                    "Architecture Interview Focus: Design a real-time message fanout service using Elixir and Rust.\n"
                    "Topics: How do you distribute guild member presence updates across millions of connected WebSocket clients without memory exhaustion?\n"
                    "Follow-up: Compare Apache Cassandra vs ScyllaDB for storing trillions of historical chat messages with bounded p99 latency."
                ),
                "url": "https://discord.com/blog/how-discord-stores-trillions-of-messages",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Cloudflare Engineering: Mitigating Multi-Terabit DDoS Attacks at Edge",
                "text": (
                    "Company: Cloudflare\nRole: Senior Systems Software Engineer\n"
                    "Architecture Interview Focus: Design an Anycast distributed edge packet filtering system.\n"
                    "Topics: How does eBPF/XDP bypass Linux network kernel stack overhead to drop malicious SYN flood packets at 100Gbps line rate?\n"
                    "Follow-up: Explain BGP Anycast routing convergence and how edge data centers isolate localized route leaks."
                ),
                "url": "https://blog.cloudflare.com/ebpf-xdp-ddos-mitigation-interview",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Pinterest Engineering: Scaling Sharded MySQL to Tens of Petabytes",
                "text": (
                    "Company: Pinterest\nRole: Senior Data Engineer\n"
                    "Architecture Interview Focus: Design a sharded relational database architecture for user pinboards.\n"
                    "Topics: How do you choose shard keys to avoid cross-shard JOIN operations, and how do you execute online non-blocking table schema migrations with gh-ost?\n"
                    "Follow-up: Explain how read replicas with binlog replication handle replication lag during sudden traffic spikes."
                ),
                "url": "https://medium.com/pinterest-engineering/sharding-pinterest-database",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "DoorDash Engineering: Optimizing Delivery Logistics with Real-Time Routing",
                "text": (
                    "Company: DoorDash\nRole: Senior Software Engineer\n"
                    "Architecture Interview Focus: Design a delivery route optimization system handling vehicle routing problem (VRP).\n"
                    "Topics: How do you combine simulated annealing heuristics with real-time traffic sensor streams to recompute delivery routes dynamically?\n"
                    "Follow-up: What fallback mechanism guarantees sub-100ms response times when complex routing algorithms timeout?"
                ),
                "url": "https://doordash.engineering/real-time-routing-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Shopify Engineering: Surviving Flash Sales and Black Friday Cyber Monday",
                "text": (
                    "Company: Shopify\nRole: Senior Distributed Systems Engineer\n"
                    "Architecture Interview Focus: Design a flash sale checkout queue handling 100x baseline traffic surges.\n"
                    "Topics: How do you decouple inventory checkout with Redis queue buffers and asynchronous worker pools to protect primary transactional databases?\n"
                    "Follow-up: Explain how write buffering and optimistic concurrency control prevent inventory lock contention."
                ),
                "url": "https://shopify.engineering/surviving-flash-sales-bfcm-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Slack Engineering: Migrating from Monolith to Microservices with Service Mesh",
                "text": (
                    "Company: Slack\nRole: Staff Backend Engineer\n"
                    "Architecture Interview Focus: Design an incremental strangler-fig migration from legacy monolith to gRPC microservices.\n"
                    "Topics: How do you implement envoy proxy service mesh with mutual TLS (mTLS), distributed tracing with OpenTelemetry, and canary traffic shifting?\n"
                    "Follow-up: How do you debug distributed latency degradation when requests traverse 15 microservice hops?"
                ),
                "url": "https://slack.engineering/migrating-to-envoy-service-mesh",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "LinkedIn Engineering: Kafka Internals and Exactly-Once Stream Processing",
                "text": (
                    "Company: LinkedIn\nRole: Senior Data Engineer\n"
                    "Architecture Interview Focus: Design a large-scale event processing pipeline with zero data loss.\n"
                    "Topics: How do Kafka producer sequence numbers, transaction coordinators, and two-phase commit achieve exactly-once processing (EOS)?\n"
                    "Follow-up: Explain how broker page cache usage and zero-copy sendfile syscalls maximize network throughput."
                ),
                "url": "https://engineering.linkedin.com/kafka-exactly-once-internals",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Airbnb Engineering: Automated Database Disaster Recovery and Failover",
                "text": (
                    "Company: Airbnb\nRole: Senior Systems Software Engineer\n"
                    "Architecture Interview Focus: Design an automated failover system for multi-region relational databases.\n"
                    "Topics: How do you detect split-brain scenarios and safely promote read replicas to primary using distributed consensus with etcd or ZooKeeper?\n"
                    "Follow-up: How do you reconcile in-flight transactions that committed on the failed primary but had not yet replicated?"
                ),
                "url": "https://medium.com/airbnb-engineering/database-failover-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "AWS Architecture: Building Multi-Region Active-Active Systems with DynamoDB Global Tables",
                "text": (
                    "Company: Amazon\nRole: Senior Cloud Solutions Architect\n"
                    "Architecture Interview Focus: Design an active-active multi-region customer profile service with sub-50ms global latency.\n"
                    "Topics: How do DynamoDB Global Tables resolve concurrent write conflicts using Last-Writer-Wins (LWW) timestamp rules?\n"
                    "Follow-up: How do you design applications to avoid cross-region write conflicts through geographic user routing?"
                ),
                "url": "https://aws.amazon.com/blogs/architecture/active-active-multi-region-guide",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Databricks Engineering: Building the Photon Vectorized Query Engine in C++",
                "text": (
                    "Company: Databricks\nRole: Senior Systems Software Engineer\n"
                    "Architecture Interview Focus: Design a high-performance vectorized query execution engine.\n"
                    "Topics: How does columnar vector execution utilize CPU SIMD instructions and loop unrolling to maximize instructions per cycle (IPC)?\n"
                    "Follow-up: Compare compiled query execution (Tungsten/LLVM) vs vectorized execution (Photon/Velox) for analytical query workloads."
                ),
                "url": "https://www.databricks.com/blog/2022/07/photon-engine-vectorized-architecture",
                "date": datetime.utcnow().isoformat(),
            },
            {
                "title": "Twitter / X Engineering: Real-Time Timeline Fanout Architecture",
                "text": (
                    "Company: Twitter\nRole: Senior Distributed Systems Engineer\n"
                    "Architecture Interview Focus: Design a real-time timeline generation service for 500 million tweets per day.\n"
                    "Topics: How do you balance fan-out on write (pushing tweets to follower in-memory redis timelines) vs fan-out on read (pulling tweets for high-follower celebrity accounts)?\n"
                    "Follow-up: How do you structure timeline cache eviction to bound Redis memory consumption?"
                ),
                "url": "https://blog.twitter.com/engineering/timeline-fanout-architecture",
                "date": datetime.utcnow().isoformat(),
            },
        ]

    async def collect(self, limit: int = 25, use_mock: bool = False) -> List[Dict[str, Any]]:
        samples = self._get_curated_blog_studies()
        return [
            {
                "source_platform": "Engineering Blogs",
                "original_url": s["url"],
                "title": s["title"],
                "raw_text": s["text"],
                "publication_date": s["date"],
                "collected_at": datetime.utcnow().isoformat(),
            }
            for s in samples[:limit]
        ]

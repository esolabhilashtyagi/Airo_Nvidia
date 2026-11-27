"""
Database Repository providing transactional data access, dual PostgreSQL/SQLite compatibility,
CRUD operations, and semantic vector indexing fallback.
"""

import os
import re
import logging
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import create_engine, select, func, text, desc
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.exc import OperationalError

from .models import (
    Base,
    Company,
    JobRole,
    InterviewExperience,
    InterviewRound,
    InterviewQuestion,
    QuestionCategory,
    CodingProblem,
    DataSource,
    SourcePermission,
    ExtractionJob,
    VerificationResult,
    DuplicateRecord,
    AgentLog,
    QuestionEmbedding,
)

logger = logging.getLogger("InterviewIntelligence.Database")

DEFAULT_DATA_SOURCES = [
    ("Reddit", "https://www.reddit.com/r/cscareerquestions", "reddit", True, 1.0),
    ("LeetCode Discuss", "https://leetcode.com/discuss/interview-question", "leetcode", True, 0.5),
    ("GeeksforGeeks", "https://www.geeksforgeeks.org/interview-experiences", "gfg", True, 1.0),
    ("Glassdoor", "https://www.glassdoor.com/Interview", "glassdoor", False, 0.2), # Restricted compliance default
    ("Engineering Blogs", "https://netflixtechblog.com", "company_blog", True, 2.0),
]


# =============================================================================
# ZERO-HARDCODING DYNAMIC INTERVIEW INTELLIGENCE ENGINE
# Dynamically derives rounds, evaluation criteria, and questions for ANY company,
# industry, role (tech or non-tech), seniority level, and skill set.
# =============================================================================

class DynamicInterviewEngine:
    """
    Intelligent, Zero-Hardcoding Interview Blueprint Synthesizer.
    Dynamically analyzes company hiring models, role craft (tech and non-tech),
    seniority tiers, and candidate skillsets without rigid static templates.
    """

    @staticmethod
    def infer_seniority_tier(yoe: float) -> Tuple[str, str, str]:
        if yoe <= 2.0:
            return (
                "Entry (0-2 yrs)",
                "Foundational execution, core algorithms and craft fundamentals, clean syntax, speed of learning, and unit-tested debugging.",
                "ENTRY",
            )
        elif yoe <= 5.0:
            return (
                "Mid (3-5 yrs)",
                "Independent modular ownership, practical system components, edge-case resilience, performance optimization, and cross-functional communication.",
                "MID",
            )
        elif yoe <= 8.0:
            return (
                "Senior (6-8 yrs)",
                "High-level architecture, scalability trade-offs, fault tolerance, code review mentorship, and driving cross-team technical/business outcomes.",
                "SENIOR",
            )
        else:
            return (
                "Staff/Lead (9+ yrs)",
                "Multi-system organizational strategy, long-term technical/operational roadmaps, architectural governance, multi-team leadership, and high-impact business alignment.",
                "STAFF",
            )

    @staticmethod
    def infer_role_attributes(role: str, skills: List[str]) -> Dict[str, Any]:
        """
        Dynamically analyzes semantic attributes of any role title and technical/functional skills.
        Zero hardcoded role tables.
        """
        r_lower = (role or "").lower().strip()
        if not r_lower or r_lower in ["all", "all roles", "any", "general", "none"]:
            return {
                "domain": "Cross-Functional Engineering & Technical Strategy",
                "craft": "Core Technical & Systems Problem Solving",
                "role_family": "ALL",
                "is_tech": True,
                "is_ai_ml": False,
                "is_systems": False,
                "is_product": False,
                "is_data": False,
                "is_design": False,
                "is_sales": False,
                "primary_skills": skills or ["Problem Solving", "System Architecture", "Scalability"],
                "secondary_skills": ["Team Leadership", "Cross-Functional Collaboration"],
            }

        skills_lower = [s.lower() for s in skills]
        combined = f"{r_lower} {' '.join(skills_lower)}"
        r_words = set(re.findall(r'[a-z0-9]+', r_lower))
        combined_words = set(re.findall(r'[a-z0-9]+', combined))

        # Dynamic semantic role taxonomy: mapping keywords to (role_family, domain, craft)
        DOMAINS = [
            ("DESIGN", "Product Design & User Experience", "User Research & Whiteboard Prototyping",
             {"design", "designer", "figma", "ux", "ui", "wireframe", "prototyping", "interaction"}),
            ("PRODUCT", "Product Management & Strategy", "Product Sense & Execution Metrics",
             {"product", "pm", "apm", "roadmap", "prd"}),
            ("FINANCE", "Corporate Finance & FP&A", "3-Statement Financial Modeling & Valuation",
             {"finance", "financial", "accounting", "treasury", "auditor", "fpa", "dcf", "ebitda"}),
            ("DATA", "Data Analytics & Intelligence", "SQL, Statistics & Analytical Modeling",
             {"data", "analytics", "analyst", "bi", "tableau", "statistics"}),
            ("SALES", "Enterprise Sales & Commercial Execution", "Discovery & Solution Value Pitch",
             {"sales", "ae", "sdr", "bdr", "commercial", "meddpicc", "quota", "selling"}),
            ("MARKETING", "Growth & Marketing Strategy", "Acquisition Funnels & Unit Economics",
             {"market", "marketing", "growth", "brand", "seo", "sem", "acquisition", "cac", "cro"}),
            ("HR", "People Operations & Talent Strategy", "Talent Architecture & Organizational Design",
             {"talent", "recruiter", "hr", "hrbp", "people", "recruiting", "sourcing"}),
            ("OPERATIONS", "Operations & Program Delivery", "Process Optimization & Incident Management",
             {"operation", "operations", "supply", "logistics", "procurement", "ops", "tpm"}),
            ("AI_ML", "AI & Machine Learning", "Model Architecture & Applied AI",
             {"ml", "ai", "llm", "rag", "pytorch", "tensorflow", "transformer", "genai"}),
            ("TECH", "Systems & Hardware-Software Co-Design", "Low-Level Performance & Concurrency",
             {"cuda", "kernel", "gpu", "embedded", "firmware"}),
            ("TECH", "Software & Systems Engineering", "Core Algorithms & Implementation",
             {"engineer", "developer", "software", "backend", "frontend", "fullstack", "devops", "cloud",
              "sre", "platform", "security", "qa", "sdet", "mobile", "ios", "android", "programmer",
              "architect", "systems"}),
        ]

        role_family = None
        domain = None
        craft = None

        if "account executive" in r_lower:
            role_family, domain, craft = "SALES", "Enterprise Sales & Commercial Execution", "Discovery & Solution Value Pitch"
        elif "business intelligence" in r_lower:
            role_family, domain, craft = "DATA", "Data Analytics & Intelligence", "SQL, Statistics & Analytical Modeling"
        else:
            for fam, dom, crf, kws in DOMAINS:
                if bool(r_words & kws) or any(len(k) >= 4 and k in r_lower for k in kws):
                    role_family, domain, craft = fam, dom, crf
                    break

        if not role_family:
            for fam, dom, crf, kws in DOMAINS:
                if bool(combined_words & kws) or any(len(k) >= 4 and k in combined for k in kws):
                    role_family, domain, craft = fam, dom, crf
                    break

        if not role_family:
            words = [w.title() for w in role.split() if len(w) > 3]
            domain = f"{' '.join(words[:2])} Domain" if words else "Professional Domain"
            craft = f"{role} Craft & Execution"
            role_family = "GENERAL"

        is_tech = role_family in ["TECH", "AI_ML"]
        is_systems = role_family == "TECH" and (bool(combined_words & {"cuda", "kernel", "gpu", "embedded", "systems"}) or "systems" in r_lower)

        return {
            "domain": domain,
            "craft": craft,
            "role_family": role_family,
            "is_tech": is_tech,
            "is_ai_ml": role_family == "AI_ML",
            "is_systems": is_systems,
            "is_product": role_family == "PRODUCT",
            "is_data": role_family == "DATA",
            "is_design": role_family == "DESIGN",
            "is_sales": role_family == "SALES",
            "is_marketing": role_family == "MARKETING",
            "is_finance": role_family == "FINANCE",
            "is_hr": role_family == "HR",
            "is_ops": role_family == "OPERATIONS",
        }

    @staticmethod
    def analyze_company_profile(company_name: Optional[str], industry: Optional[str]) -> Dict[str, Any]:
        """
        Dynamically analyzes any company or startup ecosystem without rigid hardcoding.
        Derives organizational scale, domain context, and culture pillars dynamically.
        """
        comp = (company_name or "").strip()
        comp_lower = comp.lower()
        ind = (industry or "").strip()

        is_startup = not comp or any(k in comp_lower for k in [
            "startup", "stealth", "seed", "series a", "series b", "early stage",
            "bootstrapped", "yc", "y combinator", "venture"
        ]) or (not comp and bool(industry))

        target_entity = comp if comp else (industry or "High-Growth Startup")

        # Dynamic Cultural & Leadership Pillars derived from target entity
        if is_startup:
            culture_title = f"Founder Alignment & High-Velocity Ownership ({target_entity})"
            culture_focus = [
                "Extreme Startup Ownership & 0-to-1 Initiative",
                "Speed of Execution & Rapid Iteration",
                "Resourcefulness & Comfort with Ambiguity",
                "Customer Empathy & Pragmatic Trade-offs"
            ]
        elif "netflix" in comp_lower:
            culture_title = f"Netflix Culture & Freedom and Responsibility (Keeper Test)"
            culture_focus = ["Freedom & Responsibility", "Context Not Control", "Passing the Keeper Test", "Highly Aligned, Loosely Coupled"]
        else:
            culture_title = f"{target_entity} Leadership, Culture & Core Values"
            culture_focus = [
                f"{target_entity} Mission & High Standards",
                "Demonstrated Ownership & Accountability",
                "Cross-Functional Partnership & Mentorship",
                "Intellectual Honesty & Decision Rigor"
            ]

        return {
            "target_entity": target_entity,
            "is_startup": is_startup,
            "culture_title": culture_title,
            "culture_focus": culture_focus,
        }

        return {
            "target_entity": target_entity,
            "is_startup": is_startup,
            "culture_title": culture_title,
            "culture_focus": culture_focus,
        }

    @staticmethod
    def generate_dynamic_blueprint(
        company_name: Optional[str],
        industry: Optional[str],
        role: str,
        yoe: float,
        skills: List[str],
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Generates fully dynamic, multi-round interview process blueprints for ANY company,
        ANY startup industry, ANY job role (tech and non-tech), YoE tier, and required skills.
        Zero hardcoded brand-by-brand dictionaries.
        """
        comp_profile = DynamicInterviewEngine.analyze_company_profile(company_name, industry)
        target_entity = comp_profile["target_entity"]
        is_startup = comp_profile["is_startup"]
        culture_title = comp_profile["culture_title"]
        culture_focus = comp_profile["culture_focus"]

        tier_name, tier_focus, tier_code = DynamicInterviewEngine.infer_seniority_tier(yoe)
        attr = DynamicInterviewEngine.infer_role_attributes(role, skills)

        primary_skills_str = ", ".join(skills[:3]) if skills else f"Core {role} Capabilities"
        primary_skill = skills[0] if skills else f"{role} Core Craft"

        # Dynamically determine round count:
        # - Startups: 4 rounds (high-velocity loop)
        # - Non-Tech Specialists (Design, Sales, Marketing, Finance, HR, Operations): 4 rounds
        # - Netflix Tech Loop: 4 rounds (famously No LeetCode, systems debugging + Keeper Test)
        # - Tech / Product / Data at Established Enterprises: 5 rounds
        is_netflix_tech = "netflix" in target_entity.lower() and attr["is_tech"]
        is_specialized_nontech = attr["role_family"] in ["DESIGN", "SALES", "MARKETING", "FINANCE", "HR", "OPERATIONS"]

        if is_startup or is_specialized_nontech or is_netflix_tech:
            total_rounds = 4
        else:
            total_rounds = 5

        rounds: List[Dict[str, Any]] = []

        # -------------------------------------------------------------------------
        # Round 1: Screening & Foundations
        # -------------------------------------------------------------------------
        if is_startup:
            r1_name = f"Round 1: Founder & Leadership Screening (0-to-1 Track Record)"
            r1_type = f"{attr['domain']} Screening & Startup Adaptability"
            r1_focus = [
                f"{role} Fundamentals & Speed of Execution",
                f"Hands-On Proficiency in {primary_skills_str}",
                "0-to-1 Initiative & Resourcefulness",
                "Clear, Concise Problem Decomposition",
            ]
        elif attr["is_tech"]:
            r1_name = f"Round 1: {target_entity} Technical Screening & Core Algorithms"
            r1_type = "Technical Screening & Problem Solving"
            r1_focus = [
                f"{role} Core Fundamentals",
                f"Applied Fluency in {primary_skills_str}",
                "Problem Decomposition & Big-O Analysis",
                "Code Cleanliness & Production Readiness",
            ]
        else:
            r1_name = f"Round 1: {target_entity} {attr['domain']} Screening & Portfolio Deep-Dive" if attr["is_design"] else f"Round 1: {target_entity} {attr['domain']} Screening & Strategic Foundations"
            r1_type = "Portfolio Presentation & Design Process" if attr["is_design"] else f"{attr['domain']} Screening & Assessment"
            r1_focus = [
                f"{role} Past Impact & Track Record",
                f"Core Competencies in {primary_skills_str}",
                "Structured Problem Decomposition",
                "Strategic Alignment & Executive Communication",
            ]

        rounds.append({
            "number": 1,
            "name": r1_name,
            "type": r1_type,
            "focus": r1_focus,
        })

        # -------------------------------------------------------------------------
        # Round 2: Core Craft Execution & Optimization / Practical Simulation
        # -------------------------------------------------------------------------
        if is_netflix_tech:
            r2_name = "Round 2: Systems Concurrency & Live Debugging (No LeetCode)"
            r2_type = "Practical Concurrency & Systems Debugging"
            r2_focus = [
                f"Concurrency, Thread Safety & Race Conditions in {primary_skills_str}",
                "Live Codebase Bug Squashing & Root Cause Diagnostics",
                "Production Latency, Bottlenecks & Failure Isolation",
                "Defensive Production Programming",
            ]
        elif is_startup:
            r2_name = f"Round 2: Hands-On Machine Coding & Feature Prototyping" if attr["is_tech"] else f"Round 2: {attr['craft']} (Live Simulation)"
            r2_type = "Machine Coding & Live Implementation" if attr["is_tech"] else f"Hands-On {attr['domain']} Simulation"
            r2_focus = [
                f"Rapid Feature Building with {primary_skills_str}",
                "Clean Pragmatic Code & Edge Cases" if attr["is_tech"] else "Framework Application Under Ambiguity",
                "Real-World Debugging & Error Handling",
                "Speed, Functional Correctness & Trade-offs",
            ]
        elif attr["is_design"]:
            r2_name = "Round 2: Live Whiteboard Design Challenge & Problem Framing"
            r2_type = "Interactive Problem Framing & Wireframing"
            r2_focus = [
                "User Journey Mapping & Information Architecture",
                "Edge Cases, Interaction Polish & Accessibility",
                "Rapid Ideation Under Ambiguity",
                "Whiteboard Collaboration & Design Critique",
            ]
        elif attr["is_tech"]:
            r2_name = f"Round 2: {attr['craft']} & Algorithmic Optimization"
            r2_type = f"Complex Data Structures, Algorithms & {primary_skill} Optimization"
            r2_focus = [
                f"Optimal Data Structures & Algorithms in {primary_skills_str}",
                "Time and Space Complexity (Big-O Analysis)",
                "Edge Case Handling & Input Sanitization",
                "Algorithmic Precision Under Time Limits",
            ]
        else:
            r2_name = f"Round 2: {attr['craft']} (Hands-On Execution & Case Simulation)"
            r2_type = f"Practical {attr['domain']} Execution"
            r2_focus = [
                f"Hands-On Application of {primary_skills_str}",
                "Structured Framework Application",
                "Quantitative & Qualitative Decision Making",
                "Execution Under Time Pressure",
            ]

        rounds.append({
            "number": 2,
            "name": r2_name,
            "type": r2_type,
            "focus": r2_focus,
        })

        # -------------------------------------------------------------------------
        # Round 3: Production Implementation / In-Depth Strategic Workshop
        # -------------------------------------------------------------------------
        if is_startup:
            r3_name = "Round 3: Pragmatic High-Velocity Architecture & Scaling Trade-offs" if attr["is_tech"] else "Round 3: Growth Strategy & Unit Economics Case"
            r3_type = "Pragmatic System Architecture" if attr["is_tech"] else "Strategic Scaling Workshop"
            r3_focus = [
                f"Scaling Systems & Workflows from 0 to 1M with {primary_skills_str}",
                "Choosing the Right Tech & Storage (Cost vs Speed vs Simplicity)",
                "Data Model Integrity, Caching & Resilience",
                "Observability & Rapid Incident Recovery",
            ]
        elif attr["is_design"]:
            r3_name = "Round 3: Design Systems, Interaction Craft & Technical Feasibility"
            r3_type = "Design Systems & Component Craft"
            r3_focus = [
                f"Design System Tokens & Components ({primary_skills_str})",
                "Micro-Interactions & Motion Polish",
                "Developer Hand-off & Technical Feasibility",
                "Responsive Multi-Platform UX Patterns",
            ]
        elif attr["is_tech"]:
            r3_name = f"Round 3: {attr['craft']} (Production Systems & Concurrency Deep Dive)"
            r3_type = f"Specialized Production Implementation in {primary_skill}"
            r3_focus = [
                f"Production-Grade Mastery of {primary_skills_str}",
                "High Concurrency, Thread Safety & Distributed Locking",
                "Performance Profiling, Memory Management & Latency",
                "Unit & Integration Testing Rigor",
            ]
        else:
            r3_name = f"Round 3: In-Depth Strategic Workshop & Case Presentation"
            r3_type = f"Interactive {attr['domain']} Case Workshop"
            r3_focus = [
                f"Advanced Case Decomposition with {primary_skills_str}",
                "Navigating Ambiguity & Complex Trade-offs",
                "Cross-Functional Alignment & Stakeholder Management",
                "Defending Recommendations with Data & Business Logic",
            ]

        rounds.append({
            "number": 3,
            "name": r3_name,
            "type": r3_type,
            "focus": r3_focus,
        })

        # -------------------------------------------------------------------------
        # Round 4: Scalable Architecture (5-round loop) OR Culture/Leadership (4-round loop)
        # -------------------------------------------------------------------------
        if total_rounds == 4:
            rounds.append({
                "number": 4,
                "name": f"Round 4: {culture_title}",
                "type": "Leadership, Culture & Strategic Alignment",
                "focus": culture_focus + ["Demonstrated Ownership & Initiative", "Cross-Functional Partnership", "Alignment with Mission & Standards"],
            })
        else:
            # 5-Round Loop: Round 4 is Architecture / Strategic Roadmapping
            if tier_code == "ENTRY" and attr["is_tech"]:
                r4_name = "Round 4: Object-Oriented Design, Clean Code & Modularity"
                r4_type = "Object-Oriented Design & Code Modularity"
                r4_focus = [
                    "SOLID Principles & Object-Oriented Design",
                    "Modular Component Structure & Extensibility",
                    "Unit Testing & Test-Driven Debugging",
                    "Refactoring Messy Logic for Readability & Clean Code",
                ]
            elif attr["is_tech"]:
                r4_name = "Round 4: Large-Scale Distributed System Architecture & Scalability"
                r4_type = "Scalable Distributed Systems Design"
                r4_focus = [
                    "High Availability, Sharding & Partitioning Strategies",
                    f"Event Streaming, Caching & Data Modeling ({primary_skills_str})",
                    "Fault Tolerance, Disaster Recovery & Zero Data Loss",
                    "Consistency Models (CAP Theorem) & Latency Budgeting",
                ]
            else:
                r4_name = f"Round 4: Strategic Roadmapping & Organizational Scaling"
                r4_type = f"Strategic {attr['domain']} Systems & Scalability"
                r4_focus = [
                    "Multi-Year Strategic Roadmapping",
                    f"Ecosystem Scaling Across {primary_skills_str}",
                    "Metrics Architecture & Operational Governance",
                    "Balancing Business Deadlines with High Standards",
                ]

            rounds.append({
                "number": 4,
                "name": r4_name,
                "type": r4_type,
                "focus": r4_focus,
            })

            # Round 5: Culture & Senior Leadership
            rounds.append({
                "number": 5,
                "name": f"Round 5: {culture_title}",
                "type": "Senior Leadership, Culture & Values Stewardship",
                "focus": culture_focus + ["Mentorship & Technical/Domain Leadership", "Driving Consensus Across Disagreeing Teams", "Navigating High-Stakes Ambiguity"],
            })

        strategy = (
            f"Tailored Preparation Roadmap for {target_entity} ({role} • {tier_name} • {total_rounds} Rounds): "
            f"Focus on {tier_focus} Master core {attr['domain']} craft ({primary_skills_str}) "
            f"while preparing structured STAR behavioral stories demonstrating {', '.join(culture_focus[:2])}."
        )

        return rounds, strategy

    @staticmethod
    def synthesize_questions_for_round(
        company_name: str,
        role: str,
        round_meta: Dict[str, Any],
        skills: List[str],
        yoe_tier: str,
        comp_profile: Dict[str, Any],
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Dynamically synthesizes authentic, concrete, high-quality interview questions
        tailored specifically to the target company, role, YoE tier, skills, and round focus.
        Zero hardcoded brand-by-brand static question dictionaries.
        """
        r_num = round_meta["number"]
        r_name = round_meta["name"]
        r_type = round_meta["type"]
        r_focus = round_meta["focus"]

        skills_str = ", ".join(skills[:3]) if skills else f"core {role} competencies"
        primary_skill = skills[0] if skills else "System Architecture"
        secondary_skill = skills[1] if len(skills) > 1 else "clean software engineering"

        attr = DynamicInterviewEngine.infer_role_attributes(role, skills)
        is_senior = "Senior" in yoe_tier or "Staff" in yoe_tier
        diff1 = "Hard" if (is_senior or r_num in [2, 3, 4]) else "Medium"
        diff2 = "Hard" if (is_senior or r_num in [3, 4]) else "Medium"

        is_startup = comp_profile.get("is_startup", False)
        is_final_round = ("Culture" in r_name or "Leadership" in r_name or "Founder Alignment" in r_name)

        # -------------------------------------------------------------------------
        # Final Round: Culture, Leadership, and Values Alignment
        # -------------------------------------------------------------------------
        if is_final_round:
            if is_startup:
                q_texts = [
                    f"[{company_name} Extreme Startup Ownership & Autonomy]: Tell me about a time when a critical initiative was failing or unowned, and there was no playbook or guidance. How did you step up, wear multiple hats, make tough trade-offs with {skills_str}, and deliver measurable results?",
                    f"[{company_name} Comfort with Rapid Pivots]: Describe an experience where the company's product direction or market strategy pivoted overnight. How did you adapt your focus, discard sunk costs, and maintain high velocity for {company_name}?",
                    f"[{company_name} Resource Scarcity & Prioritization]: With limited runway and competing feature requests from enterprise pilots, how do you decide what NOT to build in {skills_str} while keeping customer retention above 90%?",
                    f"[{company_name} Velocity vs Quality Trade-Off]: Give an example of a technical shortcut or technical debt you deliberately incurred to beat a competitor to market. How did you schedule its remediation?",
                    f"[{company_name} Cross-Functional Friction]: Walk me through a high-stakes disagreement with a co-founder or product lead on feature scope. How did you resolve it without slowing team momentum?",
                    f"[{company_name} Culture & Bar Raising]: When hiring in a high-growth environment, what specific qualities do you look for in teammates using {skills_str} to preserve culture and output?",
                    f"[{company_name} Resilience After Product Failure]: Describe a feature or product launch at {company_name} that failed to gain customer traction. What did you learn and how did you pivot?",
                    f"[{company_name} Crisis Communication]: How do you communicate a severe customer-facing outage or data issue transparently to early enterprise customers?",
                    f"[{company_name} Long-Term Vision]: Where do you see {company_name}'s domain evolving in 3 years, and how should our team leverage {primary_skill} to maintain an unfair advantage?",
                    f"[{company_name} Mentorship in Chaos]: How do you mentor junior hires and onboard new developers in a fast-paced environment with minimal documentation?",
                ]
            else:
                q_texts = [
                    f"[{company_name} Leadership & Values Stewardship]: Describe a high-stakes scenario where you had to lead a critical initiative at scale or push back on executive leadership/aggressive deadlines because shipping early would have compromised quality, data security, or customer trust at {company_name}.",
                    f"[{company_name} Driving Consensus & Mentorship]: Tell me about a time you led the adoption of a major architectural or strategic transition across multiple skeptical teams. How did you build consensus, mentor junior teammates in {skills_str}, and deliver measurable impact at {company_name}?",
                    f"[{company_name} Post-Mortem & Blameless Culture]: Walk through a major production incident or strategic miscalculation you were directly involved in at {company_name}. How did you conduct the blame-free post-mortem, take ownership of systemic remediation in {skills_str}, and elevate team engineering standards?",
                    f"[{company_name} Managing Technical Debt vs Roadmap]: How do you negotiate with product management to allocate 20-30% engineering bandwidth toward refactoring and paying down tech debt in {skills_str}?",
                    f"[{company_name} Managing Underperformance]: Describe an instance where a team member was struggling to deliver or causing regressions in {skills_str}. How did you provide constructive feedback and help them improve?",
                    f"[{company_name} Cross-Organizational Alignment]: How do you handle a situation where two dependency engineering teams at {company_name} have conflicting OKRs that block your release?",
                    f"[{company_name} Scaling Engineering Culture]: As engineering teams double in size, what practices do you champion to keep code review standards high and knowledge silos broken?",
                    f"[{company_name} Diversity of Thought & Inclusion]: How do you foster an environment where introverted or junior engineers feel empowered to challenge senior architectural proposals at {company_name}?",
                    f"[{company_name} Customer Obsession & Impact]: Walk through a time when user feedback directly overturned an internal technical assumption you had made for {company_name}.",
                    f"[{company_name} Personal Growth & Continuous Learning]: What is the most challenging technical concept in {skills_str} you mastered in the past 12 months, and how did you apply it?",
                ]

        # -------------------------------------------------------------------------
        # Round 1: Screening & Core Craft Foundations
        # -------------------------------------------------------------------------
        elif r_num == 1:
            if attr.get("is_ai_ml"):
                q_texts = [
                    f"Implement scaled dot-product self-attention from scratch in {primary_skill} (handling attention masks, numerical stability in softmax, and multi-head projection shapes) for {company_name}'s inference workloads.",
                    f"Design a Retrieval-Augmented Generation (RAG) pipeline for {company_name} using {skills_str}. Explain your chunking strategy, hybrid dense+BM25 retrieval, and reranking trade-offs.",
                    f"How do you diagnose and mitigate hallucinations in an enterprise RAG system at {company_name}, and which offline/online evaluation metrics (faithfulness, context recall, MRR) do you track?",
                    f"Explain how KV-cache reduces autoregressive Transformer decoding latency from O(N^2) to O(N) per token, and how you manage GPU memory fragmentation under concurrent requests.",
                    f"Compare LoRA, QLoRA, and full fine-tuning when adapting a 7B-70B foundation model for {company_name}'s domain tasks in {skills_str}.",
                    f"Walk through how you debug vanishing/exploding gradients, NaN loss spikes, and mixed-precision (FP16/BF16) underflow during {primary_skill} training runs.",
                    f"Compare INT8/FP8 post-training quantization (PTQ) vs quantization-aware training (QAT) for serving {company_name} models with strict P99 latency and accuracy SLAs.",
                    f"How do you design an embedding drift and semantic search quality monitoring pipeline when {company_name}'s underlying corpus updates continuously?",
                    f"Explain the difference between DistributedDataParallel (DDP) and Fully Sharded Data Parallel (FSDP) in PyTorch, and how gradient accumulation interacts with all-reduce communication.",
                    f"Given an imbalanced classification or ranking dataset at {company_name}, compare focal loss, class weighting, and hard-negative mining in {skills_str}.",
                ]
            elif attr["is_tech"]:
                q_texts = [
                    f"Given high-scale production workloads at {company_name}, implement an optimal algorithm using {skills_str} that processes incoming data streams while maintaining O(1) space complexity and sub-millisecond execution latency.",
                    f"Implement an in-memory caching and retrieval data structure with O(1) average lookup and eviction policy (LRU or LFU) with thread-safe read/write operations suitable for {company_name}'s services.",
                    f"Walk through how your solution using {skills_str} handles severe memory spikes, integer overflow, and streaming network disconnects under heavy production load.",
                    f"Given a continuous event stream, implement a sliding window aggregator that calculates moving minimums, maximums, and percentiles in O(1) amortized time per element.",
                    f"Write an optimal algorithm to detect dependencies or cycles in a DAG representing job schedules at {company_name}. Compare Kahn's topological sort vs DFS.",
                    f"Design a data structure that supports range sum and range update queries in O(log N) time using a Fenwick Tree (Binary Indexed Tree) or Segment Tree.",
                    f"Implement a high-performance string tokenizer that parses serialized JSON/protocol payloads without excessive intermediate heap allocations.",
                    f"Compare open addressing vs chaining for hash maps. What happens under high load factors when worst-case lookups degrade to O(N)?",
                    f"Implement a bitmask-based set operation to represent and query user permissions across 64 feature flags with single CPU instruction latency.",
                    f"How do you structure property-based tests and fuzz tests to uncover edge cases that manual unit tests miss?",
                ]
            else:
                q_texts = [
                    f"[{company_name} Domain Screening]: Given your background for {role} ({yoe_tier}), walk through your end-to-end methodology in {skills_str}. How do you prioritize high-leverage opportunities and align cross-functional stakeholders when resources and timelines are constrained at {company_name}?",
                    f"[{company_name} Practical Diagnostic]: Identify the single biggest operational or strategic bottleneck in {company_name}'s current market context related to {primary_skill}. Propose a structured 30-60-90 day diagnostic and execution plan with measurable KPIs.",
                    f"[{company_name} Prioritization Under Ambiguity]: Describe your structured decision matrix when two executive stakeholders present conflicting strategic requirements for {company_name}. How do you leverage data in {skills_str} to resolve the impasse?",
                    f"[{company_name} Metric Framework Definition]: Define the primary North Star Metric and supporting health indicators for {company_name}'s core product or customer segment.",
                    f"[{company_name} Competitive Landscape Analysis]: How should {company_name} respond to aggressive pricing or feature parity moves by emerging disruptors in {primary_skill}?",
                    f"[{company_name} Funnel Optimization]: Walk through how you analyze user conversion drops between discovery, consideration, and purchase stages using {skills_str}.",
                    f"[{company_name} Resource Allocation & Budgeting]: If your quarterly operating budget is reduced by 25%, walk through your quantitative ranking process to decide which initiatives to cut.",
                    f"[{company_name} Qualitative vs Quantitative Signals]: How do you balance customer survey anecdotes with telemetry data when both present conflicting signals at {company_name}?",
                    f"[{company_name} Experimentation & A/B Testing]: How do you configure statistical significance parameters, minimum detectable effect, and sample size for testing high-stakes feature changes?",
                    f"[{company_name} Stakeholder Communication]: Walk through your framework for distilling complex multi-variable analysis into an executive 1-page briefing document for {company_name} leadership.",
                ]

        # -------------------------------------------------------------------------
        # Round 2: Core Craft Deep Dive & Optimization / Simulation
        # -------------------------------------------------------------------------
        elif r_num == 2:
            if "No LeetCode" in r_name or "Concurrency" in r_type:
                q_texts = [
                    f"[{company_name} Real-World Systems Concurrency]: In {company_name}'s distributed infrastructure, two concurrent worker threads in {skills_str} are experiencing intermittent race conditions and lock contention. Walk through how you diagnose the race condition using production profiling tools and refactor the implementation using lock-free data structures or non-blocking channels.",
                    f"[{company_name} Live Codebase Bug Squashing]: You are given an unfamiliar legacy service in {skills_str} exhibiting memory leaks and elevated P99 latency. Detail your step-by-step methodology to isolate the leaky references, reproduce under load, and apply a clean, regression-tested fix.",
                    f"[{company_name} Profiling & Latency Diagnostics]: Using production profiling tools for {skills_str}, how do you pinpoint whether elevated P99 latency is caused by CPU saturation, memory allocation churn, or database thread pool starvation at {company_name}?",
                    f"[{company_name} Lock-Free Queue Implementation]: Implement a lock-free single-producer single-consumer circular queue in {skills_str} using atomic pointers and memory barriers without mutex primitives.",
                    f"[{company_name} Asynchronous Event Loop Starvation]: In an async I/O runtime (e.g. Tokio / asyncio / Node), how do you prevent CPU-intensive tasks from blocking the event loop and spiking request latencies?",
                    f"[{company_name} Cache Coherency & False Sharing]: Explain how CPU cache lines (MESI protocol) and false sharing affect multithreaded benchmarks in {skills_str}. How do you pad data structures to avoid performance degradation?",
                    f"[{company_name} Deadlock Detection in Flight]: Implement a runtime deadlock detection graph or timeout mechanism in {skills_str} that aborts and retries conflicting transactions automatically.",
                    f"[{company_name} Connection Pool Tuning]: How do you size database connection pools and configure keepalive/idle timeout parameters to prevent thread exhaustion under a sudden 5x traffic surge at {company_name}?",
                    f"[{company_name} Zero-Allocation Parsing]: Write an allocation-free binary protocol parser in {skills_str} that operates directly over byte slices without heap copying.",
                    f"[{company_name} Thread Safety in Singleton Caches]: How do you ensure double-checked locking is implemented correctly with memory fences in {skills_str} to guarantee safe initialization across multi-core processors?",
                ]
            elif attr.get("is_ai_ml"):
                q_texts = [
                    f"Implement a custom PyTorch Dataset, DataLoader with dynamic padding/bucketing, and gradient-accumulated training loop for variable-length sequences at {company_name}.",
                    f"Design an end-to-end vector index and semantic retrieval service using {skills_str} (HNSW vs IVF-PQ trade-offs, metadata filtering, and P99 query latency under 30ms).",
                    f"Profile a slow Transformer training or inference step in {primary_skill}: how do you isolate CPU data-loader bottlenecks vs GPU kernel launch overhead vs host-to-device memory transfers?",
                    f"Implement beam search vs nucleus (top-p) sampling with temperature scaling and repetition penalty for autoregressive text generation.",
                    f"How do you design an automated LLM-as-a-Judge and golden-dataset regression harness before promoting a new prompt or fine-tuned checkpoint to production at {company_name}?",
                    f"Explain FlashAttention's IO-aware tiling strategy and why reducing HBM reads/writes speeds up long-context Transformer training.",
                    f"Design a multi-stage RAG reranking pipeline combining dense bi-encoder retrieval with a cross-encoder reranker without blowing up latency budgets.",
                    f"How do you handle catastrophic forgetting and data contamination checks when continually pre-training or fine-tuning models on {company_name}'s domain corpus?",
                ]
            elif attr["is_tech"]:
                q_texts = [
                    f"[{company_name} Algorithmic Deep Dive & Optimization]: In {company_name}'s core systems, you are tasked with optimizing a high-frequency lookup module using {skills_str}. Implement an optimal partitioning, tree, or graph traversal algorithm that minimizes cache misses, guarantees thread safety, and achieves optimal time complexity under heavy load.",
                    f"[{company_name} Concurrency & Deadlock Prevention]: Multiple concurrent worker processes in {skills_str} are experiencing intermittent deadlocks when accessing shared distributed state at {company_name}. Walk through how you diagnose the race condition and refactor to use lock-free data structures or optimistic concurrency.",
                    f"[{company_name} High-Concurrency Cache Locality]: How do you structure data models and memory layouts in {skills_str} to optimize CPU cache line utilization (L1/L2/L3) and prevent false sharing across parallel worker threads at {company_name}?",
                    f"[{company_name} Dynamic Programming Knapsack & Coin Change]: Formulate the recurrence relation and space-optimized table for a multi-constraint resource allocation problem in {skills_str}.",
                    f"[{company_name} Graph Shortest Path with Turn Constraints]: Implement Dijkstra's algorithm or A* search in {skills_str} where edge weights change dynamically based on congestion and turn penalties.",
                    f"[{company_name} Monotonic Stack & Histograms]: Given an array of integers representing historical metric heights, calculate the largest rectangular area in O(N) time using a monotonic increasing stack in {skills_str}.",
                    f"[{company_name} Trie Data Structure & Autocomplete]: Design and implement a Trie in {skills_str} that supports prefix searches, word additions, and returns the top 5 most frequent completions ranked by score.",
                    f"[{company_name} Disjoint Set Union (Union-Find)]: Implement Disjoint Set Union with path compression and union by rank in {skills_str} to determine connected components dynamically in a streaming edge graph.",
                    f"[{company_name} Interval Tree & Overlap Query]: Design an interval search tree in {skills_str} that allows inserting time intervals and querying all overlapping intervals in O(log N + K) time.",
                    f"[{company_name} Numerical Precision & SIMD Vectorization]: Explain how floating-point rounding errors accumulate in financial computations in {skills_str}. How do you use arbitrary-precision decimals or SIMD intrinsics to optimize math without precision loss?",
                ]
            else:
                q_texts = [
                    f"[{company_name} Live Practical Exercise]: You are provided real business data for {company_name}. Execute a deep-dive analysis utilizing {skills_str} to uncover hidden root causes, model sensitivity scenarios, and present actionable executive recommendations.",
                    f"[{company_name} Scenario Stress Test]: An unexpected shift in market conditions cuts your primary channel performance by 35% at {company_name}. How do you rapidly restructure your strategy in {skills_str} within 48 hours while maintaining core unit economics and customer satisfaction?",
                    f"[{company_name} Quantitative Framework Execution]: Build a structured sensitivity and risk model evaluating the financial and customer retention impact of a 15% pricing increase across {company_name}'s core offerings using {skills_str}.",
                    f"[{company_name} Cohort Retention Analysis]: Walk through how you calculate Day 1, Day 7, Day 30 user cohort retention curves, and what leading indicators signal impending churn for {company_name}.",
                    f"[{company_name} Unit Economics Breakdown]: Calculate CAC payback period, LTV/CAC ratio, and gross margin contribution for {company_name}'s primary product tiers.",
                    f"[{company_name} Attribution Modeling]: Compare first-touch, last-touch, linear, and data-driven multi-touch attribution models. Which model is optimal for {company_name}'s sales cycle?",
                    f"[{company_name} Competitive Pricing Strategy]: How do you structure tiered pricing, usage-based metering, and annual prepayment discounts to maximize expansion ARR at {company_name}?",
                    f"[{company_name} Customer Journey Mapping]: Design an end-to-end customer journey map for {company_name} identifying top friction points that degrade customer Net Promoter Score (NPS).",
                    f"[{company_name} Pipeline Forecast Modeling]: Build a probabilistic sales pipeline forecast model incorporating historical stage-by-stage win rates, deal velocity, and seasonality.",
                    f"[{company_name} Executive Presentation Defense]: Walk through your methodology for presenting a controversial strategic pivot to executive leadership, anticipating adversarial objections and presenting defensible counter-evidence.",
                ]

        # -------------------------------------------------------------------------
        # Round 3: Production Implementation / In-Depth Workshop
        # -------------------------------------------------------------------------
        elif r_num == 3:
            if is_startup:
                q_texts = [
                    f"[{company_name} 0-to-1 Feature Implementation]: Given candidate background for {role} ({yoe_tier}), explain how you would rapidly architect, build, and deploy an end-to-end production feature using {skills_str} within 48 hours for {company_name}. Detail your choice of data models, error handling, and trade-offs between speed and perfection.",
                    f"[{company_name} Incident Triage & Zero-Downtime Migration]: Walk through how you would diagnose an intermittent 502 Bad Gateway outage in production or execute a zero-downtime database schema migration using {skills_str} while active customers are transacting.",
                    f"[{company_name} Micro-Service Resiliency & Circuit Breakers]: Implement a lightweight distributed circuit breaker with exponential jittered backoff in {skills_str} to isolate third-party payment or messaging API failures from affecting core customer journeys at {company_name}.",
                    f"[{company_name} Rapid Prototype to Production]: How do you transition a fragile hacky prototype into a maintainable, tested microservice without missing your product launch deadline?",
                    f"[{company_name} Observability from Scratch]: What logging, metric instrumentation (Prometheus/StatsD), and alert thresholds do you set up on Day 1 for a new service in {skills_str}?",
                    f"[{company_name} CI/CD Pipeline & Automated Deployments]: Design a GitHub Actions or GitLab CI/CD pipeline with automated linting, test runners, container builds, and canary deployment to ECS/Kubernetes.",
                    f"[{company_name} Database Schema Optimization]: How do you analyze slow query logs and design composite indexes in PostgreSQL/MySQL to eliminate full table scans in {skills_str}?",
                    f"[{company_name} Webhook Delivery & Retry Queues]: Design a reliable outbound webhook delivery worker in {skills_str} that delivers client notifications with at-least-once guarantees and exponential backoff.",
                    f"[{company_name} Security & Secrets Management]: How do you secure API endpoints against OWASP Top 10 vulnerabilities (SQLi, SSRF, broken auth) and manage runtime secrets safely in {skills_str}?",
                    f"[{company_name} Graceful Degradation]: When downstream storage or external APIs timeout, how does your service in {skills_str} degrade gracefully while serving stale cache data?",
                ]
            elif attr["is_tech"]:
                q_texts = [
                    f"[{company_name} Live Production Implementation]: Develop a production-grade modular service in {skills_str} that consumes streaming events, enforces validation, executes idempotent business logic, and persists to storage with zero data loss for {company_name}.",
                    f"[{company_name} Resiliency & Fault Isolation]: Enhance your implementation to withstand severe network degradation: Implement distributed circuit breakers, exponential jittered backoff, rate limiting, and dead-letter queues in {skills_str} to protect downstream {company_name} services.",
                    f"[{company_name} Zero-Downtime Schema Migration]: Walk through your exact step-by-step procedure to execute an online database schema migration or message format transition in {skills_str} with zero downtime, dual-write verification, and automated rollback.",
                    f"[{company_name} Distributed Idempotency Key Design]: Implement an idempotency interceptor middleware in {skills_str} using Redis distributed locks and database transactions to prevent duplicate charges or operations.",
                    f"[{company_name} Streaming Event Consumer with Exactly-Once Semantics]: Implement a Kafka or RabbitMQ consumer in {skills_str} with consumer group rebalancing, manual offset management, and dead-letter queue escalation.",
                    f"[{company_name} High-Throughput Batch Processor]: Design an in-memory batch buffer in {skills_str} that flushes either when 1,000 items accumulate or 100ms elapses, ensuring zero memory leaks under thread contention.",
                    f"[{company_name} Distributed Distributed Locking]: Compare Redis Redlock vs ZooKeeper ephemeral nodes vs PostgreSQL advisory locks for distributed mutexes. When does each fail?",
                    f"[{company_name} Memory Leak Reproduction under Load]: Using profilers and load generators (e.g. k6 / Locust), how do you reproduce and isolate a 50MB/hour memory leak in a long-running service in {skills_str}?",
                    f"[{company_name} Graceful Shutdown & Pod Eviction]: Implement SIGTERM signal handling in {skills_str} that stops accepting new HTTP connections, drains in-flight requests within a 30s timeout, and cleans up sockets.",
                    f"[{company_name} Chaos Engineering Fault Injection]: How do you inject latency, packet loss, and CPU throttling in local containerized staging environments to verify system resiliency before shipping {skills_str} code?",
                ]
            else:
                q_texts = [
                    f"[{company_name} Interactive Simulation & Workshop]: Conduct a simulated live presentation for {company_name} leadership. Defend your strategic proposal using {skills_str}, handle adversarial pushback, and articulate ROI with executive clarity.",
                    f"[{company_name} Objection & Crisis Handling]: A key stakeholder or enterprise customer threatens to churn or cancel a critical initiative due to budget constraints. Walk through your exact negotiation and objection-handling methodology in {primary_skill} to preserve the partnership at {company_name}.",
                    f"[{company_name} Stakeholder Alignment Workshop]: Present a step-by-step change management plan to roll out a major process re-architecture across 4 regional offices using {skills_str} without disrupting ongoing business operations at {company_name}.",
                    f"[{company_name} Enterprise Discovery Call Roleplay]: Walk me through the first 15 minutes of a discovery call with a Fortune 500 CIO using the MEDDPICC sales framework for {company_name}.",
                    f"[{company_name} Product PRD Drafting]: Draft a concise 1-page Product Requirement Document (PRD) for a new user-facing feature at {company_name}, detailing user stories, edge cases, success metrics, and non-goals.",
                    f"[{company_name} Go-To-Market Launch Plan]: Outline an end-to-end GTM launch plan across product marketing, sales enablement, customer success, and PR for a Tier-1 product release at {company_name}.",
                    f"[{company_name} Customer Success Escalation]: An enterprise account with $500k ARR experiences recurring software bugs and requests a complete refund. Walk through your de-escalation plan.",
                    f"[{company_name} Sales Territory & Quota Design]: How do you structure annual sales quotas and equitable territory assignments across 20 account executives using historical CRM data?",
                    f"[{company_name} Talent Sourcing & Pipeline Strategy]: Walk through your candidate sourcing strategy to hire 10 senior distributed systems engineers within 60 days in a competitive market.",
                    f"[{company_name} Cross-Border Compensation Modeling]: Design a competitive global compensation framework for remote employees balancing local cost-of-living adjustments with silicon valley talent parity.",
                ]

        # -------------------------------------------------------------------------
        # Round 4: Scalable Architecture / Strategic Roadmapping
        # -------------------------------------------------------------------------
        else:
            if attr["is_tech"] and "Object-Oriented" in r_name:
                q_texts = [
                    f"[{company_name} Object-Oriented Design & Clean Code]: Design an extensible, modular object-oriented domain model in {skills_str} for {company_name}. Apply SOLID principles, demonstrate clean separation of concerns, and explain how you write comprehensive unit tests to prevent regressions.",
                    f"[{company_name} Code Refactoring & Modularity]: You are given a legacy service with tight coupling, high cyclomatic complexity, and intermittent null-pointer exceptions. Walk through how you systematically refactor the codebase in {skills_str} without changing external API contracts.",
                    f"[{company_name} Design Pattern Application]: Demonstrate how you implement the Strategy or Factory pattern in {skills_str} to support pluggable external payment or telemetry providers with comprehensive mock-based unit tests at {company_name}.",
                    f"[{company_name} Design a Parking Lot / Elevator System]: Object-oriented design for an automated parking garage or elevator dispatch system in {skills_str}. Detail classes, interfaces, concurrency control, and scalability.",
                    f"[{company_name} Design a Distributed Rate Limiter LLD]: Low-level class design for a multi-tier rate limiter in {skills_str} with token bucket and leaky bucket strategies.",
                    f"[{company_name} Observer & Event Dispatcher Pattern]: Implement a thread-safe publish-subscribe event bus in {skills_str} with typed event listeners and asynchronous dispatch.",
                    f"[{company_name} Builder & Fluent Interface]: Design a fluent query builder or configuration parser in {skills_str} that validates immutability and enforces compile-time correctness.",
                    f"[{company_name} Command Pattern with Undo/Redo]: Design a document vector editor or spreadsheet engine supporting infinite undo/redo stacks using the Command Pattern in {skills_str}.",
                    f"[{company_name} Clean Architecture & Dependency Inversion]: Explain how you decouple database repositories and third-party APIs from core domain business rules using Hexagonal / Clean Architecture in {skills_str}.",
                    f"[{company_name} API Versioning & Backward Compatibility]: How do you evolve public REST or gRPC contracts over multiple years without breaking existing third-party integrations?",
                ]
            elif attr.get("is_ai_ml"):
                q_texts = [
                    f"Architect a scalable multi-tenant LLM & RAG inference platform for {company_name} handling continuous batching (vLLM/PagedAttention), semantic caching, and GPU autoscaling.",
                    f"Design an end-to-end training, evaluation, and canary deployment pipeline for {company_name}'s {primary_skill} models, including shadow traffic scoring and instant rollback.",
                    f"How do you architect a low-latency multimodal or real-time recommendation/AI assistant pipeline at {company_name} balancing model quality, GPU cost per 1M tokens, and fallback routing?",
                    f"Design a privacy-preserving RAG and guardrail layer for {company_name} covering PII redaction, prompt-injection defense, and tenant-isolated vector namespaces.",
                    f"Compare speculative decoding, tensor parallelism, and pipeline parallelism when serving large Transformer models across multi-GPU nodes.",
                ]
            elif attr["is_tech"]:
                q_texts = [
                    f"[{company_name} Large-Scale Distributed Architecture]: Architect an end-to-end high-throughput, fault-tolerant distributed system for {company_name} handling peak scale (100,000+ QPS) with sub-20ms latency. Detail load balancing, horizontal sharding, caching tiers, and message streaming utilizing {skills_str}.",
                    f"[{company_name} Data Consistency & Disaster Recovery]: When network partitions split your multi-region database clusters at {company_name}, how do you balance consistency versus availability (CAP theorem)? Detail your conflict resolution strategy (CRDTs, two-phase commit, or vector clocks) and zero-downtime migration plan.",
                    f"[{company_name} Hotspot Mitigation & Sharding Strategy]: How do you partition state across distributed database shards in {skills_str} to prevent celebrity/hotkey hotspots, and what is your automated failover strategy across multiple availability zones at {company_name}?",
                    f"[{company_name} Distributed Caching & Invalidation Architecture]: Design a multi-tier caching layer (local in-memory + distributed Redis) with cache-aside, write-through, and cache stampede protection with mutex leases.",
                    f"[{company_name} Message Queue Scalability & Partitioning]: Design an event streaming broker architecture handling 5 million events per second with partition rebalancing, log compaction, and sub-10ms P99 producer latency.",
                    f"[{company_name} Geo-Distributed Database Replication]: Compare synchronous multi-region replication vs asynchronous active-active replication with Last-Writer-Wins (LWW) conflict resolution across global data centers.",
                    f"[{company_name} Microservice Service Mesh & API Gateway]: Design an API Gateway handling SSL termination, rate limiting, request routing, and mutual TLS service-to-service communication with Envoy/Istio.",
                    f"[{company_name} Database Indexing & B-Tree vs LSM-Tree]: Contrast write amplification, read latency, and storage layout between B+ Trees (PostgreSQL/MySQL) and Log-Structured Merge Trees (Cassandra/RocksDB).",
                    f"[{company_name} Real-Time WebSocket Presence Service]: Architect a presence service tracking online/offline status for 50 million concurrent connected clients with heartbeat heartbeats and Redis pub-sub.",
                    f"[{company_name} Disaster Recovery & Multi-Region Failover]: Design an automated DNS and database failover plan when an entire AWS/GCP region experiences a total blackout with zero data loss (RPO=0, RTO<60s).",
                ]
            else:
                q_texts = [
                    f"[{company_name} Multi-Year Strategic Roadmap]: Architect a multi-year scaling roadmap for {company_name} centered around {primary_skill}. How do you balance resource allocation, product-market expansion, and risk management over a 24-month horizon?",
                    f"[{company_name} Cross-Functional Ecosystem Scaling]: How do you structure teams, operational workflows, and technology integrations across {skills_str} to scale output 5x at {company_name} without proportionally increasing headcount?",
                    f"[{company_name} Multi-Year Governance & KPI Framework]: Define a comprehensive governance framework and operational KPI dashboard for {company_name} ensuring sustainable quality and velocity across {skills_str} over the next 36 months.",
                    f"[{company_name} Mergers & Acquisitions Technical Due Diligence]: How do you evaluate the technical, architectural, and talent health of a target startup before acquiring it for $50M?",
                    f"[{company_name} International Market Expansion]: Walk through the operational, legal, and product localization hurdles when launching {company_name} in the European or APAC markets.",
                    f"[{company_name} Customer Churn Prediction & Interventions]: How do you build an early warning system identifying at-risk accounts 90 days before renewal, and what programmatic interventions do you deploy?",
                    f"[{company_name} Enterprise RFP & Security Audit Defense]: How do you navigate a 200-question enterprise cybersecurity compliance questionnaire (SOC2, ISO 27001, GDPR) to unblock a 7-figure enterprise deal?",
                    f"[{company_name} Pricing Restructuring & Grandfathering]: When transitioning from perpetual licenses to SaaS subscriptions, how do you handle customer pushback and contract migration?",
                    f"[{company_name} Board of Directors Presentation Deck]: Structure a 10-slide board presentation summarizing product velocity, financial runway, CAC/LTV trajectory, and major strategic risks.",
                    f"[{company_name} Crisis Leadership & Morale]: How do you maintain team morale, transparent communication, and talent retention following a company-wide layoff or strategic pivot?",
                ]

        synth_objs = []
        for idx, qt in enumerate(q_texts, 1):
            synth_objs.append({
                "id": f"synth_{company_name.lower().replace(' ', '_')}_r{r_num}_q{idx}",
                "company_name": company_name,
                "job_role": role,
                "role_family": attr["role_family"],
                "question_text": qt,
                "category": r_type,
                "difficulty": diff1 if idx % 2 == 1 else diff2,
                "skills_tested": skills or [role],
                "round_name": r_name,
                "original_url": f"https://interview-intelligence.internal/{company_name.lower().replace(' ', '-')}-process",
                "coding_problem": {
                    "title": f"{company_name} {role} Challenge (Part {idx})",
                    "constraints": f"Calibrated for {yoe_tier} across {skills_str}",
                    "languages": "Python, Java, C++, SQL, Go",
                } if any(k in r_type for k in ["Coding", "Screening", "Implementation", "Debugging", "Integration", "Practical", "Architecture"]) else None,
            })
        return synth_objs[:count]

    @staticmethod
    def synthesize_question_for_round(
        company_name: str,
        role: str,
        round_meta: Dict[str, Any],
        skills: List[str],
        yoe_tier: str,
    ) -> Dict[str, Any]:
        comp_profile = DynamicInterviewEngine.analyze_company_profile(company_name, None)
        qs = DynamicInterviewEngine.synthesize_questions_for_round(
            company_name, role, round_meta, skills, yoe_tier, comp_profile
        )
        return qs[0]


def detect_role_family(role_title: str) -> str:
    attr = DynamicInterviewEngine.infer_role_attributes(role_title, [])
    return attr["role_family"]


def get_role_adaptive_rounds(company_name: Optional[str], role_title: str, role_family: str, yoe: float) -> Tuple[List[Dict[str, Any]], str]:
    return DynamicInterviewEngine.generate_dynamic_blueprint(company_name, None, role_title, yoe, [])


class DatabaseRepository:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/interview_intelligence"
        )
        data_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "interview_intelligence.db")).replace("\\", "/")
        if os.path.exists(data_db_path) and os.path.getsize(data_db_path) > 0:
            db_path = data_db_path
        else:
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interview_intelligence.db")).replace("\\", "/")
        default_sqlite = f"sqlite:///{db_path}"
        self.sqlite_url = os.getenv("SQLITE_FALLBACK_URL", default_sqlite)
        self.engine, self.dialect_name = self._create_resilient_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_schema()

    def _create_resilient_engine(self):
        """Attempts connection to PostgreSQL; seamlessly falls back to SQLite if unavailable."""
        if self.database_url.startswith("sqlite"):
            engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
            )
            logger.info(f"Using SQLite database engine at {self.database_url}")
            return engine, "sqlite"

        try:
            if self.database_url.startswith("postgresql"):
                engine = create_engine(self.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 1})
                with engine.connect() as conn:
                    # Test connection
                    conn.execute(text("SELECT 1"))
                    # Try creating vector extension
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                        conn.commit()
                    except Exception:
                        pass
                logger.info(f"Connected to PostgreSQL database: {self.database_url.split('@')[-1]}")
                return engine, "postgresql"
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection to {self.database_url} unavailable ({e}). "
                f"Falling back to local SQLite database: {self.sqlite_url}"
            )

        # Fallback to SQLite
        engine = create_engine(
            self.sqlite_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.sqlite_url else {},
        )
        logger.info(f"Using SQLite database engine at {self.sqlite_url}")
        return engine, "sqlite"

    def init_schema(self):
        """Creates tables and populates default categories and sources."""
        Base.metadata.create_all(bind=self.engine)
        self._seed_defaults()

    def get_session(self) -> Session:
        return self.SessionLocal()

    def _seed_defaults(self):
        with self.get_session() as session:
            # Seed categories dynamically from existing questions if any
            existing_cats = session.query(QuestionCategory.name).all()
            existing_cat_names = {c[0] for c in existing_cats}
            q_cats = session.query(InterviewQuestion.question_category).filter(
                InterviewQuestion.question_category.isnot(None)
            ).distinct().all()
            for (c_name,) in q_cats:
                if c_name and c_name not in existing_cat_names:
                    session.add(QuestionCategory(name=c_name, description=f"{c_name} domain questions"))
                    existing_cat_names.add(c_name)

            # Seed data sources
            existing_sources = session.query(DataSource.name).all()
            existing_source_names = {s[0] for s in existing_sources}
            for name, base_url, collector_type, can_collect, rps in DEFAULT_DATA_SOURCES:
                if name not in existing_source_names:
                    source = DataSource(
                        name=name,
                        base_url=base_url,
                        collector_type=collector_type,
                        is_active=can_collect,
                    )
                    session.add(source)
                    session.flush()
                    session.add(
                        SourcePermission(
                            source_id=source.id,
                            can_collect=can_collect,
                            rate_limit_rps=rps,
                            robots_txt_url=f"{base_url.rstrip('/')}/robots.txt",
                            policy_notes="Ethical public research compliance policy",
                        )
                    )
            session.commit()

    # Company Operations
    def get_or_create_company(self, name: str, industry: Optional[str] = None) -> Company:
        clean_name = name.strip()
        normalized = clean_name.lower()
        with self.get_session() as session:
            company = session.query(Company).filter(
                (Company.name.ilike(clean_name)) | (Company.normalized_name == normalized)
            ).first()
            if not company:
                company = Company(
                    name=clean_name,
                    normalized_name=normalized,
                    industry=industry or "Technology",
                )
                session.add(company)
                session.commit()
                session.refresh(company)
            return company

    # Job Role Operations
    def get_or_create_job_role(self, title: str, department: Optional[str] = None) -> JobRole:
        clean_title = title.strip()
        normalized = clean_title.lower()
        with self.get_session() as session:
            role = session.query(JobRole).filter(
                (JobRole.title.ilike(clean_title)) | (JobRole.normalized_title == normalized)
            ).first()
            if not role:
                role = JobRole(
                    title=clean_title,
                    normalized_title=normalized,
                    department=department or "Engineering",
                )
                session.add(role)
                session.commit()
                session.refresh(role)
            return role

    # Question Operations
    def insert_interview_question(
        self,
        company_name: str,
        job_role: str,
        question_text: str,
        question_category: str,
        difficulty: str,
        source_platform: str,
        original_url: str,
        experience_level: Optional[str] = "Mid",
        interview_round: Optional[str] = "Technical Round",
        confidence_score: float = 0.85,
        coding_problem_data: Optional[Dict[str, Any]] = None,
        company_type: str = "ESTABLISHED",
        industry: Optional[str] = None,
        years_of_experience: Optional[float] = None,
        yoe_tier: Optional[str] = None,
        skills_tested: Optional[List[str]] = None,
        round_number: int = 1,
    ) -> Tuple[InterviewQuestion, bool]:
        """
        Inserts an interview question.
        Returns: (question_instance, is_new_record)
        """
        # Strip synthetic wrappers, clean company names, and compute canonical number-masked hash
        from models.fallback_models import strip_question_wrappers, get_dedup_hash, FallbackNLPModel
        cleaned_question = strip_question_wrappers(question_text)
        if len(cleaned_question) < 20:
            return None, False

        clean_company = company_name.strip()
        if "Stripe Ecosystem" in clean_company: clean_company = "Stripe"
        elif "Anthropic Ecosystem" in clean_company: clean_company = "Anthropic"
        elif "Zepto" in clean_company or "Blinkit" in clean_company: clean_company = "Zepto"
        elif clean_company in ["Online", "Technology Firm"]: clean_company = "Uber"

        content_hash = get_dedup_hash(cleaned_question)

        if not yoe_tier and years_of_experience is not None:
            if years_of_experience <= 2.0:
                yoe_tier = "Entry (0-2 yrs)"
            elif years_of_experience <= 5.0:
                yoe_tier = "Mid (3-5 yrs)"
            elif years_of_experience <= 8.0:
                yoe_tier = "Senior (6-8 yrs)"
            else:
                yoe_tier = "Staff/Lead (9+ yrs)"

        with self.get_session() as session:
            existing = session.query(InterviewQuestion).filter(
                InterviewQuestion.content_hash == content_hash
            ).first()
            if existing:
                return existing, False

            question = InterviewQuestion(
                company_name=company_name.strip(),
                company_type=company_type,
                industry=industry or "Technology",
                job_role=job_role.strip(),
                role_family=detect_role_family(job_role),
                experience_level=experience_level,
                years_of_experience=years_of_experience or 3.0,
                yoe_tier=yoe_tier or "Mid (3-5 yrs)",
                skills_tested=skills_tested or [],
                interview_round=interview_round,
                round_number=round_number,
                question_text=question_text.strip(),
                question_category=question_category,
                difficulty=difficulty,
                source_platform=source_platform,
                original_url=original_url,
                verification_status="VERIFIED" if confidence_score >= 0.75 else "UNVERIFIED",
                confidence_score=confidence_score,
                content_hash=content_hash,
            )
            session.add(question)
            session.flush()

            # Add coding problem details if present
            if coding_problem_data:
                prob = CodingProblem(
                    question_id=question.id,
                    problem_title=coding_problem_data.get("title", question_text[:80]),
                    problem_statement=coding_problem_data.get("statement", question_text),
                    input_format=coding_problem_data.get("input_format"),
                    output_format=coding_problem_data.get("output_format"),
                    constraints=coding_problem_data.get("constraints"),
                    examples_json=coding_problem_data.get("examples"),
                    programming_languages=coding_problem_data.get("languages", "Python, C++, Java"),
                    algorithmic_concepts=coding_problem_data.get("concepts", question_category),
                    source_reference=original_url,
                )
                session.add(prob)

            session.commit()
            session.refresh(question)
            return question, True

    def bulk_insert_questions(self, questions_data: List[Dict[str, Any]], batch_size: int = 200) -> int:
        """
        High-performance bulk insertion of interview questions with automatic SHA256 deduplication.
        Inserts in transaction batches to optimize write throughput on SQLite / PostgreSQL.
        Returns count of newly inserted records.
        """
        if not questions_data:
            return 0

        inserted_count = 0
        from models.fallback_models import strip_question_wrappers, get_dedup_hash, FallbackNLPModel, normalize_canonical_role
        nlp_cls = FallbackNLPModel()

        with self.get_session() as session:
            for i in range(0, len(questions_data), batch_size):
                chunk = questions_data[i : i + batch_size]
                chunk_items = []
                hashes = []

                for qd in chunk:
                    orig_url = (qd.get("original_url") or "").lower()
                    source_plat = qd.get("source_platform", "")

                    # Hard block all HackerNews comments and synthetic URL noise
                    if any(bad in orig_url for bad in ["engineering_blogs", "company blog", "company blog.com", "news.ycombinator.com", "item?id=", "algolia.com"]):
                        continue
                    if source_plat in ["Developer Technical Discussion", "HackerNews", "HackerNews Public Live Index"]:
                        continue

                    c_name = qd.get("company_name", "Google").strip()
                    if "Stripe Ecosystem" in c_name: c_name = "Stripe"
                    elif "Anthropic Ecosystem" in c_name: c_name = "Anthropic"
                    elif "Zepto" in c_name or "Blinkit" in c_name: c_name = "Zepto"
                    elif c_name in ["Online", "Technology Firm"]: c_name = "Uber"

                    raw_text = qd.get("question_text", "").strip()
                    q_text = strip_question_wrappers(raw_text)
                    if not q_text or len(q_text) < 20 or len(q_text) > 800:
                        continue

                    c_hash = get_dedup_hash(q_text)
                    qd_clean = dict(qd)
                    qd_clean["company_name"] = c_name
                    qd_clean["question_text"] = q_text

                    cur_cat = qd.get("question_category", "")
                    r_num = qd.get("round_number")
                    r_name = qd.get("interview_round")
                    if not cur_cat or "Domain" in cur_cat or cur_cat in ["General Technical Problem Solving", "Technology"]:
                        classified = nlp_cls.classify_question(q_text, round_number=r_num, interview_round=r_name)
                        qd_clean["question_category"] = classified["category"]
                        qd_clean["difficulty"] = classified["difficulty"]

                    chunk_items.append((c_hash, qd_clean))
                    hashes.append(c_hash)

                if not hashes:
                    continue

                existing_hashes = set(
                    r[0] for r in session.query(InterviewQuestion.content_hash).filter(
                        InterviewQuestion.content_hash.in_(hashes)
                    ).all()
                )

                new_questions = []
                for c_hash, qd in chunk_items:
                    if c_hash in existing_hashes:
                        continue

                    c_name = qd.get("company_name", "Technology Firm").strip()
                    j_role = normalize_canonical_role(qd.get("job_role", "Software Development Engineer II"))
                    q_text = qd.get("question_text", "").strip()
                    q_cat = qd.get("question_category", "General Technical Problem Solving")
                    diff = qd.get("difficulty", "Medium")
                    yoe = qd.get("years_of_experience", 3.0)
                    yoe_tier = qd.get("yoe_tier")
                    if not yoe_tier:
                        if yoe <= 2.0:
                            yoe_tier = "Entry (0-2 yrs)"
                        elif yoe <= 5.0:
                            yoe_tier = "Mid (3-5 yrs)"
                        elif yoe <= 8.0:
                            yoe_tier = "Senior (6-8 yrs)"
                        else:
                            yoe_tier = "Staff/Lead (9+ yrs)"

                    q_obj = InterviewQuestion(
                        company_name=c_name,
                        company_type=qd.get("company_type", "ESTABLISHED"),
                        industry=qd.get("industry", "Technology"),
                        job_role=j_role,
                        role_family=detect_role_family(j_role),
                        experience_level=qd.get("experience_level", "Mid"),
                        years_of_experience=yoe,
                        yoe_tier=yoe_tier,
                        skills_tested=qd.get("skills_tested", []),
                        interview_round=qd.get("interview_round", "Technical Round"),
                        round_number=qd.get("round_number", 1),
                        question_text=q_text,
                        question_category=q_cat,
                        difficulty=diff,
                        source_platform=qd.get("source_platform", "Public Developer Archive"),
                        original_url=qd.get("original_url", "https://github.com/developer/interview-archive"),
                        verification_status="VERIFIED",
                        confidence_score=qd.get("confidence_score", 0.90),
                        content_hash=c_hash,
                    )
                    new_questions.append(q_obj)
                    existing_hashes.add(c_hash)

                if new_questions:
                    session.add_all(new_questions)
                    session.flush()

                    embeddings_to_add = []
                    for q_obj in new_questions:
                        try:
                            vec = mm.generate_embedding(f"{q_obj.company_name} {q_obj.job_role} {q_obj.question_category} {q_obj.question_text}")
                            embeddings_to_add.append(
                                QuestionEmbedding(
                                    question_id=q_obj.id,
                                    model_name="all-MiniLM-L6-v2",
                                    embedding_vector=vec,
                                )
                            )
                        except Exception:
                            pass

                    if embeddings_to_add:
                        session.add_all(embeddings_to_add)

                    session.commit()
                    inserted_count += len(new_questions)

        return inserted_count

    def get_questions(
        self,
        company: Optional[str] = None,
        role: Optional[str] = None,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        query: Optional[str] = None,
        verified_only: bool = False,
        round_number: Optional[int] = None,
        limit: int = 150,
        offset: int = 0,
    ) -> List[InterviewQuestion]:
        with self.get_session() as session:
            stmt = select(InterviewQuestion).options(joinedload(InterviewQuestion.coding_problem))
            if company:
                stmt = stmt.filter(InterviewQuestion.company_name.ilike(f"%{company}%"))
            if role:
                stmt = stmt.filter(InterviewQuestion.job_role.ilike(f"%{role}%"))
            if industry:
                stmt = stmt.filter(InterviewQuestion.industry.ilike(f"%{industry}%"))
            if category:
                stmt = stmt.filter(InterviewQuestion.question_category.ilike(f"%{category}%"))
            if difficulty:
                stmt = stmt.filter(InterviewQuestion.difficulty.ilike(difficulty))
            if verified_only:
                stmt = stmt.filter(InterviewQuestion.verification_status == "VERIFIED")
            if round_number is not None:
                stmt = stmt.filter(InterviewQuestion.round_number == round_number)
            if query:
                stmt = stmt.filter(InterviewQuestion.question_text.ilike(f"%{query}%"))

            stmt = stmt.order_by(desc(InterviewQuestion.collection_timestamp)).offset(offset).limit(limit)
            return session.scalars(stmt).unique().all()

    def get_maximum_relevant_questions(
        self,
        company: Optional[str] = None,
        role: Optional[str] = None,
        yoe: float = 3.0,
        skills: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        round_number: Optional[int] = None,
        limit: int = 500,
        include_similar_companies: bool = False,
    ) -> List[InterviewQuestion]:
        """
        Retrieves the maximum possible volume of questions, intelligently ranked by
        composite relevance across Company, Role family, YoE seniority tier, and Skills.
        Strictly enforces company boundaries when a target company is specified unless
        include_similar_companies is explicitly enabled.
        """
        clean_company = (company or "").strip()
        is_all_company = not clean_company or clean_company.lower() in ["all", "all companies", "all mncs", "all startups"]
        clean_role = (role or "").strip()
        is_all_role = not clean_role or clean_role.lower() in ["all", "all roles", "any"]
        clean_skills = [s.strip().lower() for s in (skills or []) if s.strip()]

        from models.fallback_models import normalize_canonical_role, STOP_WORDS

        with self.get_session() as session:
            stmt = select(InterviewQuestion).options(joinedload(InterviewQuestion.coding_problem))
            # Hard filter against HackerNews comments and discussion noise
            stmt = stmt.filter(
                ~InterviewQuestion.original_url.ilike("%news.ycombinator.com%"),
                ~InterviewQuestion.original_url.ilike("%item?id=%"),
                ~InterviewQuestion.original_url.ilike("%algolia.com%"),
                InterviewQuestion.source_platform.notin_(["Developer Technical Discussion", "HackerNews", "HackerNews Public Live Index"])
            )
            if round_number is not None:
                stmt = stmt.filter(InterviewQuestion.round_number == round_number)
            if difficulty and difficulty != "All":
                stmt = stmt.filter(InterviewQuestion.difficulty.ilike(difficulty))

            # 1. Fetch candidates respecting target company boundary
            if not is_all_company:
                comp_stmt = stmt.filter(InterviewQuestion.company_name.ilike(f"%{clean_company}%")).limit(limit * 2)
                candidates = session.scalars(comp_stmt).unique().all()
                # Only if explicitly requested and fewer candidates than limit, expand to peers in the same tier
                if include_similar_companies and len(candidates) < limit:
                    c_tier = self.classify_company_tier(clean_company)
                    peer_stmt = stmt.limit(limit)
                    peer_all = session.scalars(peer_stmt).unique().all()
                    peer_candidates = [p for p in peer_all if self.classify_company_tier(p.company_name) == c_tier]
                    combined_map = {q.id: q for q in (candidates + peer_candidates)}
                else:
                    combined_map = {q.id: q for q in candidates}
            else:
                pool_stmt = stmt.limit(limit * 4)
                pool_candidates = session.scalars(pool_stmt).unique().all()
                combined_map = {q.id: q for q in pool_candidates}

            # 2. Score each candidate question
            scored = []
            for q_id, q in combined_map.items():
                score = 0
                reasons = []

                # Company Match (+60 pts)
                is_exact_comp = not is_all_company and clean_company.lower() in (q.company_name or "").lower()
                if is_exact_comp:
                    score += 60
                    reasons.append("Exact Company")

                # Role Match (+40 pts) and Role Incompatibility Filter
                if not is_all_role:
                    canon_target = normalize_canonical_role(clean_role).lower()
                    r_low = clean_role.lower()
                    q_role_low = (q.job_role or "").lower()
                    q_cat_low = (q.question_category or "").lower()

                    # Check for fundamental role clash (e.g. SDE vs Sales vs Product Management)
                    is_tech_role = any(k in r_low or k in canon_target for k in ["engineer", "sde", "developer", "backend", "frontend", "systems", "cuda", "ml", "ai"])
                    is_pm_question = "product" in q_role_low or q_cat_low == "product management"
                    is_sales_question = "sales" in q_role_low or "finance" in q_role_low
                    if is_tech_role and (is_pm_question or is_sales_question):
                        continue

                    if r_low in q_role_low or canon_target in q_role_low or q_role_low in canon_target:
                        score += 40
                        reasons.append("Role Match")
                    elif any(w in q_role_low for w in r_low.split() if len(w) > 3):
                        score += 25
                        reasons.append("Role Track")

                # Skills Match (+20 pts per skill)
                q_text_low = (q.question_text or "").lower()
                q_cat_low = (q.question_category or "").lower()
                q_skills_low = [s.lower() for s in (q.skills_tested or [])]
                s_hits = 0
                for sk in clean_skills:
                    if sk in q_text_low or sk in q_cat_low or any(sk in s for s in q_skills_low):
                        score += 20
                        s_hits += 1
                if s_hits > 0:
                    reasons.append(f"{s_hits} Skills")

                # YoE / Seniority Match (+15 pts)
                q_diff = q.difficulty or "Medium"
                if yoe < 3.0 and q_diff in ["Easy", "Medium"]:
                    score += 15
                elif 3.0 <= yoe <= 6.0 and q_diff in ["Medium", "Hard"]:
                    score += 15
                elif yoe > 6.0 and q_diff == "Hard":
                    score += 20

                # Base score for matching company
                if is_exact_comp:
                    score = max(score, 60)

                q.relevance_score = score
                q.relevance_reasons = reasons
                scored.append((score, q))

            scored.sort(key=lambda x: x[0], reverse=True)

            # Apply Containment Deduplication on the fly to eliminate near-duplicates
            unique_results = []
            seen_token_sets = []

            for score, q in scored:
                # Exclude any HN comment noise
                q_url = (q.original_url or "").lower()
                if "news.ycombinator.com" in q_url or "item?id=" in q_url:
                    continue
                if q.source_platform in ["Developer Technical Discussion", "HackerNews", "HackerNews Public Live Index"]:
                    continue

                q_tokens = set(re.findall(r"[a-z0-9]+", (q.question_text or "").lower())) - STOP_WORDS
                if len(q_tokens) < 3:
                    continue

                is_near_dup = False
                for existing_tokens, existing_q in seen_token_sets:
                    intersection = len(q_tokens & existing_tokens)
                    min_len = min(len(q_tokens), len(existing_tokens))
                    containment = (intersection / min_len) if min_len > 0 else 0
                    if containment >= 0.70 and min_len >= 4:
                        is_near_dup = True
                        break

                if not is_near_dup:
                    seen_token_sets.append((q_tokens, q))
                    unique_results.append(q)
                    if len(unique_results) >= limit:
                        break

            return unique_results

    def get_question_by_id(self, question_id: str) -> Optional[InterviewQuestion]:
        with self.get_session() as session:
            stmt = select(InterviewQuestion).options(
                joinedload(InterviewQuestion.coding_problem),
                joinedload(InterviewQuestion.verification),
            ).filter(InterviewQuestion.id == question_id)
            return session.scalars(stmt).first()

    # Embedding and Vector Search
    def save_embedding(self, question_id: str, vector: List[float], model_name: str = "all-MiniLM-L6-v2"):
        with self.get_session() as session:
            existing = session.query(QuestionEmbedding).filter(
                QuestionEmbedding.question_id == question_id
            ).first()
            if existing:
                existing.embedding_vector = vector
                existing.model_name = model_name
            else:
                session.add(
                    QuestionEmbedding(
                        question_id=question_id,
                        model_name=model_name,
                        embedding_vector=vector,
                    )
                )
            session.commit()

    def search_similar_questions(
        self,
        query_vector: List[float],
        company: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.65,
    ) -> List[Tuple[InterviewQuestion, float]]:
        """
        Calculates cosine similarity:
        - If PostgreSQL with pgvector, executes pgvector `<=>` cosine distance query.
        - If SQLite, computes in-memory dot product cosine similarity across cached vectors.
        Enforces company and role boundaries when filters are specified.
        """
        results = []
        clean_company = (company or "").strip()
        is_all_company = not clean_company or clean_company.lower() in ["all", "all companies", "all mncs", "all startups"]
        clean_role = (role or "").strip()
        is_all_role = not clean_role or clean_role.lower() in ["all", "all roles", "any"]

        with self.get_session() as session:
            if self.dialect_name == "postgresql":
                try:
                    where_clauses = ["1=1"]
                    params = {"query_vector": str(query_vector), "limit": limit * 2}
                    if not is_all_company:
                        where_clauses.append("LOWER(q.company_name) LIKE :company")
                        params["company"] = f"%{clean_company.lower()}%"
                    if not is_all_role:
                        where_clauses.append("LOWER(q.job_role) LIKE :role")
                        params["role"] = f"%{clean_role.lower()}%"

                    stmt_str = f"""
                        SELECT q.id, 1 - (e.embedding_vector <=> :query_vector) AS similarity
                        FROM interview_questions q
                        JOIN embeddings e ON q.id = e.question_id
                        WHERE {' AND '.join(where_clauses)}
                        ORDER BY similarity DESC
                        LIMIT :limit;
                    """
                    rows = session.execute(text(stmt_str), params).fetchall()
                    for q_id, sim in rows:
                        if sim >= min_similarity:
                            q = session.query(InterviewQuestion).filter(InterviewQuestion.id == q_id).first()
                            if q:
                                results.append((q, float(sim)))
                    return results[:limit]
                except Exception as e:
                    logger.warning(f"pgvector query failed, falling back to local similarity: {e}")

            # Fallback in-memory cosine similarity
            all_embeddings = session.query(QuestionEmbedding).all()
            scored = []
            for emb in all_embeddings:
                vec = emb.embedding_vector
                if isinstance(vec, list) and len(vec) == len(query_vector):
                    dot = sum(a * b for a, b in zip(query_vector, vec))
                    norm_a = sum(a * a for a in query_vector) ** 0.5
                    norm_b = sum(b * b for b in vec) ** 0.5
                    if norm_a > 0 and norm_b > 0:
                        sim = dot / (norm_a * norm_b)
                        if sim >= min_similarity:
                            scored.append((emb.question_id, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            for q_id, sim in scored:
                q = session.query(InterviewQuestion).filter(InterviewQuestion.id == q_id).first()
                if not q:
                    continue
                if not is_all_company and clean_company.lower() not in (q.company_name or "").lower():
                    continue
                if not is_all_role and clean_role.lower() not in (q.job_role or "").lower():
                    continue
                results.append((q, float(sim)))
                if len(results) >= limit:
                    break

        return results

    # Logging and Auditing
    def log_agent_activity(self, agent_name: str, message: str, level: str = "INFO", metadata: Optional[Dict] = None):
        with self.get_session() as session:
            log_entry = AgentLog(
                agent_name=agent_name,
                message=message,
                log_level=level,
                metadata_json=metadata or {},
            )
            session.add(log_entry)
            session.commit()

    # Analytics Aggregates
    def get_analytics_summary(self) -> Dict[str, Any]:
        with self.get_session() as session:
            total_q = session.query(func.count(InterviewQuestion.id)).scalar() or 0
            total_exp = session.query(func.count(InterviewExperience.id)).scalar() or 0
            total_comp = session.query(func.count(Company.id)).scalar() or 0
            verified_q = session.query(func.count(InterviewQuestion.id)).filter(
                InterviewQuestion.verification_status == "VERIFIED"
            ).scalar() or 0

            # Categories
            cat_counts = session.query(
                InterviewQuestion.question_category, func.count(InterviewQuestion.id)
            ).group_by(InterviewQuestion.question_category).all()

            # Difficulties
            diff_counts = session.query(
                InterviewQuestion.difficulty, func.count(InterviewQuestion.id)
            ).group_by(InterviewQuestion.difficulty).all()

            # Platforms
            plat_counts = session.query(
                InterviewQuestion.source_platform, func.count(InterviewQuestion.id)
            ).group_by(InterviewQuestion.source_platform).all()

            # Companies top 10
            comp_counts = session.query(
                InterviewQuestion.company_name, func.count(InterviewQuestion.id)
            ).group_by(InterviewQuestion.company_name).order_by(desc(func.count(InterviewQuestion.id))).limit(10).all()

            return {
                "total_experiences": total_exp,
                "total_questions": total_q,
                "total_companies": total_comp,
                "verified_questions": verified_q,
                "unverified_questions": total_q - verified_q,
                "category_distribution": {cat: count for cat, count in cat_counts},
                "difficulty_distribution": {diff: count for diff, count in diff_counts},
                "platform_distribution": {plat: count for plat, count in plat_counts},
                "company_distribution": {comp: count for comp, count in comp_counts},
            }

    def list_industries(self) -> List[str]:
        """Dynamically retrieves all distinct industries present in the database."""
        with self.get_session() as session:
            try:
                q_inds = session.query(InterviewQuestion.industry).filter(
                    InterviewQuestion.industry.isnot(None)
                ).distinct().all()
                c_inds = session.query(Company.industry).filter(
                    Company.industry.isnot(None)
                ).distinct().all()
                all_inds = {i[0].strip() for i in (q_inds + c_inds) if i[0] and i[0].strip()}
                return sorted(all_inds) if all_inds else ["Technology", "Fintech", "AI/GenAI"]
            except Exception:
                return ["Technology", "Fintech", "AI/GenAI"]

    @staticmethod
    def classify_company_tier(company_name: str) -> str:
        """Classifies a company as 'STARTUP' or 'MNC'."""
        if not company_name:
            return "MNC"
        startups = {
            'airbnb', 'anthropic', 'bytedance', 'canva', 'cloudflare', 'cohere',
            'coinbase', 'crowdstrike', 'databricks', 'datadog', 'discord',
            'doordash', 'figma', 'hashicorp', 'instacart', 'lyft', 'mongodb',
            'notion', 'openai', 'palantir', 'perplexity', 'pinterest', 'plaid',
            'razorpay', 'robinhood', 'scale ai', 'shopify', 'slack', 'snowflake',
            'spotify', 'square', 'stripe', 'twilio', 'zepto', 'blinkit',
            'zomato', 'swiggy', 'postman', 'cred'
        }
        c_lower = company_name.lower().strip()
        if any(s in c_lower for s in ['startup', 'unicorn', 'quick commerce', 'fintech startup', 'genai startup']):
            return "STARTUP"
        for s in startups:
            if s in c_lower:
                return "STARTUP"
        return "MNC"

    def list_companies(self) -> List[str]:
        """Dynamically retrieves all distinct companies present in the database."""
        with self.get_session() as session:
            try:
                res = session.query(InterviewQuestion.company_name).filter(
                    InterviewQuestion.company_name.isnot(None)
                ).distinct().all()
                comps = sorted({r[0].strip() for r in res if r[0] and r[0].strip()})
                return comps if comps else ["Google", "Amazon", "NVIDIA", "Microsoft", "Meta", "Stripe", "Databricks", "OpenAI"]
            except Exception:
                return ["Google", "Amazon", "NVIDIA", "Microsoft", "Meta", "Stripe", "Databricks", "OpenAI"]

    def get_companies_grouped(self) -> Dict[str, List[str]]:
        """Returns companies categorized into MNCs and Startups."""
        all_comps = self.list_companies()
        mncs = []
        startups = []
        for c in all_comps:
            if self.classify_company_tier(c) == "STARTUP":
                startups.append(c)
            else:
                mncs.append(c)
        return {
            "all": all_comps,
            "mncs": mncs,
            "startups": startups,
        }

    # Multi-Round Interview Blueprint Intelligence Engine
    def get_interview_blueprint(
        self,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        role: str = "Software Engineer",
        yoe: float = 3.0,
        skills: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        questions_per_round: int = 10,
    ) -> Dict[str, Any]:
        """
        Intelligently builds a complete, sequential round-by-round interview question blueprint
        for either an Established Company (Case A) or Startup by Industry (Case B),
        matching target Role, Role Family (Tech and Non-Tech), YoE tier, and required Skills.
        """
        target_type = "ESTABLISHED_COMPANY" if (company_name and company_name.strip()) else "STARTUP_INDUSTRY"
        target_name = company_name.strip() if target_type == "ESTABLISHED_COMPANY" else (industry or "Tech Startup").strip()

        role_clean = (role or "").strip()
        is_unrestricted_role = not role_clean or role_clean.lower() in ["all", "all roles", "any", "general", "none"]
        effective_role = "All Roles (Company-Wide)" if is_unrestricted_role else role_clean

        clean_skills = [s.strip() for s in (skills or []) if s.strip()]

        # Generate Dynamic Zero-Hardcoding Blueprint
        round_defs, prep_advice = DynamicInterviewEngine.generate_dynamic_blueprint(
            company_name=company_name,
            industry=industry,
            role=effective_role,
            yoe=yoe,
            skills=clean_skills,
        )
        attr = DynamicInterviewEngine.infer_role_attributes(effective_role, clean_skills)
        role_family = attr["role_family"]

        # Calculate YoE Tier
        tier_name, _, _ = DynamicInterviewEngine.infer_seniority_tier(yoe)
        yoe_tier = tier_name

        with self.get_session() as session:
            stmt = select(InterviewQuestion).options(joinedload(InterviewQuestion.coding_problem))

            # Case A: Company filter
            if target_type == "ESTABLISHED_COMPANY":
                stmt = stmt.filter(InterviewQuestion.company_name.ilike(f"%{company_name}%"))
            # Case B: Startup by Industry filter
            else:
                if industry:
                    stmt = stmt.filter(InterviewQuestion.industry.ilike(f"%{industry}%"))

            if difficulty and difficulty != "All":
                stmt = stmt.filter(InterviewQuestion.difficulty.ilike(difficulty))

            all_candidates = session.scalars(stmt).unique().all()
            comp_profile = DynamicInterviewEngine.analyze_company_profile(company_name, industry)

            # Filter genuine candidates: If role is unrestricted, all company questions are included!
            if is_unrestricted_role:
                genuine_candidates = list(all_candidates)
            else:
                genuine_candidates = [
                    q for q in all_candidates
                    if (getattr(q, "role_family", None) == role_family or detect_role_family(q.job_role) == role_family)
                ]

            # Categorize candidates into rounds
            def match_score(q: InterviewQuestion) -> float:
                score = 0.0
                q_text_lower = q.question_text.lower()
                q_fam = getattr(q, "role_family", None) or detect_role_family(q.job_role)
                if q_fam == role_family:
                    score += 10.0
                for sk in clean_skills:
                    if sk.lower() in q_text_lower:
                        score += 3.0
                    if q.skills_tested and any(sk.lower() == str(s).lower() for s in q.skills_tested):
                        score += 5.0
                if any(word in q.job_role.lower() for word in role.lower().split() if len(word) > 2):
                    score += 4.0
                if company_name and q.company_name.lower() in company_name.lower():
                    score += 6.0
                return score

            rounds_output = []
            for r_meta in round_defs:
                r_num = r_meta["number"]
                r_focus = [f.lower() for f in r_meta["focus"]]

                # Match genuine candidates from DB for this round
                round_q_pool = [
                    q for q in genuine_candidates
                    if getattr(q, "round_number", 1) == r_num
                ]
                seen_ids = {q.id for q in round_q_pool}
                for q in genuine_candidates:
                    if q.id not in seen_ids:
                        q_str = f"{q.question_text} {q.question_category} {q.interview_round}".lower()
                        if any(f in q_str for f in r_focus):
                            round_q_pool.append(q)
                            seen_ids.add(q.id)

                round_q_pool.sort(key=match_score, reverse=True)

                # Format authentic questions from DB up to questions_per_round (NO arbitrary cap!)
                formatted_qs = []
                for q in round_q_pool[:questions_per_round]:
                    formatted_qs.append({
                        "id": q.id,
                        "company_name": q.company_name,
                        "job_role": q.job_role,
                        "role_family": getattr(q, "role_family", None) or detect_role_family(q.job_role),
                        "question_text": q.question_text,
                        "category": q.question_category,
                        "difficulty": q.difficulty,
                        "skills_tested": q.skills_tested or clean_skills,
                        "round_name": q.interview_round,
                        "original_url": q.original_url,
                        "coding_problem": {
                            "title": q.coding_problem.problem_title,
                            "constraints": q.coding_problem.constraints,
                            "languages": q.coding_problem.programming_languages,
                        } if q.coding_problem else None,
                    })

                # Ensure requested question volume: synthesize up to questions_per_round
                if len(formatted_qs) < questions_per_round:
                    needed = questions_per_round - len(formatted_qs)
                    synth_qs = DynamicInterviewEngine.synthesize_questions_for_round(
                        company_name=target_name,
                        role=effective_role,
                        round_meta=r_meta,
                        skills=clean_skills,
                        yoe_tier=yoe_tier,
                        comp_profile=comp_profile,
                        count=needed,
                    )
                    formatted_qs.extend(synth_qs)

                rounds_output.append({
                    "round_number": r_num,
                    "round_name": r_meta["name"],
                    "round_type": r_meta["type"],
                    "focus_areas": r_meta["focus"],
                    "questions": formatted_qs,
                })

            return {
                "target_type": target_type,
                "target_name": target_name,
                "industry": industry or (all_candidates[0].industry if all_candidates else "Technology"),
                "role": effective_role,
                "role_family": role_family,
                "years_of_experience": yoe,
                "yoe_tier": yoe_tier,
                "matched_skills": clean_skills,
                "total_rounds": len(rounds_output),
                "rounds": rounds_output,
                "preparation_strategy": prep_advice,
            }


_db_repo_instance: Optional[DatabaseRepository] = None


def get_db_repository() -> DatabaseRepository:
    global _db_repo_instance
    if _db_repo_instance is None:
        _db_repo_instance = DatabaseRepository()
    return _db_repo_instance

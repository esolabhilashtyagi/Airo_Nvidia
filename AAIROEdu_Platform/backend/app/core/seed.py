import uuid
import os
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SyncSessionLocal, sync_engine
from app.core.database_guards import validate_seed_target
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile, Company
from app.models.taxonomy import Industry, IndustryCategory, JobRole, Skill
from app.models.question import Question, QuestionType, DifficultyLevel, SourceProvenance, ApprovalStatus
from app.models.module import Module, Lesson

INITIAL_INDUSTRIES = [
    {
        "name": "Information Technology",
        "slug": "information-technology",
        "icon": "Code2",
        "description": "Software engineering, cloud infrastructure, AI/ML, data platforms, and cybersecurity.",
        "categories": ["Software Development", "Cloud & DevOps", "Data & AI", "Cybersecurity"],
        "roles": [
            ("Software Engineer", "Full-stack and backend systems engineering", "Mid-Level"),
            ("Frontend Developer", "Web and client applications engineering", "Mid-Level"),
            ("Data Scientist", "Statistical modeling and machine learning applications", "Mid-Level"),
            ("DevOps Engineer", "CI/CD, container orchestration, and cloud infrastructure", "Senior")
        ]
    },
    {
        "name": "Banking and Finance",
        "slug": "banking-and-finance",
        "icon": "Building2",
        "description": "Commercial banking, investment analysis, risk management, and quantitative finance.",
        "categories": ["Investment Banking", "Corporate Banking", "Risk Management", "Fintech"],
        "roles": [
            ("Financial Analyst", "Financial modeling, equity research, valuation", "Mid-Level"),
            ("Risk Analyst", "Credit, market, and operational risk evaluation", "Mid-Level"),
            ("Investment Banking Associate", "M&A, capital markets, valuation pitchbooks", "Associate")
        ]
    },
    {
        "name": "Healthcare and Medical",
        "slug": "healthcare-and-medical",
        "icon": "HeartPulse",
        "description": "Clinical operations, health informatics, pharmaceutical research, and hospital management.",
        "categories": ["Clinical Practice", "Healthcare Administration", "Biomedical Research"],
        "roles": [
            ("Clinical Research Coordinator", "Trial protocols, patient compliance, GCP", "Mid-Level"),
            ("Healthcare Operations Manager", "Patient throughput, hospital resource planning", "Senior"),
            ("Health Informatics Specialist", "Electronic Health Records (EHR) & compliance", "Mid-Level")
        ]
    },
    {
        "name": "Human Resources",
        "slug": "human-resources",
        "icon": "Users",
        "description": "Talent acquisition, employee relations, compensation & benefits, and organizational design.",
        "categories": ["Talent Acquisition", "Employee Relations", "Total Rewards", "HR Business Partnering"],
        "roles": [
            ("Technical Recruiter", "Full-cycle candidate sourcing, technical screening, closing", "Mid-Level"),
            ("HR Business Partner", "Talent planning, employee engagement, leadership coaching", "Senior"),
            ("Compensation & Benefits Analyst", "Salary benchmarking, equity plans, payroll governance", "Mid-Level")
        ]
    },
    {
        "name": "Marketing and Sales",
        "slug": "marketing-and-sales",
        "icon": "TrendingUp",
        "description": "Digital marketing, brand strategy, enterprise sales, and growth engineering.",
        "categories": ["Growth Marketing", "Enterprise Sales", "Brand & Content Strategy"],
        "roles": [
            ("Product Marketing Manager", "Go-to-market strategies, positioning, persona research", "Mid-Level"),
            ("Enterprise Account Executive", "B2B SaaS deal cycles, prospecting, contract negotiation", "Senior"),
            ("Performance Marketing Specialist", "Paid acquisition, CAC/LTV optimization, conversion funnels", "Mid-Level")
        ]
    },
    {
        "name": "Consulting",
        "slug": "consulting",
        "icon": "Briefcase",
        "description": "Management consulting, strategy advisory, operational restructuring, and technology transformation.",
        "categories": ["Strategy Consulting", "Management Consulting", "Operations Advisory"],
        "roles": [
            ("Management Consultant", "Case interview frameworks, cost reduction, market entry", "Mid-Level"),
            ("Strategy Associate", "Financial modeling, market sizing, executive synthesis", "Associate")
        ]
    },
    {
        "name": "Manufacturing",
        "slug": "manufacturing",
        "icon": "Factory",
        "description": "Industrial manufacturing, quality assurance, lean operations, and process automation.",
        "categories": ["Process Engineering", "Quality Assurance", "Plant Operations"],
        "roles": [
            ("Quality Engineer", "Six Sigma, SPC, Root cause analysis (8D)", "Mid-Level"),
            ("Manufacturing Operations Lead", "Line balancing, OEE improvement, lean manufacturing", "Senior")
        ]
    },
    {
        "name": "Mechanical Engineering",
        "slug": "mechanical-engineering",
        "icon": "Cog",
        "description": "CAD design, thermodynamics, structural analysis, and robotics mechanisms.",
        "categories": ["Thermal Systems", "Structural Design", "Mechatronics"],
        "roles": [
            ("Mechanical Design Engineer", "SolidWorks/CATIA modeling, GD&T, FEA simulations", "Mid-Level")
        ]
    },
    {
        "name": "Civil Engineering",
        "slug": "civil-engineering",
        "icon": "HardHat",
        "description": "Structural engineering, transportation systems, geotechnical analysis, and construction management.",
        "categories": ["Structural Design", "Construction Management"],
        "roles": [
            ("Structural Engineer", "Building codes, seismic analysis, structural steel/concrete", "Mid-Level")
        ]
    },
    {
        "name": "Electrical and Electronics",
        "slug": "electrical-and-electronics",
        "icon": "Zap",
        "description": "Power systems, embedded electronics, PCB design, and analog/digital circuits.",
        "categories": ["Embedded Systems", "Power Electronics"],
        "roles": [
            ("Embedded Firmware Engineer", "C/C++, RTOS, microcontrollers, communication protocols (SPI/I2C)", "Mid-Level")
        ]
    },
    {
        "name": "Chemical and Pharmaceutical",
        "slug": "chemical-and-pharmaceutical",
        "icon": "FlaskConical",
        "description": "Process chemistry, drug formulation, regulatory affairs, and batch manufacturing.",
        "categories": ["Formulation Development", "Regulatory Affairs"],
        "roles": [
            ("Formulation Scientist", "Drug delivery kinetics, stability testing, FDA cGMP", "Senior")
        ]
    },
    {
        "name": "Education",
        "slug": "education",
        "icon": "GraduationCap",
        "description": "Curriculum development, instructional design, academic teaching, and educational technology.",
        "categories": ["Instructional Design", "Academic Administration"],
        "roles": [
            ("Instructional Designer", "ADDIE framework, interactive e-learning, curriculum rubrics", "Mid-Level")
        ]
    },
    {
        "name": "Retail and E-commerce",
        "slug": "retail-and-e-commerce",
        "icon": "ShoppingCart",
        "description": "Omnichannel merchandising, supply chain logistics, e-commerce storefronts, and category management.",
        "categories": ["Category Management", "E-commerce Operations"],
        "roles": [
            ("E-Commerce Category Manager", "Product listing optimization, pricing elasticity, margin management", "Mid-Level")
        ]
    },
    {
        "name": "Hospitality",
        "slug": "hospitality",
        "icon": "Utensils",
        "description": "Hotel management, food and beverage operations, guest relations, and luxury service.",
        "categories": ["Guest Services", "Hotel Operations"],
        "roles": [
            ("Hotel General Manager", "RevPAR, guest satisfaction index, housekeeping logistics", "Senior")
        ]
    },
    {
        "name": "Legal",
        "slug": "legal",
        "icon": "Scale",
        "description": "Corporate law, contract negotiation, regulatory compliance, and intellectual property.",
        "categories": ["Corporate Law", "Intellectual Property"],
        "roles": [
            ("Corporate Counsel", "Commercial contracts, NDA drafting, regulatory filings", "Senior")
        ]
    },
    {
        "name": "Government",
        "slug": "government",
        "icon": "Landmark",
        "description": "Public policy, government affairs, administrative services, and municipal planning.",
        "categories": ["Public Policy", "Administrative Affairs"],
        "roles": [
            ("Policy Analyst", "Legislative drafting, regulatory impact assessment, public budgeting", "Mid-Level")
        ]
    },
    {
        "name": "Media",
        "slug": "media",
        "icon": "Video",
        "description": "Journalism, video production, public relations, and digital content distribution.",
        "categories": ["Broadcast Media", "Public Relations"],
        "roles": [
            ("Communications Strategist", "Press releases, crisis communications, media briefing", "Mid-Level")
        ]
    },
    {
        "name": "Logistics and Supply Chain",
        "slug": "logistics-and-supply-chain",
        "icon": "Truck",
        "description": "Freight forwarding, inventory optimization, procurement, and warehouse operations.",
        "categories": ["Inventory Management", "Procurement"],
        "roles": [
            ("Supply Chain Planner", "Demand forecasting, safety stock analysis, supplier scorecards", "Mid-Level")
        ]
    },
    {
        "name": "Business Management",
        "slug": "business-management",
        "icon": "BarChart3",
        "description": "Executive operations, business development, operational scaling, and cross-functional leadership.",
        "categories": ["Operations Management", "Business Development"],
        "roles": [
            ("Operations Director", "P&L management, KPI governance, cross-functional execution", "Director")
        ]
    },
    {
        "name": "Research and Development",
        "slug": "research-and-development",
        "icon": "Microscope",
        "description": "Applied scientific research, patent development, prototype testing, and experimental methodology.",
        "categories": ["Applied Sciences", "Prototyping"],
        "roles": [
            ("R&D Scientist", "Experimental design, patent filing, scientific peer review", "Senior")
        ]
    }
]

COMPANIES_SEED = [
    {"name": "Google", "industry": "Information Technology", "website": "https://careers.google.com"},
    {"name": "Microsoft", "industry": "Information Technology", "website": "https://careers.microsoft.com"},
    {"name": "Goldman Sachs", "industry": "Banking and Finance", "website": "https://goldmansachs.com/careers"},
    {"name": "JPMorgan Chase", "industry": "Banking and Finance", "website": "https://jpmorganchase.com/careers"},
    {"name": "McKinsey & Company", "industry": "Consulting", "website": "https://mckinsey.com/careers"},
    {"name": "Boston Consulting Group (BCG)", "industry": "Consulting", "website": "https://bcg.com/careers"},
    {"name": "Pfizer", "industry": "Healthcare and Medical", "website": "https://pfizer.com/careers"},
    {"name": "Amazon", "industry": "Retail and E-commerce", "website": "https://amazon.jobs"},
    {"name": "Siemens", "industry": "Manufacturing", "website": "https://siemens.com/careers"},
    {"name": "Tesla", "industry": "Mechanical Engineering", "website": "https://tesla.com/careers"},
]


def seed_database(db: Session):
    print("🌱 Starting Candidate Dashboard AAIRO database seeding...")

    # 1. Seed Default Admin User
    admin = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            full_name="Aairo System Administrator",
            role=UserRole.ADMINISTRATOR,
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        db.flush()
        print(f"✅ Created Admin: {settings.INITIAL_ADMIN_EMAIL}")

    # 2. Seed Content Manager
    manager_email = "manager@aairo.ai"
    manager = db.query(User).filter(User.email == manager_email).first()
    if not manager:
        manager = User(
            email=manager_email,
            hashed_password=hash_password("ManagerPass123!"),
            full_name="Editorial Content Manager",
            role=UserRole.CONTENT_MANAGER,
            is_active=True,
            is_verified=True
        )
        db.add(manager)
        db.flush()
        print(f"✅ Created Content Manager: {manager_email}")

    # 3. Seed Demo Candidate User
    candidate_email = "candidate@aairo.ai"
    candidate = db.query(User).filter(User.email == candidate_email).first()
    if not candidate:
        candidate = User(
            email=candidate_email,
            hashed_password=hash_password("CandidatePass123!"),
            full_name="Alex Mercer",
            role=UserRole.CANDIDATE,
            is_active=True,
            is_verified=True
        )
        db.add(candidate)
        db.flush()
        print(f"✅ Created Candidate: {candidate_email}")

    # 4. Seed Companies
    for c_data in COMPANIES_SEED:
        existing_c = db.query(Company).filter(Company.name == c_data["name"]).first()
        if not existing_c:
            db.add(Company(**c_data))
    db.flush()

    # 5. Seed Industries, Categories, and Roles
    industry_map = {}
    role_map = {}
    for ind_data in INITIAL_INDUSTRIES:
        existing_ind = db.query(Industry).filter(Industry.slug == ind_data["slug"]).first()
        if not existing_ind:
            existing_ind = Industry(
                name=ind_data["name"],
                slug=ind_data["slug"],
                description=ind_data["description"],
                icon=ind_data["icon"],
                is_active=True
            )
            db.add(existing_ind)
            db.flush()

        industry_map[ind_data["slug"]] = existing_ind

        # Categories
        for cat_name in ind_data.get("categories", []):
            existing_cat = db.query(IndustryCategory).filter(
                IndustryCategory.industry_id == existing_ind.id,
                IndustryCategory.name == cat_name
            ).first()
            if not existing_cat:
                db.add(IndustryCategory(industry_id=existing_ind.id, name=cat_name))

        # Roles
        for role_title, role_desc, role_exp in ind_data.get("roles", []):
            existing_role = db.query(JobRole).filter(
                JobRole.industry_id == existing_ind.id,
                JobRole.title == role_title
            ).first()
            if not existing_role:
                new_role = JobRole(
                    industry_id=existing_ind.id,
                    title=role_title,
                    description=role_desc,
                    experience_level=role_exp,
                    is_active=True
                )
                db.add(new_role)
                db.flush()
                role_map[role_title] = new_role
            else:
                role_map[role_title] = existing_role

    db.flush()

    # 6. Populate Candidate Profile for Demo Candidate
    it_ind = industry_map.get("information-technology")
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.id).first()
    if not profile and it_ind:
        profile = CandidateProfile(
            user_id=candidate.id,
            candidate_type="working_professional",
            sub_category="job_seeker",
            industry_id=it_ind.id,
            current_company="TechCorp Solutions",
            current_role="Junior Software Engineer",
            target_role="Software Engineer",
            total_experience_months=24,
            relevant_experience_months=24,
            employment_status="Employed",
            key_skills=["Python", "FastAPI", "React", "PostgreSQL", "Docker", "REST APIs"],
            career_goals="Transition to a senior full-stack systems engineering role at top-tier tech firms.",
            onboarding_completed=True,
            onboarding_step=7,
            interview_rounds_preferred=["Technical", "Coding", "System Design", "HR"],
            interaction_preference="text",
            interview_readiness_score=78.5
        )
        db.add(profile)
        db.flush()
        print("✅ Configured Candidate Profile for Alex Mercer")

    # 7. Seed Centralized Question Bank
    sample_questions = [
        {
            "question_text": "What is the primary difference between synchronous and asynchronous database I/O in high-concurrency web services?",
            "question_type": QuestionType.MCQ_SINGLE,
            "industry_slug": "information-technology",
            "role_title": "Software Engineer",
            "subject": "System Architecture",
            "topic": "Concurrency & I/O",
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "interview_round": "Technical",
            "options": [
                {"id": "A", "text": "Synchronous I/O yields execution back to the event loop while waiting for DB socket bytes", "is_correct": False},
                {"id": "B", "text": "Asynchronous I/O releases the thread/event loop to handle other requests while waiting for network responses", "is_correct": True},
                {"id": "C", "text": "Synchronous I/O requires fewer database connections than asynchronous I/O", "is_correct": False},
                {"id": "D", "text": "Asynchronous I/O eliminates all database locks and isolation levels", "is_correct": False}
            ],
            "expected_answer": "Option B is correct. Asynchronous I/O uses non-blocking sockets that notify the event loop when I/O operations complete, freeing the thread to process other concurrent HTTP requests.",
            "explanation": "Synchronous calls block the executing worker thread until the DB returns data, causing thread starvation under load. Async I/O (e.g. asyncpg) enables thousands of concurrent connections with low memory overhead.",
            "evaluation_rubric": {"accuracy": 5, "relevance": 5, "explanation": 5},
            "tags": ["async", "database", "python", "fastapi", "performance"],
            "source_provenance": SourceProvenance.SOURCE_VERIFIED,
            "approval_status": ApprovalStatus.APPROVED
        },
        {
            "question_text": "In discounted cash flow (DCF) modeling, how does an increase in the Weighted Average Cost of Capital (WACC) impact the enterprise value of a firm?",
            "question_type": QuestionType.MCQ_SINGLE,
            "industry_slug": "banking-and-finance",
            "role_title": "Financial Analyst",
            "subject": "Valuation",
            "topic": "DCF & Capital Structure",
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "interview_round": "Technical",
            "options": [
                {"id": "A", "text": "Increases enterprise value because higher discount rates indicate higher profitability", "is_correct": False},
                {"id": "B", "text": "Decreases enterprise value because future projected cash flows are discounted more heavily", "is_correct": True},
                {"id": "C", "text": "Has no effect because WACC only applies to equity holders", "is_correct": False},
                {"id": "D", "text": "Only affects terminal value and leaves projected period valuation unchanged", "is_correct": False}
            ],
            "expected_answer": "Option B is correct. The discount rate (WACC) appears in the denominator of the present value formula PV = CF / (1 + WACC)^t. As the denominator increases, present value decreases.",
            "explanation": "Higher WACC reflects higher perceived risk or capital costs, diminishing the present value of future free cash flows to the firm (FCFF).",
            "evaluation_rubric": {"accuracy": 5, "relevance": 5},
            "tags": ["dcf", "valuation", "wacc", "finance"],
            "source_provenance": SourceProvenance.SOURCE_VERIFIED,
            "approval_status": ApprovalStatus.APPROVED
        },
        {
            "question_text": "Describe the behavioral STAR method and explain how you would handle a scenario where an engineering project deadline is compromised by an unexpected critical upstream dependency failure.",
            "question_type": QuestionType.BEHAVIORAL,
            "industry_slug": "information-technology",
            "role_title": "Software Engineer",
            "subject": "Behavioral Competency",
            "topic": "Conflict & Crisis Resolution",
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "interview_round": "HR",
            "options": [],
            "expected_answer": "A structured STAR response: Situation (context of the critical delivery), Task (ownership of the module), Action (proactive risk escalation, decoupling dependencies via contract mocks or fallback modes, transparent stakeholder realignment), and Result (quantifiable mitigation, delivery of degraded core value, root cause postmortem).",
            "explanation": "Evaluates candidate accountability, cross-functional communication, risk management, and composure under delivery pressure.",
            "evaluation_rubric": {
                "star_structure": "Did the candidate clearly delineate Situation, Task, Action, and Result?",
                "proactivity": "Did they communicate early with stakeholders or hide the delay?",
                "technical_mitigation": "Did they suggest fallback architectures (mocking, feature toggles)?",
                "reflection": "Did they conduct a post-mortem to prevent recurrence?"
            },
            "tags": ["behavioral", "star", "leadership", "risk-management"],
            "source_provenance": SourceProvenance.SOURCE_VERIFIED,
            "approval_status": ApprovalStatus.APPROVED
        },
        {
            "question_text": "Under FDA 21 CFR Part 11 and Good Clinical Practice (GCP), what audit trail requirements must electronic clinical trial data collection systems satisfy?",
            "question_type": QuestionType.DOMAIN_SPECIFIC,
            "industry_slug": "healthcare-and-medical",
            "role_title": "Clinical Research Coordinator",
            "subject": "Regulatory Compliance",
            "topic": "FDA & GCP Auditing",
            "difficulty": DifficultyLevel.ADVANCED,
            "interview_round": "Domain-Specific",
            "options": [],
            "expected_answer": "Computer-generated, time-stamped audit trails that independently record the date and time of operator entries and actions that create, modify, or delete electronic records, ensuring prior entries are not obscured.",
            "explanation": "Audit trails in clinical systems ensure complete integrity, reproducibility, and prevent retroactive tampering with adverse event reports or dosage records.",
            "evaluation_rubric": {
                "regulatory_recall": "Mentions time-stamping, immutability, and attribution",
                "compliance_depth": "Understands consequences of data alteration during clinical trials"
            },
            "tags": ["healthcare", "fda", "gcp", "clinical-trials", "audit"],
            "source_provenance": SourceProvenance.SOURCE_VERIFIED,
            "approval_status": ApprovalStatus.APPROVED
        },
        {
            "question_text": "Which of the following metrics is most suitable for evaluating the financial health of an early-stage B2B SaaS startup with high upfront customer acquisition costs?",
            "question_type": QuestionType.MCQ_SINGLE,
            "industry_slug": "marketing-and-sales",
            "role_title": "Product Marketing Manager",
            "subject": "SaaS Economics",
            "topic": "CAC Payback & LTV",
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "interview_round": "Technical",
            "options": [
                {"id": "A", "text": "Gross Revenue without regard to churn", "is_correct": False},
                {"id": "B", "text": "CAC Payback Period and Net Revenue Retention (NRR)", "is_correct": True},
                {"id": "C", "text": "Cost per Click (CPC) alone", "is_correct": False},
                {"id": "D", "text": "Book value of physical fixed assets", "is_correct": False}
            ],
            "expected_answer": "Option B is correct. CAC Payback Period measures how many months of customer subscription it takes to recoup sales and marketing spend, while NRR measures the net expansion/contraction of existing cohorts.",
            "explanation": "A CAC payback period < 12 months paired with NRR > 110% signals a highly capital-efficient SaaS business model.",
            "evaluation_rubric": {"accuracy": 5},
            "tags": ["saas", "cac", "ltv", "marketing", "metrics"],
            "source_provenance": SourceProvenance.SOURCE_VERIFIED,
            "approval_status": ApprovalStatus.APPROVED
        }
    ]

    for q_data in sample_questions:
        ind = industry_map.get(q_data["industry_slug"])
        if not ind:
            continue
        role = role_map.get(q_data.get("role_title"))
        
        existing_q = db.query(Question).filter(
            Question.question_text == q_data["question_text"]
        ).first()

        if not existing_q:
            new_q = Question(
                question_text=q_data["question_text"],
                question_type=q_data["question_type"],
                industry_id=ind.id,
                job_role_id=role.id if role else None,
                subject=q_data["subject"],
                topic=q_data["topic"],
                difficulty=q_data["difficulty"],
                interview_round=q_data["interview_round"],
                options=q_data["options"],
                expected_answer=q_data["expected_answer"],
                explanation=q_data["explanation"],
                evaluation_rubric=q_data["evaluation_rubric"],
                tags=q_data["tags"],
                source_provenance=q_data["source_provenance"],
                approval_status=q_data["approval_status"],
                workflow_status="published",
                job_roles=[role] if role else [],
            )
            db.add(new_q)

    db.flush()

    # 8. Seed Learning Modules & Lessons
    sample_modules = [
        {
            "industry_slug": "information-technology",
            "title": "Data Structures & Scalable Algorithms",
            "description": "Master algorithmic complexity, graph traversal, dynamic programming, and high-throughput data structures.",
            "difficulty": "Intermediate",
            "duration_minutes": 180,
            "order_index": 1,
            "lessons": [
                {
                    "title": "Time & Space Complexity in Practice",
                    "content": "Understanding Big-O asymptotic analysis, amortized complexity, and cache locality in modern CPU hierarchies.",
                    "duration_minutes": 30,
                    "order_index": 1
                },
                {
                    "title": "Trees, Graphs & Pathfinding",
                    "content": "Binary search trees, balanced AVL/Red-Black trees, BFS/DFS traversal, and Dijkstra's shortest path algorithms.",
                    "duration_minutes": 45,
                    "order_index": 2
                },
                {
                    "title": "Dynamic Programming Patterns",
                    "content": "Memoization vs tabulation, sub-problem overlapping, knapsack variants, and string alignment algorithms.",
                    "duration_minutes": 60,
                    "order_index": 3
                }
            ]
        },
        {
            "industry_slug": "information-technology",
            "title": "Distributed Systems & REST Architecture",
            "description": "Architect fault-tolerant microservices, handle eventual consistency, and design scalable REST/gRPC interfaces.",
            "difficulty": "Advanced",
            "duration_minutes": 240,
            "order_index": 2,
            "lessons": [
                {
                    "title": "CAP Theorem & Consistency Models",
                    "content": "Consistency, Availability, and Partition Tolerance trade-offs. ACID transactions vs BASE models.",
                    "duration_minutes": 45,
                    "order_index": 1
                },
                {
                    "title": "Caching Strategies & Database Partitioning",
                    "content": "Read-through, write-through, write-back caching. Sharding keys, replication lag, and connection pooling.",
                    "duration_minutes": 60,
                    "order_index": 2
                }
            ]
        },
        {
            "industry_slug": "banking-and-finance",
            "title": "Financial Statement Analysis & Corporate Valuation",
            "description": "Analyze balance sheets, income statements, cash flow dynamics, and calculate company valuation multiples.",
            "difficulty": "Intermediate",
            "duration_minutes": 150,
            "order_index": 1,
            "lessons": [
                {
                    "title": "Three-Statement Linkage",
                    "content": "How net income flows into retained earnings and operating cash flow; working capital adjustments.",
                    "duration_minutes": 45,
                    "order_index": 1
                },
                {
                    "title": "DCF & Comparable Company Multiples",
                    "content": "Unlevered free cash flow calculations, terminal value Gordon growth models, and EV/EBITDA comps.",
                    "duration_minutes": 60,
                    "order_index": 2
                }
            ]
        }
    ]

    for m_data in sample_modules:
        ind = industry_map.get(m_data["industry_slug"])
        if not ind:
            continue
        existing_m = db.query(Module).filter(
            Module.industry_id == ind.id,
            Module.title == m_data["title"]
        ).first()

        if not existing_m:
            mod = Module(
                industry_id=ind.id,
                title=m_data["title"],
                description=m_data["description"],
                difficulty=m_data["difficulty"],
                duration_minutes=m_data["duration_minutes"],
                order_index=m_data["order_index"],
                is_published=True
            )
            db.add(mod)
            db.flush()

            for l_data in m_data.get("lessons", []):
                db.add(Lesson(
                    module_id=mod.id,
                    title=l_data["title"],
                    content=l_data["content"],
                    duration_minutes=l_data["duration_minutes"],
                    order_index=l_data["order_index"]
                ))

    db.commit()
    print("✨ Database seed completed successfully!")


if __name__ == "__main__":
    validate_seed_target(
        sync_engine.url,
        allowed_database=os.environ.get("SEED_ALLOWED_DB"),
        environment=settings.ENVIRONMENT,
    )
    db = SyncSessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

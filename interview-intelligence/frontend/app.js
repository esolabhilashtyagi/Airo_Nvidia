/**
 * Interview Intelligence Frontend Client.
 * Connects to the local FastAPI backend (http://localhost:8000).
 * Handles Case A & Case B blueprint generation, semantic search, analytics, and 14-agent matrix.
 */

// Determine API Base URL
const API_BASE = (window.location.origin.startsWith("http") && !window.location.origin.includes(":8501"))
    ? window.location.origin
    : "http://localhost:8000";

let currentParadigm = "case_a";
let currentBlueprintData = null;

const ROLE_PRESETS = [
    { label: "💻 SDE II (Tech)", role: "Software Development Engineer II", company: "Google", industry: "Enterprise Tech", yoe: 4.0, skills: "Python, Distributed Systems, Algorithms" },
    { label: "⚡ Systems/CUDA (Tech)", role: "Senior Systems Software Engineer", company: "NVIDIA", industry: "AI/GenAI", yoe: 7.0, skills: "C++, CUDA, Concurrency, Linux" },
    { label: "🤖 AI/GenAI (Tech)", role: "AI Engineer (GenAI / RAG)", company: "Perplexity / Anthropic Ecosystem", industry: "AI/GenAI", yoe: 2.0, skills: "Python, Vector Search, FastAPI, LLMs" },
    { label: "🎯 Product Manager (Non-Tech)", role: "Senior Product Manager", company: "Google", industry: "Enterprise Tech", yoe: 6.0, skills: "Product Strategy, Metrics & Analytics, A/B Testing, User Research" },
    { label: "📊 Data Analyst (Non-Tech)", role: "Senior Data Analyst", company: "Amazon", industry: "E-Commerce", yoe: 4.5, skills: "SQL, Tableau, Statistics, A/B Testing, Data Modeling" },
    { label: "🎨 UI/UX Designer (Non-Tech)", role: "Lead Product Designer", company: "Figma / Canva Ecosystem", industry: "SaaS", yoe: 5.0, skills: "Figma, Design Systems, User Research, Wireframing" },
    { label: "💼 B2B Enterprise Sales (Non-Tech)", role: "Enterprise Account Executive", company: "Salesforce", industry: "Enterprise Software", yoe: 5.5, skills: "MEDDPICC, Pipeline Generation, Discovery, Objection Handling" },
    { label: "📈 Growth Marketing (Non-Tech)", role: "Growth Marketing Manager", company: "Zepto / Blinkit Ecosystem", industry: "Consumer Internet", yoe: 3.5, skills: "CAC/LTV, Funnel CRO, Meta Ads, Attribution Modeling" },
    { label: "💰 Finance / FP&A (Non-Tech)", role: "Senior Financial Analyst", company: "Microsoft", industry: "Enterprise Tech", yoe: 5.0, skills: "3-Statement Modeling, SaaS Metrics, DCF, Variance Analysis" },
    { label: "👥 Talent Partner / HR (Non-Tech)", role: "Senior Talent Partner", company: "Meta / Tech Ecosystem", industry: "Enterprise Tech", yoe: 4.0, skills: "Tech Sourcing, Compensation, Total Rewards, Retention" },
];

const COMMON_SKILLS = [
    "Python", "Algorithms", "Distributed Systems", "Kafka", "PostgreSQL",
    "Redis", "CUDA", "FastAPI", "C++", "Java", "Trees and Graphs", "Dynamic Programming",
    "Product Strategy", "A/B Testing", "SQL", "Tableau", "Figma", "MEDDPICC", "CAC/LTV", "3-Statement Modeling"
];

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initQuickRoles();
    initQuickSkills();
    loadIndustries();
    loadAnalytics();
    loadAgents();
    lucide.createIcons();
});

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".nav-tab").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(`tab-${tabId}`);
    const targetBtn = document.getElementById(`tab-btn-${tabId}`);
    if (targetTab) targetTab.classList.remove("hidden");
    if (targetBtn) targetBtn.classList.add("active");

    if (tabId === "analytics") loadAnalytics();
    if (tabId === "agents") loadAgents();

    lucide.createIcons();
}

// Case A vs Case B Paradigm Toggle
function setParadigm(mode) {
    currentParadigm = mode;
    const btnA = document.getElementById("btn-case-a");
    const btnB = document.getElementById("btn-case-b");
    const compField = document.getElementById("company-field-group");
    const indField = document.getElementById("industry-field-group");
    const roleInput = document.getElementById("target-role");
    const skillsInput = document.getElementById("skills-input");

    if (mode === "case_a") {
        btnA.className = "flex-1 py-3 px-4 rounded-lg font-semibold text-sm flex items-center justify-center space-x-2 transition-all bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
        btnB.className = "flex-1 py-3 px-4 rounded-lg font-semibold text-sm flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-slate-200";
        compField.classList.remove("hidden");
        indField.classList.add("hidden");
        roleInput.value = "Software Development Engineer II";
        skillsInput.value = "Python, Distributed Systems, Algorithms";
    } else {
        btnB.className = "flex-1 py-3 px-4 rounded-lg font-semibold text-sm flex items-center justify-center space-x-2 transition-all bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
        btnA.className = "flex-1 py-3 px-4 rounded-lg font-semibold text-sm flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-slate-200";
        compField.classList.add("hidden");
        indField.classList.remove("hidden");
        roleInput.value = "Backend Engineer (Payments)";
        skillsInput.value = "Kafka, PostgreSQL, Python, Idempotency";
    }
    lucide.createIcons();
}

// YoE Slider Update
function updateYoEDisplay(val) {
    const yoe = parseFloat(val);
    let tier = "Entry (0-2 yrs)";
    if (yoe > 2.0 && yoe <= 5.0) tier = "Mid (3-5 yrs)";
    else if (yoe > 5.0 && yoe <= 8.0) tier = "Senior (6-8 yrs)";
    else if (yoe > 8.0) tier = "Staff/Lead (9+ yrs)";

    document.getElementById("yoe-display").innerText = `${yoe.toFixed(1)} yrs • ${tier}`;
}

// Quick Role Pills for Tech & Non-Tech
function initQuickRoles() {
    const container = document.getElementById("quick-roles-container");
    if (!container) return;
    container.innerHTML = "";
    ROLE_PRESETS.forEach((preset, idx) => {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = `text-[11px] px-2.5 py-1 rounded-md transition-all border font-medium ${
            idx === 0 
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" 
                : "bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white border-slate-700/60"
        }`;
        pill.innerText = preset.label;
        pill.onclick = () => {
            // Update active state
            Array.from(container.children).forEach(c => {
                c.className = "text-[11px] px-2.5 py-1 rounded-md transition-all border font-medium bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white border-slate-700/60";
            });
            pill.className = "text-[11px] px-2.5 py-1 rounded-md transition-all border font-medium bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
            applyRolePreset(preset);
        };
        container.appendChild(pill);
    });
}

function applyRolePreset(preset) {
    document.getElementById("target-role").value = preset.role;
    if (preset.company && document.getElementById("target-company")) {
        document.getElementById("target-company").value = preset.company;
    }
    if (preset.industry && document.getElementById("target-industry")) {
        document.getElementById("target-industry").value = preset.industry;
    }
    const slider = document.getElementById("yoe-slider");
    if (slider) {
        slider.value = preset.yoe;
        updateYoEDisplay(preset.yoe);
    }
    if (document.getElementById("skills-input")) {
        document.getElementById("skills-input").value = preset.skills;
    }
}

// Quick Skills Pills
function initQuickSkills() {
    const container = document.getElementById("quick-skills-container");
    container.innerHTML = "";
    COMMON_SKILLS.forEach(skill => {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = "text-[11px] px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors border border-slate-700/60";
        pill.innerText = `+ ${skill}`;
        pill.onclick = () => addSkillToInput(skill);
        container.appendChild(pill);
    });
}

function addSkillToInput(skill) {
    const input = document.getElementById("skills-input");
    const current = input.value.split(",").map(s => s.strip()).filter(Boolean);
    if (!current.includes(skill)) {
        current.push(skill);
        input.value = current.join(", ");
    }
}

// Load Available Industries for Startups
async function loadIndustries() {
    try {
        const res = await fetch(`${API_BASE}/industries`);
        if (res.ok) {
            const data = await res.json();
            const datalist = document.getElementById("industry-suggestions");
            if (data.industries && datalist) {
                const existing = new Set(Array.from(datalist.options).map(o => o.value.toLowerCase()));
                data.industries.forEach(ind => {
                    if (!existing.has(ind.toLowerCase())) {
                        const opt = document.createElement("option");
                        opt.value = ind;
                        datalist.appendChild(opt);
                    }
                });
            }
        }
    } catch (e) {
        console.warn("Could not load dynamic industries, using defaults:", e);
    }
}

// Generate Blueprint
async function generateBlueprint(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-generate");
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">⚙️</span> Synthesizing Adaptive Blueprint...`;
    btn.disabled = true;

    const company = currentParadigm === "case_a" ? document.getElementById("target-company").value.trim() : null;
    const industry = currentParadigm === "case_b" ? document.getElementById("target-industry").value.trim() : null;
    const role = document.getElementById("target-role").value.trim();
    const yoe = parseFloat(document.getElementById("yoe-slider").value);
    const skills = document.getElementById("skills-input").value.split(",").map(s => s.trim()).filter(Boolean);

    const payload = {
        company_name: company,
        industry: industry,
        role: role,
        years_of_experience: yoe,
        skills: skills,
    };

    try {
        const res = await fetch(`${API_BASE}/intelligence/interview-blueprint`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            const data = await res.json();
            currentBlueprintData = data;
            renderBlueprint(data);
        } else {
            showToast("Failed to generate blueprint. Check backend.");
        }
    } catch (err) {
        console.error(err);
        showToast("Error connecting to backend API.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
        lucide.createIcons();
    }
}

// Render Blueprint Cards for all 5 rounds
function renderBlueprint(data) {
    document.getElementById("blueprint-results").classList.remove("hidden");
    document.getElementById("res-target-name").innerText = data.target_name;
    document.getElementById("res-target-type").innerText = data.target_type;
    document.getElementById("res-seniority-tier").innerText = data.yoe_tier;
    const roundsBadge = document.getElementById("res-rounds-count");
    if (roundsBadge) {
        roundsBadge.innerText = `${data.total_rounds} Rounds`;
    }
    document.getElementById("res-role-domain").innerText = `${data.role} • ${data.industry || 'Technology'}${data.role_family ? ` [${data.role_family}]` : ''}`;
    document.getElementById("res-prep-advice").innerText = data.preparation_strategy;

    const roundsContainer = document.getElementById("rounds-container");
    roundsContainer.innerHTML = "";

    data.rounds.forEach((round, rIdx) => {
        const card = document.createElement("div");
        card.className = "bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg transition-all";

        const focusPills = round.focus_areas.map(f => `<span class="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">${f}</span>`).join(" ");

        let questionsHtml = "";
        if (round.questions && round.questions.length > 0) {
            questionsHtml = round.questions.map((q, qIdx) => {
                const diffColor = q.difficulty === "Hard" ? "text-rose-400 bg-rose-500/10 border-rose-500/20" : (q.difficulty === "Medium" ? "text-amber-400 bg-amber-500/10 border-amber-500/20" : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20");
                const skillsTags = (q.skills_tested || []).map(s => `<span class="text-[11px] text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40 font-mono">${s}</span>`).join(" ");
                
                const constraintsBlock = (q.coding_problem && q.coding_problem.constraints) ? `
                    <div class="mt-2.5 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs text-slate-400">
                        <span class="font-semibold text-slate-300">⚙️ Constraints & Specification:</span> ${q.coding_problem.constraints}
                    </div>
                ` : "";

                return `
                    <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 mb-3 last:mb-0">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center space-x-2">
                                <span class="text-xs font-bold px-2 py-0.5 rounded border ${diffColor}">${q.difficulty}</span>
                                <span class="text-xs font-semibold text-slate-300">[${q.company_name}]</span>
                            </div>
                            <button onclick="copyToClipboard('${escapeJs(q.question_text)}')" class="text-xs text-slate-400 hover:text-emerald-400 flex items-center space-x-1 transition-colors">
                                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                                <span>Copy</span>
                            </button>
                        </div>
                        <p class="text-sm text-slate-200 leading-relaxed font-normal">${q.question_text}</p>
                        ${constraintsBlock}
                        <div class="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-xs">
                            <div class="flex flex-wrap gap-1.5">${skillsTags}</div>
                            <a href="${q.original_url || '#'}" target="_blank" class="text-slate-500 hover:text-slate-300 flex items-center space-x-1">
                                <span>Source Provenance</span>
                                <i data-lucide="external-link" class="w-3 h-3"></i>
                            </a>
                        </div>
                    </div>
                `;
            }).join("");
        } else {
            questionsHtml = `<p class="text-xs text-slate-500 italic p-4 text-center">Standard industry evaluation blueprint pattern applied for this round.</p>`;
        }

        card.innerHTML = `
            <div class="p-5 border-b border-slate-800/80 bg-slate-950/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                    <h3 class="font-bold text-base text-white flex items-center space-x-2">
                        <span class="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-bold border border-emerald-500/30">${round.round_number}</span>
                        <span>${round.round_name}</span>
                    </h3>
                    <p class="text-xs text-slate-400 mt-0.5 ml-8">${round.round_type}</p>
                </div>
                <div class="flex flex-wrap gap-1.5 ml-8 sm:ml-0">${focusPills}</div>
            </div>
            <div class="p-5">${questionsHtml}</div>
        `;

        roundsContainer.appendChild(card);
    });

    lucide.createIcons();
    // Smooth scroll down to results
    document.getElementById("blueprint-results").scrollIntoView({ behavior: "smooth" });
}

// Semantic Search Execution
async function executeSemanticSearch() {
    const query = document.getElementById("semantic-search-input").value.trim();
    if (!query) return;

    const list = document.getElementById("search-results-list");
    list.innerHTML = `<p class="text-slate-400 text-sm text-center py-8 animate-pulse">Running local 384-dimensional dense vector similarity search...</p>`;

    try {
        const res = await fetch(`${API_BASE}/questions/search?q=${encodeURIComponent(query)}&limit=10&min_similarity=0.25`);
        if (res.ok) {
            const data = await res.json();
            if (data.results && data.results.length > 0) {
                list.innerHTML = data.results.map(r => `
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors">
                        <div class="flex items-center justify-between mb-1.5">
                            <div class="flex items-center space-x-2">
                                <span class="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">${(r.similarity_score * 100).toFixed(0)}% Match</span>
                                <span class="font-semibold text-xs text-white">[${r.company_name}] ${r.job_role}</span>
                            </div>
                            <span class="text-xs text-slate-500">${r.category}</span>
                        </div>
                        <p class="text-sm text-slate-200 mt-1">${r.question_text}</p>
                    </div>
                `).join("");
            } else {
                list.innerHTML = `<p class="text-slate-500 text-sm text-center py-8">No questions found matching your search query.</p>`;
            }
        }
    } catch (err) {
        list.innerHTML = `<p class="text-rose-400 text-sm text-center py-8">Error querying semantic search endpoint.</p>`;
    }
    lucide.createIcons();
}

function handleSearchKey(e) {
    if (e.key === "Enter") executeSemanticSearch();
}

// Load Analytics Overview
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/analytics`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById("kpi-total-q").innerText = data.total_questions || 0;
            document.getElementById("kpi-total-comp").innerText = data.total_companies || 0;
            document.getElementById("kpi-verified-q").innerText = data.verified_questions || 0;

            // Categories
            const catContainer = document.getElementById("analytics-categories");
            if (catContainer && data.category_distribution) {
                catContainer.innerHTML = Object.entries(data.category_distribution).map(([cat, count]) => `
                    <div class="flex items-center justify-between text-xs py-1.5 border-b border-slate-800/60 last:border-0">
                        <span class="text-slate-300">${cat}</span>
                        <span class="font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">${count}</span>
                    </div>
                `).join("");
            }

            // Companies
            const compContainer = document.getElementById("analytics-companies");
            if (compContainer && data.company_distribution) {
                compContainer.innerHTML = Object.entries(data.company_distribution).map(([comp, count]) => `
                    <div class="flex items-center justify-between text-xs py-1.5 border-b border-slate-800/60 last:border-0">
                        <span class="text-slate-300 font-medium">${comp}</span>
                        <span class="font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">${count} questions</span>
                    </div>
                `).join("");
            }
        }
    } catch (e) {
        console.warn("Analytics fetch error:", e);
    }
}

// Load 14-Agent Matrix
async function loadAgents() {
    try {
        const res = await fetch(`${API_BASE}/agents/status`);
        if (res.ok) {
            const data = await res.json();
            const tbody = document.getElementById("agents-table-body");
            if (tbody && data.agents) {
                tbody.innerHTML = data.agents.map(ag => `
                    <tr class="hover:bg-slate-950/40 transition-colors">
                        <td class="py-3 px-4 font-semibold text-white">${ag.name}</td>
                        <td class="py-3 px-4 text-xs font-mono text-slate-400">${ag.type}</td>
                        <td class="py-3 px-4">
                            <span class="text-[11px] font-bold px-2 py-0.5 rounded-full ${ag.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : (ag.status === 'RUNNING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-slate-800 text-slate-400')}">
                                ${ag.status}
                            </span>
                        </td>
                        <td class="py-3 px-4 text-xs text-slate-300">${ag.tasks_completed}</td>
                        <td class="py-3 px-4 text-xs text-slate-400">${ag.current_task || 'Idle / Ready'}</td>
                    </tr>
                `).join("");
            }
        }
    } catch (e) {
        console.warn("Agents status error:", e);
    }
}

// Trigger Pipeline Run
async function triggerPipelineRun() {
    try {
        showToast("Triggering 14-Agent Multi-Source Collection Pipeline...");
        const res = await fetch(`${API_BASE}/collect/start?source_name=all&limit=2&use_mock=true`, { method: "POST" });
        if (res.ok) {
            showToast("Pipeline triggered successfully! Refreshing status in 2s...");
            setTimeout(() => {
                loadAgents();
                loadAnalytics();
            }, 2000);
        }
    } catch (e) {
        showToast("Error triggering pipeline.");
    }
}

// Download Blueprint JSON
function downloadBlueprintJSON() {
    if (!currentBlueprintData) return;
    const blob = new Blob([JSON.stringify(currentBlueprintData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `blueprint_${currentBlueprintData.target_name.toLowerCase().replace(/\\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Toast Notification
function showToast(msg) {
    const t = document.createElement("div");
    t.className = "toast-notice";
    t.innerText = msg;
    document.body.appendChild(t);
    setTimeout(() => {
        t.style.opacity = "0";
        setTimeout(() => t.remove(), 300);
    }, 3000);
}

// Clipboard Helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied question to clipboard!");
    }).catch(() => {
        showToast("Failed to copy text.");
    });
}

function escapeJs(str) {
    return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\\n/g, ' ');
}

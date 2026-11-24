"""
Agent 1: Master Orchestrator Agent.
Coordinates all 14 specialized agents, manages pipeline execution dependencies,
tracks workflow state, prevents duplicate extraction jobs, and handles task failures.
"""

import asyncio
from typing import Dict, Any, List, Optional
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger
from database.repository import get_db_repository


class MasterOrchestratorAgent:
    def __init__(self):
        self.name = "MasterOrchestratorAgent"
        workflow_state.register_agent(self.name, agent_type="CONTROLLER")
        self.db = get_db_repository()

    async def run_pipeline(
        self,
        source_name: str = "all",
        limit: int = 5,
        use_mock: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the full 14-agent pipeline across discovery, compliance, collection,
        extraction, classification, verification, deduplication, enrichment, and indexing.
        """
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task=f"Pipeline {source_name}")
        job_id = workflow_state.create_job(source_name, {"limit": limit, "use_mock": use_mock})
        logger.info(f"[{self.name}] Initiated pipeline job {job_id} for source '{source_name}'")

        try:
            # 1. Import agents dynamically to avoid circular dependencies
            from .discovery_agent import SourceDiscoveryAgent
            from .compliance_agent import SourceComplianceAgent
            from .collection_agent import WebCollectionAgent
            from .experience_extraction_agent import ExperienceExtractionAgent
            from .coding_extraction_agent import CodingProblemExtractionAgent
            from .classification_agent import QuestionClassificationAgent
            from .verification_agent import AuthenticityVerificationAgent
            from .deduplication_agent import DeduplicationAgent
            from .enrichment_agent import DataEnrichmentAgent
            from .database_agent import DatabaseManagementAgent
            from .semantic_search_agent import SemanticSearchAgent
            from .quality_agent import QualityAssuranceAgent
            from .monitoring_agent import MonitoringAnalyticsAgent

            # Instantiate agents
            discovery = SourceDiscoveryAgent()
            compliance = SourceComplianceAgent()
            collection = WebCollectionAgent()
            exp_extractor = ExperienceExtractionAgent()
            code_extractor = CodingProblemExtractionAgent()
            classifier = QuestionClassificationAgent()
            verifier = AuthenticityVerificationAgent()
            dedup = DeduplicationAgent()
            enricher = DataEnrichmentAgent()
            db_agent = DatabaseManagementAgent()
            search_agent = SemanticSearchAgent()
            qa_agent = QualityAssuranceAgent()
            monitor_agent = MonitoringAnalyticsAgent()

            # Step 1: Discover active sources
            active_sources = await discovery.discover_sources(target=source_name)
            logger.info(f"[{self.name}] Discovered {len(active_sources)} sources to process.")

            total_collected = 0
            total_extracted = 0
            total_indexed = 0
            total_duplicates = 0

            # Step 2: Iterate and process each permitted source
            for src in active_sources:
                # Step 3: Check compliance
                is_compliant, reason = await compliance.verify_compliance(src["url"], src["name"])
                if not is_compliant:
                    logger.warning(f"[{self.name}] Skipping {src['name']} due to compliance policy: {reason}")
                    continue

                # Step 4: Web Collection
                raw_documents = await collection.collect_content(src["collector_type"], limit=limit, use_mock=use_mock)
                total_collected += len(raw_documents)

                # Process each collected document through downstream agents
                for doc in raw_documents:
                    # Step 5: QA validation on raw doc
                    if not qa_agent.validate_raw_document(doc):
                        continue

                    # Step 6: Extract interview experience
                    extracted_exp = await exp_extractor.extract_experience(doc["raw_text"], doc["original_url"])
                    
                    # Step 7: Verify authenticity
                    verification = await verifier.verify_record(doc["raw_text"])

                    # Step 8: Enrich metadata
                    enriched_exp = enricher.enrich_experience(extracted_exp)

                    # Extract each question in experience with its round
                    q_items = extracted_exp.get("questions_with_rounds", [])
                    if not q_items:
                        default_r_name = extracted_exp.get("interview_round", "Round 1: Technical Assessment")
                        q_items = [(q, 1, default_r_name) for q in extracted_exp.get("questions", [])]

                    for item in q_items:
                        if isinstance(item, tuple) and len(item) == 3:
                            q_text, q_r_num, q_r_name = item
                        else:
                            q_text, q_r_num, q_r_name = item, 1, "Round 1: Technical Assessment"

                        if len(q_text.strip()) < 10:
                            continue

                        # Step 9: Extract coding problem if algorithmic
                        coding_data = await code_extractor.extract_coding_problem(q_text, doc["original_url"])

                        # Step 10: Classify topic and difficulty
                        classification = await classifier.classify_question(q_text)

                        # Step 11: Deduplication check
                        is_duplicate, original_id = dedup.check_duplicate(
                            enriched_exp["company_name"], q_text
                        )
                        if is_duplicate:
                            total_duplicates += 1
                            continue

                        # Step 12: Database storage
                        question_record, is_new = await db_agent.store_question(
                            company=enriched_exp["company_name"],
                            role=enriched_exp["job_role"],
                            question_text=q_text,
                            category=classification["category"],
                            difficulty=classification["difficulty"],
                            platform=doc["source_platform"],
                            url=doc["original_url"],
                            experience_level=enriched_exp.get("experience_level", "Mid"),
                            confidence=verification.get("confidence_score", 0.8),
                            coding_data=coding_data,
                            round_number=q_r_num,
                            interview_round=q_r_name,
                        )

                        if is_new:
                            total_extracted += 1
                            # Step 13: Semantic indexing
                            await search_agent.index_question(question_record.id, q_text)
                            total_indexed += 1

            # Step 14: Monitor execution metrics
            workflow_state.update_job_progress(
                job_id,
                collected=total_collected,
                extracted=total_extracted,
                indexed=total_indexed,
                duplicates=total_duplicates,
            )
            workflow_state.complete_job(job_id, status="COMPLETED")
            workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)

            summary = {
                "job_id": job_id,
                "status": "COMPLETED",
                "collected": total_collected,
                "extracted": total_extracted,
                "indexed": total_indexed,
                "duplicates": total_duplicates,
            }
            monitor_agent.record_pipeline_metrics(summary)
            logger.info(f"[{self.name}] Pipeline completed successfully: {summary}")
            return summary

        except Exception as e:
            logger.error(f"[{self.name}] Pipeline job {job_id} failed: {e}", exc_info=True)
            workflow_state.complete_job(job_id, status="FAILED", error=str(e))
            workflow_state.update_agent_status(self.name, AgentStatus.FAILED, failed=True)
            raise e

"""
Indexing Pipeline stage.
Generates embeddings and builds semantic vector search indices.
"""

from agents.semantic_search_agent import SemanticSearchAgent


class IndexingPipeline:
    def __init__(self):
        self.search_agent = SemanticSearchAgent()

    async def index_question(self, question_id: str, question_text: str):
        await self.search_agent.index_question(question_id, question_text)

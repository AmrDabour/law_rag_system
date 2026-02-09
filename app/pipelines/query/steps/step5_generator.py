"""
Step 5: Generator
Generate answer using Gemini LLM
"""

from typing import Any, Dict, List
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.query.models import RetrievedChunk
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class GeneratorStep(PipelineStep):
    """
    Step 5: Generate answer using Gemini LLM.
    
    Input: List[RetrievedChunk] - Top reranked chunks
    Output: str - Generated answer with article citations
    """
    
    def __init__(self):
        super().__init__("Answer Generator")
        self._llm = None
    
    @property
    def llm(self):
        """Lazy load LLM service"""
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm
    
    def process(self, data: List[RetrievedChunk], context: Dict[str, Any]) -> str:
        """
        Generate answer from retrieved chunks.
        
        Args:
            data: List of reranked chunks
            context: Pipeline context (must contain query)
            
        Returns:
            Generated answer string
        """
        if not data:
            return "لم أجد معلومات كافية للإجابة على سؤالك."
        
        query = context.get("original_query") or context.get("normalized_query", "")
        
        self.logger.info(f"Generating answer from {len(data)} chunks...")
        
        # Convert chunks to format expected by LLM service
        context_docs = [
            {
                "content": chunk.content,
                "article_number": chunk.article_number,
                "law_name": chunk.law_name,
                "page_number": chunk.page_number,
            }
            for chunk in data
        ]
        
        # Generate answer
        answer = self.llm.generate(
            query=query,
            context_docs=context_docs,
        )
        
        context["generated_answer"] = answer
        self.logger.info(f"Generated answer ({len(answer)} chars)")
        
        return answer
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        return all(isinstance(c, RetrievedChunk) for c in data)

"""
LLM Service
Google Gemini for answer generation
"""

from typing import List, Dict, Optional
import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Google Gemini LLM service.
    Generates human-readable answers from retrieved legal documents.
    
    Features:
    - Arabic-optimized system prompt
    - Article citation enforcement
    - Configurable temperature and token limits
    """
    
    # System prompt for legal assistant
    SYSTEM_PROMPT = """أنت مساعد قانوني متخصص في القوانين العربية.

مهمتك:
- الإجابة بلغة عربية بسيطة يفهمها غير المتخصصين
- الاستناد فقط إلى المواد القانونية المقدمة في السياق
- ذكر رقم المادة والقانون بوضوح في كل إجابة

قواعد صارمة يجب اتباعها:
1. يجب ذكر "مادة [رقم]" و"[اسم القانون]" لكل معلومة قانونية
2. إذا لم تجد إجابة في المواد المقدمة، قل "لم أجد معلومات كافية في المواد المتاحة"
3. لا تخترع أو تفترض معلومات قانونية غير موجودة في السياق
4. استخدم لغة سهلة ومباشرة
5. نظم الإجابة بشكل واضح باستخدام النقاط أو الأرقام عند الحاجة

تنسيق الإجابة:
- ابدأ بالإجابة المباشرة على السؤال
- اذكر المواد القانونية ذات الصلة
- أضف توضيحات إن لزم الأمر"""

    _instance: Optional['LLMService'] = None
    _client = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            LLMService._initialized = True
    
    def _initialize(self):
        """Initialize the Gemini client"""
        self.model_name = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
        logger.info(f"Initializing LLM service: {self.model_name}")
        
        try:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            
            logger.info(f"✅ LLM service initialized")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Temperature: {self.temperature}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM service: {e}")
            raise
    
    @property
    def client(self):
        """Get the client instance"""
        if self._client is None:
            self._initialize()
        return self._client
    
    def generate(
        self,
        query: str,
        context_docs: List[Dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate answer from query and context documents.
        
        Args:
            query: User question
            context_docs: Retrieved documents with content, article_number, law_name
            system_prompt: Override system prompt
            
        Returns:
            Generated answer text
        """
        # Format context with article citations
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            article_num = doc.get("article_number", "؟")
            law_name = doc.get("law_name", "القانون")
            content = doc.get("content", "")
            
            context_parts.append(
                f"[{i}] {law_name} - مادة {article_num}:\n{content}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Build prompt
        prompt = f"""السؤال: {query}

المواد القانونية المتاحة:

{context}

---

أجب على السؤال بناءً على المواد المقدمة فقط. اذكر رقم المادة واسم القانون لكل معلومة."""

        # Generate response
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt or self.SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        
        return response.text
    
    def generate_simple(self, prompt: str) -> str:
        """
        Generate response for a simple prompt (without context).
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text
        """
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        
        return response.text
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


# Singleton getter
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

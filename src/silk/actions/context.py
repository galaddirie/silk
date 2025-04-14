import logging
from typing import Any, Dict, Optional

from expression import Error, Ok, Result
from fp_ops import BaseContext


from silk.browsers.manager import BrowserManager

from pydantic import Field


logger = logging.getLogger(__name__)

class ActionContext(BaseContext):
    """
    Action context for action execution containing references to browser context and page
    instead of direct driver references.
    """

    # Use Any instead of forward references to avoid Pydantic issues
    browser_manager: Optional[BrowserManager] = Field(default=None)
    context_id: Optional[str] = Field(default=None)
    page_id: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=0)
    retry_delay_ms: int = Field(default=0)
    timeout_ms: int = Field(default=0)
    parent_context: Any = Field(default=None)  # Use Any instead of forward ref
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Explicitly set model_config for Pydantic v2
    model_config = {
        "arbitrary_types_allowed": True,
    }

    async def get_page(self) -> Result[Any, Exception]:
        """Get the browser page for this context"""
        if not self.browser_manager or not self.context_id or not self.page_id:
            return Error(
                Exception(
                    "ActionContext missing required browser_manager, context_id, or page_id"
                )
            )

        context_result = self.browser_manager.get_context(self.context_id)
        if context_result.is_error():
            return Error(context_result.error)

        context = context_result.default_value(None)
        if not context:
            return Error(Exception("No context found"))

        return context.get_page(self.page_id)

    async def get_context(self) -> Result[Any, Exception]:
        """Get the underlying context"""
        if not self.browser_manager or not self.context_id:
            return Error(Exception("No context found"))

        context_result = self.browser_manager.get_context(self.context_id)
        if context_result.is_error():
            return Error(context_result.error)

        context = context_result.default_value(None)
        if not context:
            return Error(Exception("No context found"))

        return Ok(context)

    async def get_driver(self) -> Result[Any, Exception]:
        """Get the underlying driver (for specific use cases only)"""
        if not self.browser_manager or not self.context_id:
            return Error(
                Exception(
                    "ActionContext missing required browser_manager or context_id"
                )
            )

        driver = self.browser_manager.drivers.get(self.context_id)
        if not driver:
            return Error(Exception(f"No driver found for context ID {self.context_id}"))

        return Ok(driver)

    def derive(self, **kwargs: Any) -> "ActionContext":
        """Create a new context derived from this one with some values changed"""
        # Create a new context with all the fields from this one
        new_context = ActionContext(
            browser_manager=kwargs.get("browser_manager", self.browser_manager),
            context_id=kwargs.get("context_id", self.context_id),
            page_id=kwargs.get("page_id", self.page_id),
            retry_count=kwargs.get("retry_count", self.retry_count),
            max_retries=kwargs.get("max_retries", self.max_retries),
            retry_delay_ms=kwargs.get("retry_delay_ms", self.retry_delay_ms),
            timeout_ms=kwargs.get("timeout_ms", self.timeout_ms),
            parent_context=kwargs.get("parent_context", self),
        )
        
        # Handle metadata merging
        combined_metadata = dict(self.metadata)
        if "metadata" in kwargs:
            combined_metadata.update(kwargs["metadata"])
        new_context.metadata = combined_metadata
        
        return new_context
    
    

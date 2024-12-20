from datetime import datetime, timedelta
from typing import List, Optional, Union

from langchain_core.messages import BaseMessage
from vertexai.preview import caching  # type: ignore

from langchain_google_vertexai._utils import (
    _format_model_name,
    is_gemini_advanced,
)
from langchain_google_vertexai.chat_models import (
    ChatVertexAI,
    _parse_chat_history_gemini,
)
from langchain_google_vertexai.functions_utils import (
    _format_to_gapic_tool,
    _format_tool_config,
    _ToolConfigDict,
    _ToolsType,
)
from langchain_google_vertexai.llms import VertexAI


def create_context_cache(
    model: Union[ChatVertexAI, VertexAI],
    messages: List[BaseMessage],
    expire_time: Optional[datetime] = None,
    time_to_live: Optional[timedelta] = None,
    tools: Optional[_ToolsType] = None,
    tool_config: Optional[_ToolConfigDict] = None,
) -> str:
    """Creates a cache for content in some model.

    Args:
        model: ChatVertexAI model. Must be at least gemini-1.5 pro or flash.
        messages: List of messages to cache.
        expire_time:  Timestamp of when this resource is considered expired.
        At most one of expire_time and ttl can be set. If neither is set, default TTL
            on the API side will be used (currently 1 hour).
        time_to_live:  The TTL for this resource. If provided, the expiration time is
        computed: created_time + TTL.
        At most one of expire_time and ttl can be set. If neither is set, default TTL
            on the API side will be used (currently 1 hour).
        tools:  A list of tool definitions to bind to this chat model.
            Can be a pydantic model, callable, or BaseTool. Pydantic
            models, callables, and BaseTools will be automatically converted to
            their schema dictionary representation.
        tool_config: Optional. Immutable. Tool config. This config is shared for all
            tools.

    Raises:
        ValueError: If model doesn't support context catching.

    Returns:
        String with the identificator of the created cache.
    """
    model_name = _format_model_name(
        model=model.model_name,
        project=model.project,  # type: ignore[arg-type]
        location=model.location,
    )
    if not is_gemini_advanced(model.model_family):  # type: ignore[arg-type]
        error_msg = f"Model {model_name} doesn't support context catching"
        raise ValueError(error_msg)

    system_instruction, contents = _parse_chat_history_gemini(messages, model.project)

    if tool_config:
        tool_config = _format_tool_config(tool_config)

    if tools is not None:
        tools = [_format_to_gapic_tool(tools)]

    cached_content = caching.CachedContent.create(
        model_name=model_name,
        system_instruction=system_instruction,
        contents=contents,
        ttl=time_to_live,
        expire_time=expire_time,
        tool_config=tool_config,
        tools=tools,
    )

    return cached_content.name

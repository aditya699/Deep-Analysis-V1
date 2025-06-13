from typing import Any, Optional
from app.deep_analysis.schemas import FileIDResponse

async def extract_file_id_from_response(response: Any, openai_client) -> Optional[str]:
    """
    Extract file ID from OpenAI response using multiple approaches.
    Returns the file ID if found, None otherwise.
    """
    # Approach 1: Check message outputs with content and annotations
    for output in response.output:
        if hasattr(output, 'content') and output.content:
            for content in output.content:
                if hasattr(content, 'annotations') and content.annotations:
                    for annotation in content.annotations:
                        if (hasattr(annotation, 'type') and 
                            annotation.type == 'container_file_citation' and
                            hasattr(annotation, 'file_id')):
                            return annotation.file_id

        # Approach 2: Check code interpreter tool calls
        elif hasattr(output, 'type') and output.type == 'code_interpreter_call':
            if hasattr(output, 'outputs') and output.outputs:
                for tool_output in output.outputs:
                    if (hasattr(tool_output, 'type') and 
                        tool_output.type == 'image' and
                        hasattr(tool_output, 'image') and
                        hasattr(tool_output.image, 'file_id')):
                        return tool_output.image.file_id

        # Approach 3: Check ResponseCodeInterpreterToolCall structure
        elif hasattr(output, '__class__') and 'CodeInterpreter' in str(output.__class__):
            if hasattr(output, 'results') and output.results:
                for result in output.results:
                    if hasattr(result, 'type') and result.type == 'image':
                        if hasattr(result, 'image') and hasattr(result.image, 'file_id'):
                            return result.image.file_id

    # Approach 4: Use LLM to extract file ID if other approaches fail
    try:
        prompt = f"""
        Look for file IDs in this OpenAI response. File IDs start with "file-" followed by alphanumeric characters.
        Extract ONLY the file_id string (example: "file-abc123xyz789").

        Response: {str(response)}

        Return the file_id if found, or null if no file_id exists.
        """
        
        llm_response = await openai_client.responses.parse(
            model="gpt-4.1-mini",
            input=prompt,
            text_format=FileIDResponse,
            timeout=300
        )
        
        return llm_response.output_parsed.file_id
    except Exception:
        return None

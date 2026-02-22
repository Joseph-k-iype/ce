"""
Executor Utilities
===================
Shared helpers for agent executors.
"""

import json
import re


def parse_json_response(response: str) -> dict | None:
    """Parse JSON from LLM response, handling markdown code blocks."""
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        start = json_str.find('{')
        end = json_str.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(json_str[start:end])
            except json.JSONDecodeError:
                pass
    return None

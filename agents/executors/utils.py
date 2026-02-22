"""
Executor Utilities
===================
Shared helpers for agent executors.
"""

import json
import re
from enum import Enum
from typing import Dict, List, Optional


class FailureCategory(str, Enum):
    """Categories of agent failures for circuit breaker decisions."""
    TRANSIENT = "transient"  # network, timeout, rate limit — worth retrying
    AUTH = "auth"            # authentication/authorization errors
    LOGIC = "logic"          # LLM produced invalid reasoning/output
    PARSE = "parse"          # JSON parse failure from LLM response
    DB = "db"                # database/graph execution error


# Max retries per failure category before circuit breaker trips
FAILURE_RETRY_LIMITS: Dict[str, int] = {
    FailureCategory.TRANSIENT: 5,
    FailureCategory.AUTH: 2,
    FailureCategory.LOGIC: 3,
    FailureCategory.PARSE: 3,
    FailureCategory.DB: 3,
}


def classify_failure(error: str) -> FailureCategory:
    """Classify an error string into a failure category."""
    error_lower = error.lower()

    # Auth patterns
    if any(kw in error_lower for kw in ("401", "403", "auth", "token", "unauthorized", "forbidden")):
        return FailureCategory.AUTH

    # Transient patterns
    if any(kw in error_lower for kw in (
        "timeout", "rate limit", "429", "503", "502", "504",
        "connection", "network", "retry", "temporary", "unavailable",
    )):
        return FailureCategory.TRANSIENT

    # DB patterns
    if any(kw in error_lower for kw in (
        "falkordb", "graph", "cypher", "query failed", "redis", "database",
        "syntax error", "unknown function", "type mismatch",
    )):
        return FailureCategory.DB

    # Parse patterns
    if any(kw in error_lower for kw in ("parse", "json", "decode", "unexpected token", "malformed")):
        return FailureCategory.PARSE

    # Default to logic error
    return FailureCategory.LOGIC


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


def sanitize_query_params(raw_params: dict) -> dict:
    """Sanitize LLM-generated query_params keys for FalkorDB compatibility.

    LLMs sometimes produce keys with embedded quotes or $ prefixes, e.g.:
        '"rule_id"', '$rule_id', '$"rule_id"', "'rule_id'"
    FalkorDB expects clean keys like 'rule_id' to match $rule_id in queries.
    """
    if not raw_params or not isinstance(raw_params, dict):
        return {}
    sanitized = {}
    for k, v in raw_params.items():
        if not isinstance(k, str):
            k = str(k)
        # Strip whitespace, then iteratively strip all outer quotes and $ signs
        clean = k.strip()
        prev = None
        while clean != prev:
            prev = clean
            clean = clean.strip('"').strip("'").strip()
            clean = clean.lstrip('$').strip()
        if clean:
            sanitized[clean] = v
    return sanitized

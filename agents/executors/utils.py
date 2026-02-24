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

    # Auth patterns — use precise tokens only.
    # NEVER use bare "auth" here: it substring-matches "authorities", "data_categorisation",
    # "authorized" fields in validation error messages, causing LOGIC failures to be
    # misclassified as AUTH (which has only 2 retries vs 3 for LOGIC).
    auth_exact_tokens = ("401", "403")
    auth_phrases = (
        "unauthorized", "forbidden", "authentication failed", "authentication error",
        "api key invalid", "api key expired", "invalid token", "token expired",
        "token invalid", "access denied", "permission denied", "not authorized",
    )
    if any(kw in error_lower for kw in auth_exact_tokens) or any(
        phrase in error_lower for phrase in auth_phrases
    ):
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
    """Parse JSON from LLM response with multi-strategy extraction.

    Strategies (in order):
    1. Extract from markdown code block (```json ... ``` or ``` ... ```)
    2. Direct parse of full response
    3. Extract between outermost { } braces
    4. Strip trailing non-JSON text after the last closing brace
    5. Remove JavaScript-style comments (// ...) and trailing commas
    """
    if not response or not isinstance(response, str):
        return None

    # Strategy 1: Extract from markdown code block
    code_block_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', response)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
    else:
        json_str = response.strip()

    # Strategy 2: Direct parse
    try:
        result = json.loads(json_str)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 3: Extract between outermost { }
    start = json_str.find('{')
    end = json_str.rfind('}') + 1
    if start != -1 and end > start:
        candidate = json_str[start:end]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Strategy 4: Remove JS-style line comments and trailing commas, then retry
        cleaned = re.sub(r'//[^\n]*', '', candidate)          # strip // comments
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)       # remove trailing commas
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)    # strip control chars
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 5: Find deepest valid JSON object by scanning from back
    # Handles truncated responses by finding the last complete object
    text = json_str[start:] if start != -1 else json_str
    depth = 0
    last_valid_end = -1
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    last_valid_end = i + 1
                    break

    if last_valid_end > 0:
        try:
            result = json.loads(text[:last_valid_end])
            if isinstance(result, dict):
                return result
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

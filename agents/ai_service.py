"""
AI Service
==========
Handles authentication and communication with the LLM API.
Manages JWT token generation and automatic refresh.
"""

import logging
import time
from typing import Optional, List, Dict
from dataclasses import dataclass
import requests
from threading import Lock

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """JWT Token information"""
    token: str
    issued_at: float
    expires_at: float  # Estimated expiration time

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with buffer)"""
        return time.time() >= self.expires_at - settings.ai.token_expiry_buffer_seconds


class AIAuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AIRequestError(Exception):
    """Raised when AI request fails"""
    pass


class AIService:
    """
    AI Service for LLM interactions.

    Handles:
    - JWT token generation and refresh
    - LLM API calls (without temperature/max_tokens - uses API defaults)
    - Message formatting
    """

    _instance: Optional['AIService'] = None
    _token: Optional[TokenInfo] = None
    _token_lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._token_api_url = settings.ai.token_api_url
        self._llm_api_url = settings.ai.llm_api_url
        self._username = settings.ai.token_username
        self._password = settings.ai.token_password
        self._model = settings.ai.llm_model
        self._use_case_id = settings.ai.llm_use_case_id
        self._enabled = settings.ai.enable_ai_rule_generation

        self._initialized = True
        logger.info(f"AI Service initialized (enabled={self._enabled})")

    @property
    def is_enabled(self) -> bool:
        """Check if AI service is enabled"""
        return self._enabled

    def _get_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid JWT token, refreshing if necessary.

        Args:
            force_refresh: Force token refresh even if current is valid

        Returns:
            Valid JWT token string

        Raises:
            AIAuthenticationError: If authentication fails
        """
        with self._token_lock:
            # Check if we have a valid token
            if not force_refresh and self._token and not self._token.is_expired:
                return self._token.token

            # Need to get a new token
            logger.info("Requesting new JWT token")

            try:
                response = requests.post(
                    self._token_api_url,
                    json={
                        "input_token_state": {
                            "token_type": "CREDENTIAL",
                            "username": self._username,
                            "password": self._password
                        },
                        "output_token_state": {
                            "token_type": "JWT"
                        }
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code != 200:
                    raise AIAuthenticationError(
                        f"Token request failed with status {response.status_code}: {response.text}"
                    )

                data = response.json()
                token = data.get("issued_token")

                if not token:
                    raise AIAuthenticationError(
                        f"No token in response: {data}"
                    )

                # Store token with estimated expiration (assume 1 hour validity)
                self._token = TokenInfo(
                    token=token,
                    issued_at=time.time(),
                    expires_at=time.time() + 3600  # 1 hour default
                )

                logger.info("Successfully obtained new JWT token")
                return self._token.token

            except requests.RequestException as e:
                raise AIAuthenticationError(f"Token request failed: {e}")

    def call_llm(
        self,
        messages: List[Dict[str, str]],
        retry_on_auth_error: bool = True
    ) -> str:
        """
        Call the LLM API with the given messages.
        Uses API default settings (no temperature/max_tokens override).

        Args:
            messages: List of message dicts with 'role' and 'content'
            retry_on_auth_error: Whether to retry with fresh token on auth error

        Returns:
            LLM response text

        Raises:
            AIRequestError: If request fails
            AIAuthenticationError: If authentication fails after retry
        """
        if not self._enabled:
            raise AIRequestError("AI service is not enabled")

        token = self._get_token()

        try:
            response = requests.post(
                self._llm_api_url,
                json={
                    "model": self._model,
                    "messages": messages,
                    "user": self._use_case_id
                },
                headers={
                    "Content-Type": "application/json",
                    "Token_Type": settings.ai.auth_token_type,
                    settings.ai.auth_header_name: token,
                    settings.ai.correlation_id_header: self._username,
                    settings.ai.session_id_header: self._username,
                },
                timeout=120  # LLM calls can take a while
            )

            if response.status_code == 401 and retry_on_auth_error:
                # Token might be expired, try with fresh token
                logger.warning("Got 401, refreshing token and retrying")
                token = self._get_token(force_refresh=True)
                response = requests.post(
                    self._llm_api_url,
                    json={
                        "model": self._model,
                        "messages": messages,
                        "user": self._use_case_id
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Token_Type": settings.ai.auth_token_type,
                        settings.ai.auth_header_name: token,
                        settings.ai.correlation_id_header: self._username,
                        settings.ai.session_id_header: self._username,
                    },
                    timeout=120
                )

            if response.status_code != 200:
                raise AIRequestError(
                    f"LLM request failed with status {response.status_code}: {response.text}"
                )

            data = response.json()

            # Extract response content (OpenAI format)
            choices = data.get("choices", [])
            if not choices:
                raise AIRequestError(f"No choices in response: {data}")

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise AIRequestError(f"No content in response: {data}")

            return content

        except requests.RequestException as e:
            raise AIRequestError(f"LLM request failed: {e}")

    def chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        Simple chat interface for single-turn conversations.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_message})

        return self.call_llm(messages)

    def check_availability(self) -> bool:
        """
        Check if the AI service is available.

        Returns:
            True if service is available and authenticated
        """
        if not self._enabled:
            return False

        try:
            self._get_token()
            return True
        except AIAuthenticationError:
            return False


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get the AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

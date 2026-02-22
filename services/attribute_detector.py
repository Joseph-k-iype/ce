"""
Attribute Detection Service
===========================
Detects specific data attributes (health, financial, biometric, etc.)
from metadata using token-based matching, patterns, and configurations.

Production-grade detection:
- Token-based matching (not substring) to avoid false positives
- Stop word filtering to skip common words
- Multi-word phrase matching for compound terms
- Minimum keyword length to avoid noise
- Configurable confidence thresholds
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Set, FrozenSet
from pathlib import Path
from dataclasses import dataclass

from config.settings import settings

logger = logging.getLogger(__name__)

# Common English stop words that should never trigger a match on their own
STOP_WORDS: FrozenSet[str] = frozenset({
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'must',
    'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'how',
    'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
    'it', 'its', 'i', 'we', 'you', 'he', 'she', 'they', 'me', 'us',
    'him', 'her', 'them', 'my', 'our', 'your', 'his', 'their',
    'not', 'no', 'nor', 'so', 'too', 'very', 'just', 'also',
    'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from',
    'up', 'out', 'off', 'over', 'under', 'between', 'through', 'about',
    'into', 'during', 'before', 'after', 'above', 'below',
    'all', 'any', 'each', 'every', 'both', 'few', 'more', 'most',
    'other', 'some', 'such', 'only', 'own', 'same',
    'data', 'transfer', 'sharing', 'processing', 'storage', 'use',
    'information', 'system', 'service', 'type', 'name', 'value',
    'country', 'countries', 'rule', 'rules', 'policy', 'policies',
    'true', 'false', 'null', 'none', 'yes', 'no',
})

# Minimum length for a keyword to be considered valid for matching
MIN_KEYWORD_LENGTH = 3


@dataclass
class DetectionResult:
    """Result of attribute detection"""
    detected: bool
    attribute_name: str
    detection_method: str  # keyword, pattern, category
    matched_terms: List[str]
    confidence: float


class AttributeDetectionConfig:
    """Configuration for detecting a specific attribute type"""

    def __init__(
        self,
        name: str,
        keywords: List[str] = None,
        patterns: List[str] = None,
        categories: List[str] = None,
        case_sensitive: bool = False,
        word_boundaries: bool = True,
        enabled: bool = True
    ):
        self.name = name
        self.case_sensitive = case_sensitive
        self.word_boundaries = word_boundaries
        self.enabled = enabled

        # Separate single-word keywords from multi-word phrases
        raw_keywords = [k.lower() if not case_sensitive else k for k in (keywords or [])]
        self.single_keywords: Set[str] = set()
        self.phrase_keywords: List[List[str]] = []

        for kw in raw_keywords:
            # Skip stop words and too-short keywords
            kw_clean = kw.strip()
            if not kw_clean:
                continue

            parts = kw_clean.replace('_', ' ').replace('-', ' ').split()
            # Filter out stop words from single-word entries
            non_stop_parts = [p for p in parts if p.lower() not in STOP_WORDS and len(p) >= MIN_KEYWORD_LENGTH]

            if len(parts) > 1:
                # Multi-word phrase: store as phrase for ordered matching
                if non_stop_parts:  # At least one meaningful word
                    self.phrase_keywords.append([p.lower() for p in parts])
            elif non_stop_parts:
                # Single word that's not a stop word and meets min length
                self.single_keywords.add(kw_clean.lower())

        self.patterns = [re.compile(p, re.IGNORECASE if not case_sensitive else 0) for p in (patterns or [])]
        self.categories = set(c.lower() for c in (categories or []))


class AttributeDetector:
    """
    Detects attributes from metadata using configurable rules.
    Supports keyword matching, regex patterns, and category lookups.
    """

    _instance: Optional['AttributeDetector'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._configs: Dict[str, AttributeDetectionConfig] = {}
        self._load_config_files()
        self._initialized = True
        logger.info(f"Attribute detector initialized with {len(self._configs)} configurations")

    def _load_config_files(self):
        """Load configuration files from the config directory"""
        config_dir = settings.paths.config_dir

        # Try to load health_data_config.json - this extends the default health_data config
        health_config_path = config_dir / 'health_data_config.json'
        if health_config_path.exists():
            try:
                with open(health_config_path, 'r') as f:
                    config = json.load(f)

                    # Check if config is enabled
                    if not config.get('enabled', True):
                        logger.info("Health data config is disabled")
                    else:
                        # Create or update health_data config from file
                        keywords = config.get('keywords', [])
                        patterns = config.get('patterns', [])
                        categories = config.get('categories', [])

                        # If we already have a default config, merge with it
                        if 'health_data' in self._configs:
                            existing = self._configs['health_data']
                            # Re-create by merging new keywords into a fresh config
                            merged_kw = list(existing.single_keywords) + [' '.join(p) for p in existing.phrase_keywords]
                            merged_kw.extend(k.lower() for k in keywords)
                            merged_config = AttributeDetectionConfig(
                                name='health_data',
                                keywords=merged_kw,
                                patterns=[p.pattern for p in existing.patterns] + patterns,
                                categories=list(existing.categories) + categories,
                                case_sensitive=existing.case_sensitive,
                                word_boundaries=existing.word_boundaries,
                                enabled=True,
                            )
                            self._configs['health_data'] = merged_config
                        else:
                            # Create new config from file
                            self._configs['health_data'] = AttributeDetectionConfig(
                                name='health_data',
                                keywords=keywords,
                                patterns=patterns,
                                categories=categories,
                                case_sensitive=config.get('detection_settings', {}).get('case_sensitive', False),
                                word_boundaries=config.get('detection_settings', {}).get('word_boundaries', True),
                                enabled=True
                            )

                logger.info(f"Loaded health data config from {health_config_path}")
            except Exception as e:
                logger.error(f"Error loading health_data_config.json: {e}")

        # Load generic metadata detection config
        metadata_config_path = config_dir / 'metadata_detection_config.json'
        if metadata_config_path.exists():
            try:
                with open(metadata_config_path, 'r') as f:
                    config = json.load(f)
                    for category_name, category_config in config.get('detection_categories', {}).items():
                        if category_config.get('enabled', True):
                            self._configs[category_name] = AttributeDetectionConfig(
                                name=category_name,
                                keywords=category_config.get('keywords', []),
                                patterns=category_config.get('patterns', []),
                                categories=category_config.get('categories', []),
                                case_sensitive=category_config.get('case_sensitive', False),
                                word_boundaries=category_config.get('word_boundaries', True),
                                enabled=True
                            )
                logger.info(f"Loaded metadata detection config from {metadata_config_path}")
            except Exception as e:
                logger.error(f"Error loading metadata_detection_config.json: {e}")

    def add_config(self, config: AttributeDetectionConfig):
        """Add or update an attribute detection configuration"""
        self._configs[config.name] = config
        logger.info(f"Added/updated attribute detection config: {config.name}")

    def detect(
        self,
        metadata: Dict[str, Any],
        attribute_name: Optional[str] = None
    ) -> List[DetectionResult]:
        """
        Detect attributes in the provided metadata.

        Args:
            metadata: Dictionary of metadata to check
            attribute_name: Specific attribute to detect (None = check all)

        Returns:
            List of DetectionResult for each detected attribute
        """
        results = []

        configs_to_check = (
            {attribute_name: self._configs[attribute_name]}
            if attribute_name and attribute_name in self._configs
            else self._configs
        )

        # Convert metadata to searchable text
        search_text = self._metadata_to_text(metadata)
        search_text_lower = search_text.lower()

        for name, config in configs_to_check.items():
            if not config.enabled:
                continue

            result = self._detect_single(search_text, search_text_lower, config)
            if result.detected:
                results.append(result)

        return results

    def _detect_single(
        self,
        text: str,
        text_lower: str,
        config: AttributeDetectionConfig
    ) -> DetectionResult:
        """
        Detect a single attribute type using token-based matching.

        Uses word-boundary matching to avoid false positives from substrings.
        E.g., 'health' won't match inside 'healthcare' unless 'healthcare' is
        also a keyword. Multi-word phrases are matched as contiguous sequences.
        """
        matched_terms: Set[str] = set()
        detection_method = None

        # Tokenize text into words for token-based matching
        # Split on whitespace, underscores, hyphens, commas, colons, etc.
        tokens = re.findall(r'[a-zA-Z0-9]+', text_lower)
        token_set = set(tokens)

        # Also build compound tokens (underscore/hyphen joined pairs from original)
        # This catches "health_data", "credit_card" etc. in structured metadata keys
        compound_tokens = set()
        compound_parts = re.findall(r'[a-zA-Z0-9]+(?:[_\-][a-zA-Z0-9]+)+', text_lower)
        for compound in compound_parts:
            compound_tokens.add(compound.replace('-', '_'))

        # 1. Single keyword matching — exact token match
        for keyword in config.single_keywords:
            kw_normalized = keyword.replace('-', '_').replace(' ', '_')

            # Check compound tokens first (e.g. "health_data" matches "health_data")
            if kw_normalized in compound_tokens:
                matched_terms.add(keyword)
                detection_method = 'keyword'
                continue

            # Check single token match (e.g. "diagnosis" matches token "diagnosis")
            if keyword in token_set:
                matched_terms.add(keyword)
                detection_method = 'keyword'

        # 2. Phrase matching — check if phrase words appear contiguously
        for phrase_parts in config.phrase_keywords:
            phrase_len = len(phrase_parts)
            if phrase_len == 0:
                continue

            # Check if all phrase words appear as contiguous tokens
            for i in range(len(tokens) - phrase_len + 1):
                window = tokens[i:i + phrase_len]
                if all(window[j] == phrase_parts[j] for j in range(phrase_len)):
                    matched_terms.add(' '.join(phrase_parts))
                    detection_method = detection_method or 'keyword'
                    break

            # Also check compound tokens for underscore-joined phrases
            compound_form = '_'.join(phrase_parts)
            if compound_form in compound_tokens:
                matched_terms.add(' '.join(phrase_parts))
                detection_method = detection_method or 'keyword'

        # 3. Pattern matching (regex)
        for pattern in config.patterns:
            matches = pattern.findall(text)
            if matches:
                matched_terms.update(str(m) for m in matches[:5])
                detection_method = detection_method or 'pattern'

        # Calculate confidence: require at least 2 distinct keyword matches
        # for high confidence, 1 match = low confidence
        n_matches = len(matched_terms)
        if n_matches >= 3:
            confidence = min(1.0, 0.7 + (n_matches - 3) * 0.1)
        elif n_matches == 2:
            confidence = 0.5
        elif n_matches == 1:
            confidence = 0.3
        else:
            confidence = 0.0

        # Only consider detected if confidence meets threshold
        detected = confidence >= 0.3 and n_matches >= 1

        return DetectionResult(
            detected=detected,
            attribute_name=config.name,
            detection_method=detection_method or 'none',
            matched_terms=list(matched_terms)[:10],
            confidence=confidence
        )

    def _metadata_to_text(self, metadata: Dict[str, Any]) -> str:
        """Convert metadata dictionary to searchable text"""
        parts = []

        def extract(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    extract(v, f"{prefix}{k} ")
            elif isinstance(obj, list):
                for item in obj:
                    extract(item, prefix)
            elif obj is not None:
                parts.append(f"{prefix}{str(obj)}")

        extract(metadata)
        return ' '.join(parts)

    def detect_health_data(self, metadata: Dict[str, Any]) -> DetectionResult:
        """Convenience method to detect health data specifically"""
        results = self.detect(metadata, 'health_data')
        if results:
            return results[0]
        return DetectionResult(
            detected=False,
            attribute_name='health_data',
            detection_method='none',
            matched_terms=[],
            confidence=0.0
        )

    def detect_financial_data(self, metadata: Dict[str, Any]) -> DetectionResult:
        """Convenience method to detect financial data specifically"""
        results = self.detect(metadata, 'financial_data')
        if results:
            return results[0]
        return DetectionResult(
            detected=False,
            attribute_name='financial_data',
            detection_method='none',
            matched_terms=[],
            confidence=0.0
        )

    def get_supported_attributes(self) -> List[str]:
        """Get list of supported attribute types"""
        return [name for name, config in self._configs.items() if config.enabled]


# Singleton instance
_detector: Optional[AttributeDetector] = None


def get_attribute_detector() -> AttributeDetector:
    """Get the attribute detector instance"""
    global _detector
    if _detector is None:
        _detector = AttributeDetector()
    return _detector

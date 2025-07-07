#!/usr/bin/env python3
"""Parameter extractor for matching user requests to templates using NLP."""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IntentPattern:
    """Pattern for matching user intent to templates."""
    template_name: str
    keywords: List[str]
    required_entities: List[str]
    optional_entities: List[str]
    patterns: List[str]
    confidence_boost: float = 0.0


@dataclass
class ExtractedEntity:
    """Extracted entity from user input."""
    name: str
    value: str
    confidence: float
    position: Tuple[int, int]  # start, end positions


@dataclass
class ParameterExtractionResult:
    """Result of parameter extraction."""
    template_match: Optional[str]
    confidence: float
    extracted_parameters: Dict[str, Any]
    missing_required: List[str]
    entities: List[ExtractedEntity]
    fallback_reason: Optional[str] = None


class ParameterExtractor:
    """Extract parameters from user requests and match to templates."""
    
    def __init__(self):
        self.intent_patterns = self._initialize_patterns()
        self.entity_extractors = self._initialize_extractors()
        
    def _initialize_patterns(self) -> Dict[str, IntentPattern]:
        """Initialize intent patterns for each template."""
        return {
            "gmail_monitor": IntentPattern(
                template_name="gmail_monitor",
                keywords=[
                    "gmail", "email", "inbox", "monitor", "watch", "check",
                    "mail", "messages", "notification", "alert"
                ],
                required_entities=["email_filter"],
                optional_entities=["sender_filter", "subject_filter", "check_interval", "alert_webhook"],
                patterns=[
                    r"monitor.*gmail.*from\s+(\S+)",
                    r"watch.*email.*from\s+(\S+)",
                    r"alert.*when.*email.*from\s+(\S+)",
                    r"check.*gmail.*for\s+(.+)",
                    r"notify.*me.*when.*(\S+).*emails"
                ],
                confidence_boost=0.1
            ),
            
            "slack_notifier": IntentPattern(
                template_name="slack_notifier",
                keywords=[
                    "slack", "notify", "message", "send", "alert", "notification",
                    "channel", "chat", "post", "webhook"
                ],
                required_entities=["channel"],
                optional_entities=["slack_token", "username", "icon_emoji", "webhook_url"],
                patterns=[
                    r"send.*slack.*to\s+([#@]\w+)",
                    r"notify.*slack.*channel\s+([#@]\w+)",
                    r"post.*to\s+([#@]\w+)",
                    r"slack.*notification.*([#@]\w+)",
                    r"alert.*slack.*([#@]\w+)"
                ],
                confidence_boost=0.1
            ),
            
            "web_scraper": IntentPattern(
                template_name="web_scraper",
                keywords=[
                    "scrape", "crawl", "website", "web", "extract", "monitor",
                    "url", "site", "page", "data", "content"
                ],
                required_entities=["target_url"],
                optional_entities=["scrape_interval", "css_selectors", "xpath_selectors"],
                patterns=[
                    r"scrape\s+(https?://\S+)",
                    r"monitor\s+(https?://\S+)",
                    r"extract.*from\s+(https?://\S+)",
                    r"crawl\s+(https?://\S+)",
                    r"watch\s+(https?://\S+)"
                ],
                confidence_boost=0.1
            ),
            
            "file_processor": IntentPattern(
                template_name="file_processor",
                keywords=[
                    "file", "files", "process", "copy", "move", "compress",
                    "backup", "organize", "folder", "directory", "transform"
                ],
                required_entities=["input_path", "operation"],
                optional_entities=["output_path", "file_pattern", "transformation_rules"],
                patterns=[
                    r"(copy|move|compress|backup)\s+files?\s+from\s+(.+?)\s+to\s+(.+)",
                    r"(process|organize)\s+files?\s+in\s+(.+)",
                    r"(backup|compress)\s+(.+)",
                    r"(copy|move)\s+(.+?)\s+to\s+(.+)"
                ],
                confidence_boost=0.1
            ),
            
            "data_analyzer": IntentPattern(
                template_name="data_analyzer",
                keywords=[
                    "analyze", "analysis", "data", "statistics", "stats",
                    "report", "insights", "trends", "patterns", "anomaly"
                ],
                required_entities=["data_source", "analysis_type"],
                optional_entities=["metrics", "chart_types", "export_format"],
                patterns=[
                    r"analyze\s+data\s+from\s+(.+)",
                    r"generate\s+(statistics|stats|report)\s+for\s+(.+)",
                    r"find\s+(trends|patterns|anomalies)\s+in\s+(.+)",
                    r"(analyze|process)\s+(.+?)\s+data"
                ],
                confidence_boost=0.1
            )
        }
    
    def _initialize_extractors(self) -> Dict[str, callable]:
        """Initialize entity extraction functions."""
        return {
            "email_filter": self._extract_email_filter,
            "sender_filter": self._extract_email_address,
            "subject_filter": self._extract_subject_filter,
            "channel": self._extract_slack_channel,
            "target_url": self._extract_url,
            "input_path": self._extract_file_path,
            "output_path": self._extract_file_path,
            "operation": self._extract_operation,
            "data_source": self._extract_data_source,
            "analysis_type": self._extract_analysis_type,
            "check_interval": self._extract_time_interval,
            "scrape_interval": self._extract_time_interval
        }
    
    def _extract_email_filter(self, text: str) -> List[ExtractedEntity]:
        """Extract email filter patterns."""
        entities = []
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                name="email_filter",
                value=f"from:{match.group()}",
                confidence=0.9,
                position=(match.start(), match.end())
            ))
        
        # Domain patterns
        domain_pattern = r'from\s+(\S+\.\w+)'
        for match in re.finditer(domain_pattern, text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                name="email_filter",
                value=f"from:{match.group(1)}",
                confidence=0.8,
                position=(match.start(1), match.end(1))
            ))
        
        return entities
    
    def _extract_email_address(self, text: str) -> List[ExtractedEntity]:
        """Extract email addresses."""
        entities = []
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                name="sender_filter",
                value=match.group(),
                confidence=0.9,
                position=(match.start(), match.end())
            ))
        return entities
    
    def _extract_subject_filter(self, text: str) -> List[ExtractedEntity]:
        """Extract subject filter patterns."""
        entities = []
        
        # Subject line patterns
        patterns = [
            r'subject[:\s]+["\']([^"\']+)["\']',
            r'with\s+subject\s+["\']([^"\']+)["\']',
            r'titled\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    name="subject_filter",
                    value=match.group(1),
                    confidence=0.8,
                    position=(match.start(1), match.end(1))
                ))
        
        return entities
    
    def _extract_slack_channel(self, text: str) -> List[ExtractedEntity]:
        """Extract Slack channel references."""
        entities = []
        
        # Channel patterns (#channel, @user)
        channel_pattern = r'([#@]\w+)'
        for match in re.finditer(channel_pattern, text):
            entities.append(ExtractedEntity(
                name="channel",
                value=match.group(1),
                confidence=0.9,
                position=(match.start(), match.end())
            ))
        
        # Channel name without #
        channel_name_pattern = r'channel\s+(\w+)'
        for match in re.finditer(channel_name_pattern, text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                name="channel",
                value=f"#{match.group(1)}",
                confidence=0.8,
                position=(match.start(1), match.end(1))
            ))
        
        return entities
    
    def _extract_url(self, text: str) -> List[ExtractedEntity]:
        """Extract URLs."""
        entities = []
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[^\s<>"\']+\.[a-z]{2,}(?:/[^\s<>"\']*)?'
        
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            url = match.group()
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = f"https://{url}"
                elif '.' in url:
                    url = f"https://{url}"
            
            entities.append(ExtractedEntity(
                name="target_url",
                value=url,
                confidence=0.9,
                position=(match.start(), match.end())
            ))
        
        return entities
    
    def _extract_file_path(self, text: str) -> List[ExtractedEntity]:
        """Extract file paths."""
        entities = []
        
        # Handle "from X to Y" pattern for file operations
        from_to_pattern = r'from\s+([^\s]+)\s+to\s+([^\s]+)'
        for match in re.finditer(from_to_pattern, text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                name="input_path",
                value=match.group(1),
                confidence=0.9,
                position=(match.start(1), match.end(1))
            ))
            entities.append(ExtractedEntity(
                name="output_path",
                value=match.group(2),
                confidence=0.9,
                position=(match.start(2), match.end(2))
            ))
        
        # Unix/Linux paths
        unix_path_pattern = r'/[^\s<>"\']+|~/[^\s<>"\']*|\./[^\s<>"\']*'
        for match in re.finditer(unix_path_pattern, text):
            # Skip if already captured in from_to pattern
            if not any(entity.position[0] <= match.start() <= entity.position[1] for entity in entities):
                entities.append(ExtractedEntity(
                    name="input_path",
                    value=match.group(),
                    confidence=0.8,
                    position=(match.start(), match.end())
                ))
        
        # Windows paths
        windows_path_pattern = r'[A-Za-z]:\\[^\s<>"\']+|\\\\[^\s<>"\']+|\.[/\\][^\s<>"\']*'
        for match in re.finditer(windows_path_pattern, text):
            # Skip if already captured in from_to pattern
            if not any(entity.position[0] <= match.start() <= entity.position[1] for entity in entities):
                entities.append(ExtractedEntity(
                    name="input_path",
                    value=match.group(),
                    confidence=0.8,
                    position=(match.start(), match.end())
                ))
        
        return entities
    
    def _extract_operation(self, text: str) -> List[ExtractedEntity]:
        """Extract file operations."""
        entities = []
        operations = ['copy', 'move', 'compress', 'backup', 'organize', 'cleanup', 'transform', 'analyze']
        
        for operation in operations:
            pattern = rf'\b{operation}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    name="operation",
                    value=operation.lower(),
                    confidence=0.9,
                    position=(match.start(), match.end())
                ))
        
        return entities
    
    def _extract_data_source(self, text: str) -> List[ExtractedEntity]:
        """Extract data sources."""
        entities = []
        
        # URLs
        url_entities = self._extract_url(text)
        for entity in url_entities:
            entities.append(ExtractedEntity(
                name="data_source",
                value=entity.value,
                confidence=entity.confidence,
                position=entity.position
            ))
        
        # File paths
        path_entities = self._extract_file_path(text)
        for entity in path_entities:
            entities.append(ExtractedEntity(
                name="data_source",
                value=entity.value,
                confidence=entity.confidence,
                position=entity.position
            ))
        
        return entities
    
    def _extract_analysis_type(self, text: str) -> List[ExtractedEntity]:
        """Extract analysis types."""
        entities = []
        analysis_types = {
            'statistics': 'descriptive',
            'stats': 'descriptive', 
            'trends': 'trend',
            'patterns': 'trend',
            'anomalies': 'anomaly',
            'outliers': 'anomaly',
            'correlation': 'correlation',
            'distribution': 'distribution',
            'time series': 'time_series',
            'comparison': 'comparison'
        }
        
        for keyword, analysis_type in analysis_types.items():
            pattern = rf'\b{re.escape(keyword)}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    name="analysis_type",
                    value=analysis_type,
                    confidence=0.8,
                    position=(match.start(), match.end())
                ))
        
        return entities
    
    def _extract_time_interval(self, text: str) -> List[ExtractedEntity]:
        """Extract time intervals."""
        entities = []
        
        # Pattern for time intervals (e.g., "every 5 minutes", "30 seconds", "1 hour")
        time_pattern = r'(?:every\s+)?(\d+)\s*(seconds?|minutes?|hours?|days?)'
        for match in re.finditer(time_pattern, text, re.IGNORECASE):
            value = int(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to seconds
            multipliers = {
                'second': 1, 'seconds': 1,
                'minute': 60, 'minutes': 60,
                'hour': 3600, 'hours': 3600,
                'day': 86400, 'days': 86400
            }
            
            interval_seconds = value * multipliers.get(unit, 1)
            
            entities.append(ExtractedEntity(
                name="check_interval",
                value=str(interval_seconds),
                confidence=0.8,
                position=(match.start(), match.end())
            ))
        
        return entities
    
    def calculate_intent_confidence(self, text: str, intent_pattern: IntentPattern) -> float:
        """Calculate confidence score for an intent pattern."""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Base score from keyword matching
        keyword_matches = sum(1 for keyword in intent_pattern.keywords if keyword in text_lower)
        keyword_score = keyword_matches / len(intent_pattern.keywords) if intent_pattern.keywords else 0
        
        # Pattern matching score
        pattern_score = 0
        for pattern in intent_pattern.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                pattern_score = 0.3
                break
        
        # Entity presence score
        entity_score = 0
        for entity_name in intent_pattern.required_entities:
            if entity_name in self.entity_extractors:
                entities = self.entity_extractors[entity_name](text)
                if entities:
                    entity_score += 0.2
        
        # Combine scores
        total_score = (keyword_score * 0.4) + pattern_score + entity_score + intent_pattern.confidence_boost
        return min(total_score, 1.0)
    
    def extract_entities(self, text: str, entity_names: List[str]) -> List[ExtractedEntity]:
        """Extract specified entities from text."""
        all_entities = []
        
        for entity_name in entity_names:
            if entity_name in self.entity_extractors:
                entities = self.entity_extractors[entity_name](text)
                all_entities.extend(entities)
        
        # Remove duplicates and sort by position
        unique_entities = []
        seen_positions = set()
        
        for entity in sorted(all_entities, key=lambda e: e.position[0]):
            if entity.position not in seen_positions:
                unique_entities.append(entity)
                seen_positions.add(entity.position)
        
        return unique_entities
    
    def extract_parameters(self, user_request: str) -> ParameterExtractionResult:
        """
        Extract parameters from user request and match to best template.
        
        Args:
            user_request: Natural language request from user
            
        Returns:
            ParameterExtractionResult with template match and extracted parameters
        """
        logger.info(f"Extracting parameters from: {user_request}")
        
        # Calculate confidence for each template
        template_scores = {}
        for template_name, pattern in self.intent_patterns.items():
            confidence = self.calculate_intent_confidence(user_request, pattern)
            template_scores[template_name] = confidence
            logger.debug(f"Template {template_name}: confidence {confidence:.3f}")
        
        # Find best matching template
        best_template = max(template_scores.items(), key=lambda x: x[1])
        best_template_name, best_confidence = best_template
        
        logger.info(f"Best template match: {best_template_name} (confidence: {best_confidence:.3f})")
        
        # Check if confidence is high enough
        if best_confidence < 0.3:
            return ParameterExtractionResult(
                template_match=None,
                confidence=best_confidence,
                extracted_parameters={},
                missing_required=[],
                entities=[],
                fallback_reason="Low confidence in template matching"
            )
        
        # Extract entities for the best template
        pattern = self.intent_patterns[best_template_name]
        all_entity_names = pattern.required_entities + pattern.optional_entities
        entities = self.extract_entities(user_request, all_entity_names)
        
        # Convert entities to parameters (take the first/best match for each entity type)
        extracted_parameters = {}
        for entity in entities:
            if entity.name not in extracted_parameters:
                extracted_parameters[entity.name] = entity.value
            # For multiple matches, prefer the one with higher confidence or take the first one
            # This prevents creating lists of values
        
        # Check for missing required parameters
        missing_required = [
            param for param in pattern.required_entities
            if param not in extracted_parameters
        ]
        
        # Apply some intelligent defaults and inference
        extracted_parameters = self._apply_smart_defaults(
            best_template_name, extracted_parameters, user_request
        )
        
        # Update missing required after applying defaults
        missing_required = [
            param for param in pattern.required_entities
            if param not in extracted_parameters
        ]
        
        logger.info(f"Extracted {len(extracted_parameters)} parameters, {len(missing_required)} missing")
        
        return ParameterExtractionResult(
            template_match=best_template_name,
            confidence=best_confidence,
            extracted_parameters=extracted_parameters,
            missing_required=missing_required,
            entities=entities
        )
    
    def _apply_smart_defaults(
        self, 
        template_name: str, 
        parameters: Dict[str, Any], 
        original_text: str
    ) -> Dict[str, Any]:
        """Apply intelligent defaults based on context."""
        result = parameters.copy()
        
        # Template-specific defaults
        if template_name == "gmail_monitor":
            if "check_interval" not in result:
                result["check_interval"] = "300"  # 5 minutes default
            
            # Infer email filter from context if missing
            if "email_filter" not in result:
                # Look for company domains or common patterns
                domain_hints = re.findall(r'from\s+(\w+)', original_text, re.IGNORECASE)
                if domain_hints:
                    result["email_filter"] = f"from:{domain_hints[0]}"
        
        elif template_name == "slack_notifier":
            if "channel" not in result:
                # Look for general channel references
                general_refs = re.findall(r'\b(general|random|alerts?|notifications?)\b', original_text, re.IGNORECASE)
                if general_refs:
                    result["channel"] = f"#{general_refs[0].lower()}"
        
        elif template_name == "web_scraper":
            if "scrape_interval" not in result:
                result["scrape_interval"] = "3600"  # 1 hour default
        
        elif template_name == "file_processor":
            if "operation" not in result:
                # Infer operation from context
                if any(word in original_text.lower() for word in ['backup', 'copy']):
                    result["operation"] = "copy"
                elif any(word in original_text.lower() for word in ['organize', 'clean']):
                    result["operation"] = "organize"
        
        elif template_name == "data_analyzer":
            if "analysis_type" not in result:
                result["analysis_type"] = "descriptive"  # Default analysis
        
        return result
    
    def suggest_missing_parameters(
        self, 
        template_name: str, 
        missing_params: List[str]
    ) -> Dict[str, str]:
        """Suggest prompts for missing parameters."""
        suggestions = {}
        
        prompts = {
            "email_filter": "What emails should I monitor? (e.g., 'from:example.com' or 'subject:urgent')",
            "sender_filter": "Which email address should I monitor? (e.g., 'user@example.com')",
            "channel": "Which Slack channel should I use? (e.g., '#general' or '@username')",
            "target_url": "What website should I scrape? (e.g., 'https://example.com')",
            "input_path": "What file or directory should I process? (e.g., '/path/to/files')",
            "output_path": "Where should I save the results? (e.g., '/path/to/output')",
            "operation": "What operation should I perform? (copy, move, compress, backup, analyze)",
            "data_source": "What data should I analyze? (file path, URL, or data)",
            "analysis_type": "What type of analysis? (descriptive, trends, anomalies, distribution)",
            "slack_token": "Please provide your Slack bot token",
            "check_interval": "How often should I check? (e.g., '300' for 5 minutes)",
            "scrape_interval": "How often should I scrape? (e.g., '3600' for 1 hour)"
        }
        
        for param in missing_params:
            if param in prompts:
                suggestions[param] = prompts[param]
            else:
                suggestions[param] = f"Please provide a value for {param}"
        
        return suggestions
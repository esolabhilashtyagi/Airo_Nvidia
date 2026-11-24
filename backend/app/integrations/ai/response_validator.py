import json
import logging
import re
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("aairo.ai.validator")


class ResponseValidator:
    @staticmethod
    def extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON object or array from markdown code blocks or raw strings."""
        if not raw_text:
            return None
        
        cleaned = raw_text.strip()
        # Remove ```json or ``` fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex search for { ... } or [ ... ]
            json_match = re.search(r"({[\s\S]*}|\[[\s\S]*\])", cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    logger.warning("Failed to decode regex-extracted JSON")
            return None

    @classmethod
    def validate_pydantic(
        cls,
        raw_text: str,
        schema: Type[BaseModel]
    ) -> Tuple[Optional[BaseModel], Optional[str]]:
        """Parse and validate JSON into the given Pydantic model."""
        parsed_dict = cls.extract_json(raw_text)
        if parsed_dict is None:
            return None, "Response did not contain valid parseable JSON"

        try:
            validated = schema.model_validate(parsed_dict)
            return validated, None
        except ValidationError as e:
            # Error `input` values can contain resume-derived personal data.
            # Record only field paths and error classes, never generated content.
            issues = e.errors(include_input=False, include_url=False)
            summary = "; ".join(
                f"{'.'.join(map(str, issue['loc'])) or '$'} ({issue['type']})"
                for issue in issues
            )
            logger.warning("Structured response validation failed: %s", summary)
            return None, f"Structured response failed validation: {summary}"

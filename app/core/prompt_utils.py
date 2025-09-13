"""
Prompt building utilities and helper functions for the travel booking application.

This module provides utilities for building, formatting, and managing prompts
with consistent structure and error handling.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from .prompt_templates import PromptTemplates, PromptRole


class PromptBuilder:
    """Utility class for building and formatting prompts."""

    @staticmethod
    def build_message_pair(role: PromptRole, user_prompt: str, **kwargs) -> List[Dict[str, str]]:
        """Build system/user message pair with context substitution."""

        system_message = PromptTemplates.get_system_message(role, kwargs)
        user_message = user_prompt.format(**kwargs)

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

    @staticmethod
    def build_extraction_messages(extraction_type: str, query: str, **kwargs) -> List[Dict[str, str]]:
        """Build messages for data extraction tasks."""

        current_date = datetime.now().strftime("%Y-%m-%d")

        if extraction_type == "flight":
            prompt_data = PromptTemplates.get_flight_extraction_prompt(current_date)
        elif extraction_type == "hotel":
            prompt_data = PromptTemplates.get_hotel_extraction_prompt(current_date)
        else:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

        user_content = prompt_data["user"].replace("{query}", query)

        return [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": user_content}
        ]

    @staticmethod
    def build_recommendation_messages(rec_type: str, **kwargs) -> List[Dict[str, str]]:
        """Build messages for recommendation tasks."""

        if rec_type == "flight":
            prompt_data = PromptTemplates.get_flight_recommendation_prompt(
                kwargs.get("origin", ""), kwargs.get("destination", "")
            )
        elif rec_type == "hotel":
            prompt_data = PromptTemplates.get_hotel_recommendation_prompt(
                kwargs.get("location", ""), kwargs.get("dates", {})
            )
        else:
            raise ValueError(f"Unknown recommendation type: {rec_type}")

        return [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": prompt_data["user"]}
        ]

    @staticmethod
    def build_travel_planning_messages(planning_type: str, **kwargs) -> List[Dict[str, str]]:
        """Build messages for travel planning tasks."""

        current_date = datetime.now().strftime("%Y-%m-%d")
        templates = PromptTemplates.get_travel_planning_prompts()

        if planning_type not in templates:
            raise ValueError(f"Unknown planning type: {planning_type}")

        template = templates[planning_type]

        # Substitute variables in user message
        user_content = template["user"].format(
            current_date=current_date,
            **kwargs
        )

        return [
            {"role": "system", "content": template["system"]},
            {"role": "user", "content": user_content}
        ]


class PromptValidator:
    """Utility class for validating prompt inputs and outputs."""

    @staticmethod
    def validate_extraction_output(extraction_type: str, output: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate and parse extraction output."""

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return False, {"error": "Invalid JSON output"}

        if extraction_type == "flight":
            return PromptValidator._validate_flight_extraction(data)
        elif extraction_type == "hotel":
            return PromptValidator._validate_hotel_extraction(data)
        else:
            return False, {"error": f"Unknown extraction type: {extraction_type}"}

    @staticmethod
    def _validate_flight_extraction(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate flight extraction output."""

        required_fields = ["location_origin", "location_destination", "departure_date", "adults"]

        # Check required fields
        for field in required_fields:
            if field not in data:
                return False, {"error": f"Missing required field: {field}"}

        # Validate date format and future date
        try:
            departure_date = datetime.strptime(data["departure_date"], "%Y-%m-%d")
            if departure_date.date() < datetime.now().date():
                return False, {"error": "Departure date cannot be in the past"}
        except ValueError:
            return False, {"error": "Invalid date format"}

        # Validate adults count
        if not isinstance(data["adults"], int) or data["adults"] < 1:
            return False, {"error": "Adults must be a positive integer"}

        # Validate airport codes (basic check)
        origin = data["location_origin"]
        destination = data["location_destination"]

        if origin != "MISSING" and (not isinstance(origin, str) or len(origin) != 3):
            return False, {"error": "Invalid origin airport code"}

        if not isinstance(destination, str) or len(destination) != 3:
            return False, {"error": "Invalid destination airport code"}

        return True, data

    @staticmethod
    def _validate_hotel_extraction(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate hotel extraction output."""

        required_fields = ["location", "check_in_date", "check_out_date", "adults", "rooms"]

        # Check required fields
        for field in required_fields:
            if field not in data:
                return False, {"error": f"Missing required field: {field}"}

        # Validate date formats and logic
        try:
            check_in = datetime.strptime(data["check_in_date"], "%Y-%m-%d")
            check_out = datetime.strptime(data["check_out_date"], "%Y-%m-%d")

            if check_in.date() < datetime.now().date():
                return False, {"error": "Check-in date cannot be in the past"}

            if check_out <= check_in:
                return False, {"error": "Check-out must be after check-in"}

        except ValueError:
            return False, {"error": "Invalid date format"}

        # Validate counts
        if not isinstance(data["adults"], int) or data["adults"] < 1:
            return False, {"error": "Adults must be a positive integer"}

        if not isinstance(data["rooms"], int) or data["rooms"] < 1:
            return False, {"error": "Rooms must be a positive integer"}

        # Validate price range
        valid_price_ranges = ["budget", "moderate", "expensive", "luxury"]
        if data.get("price_range") not in valid_price_ranges:
            data["price_range"] = "moderate"  # Default fallback

        return True, data


class PromptOptimizer:
    """Utilities for optimizing prompt performance and token usage."""

    @staticmethod
    def get_optimal_model_settings(task_type: str) -> Dict[str, Any]:
        """Get optimal model settings for different task types."""

        settings = {
            "extraction": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.1,
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            },
            "recommendation": {
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 1500
            },
            "planning": {
                "model": "gpt-4o-mini",
                "temperature": 0.4,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            },
            "conversation": {
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 1200
            }
        }

        return settings.get(task_type, settings["conversation"])

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Rough estimation of token count for cost planning."""
        # Rough approximation: 1 token ≈ 0.75 words
        word_count = len(text.split())
        return int(word_count / 0.75)

    @staticmethod
    def optimize_context_length(messages: List[Dict[str, str]], max_tokens: int = 4000) -> List[Dict[str, str]]:
        """Optimize message length to fit within context limits."""

        total_tokens = sum(PromptOptimizer.estimate_token_count(msg["content"]) for msg in messages)

        if total_tokens <= max_tokens:
            return messages

        # Keep system message, truncate user message if needed
        if len(messages) == 2:  # system + user
            system_tokens = PromptOptimizer.estimate_token_count(messages[0]["content"])
            available_tokens = max_tokens - system_tokens - 100  # Buffer

            user_content = messages[1]["content"]
            user_tokens = PromptOptimizer.estimate_token_count(user_content)

            if user_tokens > available_tokens:
                # Truncate user message (keep first part which usually contains instructions)
                words = user_content.split()
                target_words = int(available_tokens * 0.75)
                truncated_content = " ".join(words[:target_words]) + "...[truncated]"

                messages[1]["content"] = truncated_content

        return messages


class PromptLogger:
    """Utility for logging prompt usage and performance metrics."""

    @staticmethod
    def log_prompt_usage(task_type: str, input_tokens: int, output_tokens: int,
                        response_time: float, success: bool):
        """Log prompt usage metrics for monitoring and optimization."""

        # This could be extended to log to external systems
        from app.core.logging import logger

        logger.info(
            f"Prompt Usage - Task: {task_type}, "
            f"Input Tokens: {input_tokens}, Output Tokens: {output_tokens}, "
            f"Response Time: {response_time:.2f}s, Success: {success}"
        )

    @staticmethod
    def log_validation_failure(task_type: str, error: str, raw_output: str):
        """Log validation failures for prompt improvement."""

        from app.core.logging import logger

        logger.warning(
            f"Prompt Validation Failed - Task: {task_type}, "
            f"Error: {error}, Raw Output: {raw_output[:200]}..."
        )


# Convenience functions for common operations
def create_flight_extraction_messages(query: str) -> List[Dict[str, str]]:
    """Create messages for flight information extraction."""
    return PromptBuilder.build_extraction_messages("flight", query)


def create_hotel_extraction_messages(query: str) -> List[Dict[str, str]]:
    """Create messages for hotel information extraction."""
    return PromptBuilder.build_extraction_messages("hotel", query)


def create_flight_recommendation_messages(origin: str, destination: str) -> List[Dict[str, str]]:
    """Create messages for flight recommendations."""
    return PromptBuilder.build_recommendation_messages("flight", origin=origin, destination=destination)


def create_hotel_recommendation_messages(location: str, dates: Dict[str, str]) -> List[Dict[str, str]]:
    """Create messages for hotel recommendations."""
    return PromptBuilder.build_recommendation_messages("hotel", location=location, dates=dates)


def get_extraction_model_settings() -> Dict[str, Any]:
    """Get optimal settings for extraction tasks."""
    return PromptOptimizer.get_optimal_model_settings("extraction")


def get_recommendation_model_settings() -> Dict[str, Any]:
    """Get optimal settings for recommendation tasks."""
    return PromptOptimizer.get_optimal_model_settings("recommendation")
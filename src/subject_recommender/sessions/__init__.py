"""Expose the public session-generation API.

Inputs: Proxied to `sessions.generator.generate_session_plan`.
Outputs: Re-exported utilities so callers can import from `subject_recommender.sessions`.
"""

from __future__ import annotations

from .generator import SessionPlan, generate_session_plan

__all__ = ["SessionPlan", "generate_session_plan"]

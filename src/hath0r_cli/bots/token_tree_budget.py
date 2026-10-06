"""Multi-Agent Tree Token Budget Guard & Circuit Breaker for Hath0r FinOps."""

from __future__ import annotations

from typing import Any, Dict


class TokenBudgetExceeded(Exception):
    """Raised when subagent execution tree exceeds token or USD budget cap."""
    pass


class TokenTreeBudgetGuard:
    """Tracks cumulative prompt/completion tokens and cost across subagent execution trees."""

    def __init__(
        self,
        max_tokens_budget: int = 50000,
        max_usd_budget: float = 0.25,
    ) -> None:
        self.max_tokens_budget = max_tokens_budget
        self.max_usd_budget = max_usd_budget
        self._tree_usage: Dict[str, Dict[str, Any]] = {}

    def record_usage(
        self,
        tree_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str = "claude-3-7-sonnet",
    ) -> Dict[str, Any]:
        """Record token usage for a subagent turn and check circuit breaker limits."""
        if tree_id not in self._tree_usage:
            self._tree_usage[tree_id] = {
                "tree_id": tree_id,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "estimated_usd": 0.0,
                "status": "active",
            }

        data = self._tree_usage[tree_id]
        data["total_prompt_tokens"] += prompt_tokens
        data["total_completion_tokens"] += completion_tokens
        data["total_tokens"] = data["total_prompt_tokens"] + data["total_completion_tokens"]

        # Approximate token pricing ($3.00 / 1M prompt, $15.00 / 1M completion)
        cost = (prompt_tokens * 0.000003) + (completion_tokens * 0.000015)
        data["estimated_usd"] += round(cost, 6)

        # Check Circuit Breaker
        if data["total_tokens"] > self.max_tokens_budget or data["estimated_usd"] > self.max_usd_budget:
            data["status"] = "circuit_breaker_tripped"
            raise TokenBudgetExceeded(
                f"Token budget exceeded for tree '{tree_id}': "
                f"{data['total_tokens']} tokens (${data['estimated_usd']:.4f}) "
                f"exceeds cap of {self.max_tokens_budget} tokens / ${self.max_usd_budget:.2f}."
            )

        return data

    def check_budget(self, tree_id: str = "default_tree") -> Dict[str, Any]:
        """Inspect budget consumption for execution tree."""
        if tree_id not in self._tree_usage:
            return {
                "tree_id": tree_id,
                "status": "active",
                "total_tokens": 0,
                "max_tokens_budget": self.max_tokens_budget,
                "estimated_usd": 0.0,
                "max_usd_budget": self.max_usd_budget,
                "remaining_tokens": self.max_tokens_budget,
                "remaining_usd": self.max_usd_budget,
            }

        data = self._tree_usage[tree_id]
        rem_tokens = max(0, self.max_tokens_budget - data["total_tokens"])
        rem_usd = max(0.0, self.max_usd_budget - data["estimated_usd"])

        return {
            "tree_id": tree_id,
            "status": data["status"],
            "total_tokens": data["total_tokens"],
            "max_tokens_budget": self.max_tokens_budget,
            "estimated_usd": data["estimated_usd"],
            "max_usd_budget": self.max_usd_budget,
            "remaining_tokens": rem_tokens,
            "remaining_usd": round(rem_usd, 4),
        }


token_tree_budget_guard = TokenTreeBudgetGuard()

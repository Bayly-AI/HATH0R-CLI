"""Multi-Agent Consensus Engine & Evaluator Gate for GAIN Peer Mesh."""

from __future__ import annotations

from typing import Any, Dict, List


class MultiAgentConsensusEngine:
    """Aggregates, scores, and reconciles responses from multiple peer subagents."""

    def __init__(self, consensus_threshold: float = 0.70) -> None:
        self.consensus_threshold = consensus_threshold

    def evaluate_consensus(
        self,
        agent_responses: List[Dict[str, Any]],
        target_key: str = "output",
    ) -> Dict[str, Any]:
        """Compute agreement score across peer responses and determine evaluator gate status."""
        if not agent_responses:
            return {
                "status": "error",
                "consensus_score": 0.0,
                "passed_gate": False,
                "message": "No agent responses provided for consensus evaluation.",
            }

        # Extract values
        values = [str(resp.get(target_key, resp.get("response", ""))).strip().lower() for resp in agent_responses]
        total_agents = len(values)

        # Count frequencies
        freq: Dict[str, int] = {}
        for v in values:
            freq[v] = freq.get(v, 0) + 1

        top_val, top_count = max(freq.items(), key=lambda item: item[1])
        score = round(top_count / total_agents, 2)

        passed_gate = score >= self.consensus_threshold

        result = {
            "status": "success",
            "consensus_score": score,
            "consensus_threshold": self.consensus_threshold,
            "passed_gate": passed_gate,
            "top_consensus_value": top_val,
            "agreed_agent_count": top_count,
            "total_agents": total_agents,
            "fallback_human_in_loop_required": not passed_gate,
            "phoenix_trace_span": {
                "span_name": "multiagent_consensus_evaluation",
                "consensus_score": score,
                "agreement_ratio": f"{top_count}/{total_agents}",
            },
        }
        return result


multiagent_consensus_engine = MultiAgentConsensusEngine()

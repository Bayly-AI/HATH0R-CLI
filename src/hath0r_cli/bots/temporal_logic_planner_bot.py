"""Temporal Logic Planning (TLP) Policy Verifier and Automata Guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class LTLOperator(str, Enum):
    """Linear Temporal Logic modal and propositional operators."""

    ALWAYS = "G"        # Globally / Always (Box)
    EVENTUALLY = "F"    # Finally / Eventually (Diamond)
    UNTIL = "U"         # Until
    NEXT = "X"          # Next
    AND = "AND"
    IMPLIES = "IMPLIES"
    NOT = "NOT"


@dataclass
class DFAState:
    """State in a Deterministic Finite Automaton."""

    name: str
    is_accepting: bool = False
    is_trap: bool = False
    transitions: Dict[str, str] = field(default_factory=dict)  # input_symbol -> next_state_name


class DeterministicFiniteAutomaton:
    """Discrete state transition system verifying sequential policy compliance."""

    def __init__(self, name: str, initial_state: str) -> None:
        self.name = name
        self.initial_state = initial_state
        self.states: Dict[str, DFAState] = {}
        self.alphabet: Set[str] = set()

    def add_state(self, state: DFAState) -> None:
        self.states[state.name] = state
        for sym in state.transitions:
            self.alphabet.add(sym)

    def evaluate_trace(self, trace: List[str]) -> Tuple[bool, List[str], Optional[str]]:
        """Evaluate an ordered trace of events against the DFA transitions."""
        current = self.initial_state
        path = [current]

        for idx, symbol in enumerate(trace):
            state_obj = self.states.get(current)
            if not state_obj:
                return False, path, f"Unknown DFA state '{current}'"

            # Check wildcard or exact transition
            next_state = state_obj.transitions.get(symbol) or state_obj.transitions.get("*")
            if not next_state:
                return False, path, f"No transition from state '{current}' on symbol '{symbol}' (step {idx + 1})"

            current = next_state
            path.append(current)

            curr_obj = self.states.get(current)
            if curr_obj and curr_obj.is_trap:
                return False, path, f"Transitioned into rejecting trap state '{current}' on symbol '{symbol}' (step {idx + 1})"

        final_obj = self.states.get(current)
        is_valid = bool(final_obj and final_obj.is_accepting)
        rejection_reason = None if is_valid else f"Trace terminated in non-accepting state '{current}'"
        return is_valid, path, rejection_reason


class TemporalLogicPlannerBot:
    """Formal verifier for Hath0r governance policies and temporal lifecycle rules."""

    def __init__(self) -> None:
        self._automata: Dict[str, DeterministicFiniteAutomaton] = {}
        self._build_canonical_automata()

    def _build_canonical_automata(self) -> None:
        """Construct DFAs compiling CR-BAI-001, CR-HATH0R-INIT-001, and CR-CICCCD-001."""
        # 1. CR-BAI-001: Promotion Path Automaton
        # Rule: local -> development -> testing -> staging -> master
        dfa_bai = DeterministicFiniteAutomaton("cr-bai-001", initial_state="S_LOCAL")
        dfa_bai.add_state(DFAState("S_LOCAL", transitions={"local": "S_LOCAL", "development": "S_DEV", "*": "S_TRAP"}))
        dfa_bai.add_state(DFAState("S_DEV", transitions={"development": "S_DEV", "testing": "S_TEST", "*": "S_TRAP"}))
        dfa_bai.add_state(DFAState("S_TEST", transitions={"testing": "S_TEST", "staging": "S_STAGE", "*": "S_TRAP"}))
        dfa_bai.add_state(DFAState("S_STAGE", transitions={"staging": "S_STAGE", "master": "S_PROD", "*": "S_TRAP"}))
        dfa_bai.add_state(DFAState("S_PROD", is_accepting=True, transitions={"master": "S_PROD", "*": "S_TRAP"}))
        dfa_bai.add_state(DFAState("S_TRAP", is_trap=True, transitions={"*": "S_TRAP"}))
        self._automata["cr-bai-001"] = dfa_bai

        # 2. CR-HATH0R-INIT-001: Repo Initialization Gate Automaton
        # Rule: Both check_playbook AND check_runbook must precede scaffold_layout
        dfa_init = DeterministicFiniteAutomaton("cr-hathor-init-001", initial_state="S_START")
        dfa_init.add_state(
            DFAState(
                "S_START",
                transitions={
                    "check_playbook": "S_HAVE_PLAYBOOK",
                    "check_runbook": "S_HAVE_RUNBOOK",
                    "scaffold_layout": "S_TRAP",
                    "*": "S_START",
                },
            )
        )
        dfa_init.add_state(
            DFAState(
                "S_HAVE_PLAYBOOK",
                transitions={
                    "check_runbook": "S_READY_TO_SCAFFOLD",
                    "scaffold_layout": "S_TRAP",
                    "*": "S_HAVE_PLAYBOOK",
                },
            )
        )
        dfa_init.add_state(
            DFAState(
                "S_HAVE_RUNBOOK",
                transitions={
                    "check_playbook": "S_READY_TO_SCAFFOLD",
                    "scaffold_layout": "S_TRAP",
                    "*": "S_HAVE_RUNBOOK",
                },
            )
        )
        dfa_init.add_state(
            DFAState(
                "S_READY_TO_SCAFFOLD",
                transitions={
                    "scaffold_layout": "S_COMPLETE",
                    "*": "S_READY_TO_SCAFFOLD",
                },
            )
        )
        dfa_init.add_state(DFAState("S_COMPLETE", is_accepting=True, transitions={"*": "S_COMPLETE"}))
        dfa_init.add_state(DFAState("S_TRAP", is_trap=True, transitions={"*": "S_TRAP"}))
        self._automata["cr-hathor-init-001"] = dfa_init

        # 3. CR-CICCCD-001: Calibration Freshness Automaton
        # Rule: calibrate must precede release or deploy
        dfa_cal = DeterministicFiniteAutomaton("cr-cicccd-001", initial_state="S_UNCALIBRATED")
        dfa_cal.add_state(
            DFAState(
                "S_UNCALIBRATED",
                transitions={
                    "calibrate": "S_CALIBRATED",
                    "deploy": "S_TRAP",
                    "release": "S_TRAP",
                    "*": "S_UNCALIBRATED",
                },
            )
        )
        dfa_cal.add_state(
            DFAState(
                "S_CALIBRATED",
                is_accepting=True,
                transitions={
                    "deploy": "S_DEPLOYED",
                    "release": "S_RELEASED",
                    "calibrate": "S_CALIBRATED",
                    "*": "S_CALIBRATED",
                },
            )
        )
        dfa_cal.add_state(DFAState("S_DEPLOYED", is_accepting=True, transitions={"*": "S_DEPLOYED"}))
        dfa_cal.add_state(DFAState("S_RELEASED", is_accepting=True, transitions={"*": "S_RELEASED"}))
        dfa_cal.add_state(DFAState("S_TRAP", is_trap=True, transitions={"*": "S_TRAP"}))
        self._automata["cr-cicccd-001"] = dfa_cal

    def verify_trace(self, trace: List[str], policy_name: str = "all") -> Dict[str, Any]:
        """Verify an ordered execution trace against registered temporal automata."""
        target_policies = [policy_name] if policy_name != "all" else list(self._automata.keys())

        results = {}
        all_passed = True

        for pol in target_policies:
            dfa = self._automata.get(pol)
            if not dfa:
                results[pol] = {"valid": False, "error": f"Unknown policy '{pol}'"}
                all_passed = False
                continue

            passed, path, reason = dfa.evaluate_trace(trace)
            if not passed:
                all_passed = False

            results[pol] = {
                "valid": passed,
                "states_visited": path,
                "rejection_reason": reason,
                "initial_state": dfa.initial_state,
            }

        return {
            "valid": all_passed,
            "policies_checked": target_policies,
            "trace_length": len(trace),
            "trace": trace,
            "results": results,
        }


# Global singleton
temporal_logic_planner = TemporalLogicPlannerBot()

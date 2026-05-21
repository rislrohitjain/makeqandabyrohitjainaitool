import asyncio
import time
from typing import Dict, Any, List, Callable

class AgentStateTracker:
    """
    Thread-safe tracker for the 10-Subagent Matrix states.
    States: "Idle", "Processing", "Complete"
    """
    def __init__(self, on_update_callback: Callable[[], None] = None):
        self.states: Dict[str, str] = {
            "Supervisor Orchestrator": "Idle",
            "Ingestion Quality Evaluator": "Idle",
            "Structural Chunking Planner": "Idle",
            "Item Gen Specialist A": "Idle",
            "Item Gen Specialist B": "Idle",
            "Item Gen Specialist C": "Idle",
            "Distractor Variation Designer": "Idle",
            "Deduplication Vector Analyzer": "Idle",
            "Format Verification Auditor": "Idle",
            "Package Cryptography Agent": "Idle"
        }
        self.logs: List[str] = []
        self.on_update_callback = on_update_callback

    def update_state(self, agent_name: str, state: str, log_msg: str = None):
        if agent_name in self.states:
            self.states[agent_name] = state
            if log_msg:
                self.logs.append(f"[{agent_name}] {log_msg}")
            if self.on_update_callback:
                self.on_update_callback()

    def get_states(self) -> Dict[str, str]:
        return self.states.copy()

    def get_logs(self) -> List[str]:
        return list(self.logs)


# Abstract/Base Agent interface for structure
class BaseAgent:
    def __init__(self, name: str, tracker: AgentStateTracker):
        self.name = name
        self.tracker = tracker

    async def transition(self, state: str, log_msg: str = None):
        self.tracker.update_state(self.name, state, log_msg)
        # Yield to allow other tasks to run and Streamlit to capture updates
        await asyncio.sleep(0.1)

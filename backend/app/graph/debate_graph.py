import logging

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    START = "__start__"
    END = "__end__"

    class StateGraph:
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes = {}
            self.edges = {}
            self.conditional_edges = {}

        def add_node(self, name, func):
            self.nodes[name] = func

        def add_edge(self, from_node, to_node):
            self.edges[from_node] = to_node

        def add_conditional_edges(self, from_node, condition_func, routing_map):
            self.conditional_edges[from_node] = (condition_func, routing_map)

        def compile(self):
            class CompiledGraph:
                def __init__(self, parent):
                    self.parent = parent

                def invoke(self, state):
                    curr = dict(state)
                    curr_node = self.parent.edges.get(START, "initialize_debate")
                    visited = 0
                    while curr_node != END and visited < 50:
                        visited += 1
                        if curr_node in self.parent.nodes:
                            out = self.parent.nodes[curr_node](curr)
                            if isinstance(out, dict):
                                curr.update(out)
                        if curr_node in self.parent.conditional_edges:
                            cond_fn, r_map = self.parent.conditional_edges[curr_node]
                            target_key = cond_fn(curr)
                            curr_node = r_map.get(target_key, END)
                        elif curr_node in self.parent.edges:
                            curr_node = self.parent.edges[curr_node]
                        else:
                            break
                    return curr
            return CompiledGraph(self)

from .state import DebateGraphState
from .nodes import (
    initialize_debate,
    retrieve_pro_evidence,
    pro_agent_node,
    save_pro_message,
    retrieve_con_evidence,
    con_agent_node,
    save_con_message,
    update_rolling_summary,
    increment_round,
    compile_complete_transcript,
    judge_agent_node,
    validate_judge_output,
    save_result,
    check_initial_routing,
    check_pro_turn_routing,
    should_continue_debate,
    check_adjudication_routing,
)

logger = logging.getLogger(__name__)

def build_debate_graph():
    """
    Constructs the canonical multi-agent dialectical debate StateGraph.
    Adheres strictly to the cycle:
    START -> initialize_debate -> [check_initial_routing]
       -> (more rounds) -> retrieve_pro_evidence -> pro_agent -> save_pro_message -> [check_pro_turn_routing]
                           -> retrieve_con_evidence -> con_agent -> save_con_message -> [should_continue_debate]
                           -> (more rounds) -> increment_round -> retrieve_pro_evidence
                           -> (complete)    -> compile_complete_transcript -> [check_adjudication_routing]
                                              -> judge_agent -> validate_judge_output -> save_result -> END
                           -> (failed turn) -> save_result -> END
    """
    builder = StateGraph(DebateGraphState)

    # 1. Register Nodes
    builder.add_node("initialize_debate", initialize_debate)
    builder.add_node("retrieve_pro_evidence", retrieve_pro_evidence)
    builder.add_node("pro_agent", pro_agent_node)
    builder.add_node("save_pro_message", save_pro_message)
    builder.add_node("retrieve_con_evidence", retrieve_con_evidence)
    builder.add_node("con_agent", con_agent_node)
    builder.add_node("save_con_message", save_con_message)
    builder.add_node("update_rolling_summary", update_rolling_summary)
    builder.add_node("increment_round", increment_round)
    builder.add_node("compile_complete_transcript", compile_complete_transcript)
    builder.add_node("judge_agent", judge_agent_node)
    builder.add_node("validate_judge_output", validate_judge_output)
    builder.add_node("save_result", save_result)

    # 2. Add Standard & Conditional Initial Edges
    builder.add_edge(START, "initialize_debate")
    builder.add_conditional_edges(
        "initialize_debate",
        check_initial_routing,
        {
            "retrieve_pro_evidence": "retrieve_pro_evidence",
            "retrieve_con_evidence": "retrieve_con_evidence",
            "compile_complete_transcript": "compile_complete_transcript",
        }
    )
    builder.add_edge("retrieve_pro_evidence", "pro_agent")
    builder.add_edge("pro_agent", "save_pro_message")

    # Guard after PRO turn: route to CON on success, abort to save_result on failure
    builder.add_conditional_edges(
        "save_pro_message",
        check_pro_turn_routing,
        {
            "retrieve_con_evidence": "retrieve_con_evidence",
            "save_result": "save_result",
        }
    )

    builder.add_edge("retrieve_con_evidence", "con_agent")
    builder.add_edge("con_agent", "save_con_message")
    builder.add_edge("save_con_message", "update_rolling_summary")

    # 3. Add Conditional Edge on update_rolling_summary: advance round, proceed to adjudication, or abort to save_result
    builder.add_conditional_edges(
        "update_rolling_summary",
        should_continue_debate,
        {
            "increment_round": "increment_round",
            "compile_complete_transcript": "compile_complete_transcript",
            "save_result": "save_result",
        }
    )

    # 4. Cycle Edge back to retrieve_pro_evidence
    builder.add_edge("increment_round", "retrieve_pro_evidence")

    # 5. Adjudication Edges with guard before calling judge_agent
    builder.add_conditional_edges(
        "compile_complete_transcript",
        check_adjudication_routing,
        {
            "judge_agent": "judge_agent",
            "save_result": "save_result",
        }
    )
    builder.add_edge("judge_agent", "validate_judge_output")
    builder.add_edge("validate_judge_output", "save_result")
    builder.add_edge("save_result", END)

    return builder.compile()

# Global compiled graph
debate_graph = build_debate_graph()

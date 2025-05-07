import streamlit as st
from utils import generate_graph_basic, nx

def render_graph_page():
    st.info("Generate a basic random graph using NetworkX (if installed).")
    if not nx: st.error("NetworkX required. `pip install networkx matplotlib`."); return
    graph_cfg = st.session_state.graph; graph_cols = st.columns(2)
    with graph_cols[0]: graph_cfg['num_nodes'] = st.number_input("Num Nodes", 2, value=graph_cfg.get('num_nodes', 10), key="graph_nodes")
    with graph_cols[1]:
        current_nodes = graph_cfg.get('num_nodes', 10); max_edges = (current_nodes * (current_nodes - 1)) // 2 if current_nodes > 1 else 0
        current_edges = graph_cfg.get('num_edges', 15)
        graph_cfg['num_edges'] = st.number_input("Num Edges", 0, max_edges, min(current_edges, max_edges), key="graph_edges")
    graph_cfg['directed'] = st.checkbox("Directed Graph?", value=graph_cfg.get('directed', False), key="graph_directed")

def generate_graph_data_action():
    results = {'data': None, 'message': None, 'error': None}
    if not nx: results['error'] = "NetworkX not installed."; st.session_state.results.update(results); st.session_state.results['is_generating'] = False; return
    try:
        graph_cfg = st.session_state.graph
        G = generate_graph_basic(graph_cfg.get('num_nodes', 10), graph_cfg.get('num_edges', 15), graph_cfg.get('directed', False))
        results['data'] = G
        if G is not None: results['message'] = f"Generated graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges."
        else: results['error'] = "Graph generation failed."
    except Exception as e: results['error'] = f"Graph generation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
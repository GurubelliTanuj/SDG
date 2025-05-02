import streamlit as st
import pandas as pd
import numpy as np
from faker import Faker
import random
import string
from datetime import datetime, timedelta, date # Import date separately
import re
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont

# --- Optional, More Advanced Libraries ---
try:
    import rstr
except ImportError:
    rstr = None
try:
    from scipy import stats
except ImportError:
    stats = None
try:
    import networkx as nx
    import matplotlib.pyplot as plt
except ImportError:
    nx = None
    plt = None

# --- Initialize Faker ---
fake = Faker()

# --- Constants ---
DATA_TYPES = ["Tabular", "Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]
TABULAR_METHODS = ["Rule-Based (Faker/Random/Regex/Deps)", "Statistical (NumPy/SciPy Dist)"] # Added /Deps
IMAGE_METHODS = ["Rule-Based (Pillow Shapes)"]
TEXT_METHODS = ["Rule-Based (Faker)"]
GRAPH_METHODS = ["Rule-Based (NetworkX Random)"]
PRIVACY_METHODS = ["None", "Differential Privacy (Conceptual Placeholder)"]
USE_CASES = ["General Purpose / Testing", "Model Training (Consider Fidelity)", "Privacy Preservation (Requires Method)"]
NUMERICAL_DISTS = ["uniform", "normal", "poisson", "gamma", "beta"]
DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"]

# --- Helper Functions ---
# (Keep generate_simple_image, image_to_bytes, generate_graph_basic, draw_graph)
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    shape_margin = int(min(width, height) * 0.15)
    x1, y1 = shape_margin, shape_margin
    x2, y2 = width - shape_margin, height - shape_margin
    try:
        if shape == 'rectangle': draw.rectangle([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'ellipse': draw.ellipse([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'triangle':
             point1 = (width // 2, y1)
             point2 = (x1, y2)
             point3 = (x2, y2)
             draw.polygon([point1, point2, point3], fill=shape_color)
    except Exception as e: st.error(f"Error drawing image: {e}")
    return img

def image_to_bytes(img, format='PNG'):
    buf = io.BytesIO(); img.save(buf, format=format); return buf.getvalue()

def generate_graph_basic(num_nodes, num_edges, directed=False):
    if not nx: st.error("NetworkX library not installed."); return None
    G = nx.gnm_random_graph(num_nodes, num_edges, directed=directed)
    return G

def draw_graph(G):
    if not plt or not nx: st.error("Matplotlib/NetworkX not installed."); return None
    fig, ax = plt.subplots(); nx.draw(G, ax=ax, with_labels=True, node_color='skyblue', edge_color='gray')
    buf = io.BytesIO(); fig.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
    return buf


# --- Generation Logic for Tabular (Updated) ---
def generate_tabular_value(col_def):
    col_type = col_def.get('data_type')
    dist = col_def.get('distribution')
    params = col_def.get('params', {})

    try:
        # --- Handle NEW Simpler Types ---
        if col_type == "Numerical (Integer)":
             min_v = params.get('min', 0)
             max_v = params.get('max', 100)
             return random.randint(min_v, max_v)
        elif col_type == "Numerical (Float)":
             min_v = params.get('min', 0.0)
             max_v = params.get('max', 1.0)
             return random.uniform(min_v, max_v)
        elif col_type == "Categorical (Simple List)":
             choices = params.get('choices', ['A']) # Ensure choices is a list
             if not choices: return None
             return random.choice(choices)
        # --- Handle Existing Detailed/Specific Types ---
        elif col_type == "Integer": # With distributions
            if dist == "uniform":
                return random.randint(params.get('min', 0), params.get('max', 100))
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=params.get('mean', 50), scale=params.get('std', 10)))
                min_v, max_v = params.get('min'), params.get('max') # Optional clamping
                if min_v is not None: val = max(val, int(min_v))
                if max_v is not None: val = min(val, int(max_v))
                return val
            elif dist == "poisson" and stats:
                return stats.poisson.rvs(mu=params.get('mu', 10))
            else: return random.randint(params.get('min', 0), params.get('max', 100)) # Fallback
        elif col_type == "Float": # With distributions
             if dist == "uniform":
                return random.uniform(params.get('min', 0.0), params.get('max', 1.0))
             elif dist == "normal" and stats:
                 val = stats.norm.rvs(loc=params.get('mean', 0.5), scale=params.get('std', 0.1))
                 min_v, max_v = params.get('min'), params.get('max') # Optional clamping
                 if min_v is not None: val = max(val, float(min_v))
                 if max_v is not None: val = min(val, float(max_v))
                 return val
             elif dist == "gamma" and stats:
                 return stats.gamma.rvs(a=params.get('shape', 2.0), scale=params.get('scale', 1.0))
             elif dist == "beta" and stats:
                  return stats.beta.rvs(a=params.get('a', 2.0), b=params.get('b', 2.0))
             else: return random.uniform(params.get('min', 0.0), params.get('max', 1.0)) # Fallback
        elif col_type == "String (Faker)":
            faker_type = params.get('faker_type', 'word')
            try: return getattr(fake, faker_type)()
            except AttributeError: return fake.word()
        elif col_type == "String (Regex)" and rstr:
            return rstr.xeger(params.get('regex', r'\w{5}'))
        elif col_type == "Categorical": # With probabilities
            choices = params.get('choices', ['A', 'B'])
            probs = params.get('probabilities')
            if not choices: return None
            if probs and len(probs) == len(choices):
                 prob_sum = sum(probs) # Simple normalization
                 if not np.isclose(prob_sum, 1.0): probs = [p / prob_sum for p in probs]
                 return np.random.choice(choices, p=probs)
            else: return random.choice(choices)
        elif col_type == "Date":
            start = params.get('start_date', datetime.now().date() - timedelta(days=365))
            end = params.get('end_date', datetime.now().date())
            if isinstance(start, datetime): start = start.date() # Ensure date objects
            if isinstance(end, datetime): end = end.date()
            if start > end: start, end = end, start
            return fake.date_between_dates(date_start=start, date_end=end)
        elif col_type == "Boolean":
            return random.choice([True, False])
        else:
            return None
    except Exception as e:
        st.error(f"Error generating value for type {col_type}, dist {dist}: {e}")
        return None

# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("Modular Synthetic Data Generator")

# --- Initialize Session State ---
default_state = {
    'config': { 'data_type': DATA_TYPES[0], 'use_case': USE_CASES[0], 'privacy_level': PRIVACY_METHODS[0], 'privacy_epsilon': 1.0, 'generation_method': None, 'num_rows': 100 },
    'tabular': { 'columns': [], 'relationships': [], 'method_config': {} }, # Added relationships list
    'image': { 'count': 10, 'width': 128, 'height': 128, 'bg_color': '#DDDDDD', 'shape': 'rectangle', 'shape_color': '#FF0000', 'method_config': {} },
    'text': { 'count': 10, 'faker_method': 'sentence', 'method_config': {} },
    'graph':{ 'num_nodes': 10, 'num_edges': 15, 'directed': False, 'method_config': {} },
    'ui_state': { 'adding_column': False, 'adding_relationship': False },
    'results': { 'data': None, 'message': None, 'error': None, 'is_generating': False }
}
for key, value in default_state.items():
    if key not in st.session_state: st.session_state[key] = value

# --- App Layout ---
# == Sidebar: Global Configuration ==
st.sidebar.header("1. Define Target Data")
st.session_state.config['data_type'] = st.sidebar.selectbox("Select Data Type", DATA_TYPES, index=DATA_TYPES.index(st.session_state.config['data_type']))
st.session_state.config['use_case'] = st.sidebar.selectbox("Intended Use Case", USE_CASES, index=USE_CASES.index(st.session_state.config['use_case']))

st.sidebar.header("2. Determine Privacy Requirements")
st.session_state.config['privacy_level'] = st.sidebar.selectbox("Privacy Method", PRIVACY_METHODS, index=PRIVACY_METHODS.index(st.session_state.config['privacy_level']))
if st.session_state.config['privacy_level'] == "Differential Privacy (Conceptual Placeholder)":
    st.session_state.config['privacy_epsilon'] = st.sidebar.number_input("Epsilon (Lower = More Private)", min_value=0.01, value=st.session_state.config['privacy_epsilon'])
    st.sidebar.warning("Differential Privacy integration is complex and currently a placeholder.")

st.sidebar.header("3. Choose Generation Method")
current_data_type = st.session_state.config['data_type']
available_methods = []
if current_data_type == "Tabular": available_methods = TABULAR_METHODS
elif current_data_type == "Image (Basic Shapes)": available_methods = IMAGE_METHODS
elif current_data_type == "Text (Basic)": available_methods = TEXT_METHODS
elif current_data_type == "Graph (Basic Random)": available_methods = GRAPH_METHODS

if st.session_state.config['generation_method'] not in available_methods:
    st.session_state.config['generation_method'] = available_methods[0] if available_methods else None

st.session_state.config['generation_method'] = st.sidebar.selectbox("Select Method", available_methods, index=available_methods.index(st.session_state.config['generation_method']) if st.session_state.config['generation_method'] in available_methods else 0)

# == Main Area: Type-Specific Configuration & Generation ==
st.header(f"Configure: {current_data_type}")

# --- UI specific to Tabular Data ---
if current_data_type == "Tabular":
    st.subheader("Define Columns")
    with st.expander("Add New Column Definition", expanded=st.session_state.ui_state.get('adding_column', False)):
        col_data_types = [
            "Numerical (Integer)", "Numerical (Float)", # Simple types first
            "Categorical (Simple List)", "Boolean", "Date",
            "Integer", "Float", # Detailed types (with distributions)
            "Categorical", # The one with probability option
            "String (Faker)", "String (Regex)",
        ]
        new_col_data_type = st.selectbox("Column Data Type", col_data_types, key="new_col_type")

        new_col_params = {'data_type': new_col_data_type}
        new_col_dist = None

        param_cols = st.columns(2)
        with param_cols[0]:
            new_col_name = st.text_input("Column Name*", key="new_col_name")

            # --- Parameter Inputs based on Type ---
            if new_col_data_type == "Numerical (Integer)":
                 new_col_params['min'] = st.number_input("Min", value=0, step=1, key="new_num_int_min")
                 new_col_params['max'] = st.number_input("Max", value=100, step=1, key="new_num_int_max")
            elif new_col_data_type == "Numerical (Float)":
                 new_col_params['min'] = st.number_input("Min", value=0.0, format="%.4f", key="new_num_float_min")
                 new_col_params['max'] = st.number_input("Max", value=1.0, format="%.4f", key="new_num_float_max")
            elif new_col_data_type == "Categorical (Simple List)":
                 choices_str = st.text_area("Choices (comma-separated)", "A,B,C", key="new_cat_simple_choices")
                 new_col_params['choices'] = [c.strip() for c in choices_str.split(',') if c.strip()]

            # --- Parameters for Detailed Types ---
            elif new_col_data_type == "Integer" or new_col_data_type == "Float":
                 num_dists = [d for d in NUMERICAL_DISTS if d in ['uniform', 'normal']]
                 if stats: num_dists.extend([d for d in NUMERICAL_DISTS if d not in ['uniform', 'normal']])
                 new_col_dist = st.selectbox("Distribution", num_dists, key="new_col_dist")
                 new_col_params['distribution'] = new_col_dist
                 # ... (Keep the distribution parameter inputs as before for Integer/Float) ...
                 if new_col_dist == "uniform":
                     new_col_params['min'] = st.number_input("Min", value=0.0 if new_col_data_type=="Float" else 0, key="new_col_min")
                     new_col_params['max'] = st.number_input("Max", value=1.0 if new_col_data_type=="Float" else 100, key="new_col_max")
                 elif new_col_dist == "normal":
                     new_col_params['mean'] = st.number_input("Mean", value=0.5 if new_col_data_type=="Float" else 50, key="new_col_mean")
                     new_col_params['std'] = st.number_input("Std Dev", value=0.1 if new_col_data_type=="Float" else 10, min_value=0.01, key="new_col_std")
                     if st.checkbox("Set Min/Max Bounds?", key="new_norm_bounds"):
                        new_col_params['min'] = st.number_input("Min Bound", value=0.0 if new_col_data_type=="Float" else 0, key="new_col_norm_min")
                        new_col_params['max'] = st.number_input("Max Bound", value=1.0 if new_col_data_type=="Float" else 100, key="new_col_norm_max")
                 elif new_col_dist == "poisson": new_col_params['mu'] = st.number_input("Mu (Rate λ)", value=10, min_value=0, key="new_col_poisson_mu")
                 elif new_col_dist == "gamma": new_col_params['shape'] = st.number_input("Shape (k)", value=2.0, min_value=0.01, key="new_col_gamma_shape"); new_col_params['scale'] = st.number_input("Scale (θ)", value=1.0, min_value=0.01, key="new_col_gamma_scale")
                 elif new_col_dist == "beta": new_col_params['a'] = st.number_input("Alpha (a)", value=2.0, min_value=0.01, key="new_col_beta_a"); new_col_params['b'] = st.number_input("Beta (b)", value=2.0, min_value=0.01, key="new_col_beta_b")

            elif new_col_data_type == "String (Faker)":
                # ... (Faker type selection as before) ...
                common_faker = ['name', 'email', 'address', 'city', 'country', 'job', 'company', 'sentence', 'paragraph', 'word', 'license_plate', 'url', 'uuid4']
                new_col_params['faker_type'] = st.selectbox("Faker Type", common_faker, key="new_col_faker")
            elif new_col_data_type == "String (Regex)":
                 # ... (Regex input as before) ...
                 if rstr: new_col_params['regex'] = st.text_input("Regex Pattern", value=r"^[A-Za-z]{3}\d{3}$", key="new_col_regex")
                 else: st.warning("Rstr library not installed.")
            elif new_col_data_type == "Categorical": # With probabilities
                 new_col_params['choices'] = [c.strip() for c in st.text_input("Choices (comma-separated)", "A,B,C", key="new_col_choices").split(',') if c.strip()]
                 if st.checkbox("Specify Probabilities?", key="new_cat_probs_check"):
                      # ... (Probability input as before) ...
                      probs_str = st.text_input("Probabilities (comma-separated, matching choices)", key="new_cat_probs_str")
                      try:
                           probs_list = [float(p.strip()) for p in probs_str.split(',') if p.strip()]
                           if len(probs_list) == len(new_col_params['choices']): new_col_params['probabilities'] = probs_list
                           else: st.warning("Number of probabilities must match choices.")
                      except ValueError: st.warning("Invalid probability format.")

            elif new_col_data_type == "Date":
                 # ... (Date input as before) ...
                 today = datetime.now().date()
                 new_col_params['start_date'] = st.date_input("Start Date", value=today-timedelta(days=365), key="new_col_start_date")
                 new_col_params['end_date'] = st.date_input("End Date", value=today, key="new_col_end_date")
            # Boolean needs no params here

        with param_cols[1]:
            st.write("") # Spacer
            if st.button("➕ Add Column", key="add_col_btn"):
                # --- Validation ---
                error = False
                if not new_col_name: st.error("Column Name required."); error = True
                if any(c['name'] == new_col_name for c in st.session_state.tabular['columns']): st.error(f"Column '{new_col_name}' already exists."); error = True
                if new_col_data_type in ["Numerical (Integer)", "Numerical (Float)", "Integer", "Float"]:
                    if 'min' in new_col_params and 'max' in new_col_params and new_col_params['min'] > new_col_params['max']:
                        st.warning("Min > Max, swapping values."); new_col_params['min'], new_col_params['max'] = new_col_params['max'], new_col_params['min']
                if new_col_data_type in ["Categorical (Simple List)", "Categorical"] and not new_col_params.get('choices'):
                    st.error("Choices cannot be empty for Categorical types."); error = True
                if new_col_data_type == "Date" and new_col_params['start_date'] > new_col_params['end_date']:
                    st.warning("Start date > End date, swapping."); new_col_params['start_date'], new_col_params['end_date'] = new_col_params['end_date'], new_col_params['start_date']

                if not error:
                    st.session_state.tabular['columns'].append({
                        "name": new_col_name,
                        "data_type": new_col_data_type,
                        "distribution": new_col_dist,
                        "params": new_col_params
                    })
                    st.success(f"Column '{new_col_name}' added.")
                    st.session_state.ui_state['adding_column'] = False
                    st.rerun()

    # --- Display Defined Columns ---
    st.subheader("Defined Columns")
    # ... (Display logic remains largely the same, showing type and params) ...
    if not st.session_state.tabular['columns']: st.info("No columns defined yet.")
    else:
        cols_to_remove = []
        for i, col_def in enumerate(st.session_state.tabular['columns']):
            col_key = f"col_{i}_{col_def['name']}"
            with st.container(border=True):
                #  st.write(f"**{col_def['name']}** (`{col_def['data_type']}`{ f', Dist: {col_def.get("distribution")}' if col_def.get('distribution') else '' })")
                 # 1. Build the optional distribution string separately
                 dist_info = col_def.get('distribution')
                 dist_display_str = f', Dist: {dist_info}' if dist_info else ''

                 # 2. Use the pre-built string in the main f-string
                 st.write(f"**{col_def['name']}** (`{col_def['data_type']}`{dist_display_str})")

                 # 3. Display relevant params (filter out 'data_type' as it's already shown)
                 display_params = {k: v for k, v in col_def.get('params', {}).items() if k != 'data_type'}
                 # Optionally filter out distribution too if it's displayed above
                 # display_params = {k: v for k, v in display_params.items() if k != 'distribution'}

                 if display_params: # Only show caption if there are params to display
                     params_str = ", ".join([f"{k}: {str(v)[:30]}{'...' if len(str(v))>30 else ''}" for k, v in display_params.items()])
                     st.caption(f"Params: {params_str}")
                 # Display relevant params briefly
                 params_str = ", ".join([f"{k}: {str(v)[:30]}{'...' if len(str(v))>30 else ''}" for k,v in col_def.get('params', {}).items() if k!='data_type'])
                 st.caption(f"Params: {params_str}")
                 if st.button("❌ Remove", key=f"{col_key}_remove"): cols_to_remove.append(i)
        if cols_to_remove:
            for index in sorted(cols_to_remove, reverse=True): del st.session_state.tabular['columns'][index]
            st.rerun()

    # --- Define Relationships / Dependencies ---
    st.subheader("Define Dependencies")
    column_names = [c['name'] for c in st.session_state.tabular['columns']]
    if not column_names:
        st.info("Add columns before defining dependencies.")
    else:
        with st.expander("Add New Dependency", expanded=st.session_state.ui_state.get('adding_relationship', False)):
            rel_cols = st.columns(3)
            with rel_cols[0]:
                dep_cond_col = st.selectbox("IF Column:", column_names, key="dep_cond_col", index=None)
            with rel_cols[1]:
                dep_condition = st.selectbox("Condition:", DEPENDENCY_CONDITIONS, key="dep_condition", index=None)
            with rel_cols[2]:
                # Use text input, parsing happens during generation
                dep_cond_val_str = st.text_input("Condition Value:", key="dep_cond_val", help="For 'in list', use comma-separated values.")

            set_cols = st.columns(2)
            with set_cols[0]:
                 dep_dependent_col = st.selectbox("THEN Set Column:", column_names, key="dep_dependent_col", index=None)
            with set_cols[1]:
                 dep_dependent_val_str = st.text_input("To Value:", key="dep_dependent_val")

            if st.button("➕ Add Dependency", key="add_dep_btn"):
                if dep_cond_col and dep_condition and dep_dependent_col is not None and dep_dependent_val_str is not None:
                     if dep_cond_col == dep_dependent_col:
                          st.error("Condition column and Dependent column cannot be the same.")
                     else:
                          st.session_state.tabular['relationships'].append({
                              'condition_col': dep_cond_col,
                              'condition': dep_condition,
                              'condition_value_str': dep_cond_val_str, # Store as string initially
                              'dependent_col': dep_dependent_col,
                              'dependent_value_str': dep_dependent_val_str # Store as string
                          })
                          st.success("Dependency added.")
                          st.session_state.ui_state['adding_relationship'] = False
                          st.rerun()
                else:
                     st.warning("Please fill all dependency fields.")

    # --- Display Defined Dependencies ---
    st.subheader("Defined Dependencies")
    if not st.session_state.tabular['relationships']: st.info("No dependencies defined yet.")
    else:
        rels_to_remove = []
        for i, rel in enumerate(st.session_state.tabular['relationships']):
            rel_key = f"rel_{i}"
            with st.container(border=True):
                 st.write(f"**Rule {i+1}:** IF `{rel['condition_col']}` {rel['condition']} `{rel['condition_value_str']}` THEN SET `{rel['dependent_col']}` TO `{rel['dependent_value_str']}`")
                 if st.button("❌ Remove Rule", key=f"{rel_key}_remove"): rels_to_remove.append(i)
        if rels_to_remove:
            for index in sorted(rels_to_remove, reverse=True): del st.session_state.tabular['relationships'][index]
            st.rerun()

# --- UI for other data types (Image, Text, Graph) remains the same ---
elif current_data_type == "Image (Basic Shapes)":
    # ... (Image config UI as before) ...
    img_cfg = st.session_state.image; img_cols = st.columns(2)
    with img_cols[0]: img_cfg['count'] = st.number_input("Number of Images", 1, 1000, img_cfg['count']); img_cfg['width'] = st.number_input("Width (px)", 16, 1024, img_cfg['width']); img_cfg['height'] = st.number_input("Height (px)", 16, 1024, img_cfg['height'])
    with img_cols[1]: img_cfg['bg_color'] = st.color_picker("Background Color", img_cfg['bg_color']); img_cfg['shape'] = st.selectbox("Shape", ['rectangle', 'ellipse', 'triangle'], index=['rectangle', 'ellipse', 'triangle'].index(img_cfg['shape'])); img_cfg['shape_color'] = st.color_picker("Shape Color", img_cfg['shape_color'])
elif current_data_type == "Text (Basic)":
    # ... (Text config UI as before) ...
    txt_cfg = st.session_state.text; txt_cfg['count'] = st.number_input("Number of Text Samples", 1, 5000, txt_cfg['count']); common_faker = ['sentence', 'paragraph', 'text', 'bs', 'catch_phrase']; txt_cfg['faker_method'] = st.selectbox("Faker Text Type", common_faker, index=common_faker.index(txt_cfg['faker_method']))
elif current_data_type == "Graph (Basic Random)":
     # ... (Graph config UI as before) ...
     if not nx: st.error("NetworkX library not installed.")
     else: graph_cfg = st.session_state.graph; graph_cols = st.columns(2)
     with graph_cols[0]: graph_cfg['num_nodes'] = st.number_input("Number of Nodes", 2, value=graph_cfg['num_nodes'])
     with graph_cols[1]: max_edges = (graph_cfg['num_nodes'] * (graph_cfg['num_nodes'] - 1)) // 2; graph_cfg['num_edges'] = st.number_input("Number of Edges", 0, max_edges, min(graph_cfg['num_edges'], max_edges))
     graph_cfg['directed'] = st.checkbox("Directed Graph?", value=graph_cfg['directed'])

# --- Generation Section ---
st.divider()
st.header("4. Generate Data")
st.session_state.config['num_rows'] = st.number_input(f"Number of Rows/Items", 1, 100000, st.session_state.config['num_rows'], key="global_num_rows", help="...")
if st.button("🚀 Generate Data", key="generate_data", type="primary", disabled=st.session_state.results['is_generating']):
    st.session_state.results['is_generating'] = True
    st.session_state.results['data'] = None; st.session_state.results['message'] = None; st.session_state.results['error'] = None
    st.rerun()

if st.session_state.results['is_generating']:
    with st.spinner(f"Generating {st.session_state.config['data_type']} data..."):
        try:
            dtype = st.session_state.config['data_type']
            method = st.session_state.config['generation_method']
            num_items = st.session_state.config['num_rows']
            generated_output = None

            if dtype == "Tabular":
                if not st.session_state.tabular['columns']: raise ValueError("No columns defined.")
                columns = st.session_state.tabular['columns']
                relationships = st.session_state.tabular['relationships']
                # Create a lookup for column type by name for faster checking during dependency eval
                col_type_lookup = {col['name']: col['data_type'] for col in columns}

                if "Rule-Based" in method or "Statistical" in method : # Apply deps for these methods
                    all_rows = []
                    for _ in range(num_items):
                         # 1. Generate Base Row
                         row = {col['name']: generate_tabular_value(col) for col in columns}

                         # 2. Apply Dependencies Sequentially
                         for rel in relationships:
                             try:
                                 cond_col = rel['condition_col']
                                 dep_col = rel['dependent_col']
                                 cond_val_str = rel['condition_value_str']
                                 dep_val_str = rel['dependent_value_str']
                                 condition = rel['condition']

                                 if cond_col not in row: continue # Skip if condition col somehow missing

                                 actual_value = row[cond_col]
                                 condition_met = False

                                 # --- Attempt Type Coercion for Comparison ---
                                 target_cond_type_str = col_type_lookup.get(cond_col, 'unknown').lower()
                                 compare_value = cond_val_str # Default to string
                                 try:
                                     if actual_value is not None:
                                         if 'int' in target_cond_type_str: compare_value = int(cond_val_str)
                                         elif 'float' in target_cond_type_str: compare_value = float(cond_val_str)
                                         elif 'bool' in target_cond_type_str: compare_value = cond_val_str.lower() in ['true', '1', 'yes']
                                         elif 'date' in target_cond_type_str: compare_value = datetime.strptime(cond_val_str, "%Y-%m-%d").date()
                                         # For 'in list'/'not in list', compare_value needs to be a list
                                         if condition in ["in list", "not in list"]:
                                             list_vals_str = [v.strip() for v in cond_val_str.split(',') if v.strip()]
                                             # Try coercing list items based on actual_value type
                                             compare_value = []
                                             for item_str in list_vals_str:
                                                 if 'int' in target_cond_type_str: compare_value.append(int(item_str))
                                                 elif 'float' in target_cond_type_str: compare_value.append(float(item_str))
                                                 elif 'bool' in target_cond_type_str: compare_value.append(item_str.lower() in ['true', '1', 'yes'])
                                                 # Add date parsing for lists if needed
                                                 else: compare_value.append(item_str) # Fallback to string in list
                                 except Exception as e:
                                     st.warning(f"Type conversion failed for condition value '{cond_val_str}' comparison against column '{cond_col}'. Comparing as strings. Error: {e}", icon="⚠️")
                                     compare_value = cond_val_str # Ensure it's back to string if list parsing failed mid-way
                                     if condition in ["in list", "not in list"]: # Ensure compare_value is list of strings if conversion failed
                                          compare_value = [v.strip() for v in cond_val_str.split(',') if v.strip()]


                                 # --- Perform Comparison ---
                                 # Handle None comparisons carefully
                                 if actual_value is None:
                                     if condition == "equals" and (compare_value is None or str(compare_value).lower() in ['none', 'null', '']): condition_met = True
                                     elif condition == "not equals" and not (compare_value is None or str(compare_value).lower() in ['none', 'null', '']): condition_met = True
                                 elif condition == "equals": condition_met = (actual_value == compare_value)
                                 elif condition == "not equals": condition_met = (actual_value != compare_value)
                                 # Comparisons below assume actual_value is not None
                                 elif condition == "greater than" and actual_value > compare_value: condition_met = True
                                 elif condition == "less than" and actual_value < compare_value: condition_met = True
                                 elif condition == "in list" and isinstance(compare_value, list) and actual_value in compare_value: condition_met = True
                                 elif condition == "not in list" and isinstance(compare_value, list) and actual_value not in compare_value: condition_met = True

                             except Exception as e:
                                 st.error(f"Error evaluating dependency rule: {rel}. Error: {e}")
                                 condition_met = False # Skip rule on error

                             # 3. Set Dependent Value if Condition Met
                             if condition_met:
                                 try:
                                     # Attempt to cast dependent value to target column type
                                     target_dep_type_str = col_type_lookup.get(dep_col, 'unknown').lower()
                                     final_dep_val = dep_val_str # Default string
                                     if 'int' in target_dep_type_str: final_dep_val = int(dep_val_str)
                                     elif 'float' in target_dep_type_str: final_dep_val = float(dep_val_str)
                                     elif 'bool' in target_dep_type_str: final_dep_val = dep_val_str.lower() in ['true', '1', 'yes']
                                     elif 'date' in target_dep_type_str: final_dep_val = datetime.strptime(dep_val_str, "%Y-%m-%d").date()
                                     # Note: String types just use the string value

                                     row[dep_col] = final_dep_val # Update the row
                                 except Exception as e:
                                      st.warning(f"Type conversion failed for dependent value '{dep_val_str}' for column '{dep_col}'. Setting as string. Error: {e}", icon="⚠️")
                                      row[dep_col] = dep_val_str # Set as string on failure

                         all_rows.append(row) # Append potentially modified row
                    generated_output = pd.DataFrame(all_rows)
                # ... (Handle SDV methods or other methods if implemented) ...
                else:
                    raise NotImplementedError(f"Method '{method}' not implemented for Tabular data.")

            # --- Generation for other data types (Image, Text, Graph) remains the same ---
            elif dtype == "Image (Basic Shapes)":
                 # ... (Image generation logic as before) ...
                 img_cfg = st.session_state.image; num_items = img_cfg['count']; generated_output = []
                 for i in range(num_items): img = generate_simple_image(img_cfg['width'], img_cfg['height'], img_cfg['bg_color'], img_cfg['shape'], img_cfg['shape_color']); generated_output.append({'filename': f'image_{i}_{img_cfg["shape"]}.png', 'image': img})
            elif dtype == "Text (Basic)":
                 # ... (Text generation logic as before) ...
                 txt_cfg = st.session_state.text; num_items = txt_cfg['count']; faker_method_name = txt_cfg['faker_method']; generated_output = []
                 try: faker_func = getattr(fake, faker_method_name); generated_output = [faker_func() for _ in range(num_items)]
                 except AttributeError: raise ValueError(f"Invalid Faker method: {faker_method_name}")
            elif dtype == "Graph (Basic Random)":
                 # ... (Graph generation logic as before) ...
                 graph_cfg = st.session_state.graph; import networkx as nx; G = generate_graph_basic(graph_cfg['num_nodes'], graph_cfg['num_edges'], graph_cfg['directed']); generated_output = G

            st.session_state.results['data'] = generated_output
            st.session_state.results['message'] = f"Successfully generated {num_items} items of {dtype} data."
        except Exception as e:
            st.session_state.results['error'] = f"Generation failed: {e}"; st.exception(e)
        finally:
            st.session_state.results['is_generating'] = False; st.rerun()

# --- Display Results and Download ---
st.divider()
st.header("5. Results")
# ... (Results display and download section remains the same as the previous version) ...
if st.session_state.results['error']: st.error(st.session_state.results['error'])
elif st.session_state.results['message']: st.success(st.session_state.results['message'])
results_data = st.session_state.results['data']; data_type_generated = st.session_state.config['data_type']
if results_data is not None:
    if data_type_generated == "Tabular" and isinstance(results_data, pd.DataFrame):
        st.dataframe(results_data); csv = results_data.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Tabular Data (CSV)", data=csv, file_name=f"synthetic_tabular_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv")
    elif data_type_generated == "Image (Basic Shapes)" and isinstance(results_data, list):
        st.subheader("Image Preview (First 10)"); cols = st.columns(5)
        for i, img_data in enumerate(results_data[:10]):
            with cols[i % 5]: st.image(img_data['image'], caption=img_data['filename'], width=100)
        zip_buffer = io.BytesIO();
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
            for img_data in results_data: zf.writestr(img_data["filename"], image_to_bytes(img_data["image"]))
        st.download_button(label="Download All Images (ZIP)", data=zip_buffer.getvalue(), file_name=f"synthetic_images_{datetime.now():%Y%m%d_%H%M%S}.zip", mime="application/zip")
    elif data_type_generated == "Text (Basic)" and isinstance(results_data, list):
        st.subheader("Text Samples (First 10)")
        for i, sample in enumerate(results_data[:10]): st.text_area(f"Sample {i+1}", sample, height=50, disabled=True)
        text_content = "\n".join(results_data)
        st.download_button(label="Download Text Samples (TXT)", data=text_content.encode('utf-8'), file_name=f"synthetic_text_{datetime.now():%Y%m%d_%H%M%S}.txt", mime="text/plain")
    elif data_type_generated == "Graph (Basic Random)" and nx and isinstance(results_data, nx.Graph):
         st.subheader("Generated Graph Info"); st.text(f"Nodes: {results_data.number_of_nodes()}, Edges: {results_data.number_of_edges()}")
         st.subheader("Graph Visualization"); graph_img_buf = draw_graph(results_data)
         if graph_img_buf: st.image(graph_img_buf); st.download_button(label="Download Graph Image (PNG)", data=graph_img_buf.getvalue(), file_name=f"synthetic_graph_{datetime.now():%Y%m%d_%H%M%S}.png", mime="image/png")
         edge_list_df = nx.to_pandas_edgelist(results_data); csv_graph = edge_list_df.to_csv(index=False).encode('utf-8')
         st.download_button(label="Download Edge List (CSV)", data=csv_graph, file_name=f"synthetic_graph_edges_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv", key="download_graph_csv")


# --- Footer/Info ---
st.sidebar.markdown("---")
st.sidebar.info("Configure global settings, define specifics per data type (columns, dependencies), then generate.")
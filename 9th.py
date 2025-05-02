# --- START OF MODIFIED 5th.py (Editable Excel Augmentation Mode) ---

import streamlit as st
import pandas as pd
import numpy as np
from faker import Faker
import random
import string
from datetime import datetime, timedelta, date
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
    nx = None; plt = None

# --- Initialize Faker ---
fake = Faker()

# --- Constants ---
# Keep Excel Augmentation Type
DATA_TYPES = ["Tabular", "Excel Augmentation", "Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]
# Add specific column types for the UI editing (consistent across modes)
COLUMN_DATA_TYPES_UI = ["Integer", "Float", "Categorical", "String (Faker)", "String (Regex)", "Date", "Boolean"]
TABULAR_METHODS = ["Rule-Based (Faker/Random/Regex/Deps)", "Statistical (NumPy/SciPy Dist)"]
EXCEL_AUG_METHODS = ["Inferred Schema Generation (Editable)"] # Update name
IMAGE_METHODS = ["Rule-Based (Pillow Shapes)"]
TEXT_METHODS = ["Rule-Based (Faker)"]
GRAPH_METHODS = ["Rule-Based (NetworkX Random)"]
PRIVACY_METHODS = ["None", "Differential Privacy (Conceptual Placeholder)"]
USE_CASES = ["General Purpose / Testing", "Model Training (Consider Fidelity)", "Privacy Preservation (Requires Method)"]
NUMERICAL_DISTS = ["uniform", "normal"] # Keep simplified list, add others if needed
if stats: NUMERICAL_DISTS.extend(["poisson", "gamma", "beta"])
DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"]

# PANDAS_TYPE_MAP - Used for INFERENCE only
PANDAS_TYPE_MAP = {
    'int64': 'Integer', 'Int64': 'Integer',
    'float64': 'Float', 'Float64': 'Float',
    'datetime64[ns]': 'Date', 'timedelta[ns]': 'Date', # Handle timedelta too
    'bool': 'Boolean', 'boolean': 'Boolean',
    'object': 'String (Faker)', 'string': 'String (Faker)', # Handle pandas string type
    'category': 'Categorical'
}

# --- Helper Functions ---
# generate_simple_image, image_to_bytes, generate_graph_basic, draw_graph remain the same
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    img = Image.new('RGB', (width, height), color=bg_color); draw = ImageDraw.Draw(img)
    m = int(min(width, height)*0.15); x1,y1,x2,y2 = m,m,width-m,height-m
    try:
        if shape == 'rectangle': draw.rectangle([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'ellipse': draw.ellipse([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'triangle': draw.polygon([(width//2, y1), (x1, y2), (x2, y2)], fill=shape_color)
    except Exception as e: st.error(f"Error drawing image: {e}")
    # Add text logic if needed (omitted for brevity, can copy from previous versions)
    return img

def image_to_bytes(img, format='PNG'):
    buf = io.BytesIO(); img.save(buf, format=format); return buf.getvalue()

def generate_graph_basic(num_nodes, num_edges, directed=False):
    if not nx: st.error("NetworkX library not installed."); return None
    G = nx.gnm_random_graph(num_nodes, num_edges, directed=directed); return G

def draw_graph(G):
    if not plt or not nx: st.error("Matplotlib/NetworkX not installed."); return None
    fig, ax = plt.subplots(); nx.draw(G, ax=ax, with_labels=True, node_color='skyblue', edge_color='gray')
    buf = io.BytesIO(); fig.savefig(buf, format='png'); plt.close(fig); buf.seek(0); return buf

# --- Generation Logic for Tabular Values (generate_tabular_value) ---
# This function generates a SINGLE value based on a column definition DICT
# It needs to handle the structure used in the EDITABLE state (tabular['columns'] or excel_aug_editable_columns)
def generate_tabular_value(col_def):
    col_type = col_def.get('data_type') # This is the type from COLUMN_DATA_TYPES_UI
    dist = col_def.get('distribution')
    params = col_def.get('params', {})

    try:
        if col_type == "Integer":
            min_v = params.get('min', 0)
            max_v = params.get('max', 100)
            mean_v = params.get('mean', (min_v+max_v)/2)
            std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 10)
            mu_v = params.get('mu', 10) # For poisson

            if dist == "uniform": return random.randint(int(min_v), int(max_v))
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=mean_v, scale=max(0.1, std_v)))
                if 'min' in params: val = max(val, int(params['min'])) # Check bounds from params
                if 'max' in params: val = min(val, int(params['max']))
                return val
            elif dist == "poisson" and stats: return stats.poisson.rvs(mu=max(0, mu_v))
            else: return random.randint(int(min_v), int(max_v)) # Fallback

        elif col_type == "Float":
             min_v = params.get('min', 0.0); max_v = params.get('max', 1.0)
             mean_v = params.get('mean', (min_v+max_v)/2); std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 0.1)
             shape_v = params.get('shape', 2.0); scale_v = params.get('scale', 1.0) # gamma
             a_v = params.get('a', 2.0); b_v = params.get('b', 2.0) # beta

             if dist == "uniform": return random.uniform(min_v, max_v)
             elif dist == "normal" and stats:
                 val = stats.norm.rvs(loc=mean_v, scale=max(0.01, std_v))
                 if 'min' in params: val = max(val, params['min'])
                 if 'max' in params: val = min(val, params['max'])
                 return val
             elif dist == "gamma" and stats: return stats.gamma.rvs(a=max(0.01, shape_v), scale=max(0.01, scale_v))
             elif dist == "beta" and stats: return stats.beta.rvs(a=max(0.01, a_v), b=max(0.01, b_v))
             else: return random.uniform(min_v, max_v) # Fallback

        elif col_type == "String (Faker)":
            faker_type = params.get('faker_type', 'word')
            try: return getattr(fake, faker_type)()
            except AttributeError: return fake.word()
            except Exception as e_faker: st.warning(f"Faker error: {e_faker}"); return fake.word()

        elif col_type == "String (Regex)" and rstr:
            regex = params.get('regex', r'\w{5}')
            try: return rstr.xeger(regex)
            except Exception as e_regex: st.warning(f"Regex error: {e_regex}"); return "".join(random.choices(string.ascii_letters + string.digits, k=5))

        elif col_type == "Categorical":
            choices = params.get('choices', ['A'])
            probs = params.get('probabilities')
            if not choices or not isinstance(choices, list): return None
            if probs and len(probs) == len(choices):
                 try:
                     probs_f = [float(p) for p in probs]; prob_sum = sum(probs_f)
                     if not np.isclose(prob_sum, 1.0): probs_f = [p/prob_sum for p in probs_f] if prob_sum > 0 else [1.0/len(choices)]*len(choices)
                     return np.random.choice(choices, p=probs_f)
                 except (ValueError, TypeError): return random.choice(choices) # Fallback
            else: return random.choice(choices) # Equal probability

        elif col_type == "Date":
            start_dt = params.get('start_date', date.today() - timedelta(days=365))
            end_dt = params.get('end_date', date.today())
            # Ensure date objects
            if isinstance(start_dt, str): start_dt = date.fromisoformat(start_dt)
            if isinstance(end_dt, str): end_dt = date.fromisoformat(end_dt)
            if isinstance(start_dt, datetime): start_dt = start_dt.date()
            if isinstance(end_dt, datetime): end_dt = end_dt.date()
            if not isinstance(start_dt, date) or not isinstance(end_dt, date): start_dt = date.today()-timedelta(days=365); end_dt = date.today()
            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            try: return fake.date_between_dates(date_start=start_dt, date_end=end_dt)
            except Exception: return start_dt # Fallback

        elif col_type == "Boolean":
            return random.choice([True, False])
        else: # Handle simple types from old version if they sneak in? No, stick to UI types.
             return None
    except Exception as e:
        st.error(f"Error generating value for type {col_type}, dist {dist}: {e}")
        return None


# --- Schema Inference Function (infer_schema_from_df) ---
# This function infers schema AND converts it to the EDITABLE column format
def infer_schema_and_convert_for_editing(df):
    inferred_editable_columns = []
    row_count = len(df)
    if row_count == 0:
        st.warning("Uploaded file has no data rows to infer schema from.")
        return []

    sample_size = min(row_count, 5000)
    df_sample = df.sample(sample_size) if row_count > sample_size else df

    for col_name_orig in df.columns:
        col_name = str(col_name_orig)
        col_data = df_sample[col_name].dropna()
        num_unique = col_data.nunique()
        dtype_obj = df[col_name].dtype

        # This dictionary will match the structure of st.session_state.tabular['columns']
        col_def = {'name': col_name, 'params': {}, 'distribution': None}

        # Determine the primary data_type based on PANDAS_TYPE_MAP for UI selection
        base_pandas_type_str = str(dtype_obj)
        ui_data_type = PANDAS_TYPE_MAP.get(base_pandas_type_str, 'String (Faker)')

        try:
            if ui_data_type == 'Integer':
                col_def['data_type'] = 'Integer' # Set the UI type
                if not col_data.empty:
                    min_v = int(col_data.min()); max_v = int(col_data.max())
                    col_def['params']['min'] = min_v; col_def['params']['max'] = max_v
                    # Check if looks categorical
                    if num_unique <= 30 or (sample_size > 0 and num_unique / sample_size < 0.05):
                        col_def['data_type'] = 'Categorical' # OVERRIDE UI type
                        col_def['params']['choices'] = sorted([int(x) for x in col_data.unique()])
                        counts = col_data.value_counts(normalize=True)
                        col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in col_def['params']['choices']]
                        col_def['params'].pop('min', None); col_def['params'].pop('max', None)
                    else: # Treat as numerical integer
                        col_def['distribution'] = 'uniform' # Default distribution
                        col_def['params']['mean'] = float(col_data.mean()) # Add stats for potential edit
                        col_def['params']['std'] = float(col_data.std())
                else: col_def['params']['min'] = 0; col_def['params']['max'] = 100; col_def['distribution'] = 'uniform'

            elif ui_data_type == 'Float':
                col_def['data_type'] = 'Float'
                if not col_data.empty:
                    min_v = float(col_data.min()); max_v = float(col_data.max())
                    col_def['params']['min'] = min_v; col_def['params']['max'] = max_v
                    col_def['distribution'] = 'uniform'
                    col_def['params']['mean'] = float(col_data.mean()); col_def['params']['std'] = float(col_data.std())
                else: col_def['params']['min'] = 0.0; col_def['params']['max'] = 1.0; col_def['distribution'] = 'uniform'

            elif ui_data_type == 'Date':
                col_def['data_type'] = 'Date'
                default_start = date.today() - timedelta(days=365); default_end = date.today()
                if not col_data.empty:
                    try:
                        min_d = pd.to_datetime(col_data.min()).date(); max_d = pd.to_datetime(col_data.max()).date()
                        col_def['params']['start_date'] = min_d; col_def['params']['end_date'] = max_d
                    except Exception: col_def['params']['start_date'] = default_start; col_def['params']['end_date'] = default_end
                else: col_def['params']['start_date'] = default_start; col_def['params']['end_date'] = default_end

            elif ui_data_type == 'Boolean':
                col_def['data_type'] = 'Boolean'

            elif ui_data_type == 'Categorical': # Pandas Categorical type
                 col_def['data_type'] = 'Categorical'
                 col_def['params']['choices'] = list(df[col_name].cat.categories)
                 counts = col_data.value_counts(normalize=True)
                 col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in col_def['params']['choices']]

            elif ui_data_type == 'String (Faker)': # Default for object/string
                # Check if looks like categorical string
                if num_unique <= 50 or (sample_size > 0 and num_unique / sample_size < 0.1):
                    col_def['data_type'] = 'Categorical' # Override UI type
                    choices = sorted([str(x) for x in col_data.unique()])
                    col_def['params']['choices'] = choices
                    counts = col_data.value_counts(normalize=True)
                    col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in choices]
                else: # Treat as general string, guess Faker type for params
                    col_def['data_type'] = 'String (Faker)' # Keep UI type
                    first_val = str(col_data.iloc[0]) if not col_data.empty else ""
                    if re.match(r"[^@]+@[^@]+\.[^@]+", first_val): col_def['params']['faker_type'] = 'email'
                    elif re.match(r"[A-Z][a-z]+ [A-Z][a-z]+", first_val): col_def['params']['faker_type'] = 'name' # Simple name guess
                    elif re.match(r"https?://[^\s]+", first_val): col_def['params']['faker_type'] = 'url'
                    elif len(first_val.split()) > 3: col_def['params']['faker_type'] = 'sentence'
                    else: col_def['params']['faker_type'] = 'word'

            col_def['params']['inferred_dtype'] = base_pandas_type_str # Keep for info

        except Exception as e:
            st.error(f"Error inferring schema for column '{col_name}': {e}")
            col_def['data_type'] = 'String (Faker)'; col_def['params']['faker_type'] = 'word'; col_def['params']['error'] = str(e)

        # IMPORTANT: Remove the top-level 'distribution' key unless it's numeric AND not inferred as Categorical
        if not (col_def['data_type'] in ['Integer', 'Float'] and 'distribution' in col_def):
            col_def.pop('distribution', None)

        inferred_editable_columns.append(col_def)

    st.info("Schema inference complete. Review and edit the column definitions below.")
    return inferred_editable_columns

# --- UI Function for Editing Columns ---
# Takes the session state LIST where columns are stored and a unique prefix for keys
def column_editor_ui(columns_state_list, key_prefix=""):
    if not columns_state_list:
        st.info("No columns defined yet.")
        return

    st.markdown("**Current Column Definitions (Editable)**")
    cols_to_remove_indices = []

    for i, col_def in enumerate(columns_state_list):
        col_name = col_def.get('name', f'col_{i}')
        unique_key = f"{key_prefix}_{i}_{col_name.replace(' ', '_')}"

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1]) # Name, Type, Dist/Action, Remove
            with c1:
                st.markdown(f"**`{col_name}`**") # Display name
            with c2:
                # --- EDIT TYPE ---
                current_type = col_def.get('data_type', 'String (Faker)')
                try: type_idx = COLUMN_DATA_TYPES_UI.index(current_type)
                except ValueError: type_idx = COLUMN_DATA_TYPES_UI.index('String (Faker)') # Fallback
                new_type = st.selectbox("Data Type", COLUMN_DATA_TYPES_UI, index=type_idx, key=f"{unique_key}_type", label_visibility="collapsed")
                if new_type != current_type:
                    col_def['data_type'] = new_type
                    # Reset distribution/params if type changes significantly? Optional.
                    col_def['distribution'] = None
                    col_def['params'] = {} # Clear params on type change
                    st.rerun()

            with c3:
                 # --- EDIT DISTRIBUTION (if applicable) ---
                 current_type = col_def.get('data_type')
                 dist_options = []
                 if current_type in ["Integer", "Float"]: dist_options = NUMERICAL_DISTS
                 # Add more type/distribution mappings if needed later

                 if dist_options:
                     current_dist = col_def.get('distribution')
                     dist_idx = dist_options.index(current_dist) if current_dist in dist_options else 0
                     new_dist = st.selectbox("Distribution", dist_options, index=dist_idx, key=f"{unique_key}_dist", label_visibility="collapsed")
                     if new_dist != current_dist:
                         col_def['distribution'] = new_dist
                         # Clear incompatible params? e.g. mean/std if switching from normal to uniform
                         if new_dist == 'uniform': col_def['params'].pop('mean', None); col_def['params'].pop('std', None)
                         elif new_dist == 'normal': col_def['params'].pop('min', None); col_def['params'].pop('max', None) # Might keep bounds? debatable
                         st.rerun()
                 else:
                     st.caption("N/A") # No distribution for this type

            with c4:
                # --- REMOVE COLUMN ---
                if st.button("❌ Remove", key=f"{unique_key}_remove"):
                    cols_to_remove_indices.append(i)

            # --- EDIT PARAMETERS (inside expander) ---
            with st.expander(f"Configure Parameters for `{col_name}`"):
                col_type = col_def.get('data_type')
                dist = col_def.get('distribution')
                params = col_def.setdefault('params', {}) # Ensure params dict exists

                # Parameter inputs based on selected type and distribution
                # (Logic adapted from the original Tabular "Add/Edit Column" section)
                if col_type == "Integer" or col_type == "Float":
                     format_str = "%.4f" if col_type == "Float" else "%d"
                     if dist == "uniform":
                         params['min'] = st.number_input("Min", value=params.get('min', 0.0 if col_type=='Float' else 0), key=f"{unique_key}_p_min", format=format_str)
                         params['max'] = st.number_input("Max", value=params.get('max', 1.0 if col_type=='Float' else 100), key=f"{unique_key}_p_max", format=format_str)
                     elif dist == "normal":
                         params['mean'] = st.number_input("Mean", value=params.get('mean', 0.5 if col_type=='Float' else 50), key=f"{unique_key}_p_mean", format="%.4f")
                         params['std'] = st.number_input("Std Dev", value=params.get('std', 0.1 if col_type=='Float' else 10), min_value=0.01, key=f"{unique_key}_p_std", format="%.4f")
                         # Add bounds option if needed
                     # Add elif for poisson, gamma, beta params if stats available
                     elif dist == "poisson" and stats: params['mu'] = st.number_input("Mu (Rate λ)", value=params.get('mu', 10), min_value=0, step=1, key=f"{unique_key}_p_poi_mu")
                     # ... add gamma/beta params ...
                     else: st.caption(f"Parameters for '{dist}' distribution.")

                elif col_type == "String (Faker)":
                     common_faker = ['name', 'email', 'address', 'city', 'country', 'job', 'company', 'sentence', 'paragraph', 'word', 'license_plate', 'url', 'uuid4', 'phone_number', 'ssn', 'user_name']
                     params['faker_type'] = st.selectbox("Faker Type", common_faker, index=common_faker.index(params.get('faker_type', 'word')), key=f"{unique_key}_p_faker")

                elif col_type == "String (Regex)":
                     if rstr: params['regex'] = st.text_input("Regex Pattern", value=params.get('regex', r"^\w{5}$"), key=f"{unique_key}_p_regex")
                     else: st.warning("Rstr library not installed.")

                elif col_type == "Categorical":
                     choices_list = params.get('choices', [])
                     choices_str = "\n".join(map(str, choices_list)) # Handle non-string choices from inference
                     choices_new_str = st.text_area("Choices (one per line)", value=choices_str, key=f"{unique_key}_p_choices", height=max(80, len(choices_list)*18))
                     params['choices'] = [c.strip() for c in choices_new_str.split('\n') if c.strip()]
                     # Probability editing (optional, complex UI)
                     # For simplicity, let's not allow editing probabilities easily here.
                     # We'll use the inferred ones if they exist, otherwise equal prob.
                     if 'probabilities' in params: st.caption(f"Using inferred probabilities (Count: {len(params.get('probabilities',[]))})")
                     else: st.caption("Using equal probability for choices.")


                elif col_type == "Date":
                    today = datetime.now().date(); default_start = today-timedelta(days=365); default_end = today
                    start_val = params.get('start_date', default_start); end_val = params.get('end_date', default_end)
                    # Handle potential string dates from initial inference
                    if isinstance(start_val, str): start_val = date.fromisoformat(start_val)
                    if isinstance(end_val, str): end_val = date.fromisoformat(end_val)
                    params['start_date'] = st.date_input("Start Date", value=start_val, key=f"{unique_key}_p_start")
                    params['end_date'] = st.date_input("End Date", value=end_val, key=f"{unique_key}_p_end")

                elif col_type == "Boolean":
                    st.caption("No parameters needed.")
                else:
                    st.caption("Parameters not applicable for this type.")

    # Remove columns marked for deletion (iterate in reverse)
    if cols_to_remove_indices:
        for index in sorted(cols_to_remove_indices, reverse=True):
            del columns_state_list[index]
        st.rerun()


# --- UI Function for Adding New Column ---
# Takes the session state LIST where column should be added and a unique prefix for keys
def add_new_column_ui(columns_state_list, key_prefix=""):
    st.subheader("Add New Manual Column")
    with st.form(f"{key_prefix}_add_col_form", clear_on_submit=True):
        new_col_name = st.text_input("Column Name*", key=f"{key_prefix}_new_name")
        new_col_type = st.selectbox("Data Type", COLUMN_DATA_TYPES_UI, key=f"{key_prefix}_new_type")
        # Minimal params for adding - can be edited later
        submitted = st.form_submit_button("➕ Add Column")
        if submitted:
            if not new_col_name:
                st.warning("Column Name is required.")
            else:
                existing_names = [c.get('name') for c in columns_state_list]
                if new_col_name in existing_names:
                    st.warning(f"Column '{new_col_name}' already exists.")
                else:
                    # Add basic definition, user edits params later
                    new_col_def = {"name": new_col_name, "data_type": new_col_type, "params": {}}
                    # Add default distribution if numeric
                    if new_col_type in ["Integer", "Float"]: new_col_def['distribution'] = 'uniform'
                    columns_state_list.append(new_col_def)
                    st.success(f"Added column '{new_col_name}'. Configure its parameters above.")
                    st.rerun()


# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("Modular Synthetic Data Generator (Editable Excel Aug)")

# --- Initialize Session State ---
default_state = {
    'config': { 'data_type': DATA_TYPES[0], 'use_case': USE_CASES[0], 'privacy_level': PRIVACY_METHODS[0], 'privacy_epsilon': 1.0, 'generation_method': None, 'num_rows': 100 },
    'tabular': { 'columns': [], 'relationships': [] }, # Relationships only for Tabular mode
    # NEW: State for Excel Mode using EDITABLE columns
    'excel_mode': { 'base_df_preview': None, 'excel_aug_editable_columns': [], 'selected_sheet': None, 'num_new_rows': 100, 'file_uploader_key': 0, 'processed_filename': None },
    # State for other modes (unchanged structure)
    'image': { 'count': 10, 'width': 128, 'height': 128, 'bg_color': '#DDDDDD', 'shape': 'rectangle', 'shape_color': '#FF0000' },
    'text': { 'count': 10, 'faker_method': 'sentence' },
    'graph':{ 'num_nodes': 10, 'num_edges': 15, 'directed': False },
    # Results state
    'results': { 'data': None, 'message': None, 'error': None, 'is_generating': False }
}
# Initialize missing keys
for key, value in default_state.items():
    if key not in st.session_state: st.session_state[key] = value
# Ensure nested keys are present
for mode_key, mode_defaults in default_state.items():
    if isinstance(mode_defaults, dict):
        if mode_key not in st.session_state: st.session_state[mode_key] = {} # Ensure mode dict exists
        for sub_key, sub_value in mode_defaults.items():
             if sub_key not in st.session_state.get(mode_key,{}):
                 st.session_state.setdefault(mode_key, {})[sub_key] = sub_value


# --- App Layout ---
# == Sidebar: Global Configuration ==
st.sidebar.header("1. Define Target Data")
selected_data_type = st.sidebar.selectbox( "Select Data Type", DATA_TYPES,
    index=DATA_TYPES.index(st.session_state.config.get('data_type', DATA_TYPES[0])), key="data_type_selector" )
# Reset specific mode state if type changes
if selected_data_type != st.session_state.config.get('data_type'):
    st.session_state.config['data_type'] = selected_data_type
    # Reset relevant states (keep it simple for now)
    st.session_state.results = default_state['results'].copy()
    # Clear specific configs - BE CAREFUL with full resets, might lose work unintentionally
    # if selected_data_type != 'Tabular': st.session_state.tabular = default_state['tabular'].copy()
    # if selected_data_type != 'Excel Augmentation': st.session_state.excel_mode = default_state['excel_mode'].copy()
    st.rerun()

st.session_state.config['use_case'] = st.sidebar.selectbox("Intended Use Case", USE_CASES, index=USE_CASES.index(st.session_state.config['use_case']))
# Privacy config (unchanged)
st.sidebar.header("2. Determine Privacy (Optional)")
st.session_state.config['privacy_level'] = st.sidebar.selectbox("Privacy Method", PRIVACY_METHODS, index=PRIVACY_METHODS.index(st.session_state.config['privacy_level']))
# ... (epsilon input)

st.sidebar.header("3. Generation Method")
current_data_type = st.session_state.config['data_type']
available_methods = []
if current_data_type == "Tabular": available_methods = TABULAR_METHODS
elif current_data_type == "Excel Augmentation": available_methods = EXCEL_AUG_METHODS
elif current_data_type == "Image (Basic Shapes)": available_methods = IMAGE_METHODS
# ... (other modes)

# Update generation method state
current_method = st.session_state.config.get('generation_method')
method_disabled = (current_data_type == "Excel Augmentation") # Disable for Excel Augmentation as method is implicit
if not available_methods: st.session_state.config['generation_method'] = None
elif current_method not in available_methods: st.session_state.config['generation_method'] = available_methods[0]

st.session_state.config['generation_method'] = st.sidebar.selectbox( "Select Method", available_methods,
    index=available_methods.index(st.session_state.config['generation_method']) if st.session_state.config['generation_method'] in available_methods else 0,
    disabled=method_disabled )

# == Main Area: Type-Specific Configuration & Generation ==
st.header(f"Configure: {current_data_type}")

# --- UI specific to Tabular Data ---
if current_data_type == "Tabular":
    st.info("Define columns and relationships manually.")
    st.subheader("Define Columns")
    if st.button("Clear Tabular Config", key="clear_tab_config"):
         st.session_state.tabular = default_state['tabular'].copy(); st.rerun()
    # Use the shared UI editor, passing the correct state key
    column_editor_ui(st.session_state.tabular['columns'], key_prefix="tab")
    st.divider()
    # Use the shared Add column UI
    add_new_column_ui(st.session_state.tabular['columns'], key_prefix="tab")
    st.divider()

    # --- Define Relationships / Dependencies (ONLY for Tabular Mode) ---
    st.subheader("Define Dependencies (Tabular Mode Only)")
    column_names = [c['name'] for c in st.session_state.tabular['columns']]
    if not column_names: st.info("Add columns before defining dependencies.")
    else:
        # (Dependency definition UI - unchanged from 5th.py, uses tabular state)
        with st.expander("Add New Dependency"):
             # ... (Dependency input fields using 'tab' state keys) ...
             rel_cols = st.columns(3)
             with rel_cols[0]: dep_cond_col = st.selectbox("IF Column:", column_names, key="tab_dep_cond_col", index=None)
             with rel_cols[1]: dep_condition = st.selectbox("Condition:", DEPENDENCY_CONDITIONS, key="tab_dep_condition", index=None)
             with rel_cols[2]: dep_cond_val_str = st.text_input("Condition Value:", key="tab_dep_cond_val", help="For 'in list', use comma-sep")
             set_cols = st.columns(2)
             with set_cols[0]: dep_dependent_col = st.selectbox("THEN Set Column:", column_names, key="tab_dep_dep_col", index=None)
             with set_cols[1]: dep_dependent_val_str = st.text_input("To Value:", key="tab_dep_dep_val")
             if st.button("➕ Add Dependency", key="tab_add_dep_btn"):
                  if dep_cond_col and dep_condition and dep_dependent_col is not None and dep_dependent_val_str is not None:
                       if dep_cond_col == dep_dependent_col: st.error("Condition/Dependent cols must be different.")
                       else:
                           # Store strings, parsing happens during generation
                           st.session_state.tabular['relationships'].append({'condition_col': dep_cond_col, 'condition': dep_condition, 'condition_value_str': dep_cond_val_str, 'dependent_col': dep_dependent_col, 'dependent_value_str': dep_dependent_val_str})
                           st.success("Dependency added."); st.rerun() # Rerun to clear fields slightly
                  else: st.warning("Fill all dependency fields.")
        st.subheader("Defined Dependencies")
        # ... (Display/Remove dependencies using tabular state) ...
        if not st.session_state.tabular['relationships']: st.caption("No dependencies defined.")
        else:
             rels_to_remove = []
             for i, rel in enumerate(st.session_state.tabular['relationships']):
                 with st.container(border=True):
                     st.write(f"**Rule {i+1}:** IF `{rel['condition_col']}` {rel['condition']} `{rel['condition_value_str']}` THEN SET `{rel['dependent_col']}` TO `{rel['dependent_value_str']}`")
                     if st.button("❌ Remove", key=f"tab_rel_{i}_remove"): rels_to_remove.append(i)
             if rels_to_remove:
                 for idx in sorted(rels_to_remove, reverse=True): del st.session_state.tabular['relationships'][idx]
                 st.rerun()


# --- *** UPDATED: UI for Excel Augmentation Mode *** ---
elif current_data_type == "Excel Augmentation":
    st.info("Upload Excel -> Review/Edit Inferred Columns -> Add New Columns (Optional) -> Generate")

    # File Uploader with dynamic key
    file_uploader_key = f"excel_uploader_aug_{st.session_state.excel_mode['file_uploader_key']}"
    uploaded_file_aug = st.file_uploader( "Upload Excel File (.xlsx, .xls)", type=['xlsx', 'xls'], key=file_uploader_key )

    # Button to clear Excel config
    if st.session_state.excel_mode.get('excel_aug_editable_columns'):
         if st.button("Clear Excel Config & Upload New", key="clear_excel_config"):
             st.session_state.excel_mode = default_state['excel_mode'].copy() # Reset state
             st.session_state.excel_mode['file_uploader_key'] += 1 # Increment key
             st.session_state.results = default_state['results'].copy() # Clear results too
             st.rerun()

    if uploaded_file_aug:
        # Process only if file is new or no editable columns exist yet
        if uploaded_file_aug.name != st.session_state.excel_mode.get('processed_filename') or not st.session_state.excel_mode.get('excel_aug_editable_columns'):
            try:
                xls = pd.ExcelFile(uploaded_file_aug); sheet_names = xls.sheet_names
                selected_sheet = None
                if len(sheet_names) > 1: selected_sheet = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_aug", index=None, placeholder="Select sheet...")
                else: selected_sheet = sheet_names[0]

                if selected_sheet:
                    with st.spinner(f"Reading '{selected_sheet}' and inferring schema..."):
                        df_uploaded = pd.read_excel(uploaded_file_aug, sheet_name=selected_sheet)
                        st.session_state.excel_mode['base_df_preview'] = df_uploaded.head()
                        # Infer schema AND convert to editable format
                        editable_schema = infer_schema_and_convert_for_editing(df_uploaded)
                        st.session_state.excel_mode['excel_aug_editable_columns'] = editable_schema
                        st.session_state.excel_mode['selected_sheet'] = selected_sheet
                        st.session_state.excel_mode['processed_filename'] = uploaded_file_aug.name
                        st.session_state.results = default_state['results'].copy() # Clear old results
                        st.rerun()
            except Exception as e: st.error(f"Error processing Excel: {e}")

    # Display preview if available
    if st.session_state.excel_mode.get('base_df_preview') is not None:
         st.subheader(f"Preview of Uploaded Data ('{st.session_state.excel_mode['selected_sheet']}')")
         st.dataframe(st.session_state.excel_mode['base_df_preview'])

    # --- Display EDITABLE Columns using the shared UI function ---
    st.divider()
    if st.session_state.excel_mode.get('excel_aug_editable_columns'):
        st.subheader("Review / Edit / Add Columns for Generation")
        # Use the shared editor UI, passing the EXCEL state key
        column_editor_ui(st.session_state.excel_mode['excel_aug_editable_columns'], key_prefix="excel_aug")
        st.divider()
        # Use the shared Add column UI, passing the EXCEL state key
        add_new_column_ui(st.session_state.excel_mode['excel_aug_editable_columns'], key_prefix="excel_aug")
        st.divider()
        # Number of rows input
        st.session_state.excel_mode['num_new_rows'] = st.number_input( "Number of NEW Rows to Generate", min_value=1, max_value=100000,
            value=st.session_state.excel_mode.get('num_new_rows', 100), key="excel_num_rows_input" )
    elif not uploaded_file_aug :
         st.info("Upload an Excel file above to begin.")


# --- UI for other data types (Image, Text, Graph - unchanged) ---
elif current_data_type == "Image (Basic Shapes)":
    # ... (Image config UI) ...
    img_cfg = st.session_state.image; img_cols = st.columns(2)
    with img_cols[0]: img_cfg['count'] = st.number_input("Number of Images", 1, 1000, img_cfg['count']); img_cfg['width'] = st.number_input("Width (px)", 16, 1024, img_cfg['width']); img_cfg['height'] = st.number_input("Height (px)", 16, 1024, img_cfg['height'])
    with img_cols[1]: img_cfg['bg_color'] = st.color_picker("Background Color", img_cfg['bg_color']); img_cfg['shape'] = st.selectbox("Shape", ['rectangle', 'ellipse', 'triangle'], index=['rectangle', 'ellipse', 'triangle'].index(img_cfg['shape'])); img_cfg['shape_color'] = st.color_picker("Shape Color", img_cfg['shape_color'])

elif current_data_type == "Text (Basic)":
    # ... (Text config UI) ...
    txt_cfg = st.session_state.text; txt_cfg['count'] = st.number_input("Number of Text Samples", 1, 5000, txt_cfg['count']); common_faker = ['sentence', 'paragraph', 'text', 'bs', 'catch_phrase']; txt_cfg['faker_method'] = st.selectbox("Faker Text Type", common_faker, index=common_faker.index(txt_cfg['faker_method']))

elif current_data_type == "Graph (Basic Random)":
     # ... (Graph config UI) ...
     if not nx: st.error("NetworkX library not installed.")
     else: graph_cfg = st.session_state.graph; graph_cols = st.columns(2)
     with graph_cols[0]: graph_cfg['num_nodes'] = st.number_input("Number of Nodes", 2, value=graph_cfg['num_nodes'])
     with graph_cols[1]: max_edges = (graph_cfg['num_nodes'] * (graph_cfg['num_nodes'] - 1)) // 2 if graph_cfg['num_nodes'] > 1 else 0; graph_cfg['num_edges'] = st.number_input("Number of Edges", 0, max_edges, min(graph_cfg.get('num_edges',0), max_edges)) # Use .get
     graph_cfg['directed'] = st.checkbox("Directed Graph?", value=graph_cfg['directed'])

# --- Generation Section ---
st.divider()
st.header("4. Generate Data")

# Determine if generation is possible based on the ACTIVE mode's state
generation_possible = False
active_config_key = None # Key to the list of column definitions
num_items_to_gen = 0

if current_data_type == "Tabular" and st.session_state.tabular['columns']:
    generation_possible = True
    active_config_key = 'tabular'
    num_items_to_gen = st.session_state.config.get('num_rows', 100)
elif current_data_type == "Excel Augmentation" and st.session_state.excel_mode['excel_aug_editable_columns']:
    generation_possible = True
    active_config_key = 'excel_mode' # We'll use 'excel_aug_editable_columns' inside this
    num_items_to_gen = st.session_state.excel_mode.get('num_new_rows', 100)
elif current_data_type in ["Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]:
     if current_data_type == "Graph (Basic Random)" and not nx: st.error("Cannot generate Graph: NetworkX missing.")
     else: generation_possible = True; # Num items handled inside generation for these
     if current_data_type == "Image (Basic Shapes)": num_items_to_gen = st.session_state.image['count']
     elif current_data_type == "Text (Basic)": num_items_to_gen = st.session_state.text['count']
     elif current_data_type == "Graph (Basic Random)": num_items_to_gen = st.session_state.graph['num_nodes'] # Use nodes as count item

# Central Generate Button
if generation_possible:
    button_label = f"🚀 Generate {num_items_to_gen} items" if num_items_to_gen > 0 else "🚀 Generate Data"
    if st.button(button_label, key="generate_data", type="primary", disabled=st.session_state.results['is_generating']):
        st.session_state.results['is_generating'] = True
        st.session_state.results['data'] = None
        st.session_state.results['message'] = None
        st.session_state.results['error'] = None
        st.rerun()
elif current_data_type in ["Tabular", "Excel Augmentation"]:
     st.warning(f"Cannot generate {current_data_type} data. Please define/load columns first.")


# --- Generation Logic ---
if st.session_state.results['is_generating']:
    data_type_to_generate = st.session_state.config['data_type'] # Get mode at time of click
    # Get config and row count based on the mode active during the click
    column_config_list = []
    relationships_to_apply = [] # Only for Tabular mode
    row_count = 0

    if data_type_to_generate == "Tabular":
        column_config_list = st.session_state.tabular['columns']
        relationships_to_apply = st.session_state.tabular['relationships']
        row_count = st.session_state.config.get('num_rows', 100)
    elif data_type_to_generate == "Excel Augmentation":
        column_config_list = st.session_state.excel_mode['excel_aug_editable_columns']
        row_count = st.session_state.excel_mode.get('num_new_rows', 100)
        relationships_to_apply = [] # NO relationships applied in Aug mode
    # ... (get counts for image/text/graph if needed here) ...
    elif data_type_to_generate == "Image (Basic Shapes)": row_count = st.session_state.image['count']
    elif data_type_to_generate == "Text (Basic)": row_count = st.session_state.text['count']

    spinner_label = f"Generating {row_count} items of {data_type_to_generate} data..."
    if data_type_to_generate == "Graph (Basic Random)": spinner_label = "Generating Graph..."

    with st.spinner(spinner_label):
        try:
            generated_output = None
            if data_type_to_generate in ["Tabular", "Excel Augmentation"]:
                if not column_config_list: raise ValueError("No columns configured.")
                all_rows_data = []
                col_type_lookup = {col['name']: col['data_type'] for col in column_config_list}

                for _ in range(row_count):
                    row = {col['name']: generate_tabular_value(col) for col in column_config_list}

                    # Apply Dependencies ONLY if in Tabular mode
                    if data_type_to_generate == "Tabular":
                         cols_to_update = {}
                         for rel in relationships_to_apply:
                             try:
                                 cond_col = rel['condition_col']; dep_col = rel['dependent_col']; cond_val_str = rel['condition_value_str']; dep_val_str = rel['dependent_value_str']; condition = rel['condition']
                                 if cond_col not in row or row[cond_col] is None: continue

                                 actual_value = row[cond_col]; condition_met = False; target_cond_type_str = col_type_lookup.get(cond_col, 'unknown').lower()
                                 compare_value = None # Will hold coerced value

                                 # Type Coercion for comparison value based on ACTUAL value type
                                 try:
                                     target_type = type(actual_value)
                                     is_list_condition = condition in ["in list", "not in list"]
                                     if is_list_condition:
                                          list_vals_str = [v.strip() for v in cond_val_str.split(',') if v.strip()]
                                          compare_value = []
                                          for item_str in list_vals_str:
                                               try: compare_value.append(target_type(item_str)) # Coerce list items
                                               except (ValueError, TypeError): compare_value.append(item_str) # Keep as string if fail
                                     elif target_type is date and isinstance(cond_val_str, str): compare_value = date.fromisoformat(cond_val_str)
                                     elif target_type is bool and isinstance(cond_val_str, str): compare_value = cond_val_str.lower() in ['true', '1', 'yes']
                                     elif target_type not in [list, dict, set] and not isinstance(cond_val_str, target_type): # Basic types
                                         compare_value = target_type(cond_val_str)
                                     else: compare_value = cond_val_str # Use raw if complex or already correct type
                                 except (ValueError, TypeError) as e_conv:
                                     st.warning(f"Rel Conv Warn: {e_conv}", icon="⚠️"); compare_value = cond_val_str # Compare raw on error

                                 # Comparison Logic (handle None)
                                 if actual_value is None:
                                      if condition == "equals" and (compare_value is None or str(compare_value).lower() in ['none','null','']): condition_met = True
                                      elif condition == "not equals" and not (compare_value is None or str(compare_value).lower() in ['none','null','']): condition_met = True
                                 else:
                                      try: # Try comparison
                                          if condition == "equals": condition_met = (actual_value == compare_value)
                                          elif condition == "not equals": condition_met = (actual_value != compare_value)
                                          elif condition == "greater than": condition_met = (actual_value > compare_value)
                                          elif condition == "less than": condition_met = (actual_value < compare_value)
                                          elif condition == "in list" and isinstance(compare_value, list): condition_met = (actual_value in compare_value)
                                          elif condition == "not in list" and isinstance(compare_value, list): condition_met = (actual_value not in compare_value)
                                      except TypeError: condition_met = False # Incomparable types

                             except Exception as e_eval: st.error(f"Rel Eval Err: {e_eval}"); condition_met = False

                             if condition_met: cols_to_update[dep_col] = dep_val_str # Store the string value to be assigned

                         # Apply updates for the row
                         for col_to_set, val_str in cols_to_update.items():
                             try: # Cast dependent value based on TARGET column type
                                 target_dep_type_str = col_type_lookup.get(col_to_set, 'unknown').lower(); final_dep_val = val_str
                                 if 'int' in target_dep_type_str: final_dep_val = int(val_str)
                                 elif 'float' in target_dep_type_str: final_dep_val = float(val_str)
                                 elif 'bool' in target_dep_type_str: final_dep_val = val_str.lower() in ['true', '1', 'yes']
                                 elif 'date' in target_dep_type_str: final_dep_val = date.fromisoformat(val_str)
                                 # else: Keep as string (covers String, Categorical etc.)
                                 row[col_to_set] = final_dep_val
                             except (ValueError, TypeError) as e_dep_conv:
                                 st.warning(f"Dep Conv Warn: {e_dep_conv}", icon="⚠️"); row[col_to_set] = val_str # Assign raw string on failure

                    all_rows_data.append(row)
                generated_output = pd.DataFrame(all_rows_data)
                # --- Add Final Type Coercion/Cleanup for DataFrame ---
                for col_def in column_config_list:
                     col_name = col_def['name']
                     target_ui_type = col_def['data_type']
                     if col_name in generated_output.columns:
                          try:
                              current_dtype = generated_output[col_name].dtype
                              if target_ui_type == "Integer" and not pd.api.types.is_integer_dtype(current_dtype):
                                  generated_output[col_name] = pd.to_numeric(generated_output[col_name], errors='coerce').astype('Int64')
                              elif target_ui_type == "Float" and not pd.api.types.is_float_dtype(current_dtype):
                                   generated_output[col_name] = pd.to_numeric(generated_output[col_name], errors='coerce').astype('Float64')
                              elif target_ui_type == "Date" and not pd.api.types.is_datetime64_any_dtype(current_dtype):
                                   generated_output[col_name] = pd.to_datetime(generated_output[col_name], errors='coerce').dt.date
                              elif target_ui_type == "Boolean" and not pd.api.types.is_bool_dtype(current_dtype):
                                   generated_output[col_name] = generated_output[col_name].astype('boolean')
                              # Categorical might need specific handling if not already category dtype
                              elif target_ui_type == "Categorical" and not pd.api.types.is_categorical_dtype(current_dtype):
                                   generated_output[col_name] = generated_output[col_name].astype('category')

                          except Exception as e_final_conv: st.warning(f"Final conversion warning for '{col_name}': {e_final_conv}")

            # ... [Generation logic for Image, Text, Graph - unchanged] ...
            elif data_type_to_generate == "Image (Basic Shapes)":
                 img_cfg = st.session_state.image; generated_output = []
                 for i in range(row_count): img = generate_simple_image(img_cfg['width'], img_cfg['height'], img_cfg['bg_color'], img_cfg['shape'], img_cfg['shape_color']); generated_output.append({'filename': f'image_{i}_{img_cfg["shape"]}.png', 'image': img})
            elif data_type_to_generate == "Text (Basic)":
                 txt_cfg = st.session_state.text; faker_method_name = txt_cfg['faker_method']; generated_output = []
                 try: faker_func = getattr(fake, faker_method_name); generated_output = [faker_func() for _ in range(row_count)]
                 except AttributeError: raise ValueError(f"Invalid Faker method: {faker_method_name}")
            elif data_type_to_generate == "Graph (Basic Random)":
                 graph_cfg = st.session_state.graph; G = generate_graph_basic(graph_cfg['num_nodes'], graph_cfg['num_edges'], graph_cfg['directed']); generated_output = G


            # --- Store results ---
            st.session_state.results['data'] = generated_output
            actual_count = 0
            if isinstance(generated_output, (list, pd.DataFrame)): actual_count = len(generated_output)
            elif nx and isinstance(generated_output, nx.Graph): actual_count = generated_output.number_of_nodes() # Count nodes
            st.session_state.results['message'] = f"Successfully generated {actual_count} items."

        except Exception as e: st.session_state.results['error'] = f"Generation failed: {e}"; st.exception(e)
        finally: st.session_state.results['is_generating'] = False; st.rerun()


# --- Display Results and Download ---
st.divider()
st.header("5. Results")
if st.session_state.results['error']: st.error(st.session_state.results['error'])
elif st.session_state.results['message']: st.success(st.session_state.results['message'])

results_data = st.session_state.results['data']
data_type_generated = st.session_state.config.get('data_type') # Get type generated

if results_data is not None:
    # Display logic handles DataFrames from Tabular and Excel Augmentation
    if data_type_generated in ["Tabular", "Excel Augmentation"] and isinstance(results_data, pd.DataFrame):
         st.dataframe(results_data); csv = results_data.to_csv(index=False).encode('utf-8')
         f_name_prefix = data_type_generated.lower().replace(' ', '_')
         st.download_button(label=f"Download {data_type_generated} Data (CSV)", data=csv, file_name=f"synthetic_{f_name_prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv")
    # ... [Result display/download for Image, Text, Graph - unchanged] ...
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
         for i, sample in enumerate(results_data[:10]): st.text_area(f"Sample {i+1}", sample, height=50, disabled=True, key=f"txt_sample_{i}")
         text_content = "\n---\n".join(results_data); st.download_button(label="Download Text Samples (TXT)", data=text_content.encode('utf-8'), file_name=f"synthetic_text_{datetime.now():%Y%m%d_%H%M%S}.txt", mime="text/plain")
    elif data_type_generated == "Graph (Basic Random)" and nx and isinstance(results_data, nx.Graph):
          st.subheader("Generated Graph Info"); st.text(f"Nodes: {results_data.number_of_nodes()}, Edges: {results_data.number_of_edges()}")
          st.subheader("Graph Visualization"); graph_img_buf = draw_graph(results_data)
          if graph_img_buf: st.image(graph_img_buf); st.download_button(label="Download Graph Image (PNG)", data=graph_img_buf.getvalue(), file_name=f"synthetic_graph_{datetime.now():%Y%m%d_%H%M%S}.png", mime="image/png")
          edge_list_df = nx.to_pandas_edgelist(results_data); csv_graph = edge_list_df.to_csv(index=False).encode('utf-8'); st.download_button(label="Download Edge List (CSV)", data=csv_graph, file_name=f"synthetic_graph_edges_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv", key="download_graph_csv")


# --- Footer/Info ---
st.sidebar.markdown("---")
st.sidebar.info("Configure global settings, define specifics per data type, then generate.")

# --- END OF MODIFIED 5th.py ---
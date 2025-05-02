# --- START OF MODIFIED 4th.py (Excel Augmentation Mode) ---

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
# ... (imports remain the same) ...
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
# *** ADD "Excel Augmentation" Data Type ***
DATA_TYPES = ["Tabular", "Excel Augmentation", "Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]
# *** END ADD ***
TABULAR_METHODS = ["Rule-Based (Faker/Random/Regex/Deps)", "Statistical (NumPy/SciPy Dist)"]
# Methods for Excel Augmentation will implicitly use the inferred schema logic
EXCEL_AUG_METHODS = ["Inferred Schema Generation"] # Placeholder name
IMAGE_METHODS = ["Rule-Based (Pillow Shapes)"]
TEXT_METHODS = ["Rule-Based (Faker)"]
GRAPH_METHODS = ["Rule-Based (NetworkX Random)"]
PRIVACY_METHODS = ["None", "Differential Privacy (Conceptual Placeholder)"]
USE_CASES = ["General Purpose / Testing", "Model Training (Consider Fidelity)", "Privacy Preservation (Requires Method)"]
NUMERICAL_DISTS = ["uniform", "normal", "poisson", "gamma", "beta"]
DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"]

PANDAS_TYPE_MAP = {
    'int64': 'Integer',
    'float64': 'Float',
    'datetime64[ns]': 'Date',
    'bool': 'Boolean',
    'object': 'String (Faker)',
    'category': 'Categorical'
}


# --- Helper Functions ---
# (generate_simple_image, image_to_bytes, generate_graph_basic, draw_graph remain the same)
# ...
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    # ... (implementation unchanged) ...
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
    # ... (implementation unchanged) ...
    buf = io.BytesIO(); img.save(buf, format=format); return buf.getvalue()


def generate_graph_basic(num_nodes, num_edges, directed=False):
    # ... (implementation unchanged) ...
    if not nx: st.error("NetworkX library not installed."); return None
    G = nx.gnm_random_graph(num_nodes, num_edges, directed=directed)
    return G


def draw_graph(G):
    # ... (implementation unchanged) ...
    if not plt or not nx: st.error("Matplotlib/NetworkX not installed."); return None
    fig, ax = plt.subplots(); nx.draw(G, ax=ax, with_labels=True, node_color='skyblue', edge_color='gray')
    buf = io.BytesIO(); fig.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
    return buf


# --- Generation Logic for Tabular (generate_tabular_value remains the same) ---
# This function is REUSED by the Excel Augmentation mode
def generate_tabular_value(col_def):
    # ... (implementation unchanged from previous version) ...
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
            min_param = params.get('min', 0)
            max_param = params.get('max', 100)
            mean_param = params.get('mean', (min_param+max_param)/2 if max_param > min_param else 50)
            std_param = params.get('std', (max_param-min_param)/4 if max_param > min_param else 10)
            mu_param = params.get('mu', 10)

            if dist == "uniform":
                return random.randint(int(min_param), int(max_param))
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=mean_param, scale=max(0.1, std_param))) # Ensure std > 0
                if 'min' in params: val = max(val, int(min_param))
                if 'max' in params: val = min(val, int(max_param))
                return val
            elif dist == "poisson" and stats:
                return stats.poisson.rvs(mu=max(0, mu_param)) # Ensure mu >= 0
            else: return random.randint(int(min_param), int(max_param)) # Fallback

        elif col_type == "Float": # With distributions
             min_param = params.get('min', 0.0)
             max_param = params.get('max', 1.0)
             mean_param = params.get('mean', (min_param+max_param)/2 if max_param > min_param else 0.5)
             std_param = params.get('std', (max_param-min_param)/4 if max_param > min_param else 0.1)
             shape_param = params.get('shape', 2.0)
             scale_param = params.get('scale', 1.0)
             a_param = params.get('a', 2.0)
             b_param = params.get('b', 2.0)

             if dist == "uniform":
                return random.uniform(min_param, max_param)
             elif dist == "normal" and stats:
                 val = stats.norm.rvs(loc=mean_param, scale=max(0.01, std_param)) # Ensure std > 0
                 if 'min' in params: val = max(val, min_param)
                 if 'max' in params: val = min(val, max_param)
                 return val
             elif dist == "gamma" and stats:
                 return stats.gamma.rvs(a=max(0.01, shape_param), scale=max(0.01, scale_param))
             elif dist == "beta" and stats:
                  return stats.beta.rvs(a=max(0.01, a_param), b=max(0.01, b_param))
             else: return random.uniform(min_param, max_param) # Fallback

        elif col_type == "String (Faker)":
            faker_type = params.get('faker_type', 'word')
            try: return getattr(fake, faker_type)()
            except AttributeError: return fake.word()
            except Exception as e_faker:
                st.warning(f"Faker error for {faker_type}: {e_faker}. Falling back to word.")
                return fake.word()
        elif col_type == "String (Regex)" and rstr:
            try: return rstr.xeger(params.get('regex', r'\w{5}'))
            except Exception as e_regex:
                 st.warning(f"Regex error for pattern {params.get('regex')}: {e_regex}. Falling back.")
                 return "".join(random.choices(string.ascii_letters + string.digits, k=5))
        elif col_type == "Categorical":
            choices = params.get('choices', ['A', 'B'])
            probs = params.get('probabilities')
            if not choices: return None
            if not isinstance(choices, list): choices = list(choices)

            if probs and len(probs) == len(choices):
                 try:
                     probs = [float(p) for p in probs]
                     prob_sum = sum(probs)
                     if not np.isclose(prob_sum, 1.0):
                         if prob_sum > 0: probs = [p / prob_sum for p in probs]
                         else: probs = [1.0 / len(choices)] * len(choices)
                     return np.random.choice(choices, p=probs)
                 except (ValueError, TypeError):
                     st.warning("Invalid probabilities format. Using equal probability.")
                     return random.choice(choices)
            else: return random.choice(choices)
        elif col_type == "Date":
            start_dt = params.get('start_date', date.today() - timedelta(days=365))
            end_dt = params.get('end_date', date.today())
            if isinstance(start_dt, datetime): start_dt = start_dt.date()
            if isinstance(end_dt, datetime): end_dt = end_dt.date()
            if isinstance(start_dt, str):
                try: start_dt = date.fromisoformat(start_dt)
                except ValueError: start_dt = date.today() - timedelta(days=365)
            if isinstance(end_dt, str):
                try: end_dt = date.fromisoformat(end_dt)
                except ValueError: end_dt = date.today()

            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            try: return fake.date_between_dates(date_start=start_dt, date_end=end_dt)
            except TypeError: return start_dt
        elif col_type == "Boolean":
            return random.choice([True, False])
        else: return None
    except Exception as e:
        st.error(f"Error generating value for type {col_type}, dist {dist}: {e}")
        return None


# --- Schema Inference Function (infer_schema_from_df remains the same) ---
# This function is REUSED by the Excel Augmentation mode
def infer_schema_from_df(df):
    # ... (implementation unchanged from previous version) ...
    inferred_columns = []
    row_count = len(df)
    if row_count == 0:
        st.warning("Uploaded file has no data rows to infer schema from.")
        return []

    for col_name in df.columns:
        col_data = df[col_name].dropna()
        num_unique = col_data.nunique()
        dtype = df[col_name].dtype

        col_def = {'name': col_name, 'params': {}}
        base_type_str = str(dtype)
        col_def['data_type'] = PANDAS_TYPE_MAP.get(base_type_str, 'String (Faker)')
        col_def['distribution'] = None

        try:
            if pd.api.types.is_integer_dtype(dtype):
                col_def['data_type'] = 'Integer'
                if not col_data.empty:
                    min_v = int(col_data.min())
                    max_v = int(col_data.max())
                    col_def['params']['min'] = min_v
                    col_def['params']['max'] = max_v
                    if num_unique < 20 or (row_count > 0 and num_unique / row_count < 0.05):
                        col_def['data_type'] = 'Categorical'
                        col_def['params']['choices'] = sorted(list(col_data.unique()))
                        col_def['params'].pop('min', None); col_def['params'].pop('max', None)
                    else:
                        col_def['distribution'] = 'uniform'
                        col_def['params']['mean'] = float(col_data.mean())
                        col_def['params']['std'] = float(col_data.std())
                else:
                    col_def['params']['min'] = 0; col_def['params']['max'] = 100 # Default if empty

            elif pd.api.types.is_float_dtype(dtype):
                col_def['data_type'] = 'Float'
                if not col_data.empty:
                    min_v = float(col_data.min())
                    max_v = float(col_data.max())
                    col_def['params']['min'] = min_v
                    col_def['params']['max'] = max_v
                    col_def['distribution'] = 'uniform'
                    col_def['params']['mean'] = float(col_data.mean())
                    col_def['params']['std'] = float(col_data.std())
                else:
                    col_def['params']['min'] = 0.0; col_def['params']['max'] = 1.0 # Default if empty


            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_def['data_type'] = 'Date'
                if not col_data.empty:
                    try:
                        min_d = col_data.min().date()
                        max_d = col_data.max().date()
                        col_def['params']['start_date'] = min_d
                        col_def['params']['end_date'] = max_d
                    except Exception:
                         st.warning(f"Could not determine date range for '{col_name}'. Using defaults.")
                         col_def['params']['start_date'] = date.today() - timedelta(days=365)
                         col_def['params']['end_date'] = date.today()
                else:
                     col_def['params']['start_date'] = date.today() - timedelta(days=365)
                     col_def['params']['end_date'] = date.today()


            elif pd.api.types.is_bool_dtype(dtype):
                col_def['data_type'] = 'Boolean'

            elif pd.api.types.is_categorical_dtype(dtype):
                 col_def['data_type'] = 'Categorical'
                 col_def['params']['choices'] = list(col_data.cat.categories)

            elif pd.api.types.is_object_dtype(dtype):
                if num_unique <= 30 or (row_count > 0 and num_unique / row_count < 0.1):
                    col_def['data_type'] = 'Categorical'
                    choices = sorted([str(x) for x in col_data.unique()])
                    col_def['params']['choices'] = choices
                else:
                    # Basic pattern guessing (can be expanded)
                    first_val = str(col_data.iloc[0]) if not col_data.empty else ""
                    if re.match(r"[^@]+@[^@]+\.[^@]+", first_val): col_def['params']['faker_type'] = 'email'
                    elif re.match(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?", first_val): col_def['params']['faker_type'] = 'date' # Or maybe YYYY-MM-DD?
                    elif re.match(r"[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}", first_val): col_def['params']['faker_type'] = 'uuid4'
                    elif len(first_val.split()) > 3: col_def['params']['faker_type'] = 'sentence' # Guess sentence if long
                    else: col_def['params']['faker_type'] = 'word'
                    col_def['data_type'] = 'String (Faker)' # Set type after guess

            col_def['params']['inferred_dtype'] = base_type_str
            col_def['params']['data_type'] = col_def['data_type']

        except Exception as e:
            st.error(f"Error inferring schema for column '{col_name}': {e}")
            col_def['data_type'] = 'String (Faker)'; col_def['params']['faker_type'] = 'word'; col_def['params']['error'] = str(e)

        inferred_columns.append(col_def)

    st.info("Schema inference is heuristic. Generation will follow these inferred rules.")
    return inferred_columns


# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("Modular Synthetic Data Generator")

# --- Initialize Session State ---
default_state = {
    'config': { 'data_type': DATA_TYPES[0], 'use_case': USE_CASES[0], 'privacy_level': PRIVACY_METHODS[0], 'privacy_epsilon': 1.0, 'generation_method': None, 'num_rows': 100 },
    'tabular': { 'columns': [], 'relationships': [], 'method_config': {} },
    # *** ADD State for Excel Mode ***
    'excel_mode': { 'base_df': None, 'inferred_schema': None, 'selected_sheet': None, 'num_new_rows': 100, 'file_uploader_key': 0 },
    # *** END ADD ***
    'image': { 'count': 10, 'width': 128, 'height': 128, 'bg_color': '#DDDDDD', 'shape': 'rectangle', 'shape_color': '#FF0000', 'method_config': {} },
    'text': { 'count': 10, 'faker_method': 'sentence', 'method_config': {} },
    'graph':{ 'num_nodes': 10, 'num_edges': 15, 'directed': False, 'method_config': {} },
    'ui_state': { 'adding_column': False, 'adding_relationship': False }, # Removed upload state from here
    'results': { 'data': None, 'message': None, 'error': None, 'is_generating': False }
}
for key, value in default_state.items():
    if key not in st.session_state: st.session_state[key] = value


# --- App Layout ---
# == Sidebar: Global Configuration ==
st.sidebar.header("1. Define Target Data")
# Update sidebar logic to reset specific mode state when data_type changes
selected_data_type = st.sidebar.selectbox(
    "Select Data Type",
    DATA_TYPES,
    index=DATA_TYPES.index(st.session_state.config.get('data_type', DATA_TYPES[0])), # Use .get for safety
    key="data_type_selector"
)
# Reset other modes' state if the type changes
if selected_data_type != st.session_state.config.get('data_type'):
    st.session_state.config['data_type'] = selected_data_type
    # Reset specific states (optional, but good practice)
    st.session_state.tabular = default_state['tabular'].copy()
    st.session_state.excel_mode = default_state['excel_mode'].copy()
    st.session_state.image = default_state['image'].copy()
    st.session_state.text = default_state['text'].copy()
    st.session_state.graph = default_state['graph'].copy()
    st.session_state.results = default_state['results'].copy()
    st.rerun() # Rerun immediately to reflect the change and load correct UI

st.session_state.config['use_case'] = st.sidebar.selectbox("Intended Use Case", USE_CASES, index=USE_CASES.index(st.session_state.config['use_case']))

st.sidebar.header("2. Determine Privacy Requirements")
# ... (Privacy config unchanged) ...
st.session_state.config['privacy_level'] = st.sidebar.selectbox("Privacy Method", PRIVACY_METHODS, index=PRIVACY_METHODS.index(st.session_state.config['privacy_level']))
if st.session_state.config['privacy_level'] == "Differential Privacy (Conceptual Placeholder)":
    st.session_state.config['privacy_epsilon'] = st.sidebar.number_input("Epsilon (Lower = More Private)", min_value=0.01, value=st.session_state.config['privacy_epsilon'])
    st.sidebar.warning("Differential Privacy integration is complex and currently a placeholder.")

st.sidebar.header("3. Choose Generation Method")
current_data_type = st.session_state.config['data_type']
available_methods = []
# Assign methods based on the *current* data type
if current_data_type == "Tabular": available_methods = TABULAR_METHODS
elif current_data_type == "Excel Augmentation": available_methods = EXCEL_AUG_METHODS # Use the specific method list
elif current_data_type == "Image (Basic Shapes)": available_methods = IMAGE_METHODS
elif current_data_type == "Text (Basic)": available_methods = TEXT_METHODS
elif current_data_type == "Graph (Basic Random)": available_methods = GRAPH_METHODS

# Set default method if current selection is invalid or not set
current_method = st.session_state.config.get('generation_method')
if not available_methods: # Handle case where no methods are defined
     st.session_state.config['generation_method'] = None
elif current_method not in available_methods:
     st.session_state.config['generation_method'] = available_methods[0]

# Display the selectbox for method
st.session_state.config['generation_method'] = st.sidebar.selectbox(
    "Select Method",
    available_methods,
    index=available_methods.index(st.session_state.config['generation_method']) if st.session_state.config['generation_method'] in available_methods else 0,
    disabled=(current_data_type == "Excel Augmentation") # Disable method selection for Excel mode
)

# == Main Area: Type-Specific Configuration & Generation ==
st.header(f"Configure: {current_data_type}")

# --- UI specific to Tabular Data ---
if current_data_type == "Tabular":
    # Clear Excel state if switching to Tabular
    # st.session_state.excel_mode = default_state['excel_mode'].copy() # Might cause loop if not careful

    # --- Upload section (now only for potentially pre-filling Tabular config) ---
    with st.expander("Optional: Load Initial Config from Excel", expanded=False):
        st.info("Uploading here will infer a schema you can then manually edit below in the 'Tabular' definition sections.")
        uploaded_file_tab = st.file_uploader("Upload Excel (.xlsx, .xls)", type=['xlsx', 'xls'], key="excel_uploader_tab_init")
        inferred_schema_tab = None
        selected_sheet_tab = None

        if uploaded_file_tab:
             try:
                 xls = pd.ExcelFile(uploaded_file_tab)
                 sheet_names = xls.sheet_names
                 if len(sheet_names) > 1:
                     selected_sheet_tab = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_tab_init", index=None, placeholder="Select sheet...")
                 else:
                     selected_sheet_tab = sheet_names[0]

                 if selected_sheet_tab:
                     df_uploaded = pd.read_excel(uploaded_file_tab, sheet_name=selected_sheet_tab)
                     st.write("Preview:")
                     st.dataframe(df_uploaded.head())
                     inferred_schema_tab = infer_schema_from_df(df_uploaded) # Run inference
                     st.write("**Inferred Schema Preview:**")
                     # Display inferred schema simply
                     # ... (Display logic similar to before) ...
                     inferred_display = []
                     for col in inferred_schema_tab:
                          params_preview = {k: v for k, v in col.get('params', {}).items() if k not in ['data_type', 'inferred_dtype']}
                          params_str = ", ".join([f"{k}: {str(v)[:20]}{'...' if len(str(v))>20 else ''}" for k, v in params_preview.items()])
                          dist_str = f", Dist: {col.get('distribution')}" if col.get('distribution') else ""
                          inferred_display.append(f"- **{col['name']}**: `{col['data_type']}`{dist_str} (Params: {params_str if params_str else 'N/A'})")
                     st.markdown("\n".join(inferred_display))


                     if st.button("✅ Apply Inferred Schema to Tabular Config", key="apply_schema_tab_btn"):
                         st.session_state.tabular['columns'] = inferred_schema_tab
                         st.session_state.tabular['relationships'] = [] # Reset relationships
                         st.success("Inferred schema applied. Edit below.")
                         st.rerun()

             except Exception as e:
                 st.error(f"Error processing Excel for Tabular config: {e}")


    st.divider()
    st.subheader("Define Columns (Manually or Edit Inferred)")
    # --- Column Definition UI (remains the same) ---
    # ... (Expander for Add/Edit Column) ...
    with st.expander("Add/Edit Column Definition", expanded=st.session_state.ui_state.get('adding_column', False)):
        # ... (Code for adding/editing columns as before) ...
        col_data_types = ["Numerical (Integer)", "Numerical (Float)", "Categorical (Simple List)", "Boolean", "Date", "Integer", "Float", "Categorical", "String (Faker)", "String (Regex)"]
        new_col_data_type = st.selectbox("Column Data Type", col_data_types, key="new_col_type")
        new_col_params = {'data_type': new_col_data_type}; new_col_dist = None
        param_cols = st.columns(2)
        with param_cols[0]:
            new_col_name = st.text_input("Column Name*", key="new_col_name")
            # ... (Rest of the parameter inputs based on type) ...
            if new_col_data_type == "Numerical (Integer)":
                 new_col_params['min'] = st.number_input("Min", value=0, step=1, key="new_num_int_min")
                 new_col_params['max'] = st.number_input("Max", value=100, step=1, key="new_num_int_max")
            elif new_col_data_type == "Numerical (Float)":
                 new_col_params['min'] = st.number_input("Min", value=0.0, format="%.4f", key="new_num_float_min")
                 new_col_params['max'] = st.number_input("Max", value=1.0, format="%.4f", key="new_num_float_max")
            elif new_col_data_type == "Categorical (Simple List)":
                 choices_str = st.text_area("Choices (comma-separated)", "A,B,C", key="new_cat_simple_choices")
                 new_col_params['choices'] = [c.strip() for c in choices_str.split(',') if c.strip()]
            elif new_col_data_type == "Integer" or new_col_data_type == "Float":
                 num_dists = [d for d in NUMERICAL_DISTS if d in ['uniform', 'normal']]
                 if stats: num_dists.extend([d for d in NUMERICAL_DISTS if d not in ['uniform', 'normal']])
                 new_col_dist = st.selectbox("Distribution", num_dists, key="new_col_dist")
                 new_col_params['distribution'] = new_col_dist
                 format_str = "%.4f" if new_col_data_type == "Float" else None
                 if new_col_dist == "uniform":
                     new_col_params['min'] = st.number_input("Min", value=0.0 if new_col_data_type=="Float" else 0, key="new_col_min", format=format_str)
                     new_col_params['max'] = st.number_input("Max", value=1.0 if new_col_data_type=="Float" else 100, key="new_col_max", format=format_str)
                 elif new_col_dist == "normal":
                     new_col_params['mean'] = st.number_input("Mean", value=0.5 if new_col_data_type=="Float" else 50, key="new_col_mean", format=format_str)
                     new_col_params['std'] = st.number_input("Std Dev", value=0.1 if new_col_data_type=="Float" else 10, min_value=0.01, key="new_col_std", format=format_str)
                     if st.checkbox("Set Min/Max Bounds?", key="new_norm_bounds"):
                        new_col_params['min'] = st.number_input("Min Bound", value=0.0 if new_col_data_type=="Float" else 0, key="new_col_norm_min", format=format_str)
                        new_col_params['max'] = st.number_input("Max Bound", value=1.0 if new_col_data_type=="Float" else 100, key="new_col_norm_max", format=format_str)
                 elif new_col_dist == "poisson": new_col_params['mu'] = st.number_input("Mu (Rate λ)", value=10, min_value=0, step=1, key="new_col_poisson_mu")
                 elif new_col_dist == "gamma": new_col_params['shape'] = st.number_input("Shape (k)", value=2.0, min_value=0.01, key="new_col_gamma_shape", format="%.4f"); new_col_params['scale'] = st.number_input("Scale (θ)", value=1.0, min_value=0.01, key="new_col_gamma_scale", format="%.4f")
                 elif new_col_dist == "beta": new_col_params['a'] = st.number_input("Alpha (a)", value=2.0, min_value=0.01, key="new_col_beta_a", format="%.4f"); new_col_params['b'] = st.number_input("Beta (b)", value=2.0, min_value=0.01, key="new_col_beta_b", format="%.4f")
            elif new_col_data_type == "String (Faker)":
                common_faker = ['name', 'email', 'address', 'city', 'country', 'job', 'company', 'sentence', 'paragraph', 'word', 'license_plate', 'url', 'uuid4', 'phone_number', 'ssn', 'user_name']
                new_col_params['faker_type'] = st.selectbox("Faker Type", common_faker, key="new_col_faker")
            elif new_col_data_type == "String (Regex)":
                 if rstr: new_col_params['regex'] = st.text_input("Regex Pattern", value=r"^[A-Za-z]{3}\d{3}$", key="new_col_regex")
                 else: st.warning("Rstr library not installed. Cannot use Regex.")
            elif new_col_data_type == "Categorical":
                 new_col_params['choices'] = [c.strip() for c in st.text_input("Choices (comma-separated)", "A,B,C", key="new_col_choices").split(',') if c.strip()]
                 if st.checkbox("Specify Probabilities?", key="new_cat_probs_check"):
                      probs_str = st.text_input("Probabilities (comma-separated, matching choices)", key="new_cat_probs_str")
                      try:
                           probs_list = [float(p.strip()) for p in probs_str.split(',') if p.strip()]
                           if len(probs_list) == len(new_col_params['choices']): new_col_params['probabilities'] = probs_list
                           else: st.warning("Number of probabilities must match choices.")
                      except ValueError: st.warning("Invalid probability format (must be numbers).")
            elif new_col_data_type == "Date":
                 today = datetime.now().date(); default_start = today-timedelta(days=365); default_end = today
                 current_start = new_col_params.get('start_date', default_start)
                 current_end = new_col_params.get('end_date', default_end)
                 if isinstance(current_start, str): current_start = date.fromisoformat(current_start) if current_start else default_start
                 if isinstance(current_end, str): current_end = date.fromisoformat(current_end) if current_end else default_end
                 new_col_params['start_date'] = st.date_input("Start Date", value=current_start, key="new_col_start_date")
                 new_col_params['end_date'] = st.date_input("End Date", value=current_end, key="new_col_end_date")
        with param_cols[1]:
            st.write("") # Spacer
            if st.button("➕ Add/Update Column", key="add_col_btn"):
                 # ... (Validation and Add/Update logic) ...
                 error = False
                 if not new_col_name: st.error("Column Name required."); error = True
                 existing_col_index = next((idx for idx, c in enumerate(st.session_state.tabular['columns']) if c['name'] == new_col_name), None)
                 if not error: # Basic validation passed
                     if new_col_data_type not in ["Integer", "Float"]: new_col_dist = None
                     # ... (Specific validation logic from before) ...
                 if not error:
                    col_definition = {"name": new_col_name, "data_type": new_col_data_type, "distribution": new_col_dist, "params": new_col_params}
                    if existing_col_index is not None: st.session_state.tabular['columns'][existing_col_index] = col_definition; st.success(f"Column '{new_col_name}' updated.")
                    else: st.session_state.tabular['columns'].append(col_definition); st.success(f"Column '{new_col_name}' added.")
                    st.session_state.ui_state['adding_column'] = False
                    st.rerun()

    # --- Display Defined Columns (remains the same) ---
    st.subheader("Current Column Definitions")
    # ... (Display logic as before, including remove button) ...
    if not st.session_state.tabular['columns']: st.info("No columns defined yet. Add manually or load from Excel and apply schema.")
    else:
        cols_to_remove = []
        for i, col_def in enumerate(st.session_state.tabular['columns']):
            col_key = f"col_{i}_{col_def['name']}"
            with st.container(border=True):
                 dist_info = col_def.get('distribution'); dist_display_str = f', Dist: {dist_info}' if dist_info else ''
                 st.write(f"**{col_def['name']}** (`{col_def['data_type']}`{dist_display_str})")
                 display_params = {k: v for k, v in col_def.get('params', {}).items() if k != 'data_type'}
                 if display_params:
                     params_str = ", ".join([f"{k}: {str(v)[:30]}{'...' if len(str(v))>30 else ''}" for k, v in display_params.items()])
                     st.caption(f"Params: {params_str}")
                 if st.button("❌ Remove", key=f"{col_key}_remove"): cols_to_remove.append(i)
        if cols_to_remove:
            for index in sorted(cols_to_remove, reverse=True): del st.session_state.tabular['columns'][index]
            st.rerun()


    # --- Define Relationships / Dependencies (remains the same) ---
    st.subheader("Define Dependencies")
    # ... (Dependency definition UI and display logic as before) ...
    column_names = [c['name'] for c in st.session_state.tabular['columns']]
    if not column_names: st.info("Add columns before defining dependencies.")
    else:
        with st.expander("Add New Dependency", expanded=st.session_state.ui_state.get('adding_relationship', False)):
            # ... (UI for adding dependencies) ...
            rel_cols = st.columns(3)
            with rel_cols[0]: dep_cond_col = st.selectbox("IF Column:", column_names, key="dep_cond_col", index=None)
            with rel_cols[1]: dep_condition = st.selectbox("Condition:", DEPENDENCY_CONDITIONS, key="dep_condition", index=None)
            with rel_cols[2]: dep_cond_val_str = st.text_input("Condition Value:", key="dep_cond_val", help="For 'in list', use comma-separated values.")
            set_cols = st.columns(2)
            with set_cols[0]: dep_dependent_col = st.selectbox("THEN Set Column:", column_names, key="dep_dependent_col", index=None)
            with set_cols[1]: dep_dependent_val_str = st.text_input("To Value:", key="dep_dependent_val")
            if st.button("➕ Add Dependency", key="add_dep_btn"):
                 # ... (Add dependency logic) ...
                 if dep_cond_col and dep_condition and dep_dependent_col is not None and dep_dependent_val_str is not None:
                     if dep_cond_col == dep_dependent_col: st.error("Condition column and Dependent column cannot be the same.")
                     else:
                         st.session_state.tabular['relationships'].append({'condition_col': dep_cond_col, 'condition': dep_condition, 'condition_value_str': dep_cond_val_str, 'dependent_col': dep_dependent_col, 'dependent_value_str': dep_dependent_val_str})
                         st.success("Dependency added."); st.session_state.ui_state['adding_relationship'] = False; st.rerun()
                 else: st.warning("Please fill all dependency fields.")
        st.subheader("Defined Dependencies")
        if not st.session_state.tabular['relationships']: st.info("No dependencies defined yet.")
        else:
             # ... (Display dependencies) ...
             rels_to_remove = []
             for i, rel in enumerate(st.session_state.tabular['relationships']):
                 rel_key = f"rel_{i}"
                 with st.container(border=True):
                      st.write(f"**Rule {i+1}:** IF `{rel['condition_col']}` {rel['condition']} `{rel['condition_value_str']}` THEN SET `{rel['dependent_col']}` TO `{rel['dependent_value_str']}`")
                      if st.button("❌ Remove Rule", key=f"{rel_key}_remove"): rels_to_remove.append(i)
             if rels_to_remove:
                 for index in sorted(rels_to_remove, reverse=True): del st.session_state.tabular['relationships'][index]
                 st.rerun()


# --- *** NEW: UI for Excel Augmentation Mode *** ---
elif current_data_type == "Excel Augmentation":
    # Clear Tabular state if switching to Excel mode
    # st.session_state.tabular = default_state['tabular'].copy() # Might cause loop if not careful

    st.info("Upload an Excel file. The generator will infer the schema and generate new rows based on the patterns found in your data (focusing on individual column distributions).")

    # Use a unique key that increments to force re-render of file_uploader on demand
    file_uploader_key = f"excel_uploader_aug_{st.session_state.excel_mode['file_uploader_key']}"
    uploaded_file_aug = st.file_uploader(
        "Upload Excel File (.xlsx, .xls)",
        type=['xlsx', 'xls'],
        key=file_uploader_key # Use the dynamic key
    )

    # Button to clear the current Excel file state and increment the key
    if st.session_state.excel_mode.get('base_df') is not None or st.session_state.excel_mode.get('inferred_schema') is not None:
         if st.button("Clear Uploaded Excel and Start Over"):
             st.session_state.excel_mode = default_state['excel_mode'].copy() # Reset state
             st.session_state.excel_mode['file_uploader_key'] += 1 # Increment key
             st.rerun() # Rerun to show the fresh uploader

    if uploaded_file_aug:
        # Process sheet selection only if base_df is not already loaded
        if st.session_state.excel_mode.get('base_df') is None:
            try:
                xls = pd.ExcelFile(uploaded_file_aug)
                sheet_names = xls.sheet_names
                selected_sheet_aug = None
                if len(sheet_names) > 1:
                    selected_sheet_aug = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_aug", index=None, placeholder="Select the sheet to process...")
                else:
                    selected_sheet_aug = sheet_names[0]
                    st.write(f"Using single sheet: **{selected_sheet_aug}**")

                # If a sheet is selected, read data and infer schema
                if selected_sheet_aug:
                    st.session_state.excel_mode['selected_sheet'] = selected_sheet_aug
                    # Read data
                    df_uploaded = pd.read_excel(uploaded_file_aug, sheet_name=selected_sheet_aug)
                    st.session_state.excel_mode['base_df'] = df_uploaded
                    # Infer schema
                    st.session_state.excel_mode['inferred_schema'] = infer_schema_from_df(df_uploaded)
                    st.rerun() # Rerun to display preview and schema info

            except Exception as e:
                st.error(f"Error reading or processing Excel file: {e}")
                # Reset state on error
                st.session_state.excel_mode = default_state['excel_mode'].copy()
                st.session_state.excel_mode['file_uploader_key'] += 1
                # Don't rerun here, let the error message show


    # Display preview and schema if available
    if st.session_state.excel_mode.get('base_df') is not None:
         st.subheader("Uploaded Data Preview (First 5 Rows)")
         st.dataframe(st.session_state.excel_mode['base_df'].head())

    if st.session_state.excel_mode.get('inferred_schema') is not None:
         st.subheader("Inferred Schema (Read-Only)")
         st.warning("Generation will be based on this inferred schema. Column relationships (correlations) are generally NOT preserved automatically.")
         inferred_schema = st.session_state.excel_mode['inferred_schema']
         inferred_display_aug = []
         for col in inferred_schema:
             params_preview = {k: v for k, v in col.get('params', {}).items() if k not in ['data_type', 'inferred_dtype']}
             params_str = ", ".join([f"{k}: {str(v)[:20]}{'...' if len(str(v))>20 else ''}" for k, v in params_preview.items()])
             dist_str = f", Dist: {col.get('distribution')}" if col.get('distribution') else ""
             inferred_display_aug.append(f"- **{col['name']}**: `{col['data_type']}`{dist_str} (Params: {params_str if params_str else 'N/A'})")
         st.markdown("\n".join(inferred_display_aug))

         st.divider()
         # Get number of new rows
         st.session_state.excel_mode['num_new_rows'] = st.number_input(
                "Number of NEW Rows to Generate",
                min_value=1,
                max_value=100000, # Adjust max
                value=st.session_state.excel_mode.get('num_new_rows', 100),
                key="excel_num_new_rows"
         )


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
     with graph_cols[1]: max_edges = (graph_cfg['num_nodes'] * (graph_cfg['num_nodes'] - 1)) // 2 if graph_cfg['num_nodes'] > 1 else 0; graph_cfg['num_edges'] = st.number_input("Number of Edges", 0, max_edges, min(graph_cfg['num_edges'], max_edges))
     graph_cfg['directed'] = st.checkbox("Directed Graph?", value=graph_cfg['directed'])

# --- Generation Section ---
st.divider()
# Place Generation Header and Button OUTSIDE the mode-specific UI if it applies to all modes that configure something
st.header("4. Generate Data")

# Determine if generation is possible based on mode and state
generation_possible = False
if current_data_type == "Tabular" and st.session_state.tabular['columns']:
    generation_possible = True
elif current_data_type == "Excel Augmentation" and st.session_state.excel_mode.get('inferred_schema'):
    generation_possible = True
elif current_data_type in ["Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]:
     # Add checks if necessary (e.g., networkx installed for graph)
     if current_data_type == "Graph (Basic Random)" and not nx:
          st.error("Cannot generate Graph: NetworkX library not installed.")
     else:
          generation_possible = True


# Central Generate Button
if generation_possible:
    if st.button("🚀 Generate Data", key="generate_data", type="primary", disabled=st.session_state.results['is_generating']):
        st.session_state.results['is_generating'] = True
        st.session_state.results['data'] = None
        st.session_state.results['message'] = None
        st.session_state.results['error'] = None
        st.rerun()
elif current_data_type in ["Tabular", "Excel Augmentation"]:
     st.warning(f"Cannot generate {current_data_type} data. Please configure columns or upload a valid Excel file first.")


if st.session_state.results['is_generating']:
    # Determine number of items based on mode
    num_items_to_generate = 0
    if current_data_type == "Tabular":
        num_items_to_generate = st.session_state.config.get('num_rows', 100)
    elif current_data_type == "Excel Augmentation":
        num_items_to_generate = st.session_state.excel_mode.get('num_new_rows', 100)
    elif current_data_type == "Image (Basic Shapes)":
        num_items_to_generate = st.session_state.image.get('count', 10)
    elif current_data_type == "Text (Basic)":
        num_items_to_generate = st.session_state.text.get('count', 10)
    # Graph generation uses its own node/edge count, not num_items

    with st.spinner(f"Generating {num_items_to_generate if current_data_type != 'Graph (Basic Random)' else ''} items of {current_data_type} data..."):
        try:
            dtype = st.session_state.config['data_type']
            generated_output = None

            if dtype == "Tabular":
                # ... (Tabular generation logic remains the same) ...
                if not st.session_state.tabular['columns']: raise ValueError("No columns defined.")
                columns = st.session_state.tabular['columns']; relationships = st.session_state.tabular['relationships']
                col_type_lookup = {col['name']: col['data_type'] for col in columns}
                all_rows = []
                for _ in range(num_items_to_generate):
                     row = {col['name']: generate_tabular_value(col) for col in columns}
                     # Apply Dependencies
                     for rel in relationships:
                         try:
                              # ... (Dependency eval/apply logic as before) ...
                              cond_col = rel['condition_col']; dep_col = rel['dependent_col']; cond_val_str = rel['condition_value_str']; dep_val_str = rel['dependent_value_str']; condition = rel['condition']
                              if cond_col not in row: continue
                              actual_value = row[cond_col]; condition_met = False; target_cond_type_str = col_type_lookup.get(cond_col, 'unknown').lower(); compare_value = cond_val_str
                              try: # Type Coercion Block
                                  if actual_value is not None:
                                      is_list_condition = condition in ["in list", "not in list"]
                                      if is_list_condition:
                                          list_vals_str = [v.strip() for v in cond_val_str.split(',') if v.strip()]; compare_value = []
                                          item_type = 'string';
                                          if 'int' in target_cond_type_str: item_type = 'int'
                                          elif 'float' in target_cond_type_str: item_type = 'float'
                                          elif 'bool' in target_cond_type_str: item_type = 'bool'
                                          elif 'date' in target_cond_type_str: item_type = 'date'
                                          for item_str in list_vals_str:
                                              try:
                                                  if item_type == 'int': compare_value.append(int(item_str))
                                                  elif item_type == 'float': compare_value.append(float(item_str))
                                                  elif item_type == 'bool': compare_value.append(item_str.lower() in ['true', '1', 'yes'])
                                                  elif item_type == 'date': compare_value.append(date.fromisoformat(item_str))
                                                  else: compare_value.append(item_str)
                                              except ValueError: compare_value.append(item_str)
                                      else: # Single value coercion
                                          if 'int' in target_cond_type_str: compare_value = int(cond_val_str)
                                          elif 'float' in target_cond_type_str: compare_value = float(cond_val_str)
                                          elif 'bool' in target_cond_type_str: compare_value = cond_val_str.lower() in ['true', '1', 'yes']
                                          elif 'date' in target_cond_type_str: compare_value = date.fromisoformat(cond_val_str)
                              except (ValueError, TypeError) as e_conv: # Coercion Failed
                                  st.warning(f"Type conversion failed for condition value '{cond_val_str}' vs column '{cond_col}'. Comparing as strings. Error: {e_conv}", icon="⚠️")
                                  if condition in ["in list", "not in list"]: compare_value = [v.strip() for v in cond_val_str.split(',') if v.strip()]
                                  else: compare_value = cond_val_str
                              # Comparison Block
                              if actual_value is None: # Handle None
                                  if condition == "equals" and (compare_value is None or str(compare_value).lower() in ['none', 'null', '']): condition_met = True
                                  elif condition == "not equals" and not (compare_value is None or str(compare_value).lower() in ['none', 'null', '']): condition_met = True
                              elif condition == "equals": condition_met = (actual_value == compare_value)
                              elif condition == "not equals": condition_met = (actual_value != compare_value)
                              else: # Comparisons assuming not None
                                  try:
                                      if condition == "greater than" and actual_value > compare_value: condition_met = True
                                      elif condition == "less than" and actual_value < compare_value: condition_met = True
                                      elif condition == "in list" and isinstance(compare_value, list) and actual_value in compare_value: condition_met = True
                                      elif condition == "not in list" and isinstance(compare_value, list) and actual_value not in compare_value: condition_met = True
                                  except TypeError: condition_met = False # Incompatible types for >, <
                         except Exception as e: # Error in rule eval
                             st.error(f"Error evaluating dependency rule: {rel}. Error: {e}"); condition_met = False
                         # Apply if Met
                         if condition_met:
                             try: # Cast dependent value
                                 target_dep_type_str = col_type_lookup.get(dep_col, 'unknown').lower(); final_dep_val = dep_val_str
                                 if 'int' in target_dep_type_str: final_dep_val = int(dep_val_str)
                                 elif 'float' in target_dep_type_str: final_dep_val = float(dep_val_str)
                                 elif 'bool' in target_dep_type_str: final_dep_val = dep_val_str.lower() in ['true', '1', 'yes']
                                 elif 'date' in target_dep_type_str: final_dep_val = date.fromisoformat(dep_val_str)
                                 row[dep_col] = final_dep_val
                             except (ValueError, TypeError) as e_dep_conv: # Cast failed
                                  st.warning(f"Type conversion failed for dependent value '{dep_val_str}' for column '{dep_col}'. Setting as string. Error: {e_dep_conv}", icon="⚠️")
                                  row[dep_col] = dep_val_str
                     all_rows.append(row)
                generated_output = pd.DataFrame(all_rows)

            # --- *** NEW: Generation Logic for Excel Augmentation *** ---
            elif dtype == "Excel Augmentation":
                inferred_schema = st.session_state.excel_mode.get('inferred_schema')
                if not inferred_schema:
                    raise ValueError("No inferred schema found. Please upload a valid Excel file.")

                generated_rows = []
                for _ in range(num_items_to_generate): # Use the specific count for new rows
                    new_row = {}
                    for col_def in inferred_schema:
                        # Use the same generation function as the Tabular mode
                        new_row[col_def['name']] = generate_tabular_value(col_def)
                    generated_rows.append(new_row)

                if generated_rows:
                    generated_output = pd.DataFrame(generated_rows)
                else:
                    generated_output = pd.DataFrame(columns=[c['name'] for c in inferred_schema]) # Empty DF with correct columns
            # --- *** END NEW *** ---

            # --- Generation for other data types (Image, Text, Graph) remains the same ---
            elif dtype == "Image (Basic Shapes)":
                 img_cfg = st.session_state.image; generated_output = []
                 for i in range(num_items_to_generate): img = generate_simple_image(img_cfg['width'], img_cfg['height'], img_cfg['bg_color'], img_cfg['shape'], img_cfg['shape_color']); generated_output.append({'filename': f'image_{i}_{img_cfg["shape"]}.png', 'image': img})
            elif dtype == "Text (Basic)":
                 txt_cfg = st.session_state.text; faker_method_name = txt_cfg['faker_method']; generated_output = []
                 try: faker_func = getattr(fake, faker_method_name); generated_output = [faker_func() for _ in range(num_items_to_generate)]
                 except AttributeError: raise ValueError(f"Invalid Faker method: {faker_method_name}")
            elif dtype == "Graph (Basic Random)":
                 graph_cfg = st.session_state.graph; import networkx as nx; G = generate_graph_basic(graph_cfg['num_nodes'], graph_cfg['num_edges'], graph_cfg['directed']); generated_output = G

            st.session_state.results['data'] = generated_output
            # Get actual count generated
            actual_generated_count = 0
            if isinstance(generated_output, (list, pd.DataFrame)): actual_generated_count = len(generated_output)
            elif isinstance(generated_output, nx.Graph): actual_generated_count = generated_output.number_of_nodes() # Count nodes for graph
            st.session_state.results['message'] = f"Successfully generated {actual_generated_count} items of {dtype} data."

        except Exception as e:
            st.session_state.results['error'] = f"Generation failed: {e}"; st.exception(e)
        finally:
            st.session_state.results['is_generating'] = False; st.rerun()

# --- Display Results and Download ---
st.divider()
st.header("5. Results")
if st.session_state.results['error']: st.error(st.session_state.results['error'])
elif st.session_state.results['message']: st.success(st.session_state.results['message'])

results_data = st.session_state.results['data']
data_type_generated = st.session_state.config.get('data_type', 'Unknown') # Get the type that was generated

if results_data is not None:
    # Display logic remains largely the same, handles DataFrames from Tabular and Excel Augmentation
    # ... (code for displaying dataframe, images, text, graph and download buttons) ...
    if data_type_generated in ["Tabular", "Excel Augmentation"] and isinstance(results_data, pd.DataFrame):
         st.dataframe(results_data); csv = results_data.to_csv(index=False).encode('utf-8')
         st.download_button(label=f"Download {data_type_generated} Data (CSV)", data=csv, file_name=f"synthetic_{data_type_generated.lower().replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv")
    elif data_type_generated == "Image (Basic Shapes)" and isinstance(results_data, list):
         # ... (image display and download) ...
         st.subheader("Image Preview (First 10)"); cols = st.columns(5)
         for i, img_data in enumerate(results_data[:10]):
             with cols[i % 5]: st.image(img_data['image'], caption=img_data['filename'], width=100)
         zip_buffer = io.BytesIO();
         with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
             for img_data in results_data: zf.writestr(img_data["filename"], image_to_bytes(img_data["image"]))
         st.download_button(label="Download All Images (ZIP)", data=zip_buffer.getvalue(), file_name=f"synthetic_images_{datetime.now():%Y%m%d_%H%M%S}.zip", mime="application/zip")
    elif data_type_generated == "Text (Basic)" and isinstance(results_data, list):
         # ... (text display and download) ...
         st.subheader("Text Samples (First 10)")
         for i, sample in enumerate(results_data[:10]): st.text_area(f"Sample {i+1}", sample, height=50, disabled=True, key=f"txt_sample_{i}")
         text_content = "\n---\n".join(results_data) # Add separator for readability
         st.download_button(label="Download Text Samples (TXT)", data=text_content.encode('utf-8'), file_name=f"synthetic_text_{datetime.now():%Y%m%d_%H%M%S}.txt", mime="text/plain")
    elif data_type_generated == "Graph (Basic Random)" and nx and isinstance(results_data, nx.Graph):
          # ... (graph display and download) ...
          st.subheader("Generated Graph Info"); st.text(f"Nodes: {results_data.number_of_nodes()}, Edges: {results_data.number_of_edges()}")
          st.subheader("Graph Visualization"); graph_img_buf = draw_graph(results_data)
          if graph_img_buf: st.image(graph_img_buf); st.download_button(label="Download Graph Image (PNG)", data=graph_img_buf.getvalue(), file_name=f"synthetic_graph_{datetime.now():%Y%m%d_%H%M%S}.png", mime="image/png")
          edge_list_df = nx.to_pandas_edgelist(results_data); csv_graph = edge_list_df.to_csv(index=False).encode('utf-8')
          st.download_button(label="Download Edge List (CSV)", data=csv_graph, file_name=f"synthetic_graph_edges_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv", key="download_graph_csv")


# --- Footer/Info ---
st.sidebar.markdown("---")
st.sidebar.info("Configure global settings, define specifics per data type, then generate.")

# --- END OF MODIFIED 4th.py (Excel Augmentation Mode) ---
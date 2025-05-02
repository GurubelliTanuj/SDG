# utils.py
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

# --- Import Constants ---
# Import specific constants needed by functions in this file
from constants import (
    COLUMN_DATA_TYPES_UI, NUMERICAL_DISTS, PANDAS_TYPE_MAP
)

# --- Optional Libraries Check (Keep checks here for functions that use them) ---
try:
    import rstr
except ImportError:
    rstr = None
    # Warning moved to constants.py or main.py potentially
try:
    import scipy.stats as stats # Import specific submodule if preferred
except ImportError:
    stats = None
try:
    import networkx as nx
    import matplotlib.pyplot as plt
except ImportError:
    nx = None; plt = None

# --- Initialize Faker ---
fake = Faker()

# --- Helper Functions (Image/Graph - Unchanged) ---
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    # ... (function definition remains the same) ...
    if width < 1 or height < 1:
        st.error("Image dimensions must be positive.")
        return None
    try:
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        m = int(min(width, height)*0.15)
        x1,y1,x2,y2 = m,m,width-m,height-m
        if x1 >= x2 or y1 >= y2:
             st.warning(f"Image dimensions ({width}x{height}) too small for margins. Drawing shapes at edge.")
             x1, y1, x2, y2 = 0, 0, width - 1, height - 1 # Fallback bounds
        if shape == 'rectangle': draw.rectangle([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'ellipse': draw.ellipse([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'triangle': draw.polygon([(width//2, y1), (x1, y2), (x2, y2)], fill=shape_color)
        return img
    except Exception as e:
        st.error(f"Error generating image: {e}")
        return None


def image_to_bytes(img, format='PNG'):
    # ... (function definition remains the same) ...
    if not isinstance(img, Image.Image): return None
    try:
        buf = io.BytesIO()
        img.save(buf, format=format)
        return buf.getvalue()
    except Exception as e:
        st.error(f"Error converting image to bytes: {e}")
        return None

def generate_graph_basic(num_nodes, num_edges, directed=False):
    # ... (function definition remains the same, includes nx check) ...
    if not nx: st.error("NetworkX library not installed."); return None
    if num_nodes < 0: st.error("Number of nodes must be non-negative."); return None
    if num_edges < 0: st.error("Number of edges must be non-negative."); return None
    max_possible_edges = num_nodes * (num_nodes - 1)
    if not directed: max_possible_edges //= 2
    if num_edges > max_possible_edges and num_nodes > 0:
         st.warning(f"Number of edges ({num_edges}) exceeds maximum possible ({max_possible_edges}) for {num_nodes} nodes. Clipping.")
         num_edges = max_possible_edges
    try:
        G = nx.gnm_random_graph(num_nodes, num_edges, directed=directed)
        return G
    except Exception as e:
        st.error(f"Error generating graph: {e}")
        return None

def draw_graph(G):
    # ... (function definition remains the same, includes checks) ...
    if not plt or not nx: st.error("Matplotlib/NetworkX not installed."); return None
    if not isinstance(G, nx.Graph): st.error("Invalid graph object provided."); return None
    try:
        fig, ax = plt.subplots()
        nx.draw(G, ax=ax, with_labels=True, node_color='skyblue', edge_color='gray')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Error drawing graph: {e}")
        return None

# --- Generation Logic for Single Tabular Value (Unchanged) ---
def generate_tabular_value(col_def):
    # ... (function definition remains the same) ...
    # It uses constants implicitly via global scope or explicitly if imported above
    if not isinstance(col_def, dict): return None
    col_type = col_def.get('data_type')
    dist = col_def.get('distribution')
    params = col_def.get('params', {})
    try:
        if col_type == "Integer":
            min_v = params.get('min', 0); max_v = params.get('max', 100)
            try: min_v, max_v = int(min_v), int(max_v)
            except (ValueError, TypeError): min_v, max_v = 0, 100
            if min_v > max_v: min_v, max_v = max_v, min_v
            mean_v = params.get('mean', (min_v+max_v)/2)
            std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 10)
            mu_v = params.get('mu', 10)
            try: mean_v, std_v, mu_v = float(mean_v), float(std_v), float(mu_v)
            except (ValueError, TypeError): mean_v, std_v, mu_v = (min_v+max_v)/2, 10, 10
            if dist == "uniform": return random.randint(min_v, max_v)
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=mean_v, scale=max(0.1, std_v)))
                bound_min = params.get('min', None); bound_max = params.get('max', None)
                if bound_min is not None:
                     try: val = max(val, int(bound_min))
                     except (ValueError, TypeError): pass
                if bound_max is not None:
                     try: val = min(val, int(bound_max))
                     except (ValueError, TypeError): pass
                return val
            elif dist == "poisson" and stats: return stats.poisson.rvs(mu=max(0, mu_v))
            else: return random.randint(min_v, max_v)
        elif col_type == "Float":
             min_v = params.get('min', 0.0); max_v = params.get('max', 1.0)
             try: min_v, max_v = float(min_v), float(max_v)
             except (ValueError, TypeError): min_v, max_v = 0.0, 1.0
             if min_v > max_v: min_v, max_v = max_v, min_v
             mean_v = params.get('mean', (min_v+max_v)/2); std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 0.1)
             shape_v = params.get('shape', 2.0); scale_v = params.get('scale', 1.0)
             a_v = params.get('a', 2.0); b_v = params.get('b', 2.0)
             try: mean_v, std_v, shape_v, scale_v, a_v, b_v = float(mean_v), float(std_v), float(shape_v), float(scale_v), float(a_v), float(b_v)
             except (ValueError, TypeError): mean_v, std_v, shape_v, scale_v, a_v, b_v = (min_v+max_v)/2, 0.1, 2.0, 1.0, 2.0, 2.0
             if dist == "uniform": return random.uniform(min_v, max_v)
             elif dist == "normal" and stats:
                 val = stats.norm.rvs(loc=mean_v, scale=max(0.01, std_v))
                 bound_min = params.get('min', None); bound_max = params.get('max', None)
                 if bound_min is not None:
                      try: val = max(val, float(bound_min))
                      except (ValueError, TypeError): pass
                 if bound_max is not None:
                      try: val = min(val, float(bound_max))
                      except (ValueError, TypeError): pass
                 return val
             elif dist == "gamma" and stats: return stats.gamma.rvs(a=max(0.01, shape_v), scale=max(0.01, scale_v))
             elif dist == "beta" and stats: return stats.beta.rvs(a=max(0.01, a_v), b=max(0.01, b_v))
             else: return random.uniform(min_v, max_v)
        elif col_type == "String (Faker)":
            faker_type = params.get('faker_type', 'word')
            try:
                 if not isinstance(faker_type, str) or not hasattr(fake, faker_type) or callable(getattr(fake, faker_type)) is False:
                     st.warning(f"Invalid Faker type: '{faker_type}'. Using 'word'.")
                     faker_type = 'word'
                 return getattr(fake, faker_type)()
            except Exception as e_faker:
                 st.warning(f"Faker error ('{faker_type}'): {e_faker}. Using 'word'.")
                 return fake.word()
        elif col_type == "String (Regex)":
            if not rstr: return "REQUIRES_RSTR"
            regex = params.get('regex', r'\w{5}')
            if not isinstance(regex, str) or not regex: regex = r'\w{5}'
            try: return rstr.xeger(regex)
            except Exception as e_regex:
                 st.warning(f"Regex error ('{regex}'): {e_regex}. Using random string.")
                 return "".join(random.choices(string.ascii_letters + string.digits, k=5))
        elif col_type == "Categorical":
            choices = params.get('choices', [])
            if not isinstance(choices, list): choices = []
            valid_choices = [c for c in choices if c is not None and str(c).strip() != ""]
            if not valid_choices: return None
            probs_raw = params.get('probabilities'); valid_probs = None
            if isinstance(probs_raw, list) and len(probs_raw) == len(valid_choices):
                 try:
                     probs_f = [float(p) for p in probs_raw]; prob_sum = sum(probs_f)
                     if prob_sum > 0 and not np.isclose(prob_sum, 1.0): valid_probs = [p/prob_sum for p in probs_f]
                     elif np.isclose(prob_sum, 1.0): valid_probs = probs_f
                     else: valid_probs = [1.0/len(valid_choices)] * len(valid_choices)
                 except (ValueError, TypeError): valid_probs = None
            if valid_probs: return np.random.choice(valid_choices, p=valid_probs)
            else: return random.choice(valid_choices)
        elif col_type == "Date":
            today = datetime.now().date(); default_start = today - timedelta(days=365); default_end = today
            start_dt_raw = params.get('start_date', default_start); end_dt_raw = params.get('end_date', default_end)
            start_dt, end_dt = default_start, default_end
            try:
                if isinstance(start_dt_raw, str): start_dt = date.fromisoformat(start_dt_raw)
                elif isinstance(start_dt_raw, datetime): start_dt = start_dt_raw.date()
                elif isinstance(start_dt_raw, date): start_dt = start_dt_raw
            except (ValueError, TypeError): pass
            try:
                if isinstance(end_dt_raw, str): end_dt = date.fromisoformat(end_dt_raw)
                elif isinstance(end_dt_raw, datetime): end_dt = end_dt_raw.date()
                elif isinstance(end_dt_raw, date): end_dt = end_dt_raw
            except (ValueError, TypeError): pass
            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            try: return fake.date_between_dates(date_start=start_dt, date_end=end_dt)
            except Exception as e_date:
                 st.warning(f"Faker date error: {e_date}. Returning start date.")
                 return start_dt
        elif col_type == "Boolean": return random.choice([True, False])
        else: st.warning(f"Unrecognized type: {col_type}"); return None
    except Exception as e: st.error(f"Value Gen Error ({col_type}/{dist}): {e}"); return None


# --- Schema Inference Function (Unchanged) ---
# Uses PANDAS_TYPE_MAP constant imported from constants.py
def infer_schema_and_convert_for_editing(df):
    # ... (function definition remains the same) ...
    # It uses PANDAS_TYPE_MAP from the imported constants
    inferred_editable_columns = []
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Cannot infer schema from empty or invalid DataFrame.")
        return []
    row_count = len(df); sample_size = min(row_count, 5000)
    df_sample = df.sample(n=sample_size, random_state=42) if row_count > sample_size else df
    for col_name_orig in df.columns:
        col_name = str(col_name_orig)
        col_data_series = df[col_name]
        col_data_sample = df_sample[col_name].dropna()
        num_unique = col_data_sample.nunique()
        dtype_obj = col_data_series.dtype
        col_def = {'name': col_name, 'params': {}, 'distribution': None}
        base_pandas_type_str = str(dtype_obj)
        ui_data_type = PANDAS_TYPE_MAP.get(base_pandas_type_str, 'String (Faker)')
        try:
            if ui_data_type == 'Integer':
                col_def['data_type'] = 'Integer'
                col_data_numeric = pd.to_numeric(col_data_sample, errors='coerce').dropna()
                if not col_data_numeric.empty:
                    min_v = int(col_data_numeric.min()); max_v = int(col_data_numeric.max())
                    col_def['params']['min'] = min_v; col_def['params']['max'] = max_v
                    if num_unique <= 30 or (sample_size > 0 and num_unique / sample_size < 0.05):
                        col_def['data_type'] = 'Categorical'
                        unique_vals = pd.to_numeric(col_data_series.unique(), errors='coerce')
                        unique_vals = unique_vals[~np.isnan(unique_vals)]
                        col_def['params']['choices'] = sorted([int(x) for x in unique_vals])
                        counts = col_data_numeric.value_counts(normalize=True)
                        col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in col_def['params']['choices']]
                        col_def['params'].pop('min', None); col_def['params'].pop('max', None)
                    else:
                        col_def['distribution'] = 'uniform'
                        col_def['params']['mean'] = float(col_data_numeric.mean())
                        col_def['params']['std'] = float(col_data_numeric.std())
                else: col_def['params']['min'] = 0; col_def['params']['max'] = 100; col_def['distribution'] = 'uniform'
            elif ui_data_type == 'Float':
                col_def['data_type'] = 'Float'
                col_data_numeric = pd.to_numeric(col_data_sample, errors='coerce').dropna()
                if not col_data_numeric.empty:
                    min_v = float(col_data_numeric.min()); max_v = float(col_data_numeric.max())
                    col_def['params']['min'] = min_v; col_def['params']['max'] = max_v
                    col_def['distribution'] = 'uniform'
                    col_def['params']['mean'] = float(col_data_numeric.mean()); col_def['params']['std'] = float(col_data_numeric.std())
                else: col_def['params']['min'] = 0.0; col_def['params']['max'] = 1.0; col_def['distribution'] = 'uniform'
            elif ui_data_type == 'Date':
                col_def['data_type'] = 'Date'
                default_start = date.today() - timedelta(days=365); default_end = date.today()
                col_data_dates = pd.to_datetime(col_data_sample, errors='coerce').dropna()
                if not col_data_dates.empty:
                    try:
                        min_d = col_data_dates.min().date(); max_d = col_data_dates.max().date()
                        col_def['params']['start_date'] = min_d; col_def['params']['end_date'] = max_d
                    except Exception: col_def['params']['start_date'] = default_start; col_def['params']['end_date'] = default_end
                else: col_def['params']['start_date'] = default_start; col_def['params']['end_date'] = default_end
            elif ui_data_type == 'Boolean': col_def['data_type'] = 'Boolean'
            elif ui_data_type == 'Categorical':
                 col_def['data_type'] = 'Categorical'
                 if hasattr(col_data_series.dtype, 'categories'): col_def['params']['choices'] = list(col_data_series.dtype.categories)
                 else: col_def['params']['choices'] = list(col_data_sample.unique())
                 counts = col_data_sample.value_counts(normalize=True)
                 col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in col_def['params']['choices']]
            elif ui_data_type == 'String (Faker)':
                if num_unique <= 50 or (sample_size > 0 and num_unique / sample_size < 0.1):
                    col_def['data_type'] = 'Categorical'
                    choices = sorted([str(x) for x in col_data_sample.unique()])
                    col_def['params']['choices'] = choices
                    counts = col_data_sample.value_counts(normalize=True)
                    col_def['params']['probabilities'] = [counts.get(choice, 0) for choice in choices]
                else:
                    col_def['data_type'] = 'String (Faker)'
                    first_val = str(col_data_sample.iloc[0]) if not col_data_sample.empty else ""
                    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", first_val): col_def['params']['faker_type'] = 'email'
                    elif re.match(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", first_val): col_def['params']['faker_type'] = 'name'
                    elif re.match(r"https?://[^\s]+", first_val): col_def['params']['faker_type'] = 'url'
                    elif len(first_val.split()) > 3: col_def['params']['faker_type'] = 'sentence'
                    else: col_def['params']['faker_type'] = 'word'
            col_def['params']['inferred_dtype'] = base_pandas_type_str
        except Exception as e:
            st.error(f"Error inferring details for '{col_name}': {e}")
            col_def['data_type'] = 'String (Faker)'; col_def['params']['faker_type'] = 'word'; col_def['params']['error'] = str(e)
        is_numeric_ui = col_def['data_type'] in ['Integer', 'Float']; is_categorical_ui = col_def['data_type'] == 'Categorical'
        if not (is_numeric_ui and not is_categorical_ui): col_def.pop('distribution', None)
        inferred_editable_columns.append(col_def)
    st.info("Schema inference complete. Review/edit below.")
    return inferred_editable_columns

# --- Shared UI Function for Editing Columns (Unchanged) ---
# Uses COLUMN_DATA_TYPES_UI and NUMERICAL_DISTS constants imported from constants.py
def column_editor_ui(columns_state_list, key_prefix=""):
    # ... (Using the version with simplified keys: f"{key_prefix}_col_{i}") ...
    if not columns_state_list or not isinstance(columns_state_list, list): return
    st.markdown("**Column Definitions (Editable)**"); cols_to_remove_indices = []
    indices = list(range(len(columns_state_list)))
    for i in indices:
        if i >= len(columns_state_list): continue # Defensive check
        col_def = columns_state_list[i]
        if not isinstance(col_def, dict): st.warning(f"Invalid col def idx {i}."); continue
        col_name = col_def.get('name', f'col_{i}'); unique_key = f"{key_prefix}_col_{i}" # Simplified Key
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1: st.markdown(f"**`{col_name}`**")
            with c2: # Type
                current_type = col_def.get('data_type', 'String (Faker)')
                if current_type not in COLUMN_DATA_TYPES_UI: current_type = 'String (Faker)'; col_def['data_type'] = current_type
                type_idx = COLUMN_DATA_TYPES_UI.index(current_type)
                new_type = st.selectbox("Type", COLUMN_DATA_TYPES_UI, index=type_idx, key=f"{unique_key}_type", label_visibility="collapsed")
                if new_type != current_type: col_def['data_type'] = new_type; col_def['distribution'] = None; col_def['params'] = {}; st.rerun()
            with c3: # Distribution
                 current_type = col_def.get('data_type'); dist_options = []
                 if current_type in ["Integer", "Float"]: dist_options = NUMERICAL_DISTS
                 if dist_options:
                     current_dist = col_def.get('distribution')
                     if current_dist not in dist_options: current_dist = dist_options[0] if dist_options else None
                     dist_idx = dist_options.index(current_dist) if current_dist in dist_options else 0
                     new_dist = st.selectbox("Dist", dist_options, index=dist_idx, key=f"{unique_key}_dist", label_visibility="collapsed")
                     if new_dist != current_dist: col_def['distribution'] = new_dist; st.rerun()
                 else: st.caption("N/A"); col_def.pop('distribution', None)
            with c4: # Remove
                if st.button("❌ Remove", key=f"{unique_key}_remove", help=f"Remove '{col_name}'"): cols_to_remove_indices.append(i)
            with st.expander(f"Params for `{col_name}`"): # Parameters
                 # ... (Parameter logic using unique_key prefix remains same) ...
                 col_type = col_def.get('data_type'); dist = col_def.get('distribution'); params = col_def.setdefault('params', {})
                 # (Parameter UI widgets as in previous correct version)
                 if col_type == "Integer" or col_type == "Float":
                     format_str = "%.6f" if col_type == "Float" else "%d"
                     params['min'] = st.number_input("Min/Lower", value=params.get('min', 0.0 if col_type=='Float' else 0), key=f"{unique_key}_p_min", format=format_str)
                     params['max'] = st.number_input("Max/Upper", value=params.get('max', 1.0 if col_type=='Float' else 100), key=f"{unique_key}_p_max", format=format_str)
                     # ... (other numeric distribution params) ...
                 elif col_type == "String (Faker)": # ... (Faker type selectbox) ...
                      common_faker = sorted(['name', 'email', 'address', 'city', 'country', 'job', 'company', 'sentence', 'paragraph', 'word', 'license_plate', 'url', 'uuid4', 'phone_number', 'ssn', 'user_name', 'text', 'bs', 'catch_phrase', 'date', 'time', 'ipv4', 'mac_address'])
                      current_faker = params.get('faker_type', 'word'); faker_idx = common_faker.index(current_faker) if current_faker in common_faker else 0
                      params['faker_type'] = st.selectbox("Faker Type", common_faker, index=faker_idx, key=f"{unique_key}_p_faker")
                      st.caption("Select Faker data type (e.g., 'sentence').")
                 elif col_type == "String (Regex)": # ... (Regex input) ...
                     if rstr: params['regex'] = st.text_input("Regex", value=params.get('regex', r"^\w{5}$"), key=f"{unique_key}_p_regex", help="Py syntax.")
                     else: st.warning("Rstr not installed.")
                 elif col_type == "Categorical": # ... (Categorical choices textarea) ...
                      choices_list = params.get('choices', []); choices_str = "\n".join(map(str, choices_list))
                      choices_new_str = st.text_area("Choices (one/line)", value=choices_str, key=f"{unique_key}_p_choices", height=max(80, len(choices_list)*20))
                      params['choices'] = [c.strip() for c in choices_new_str.splitlines() if c.strip()]
                      st.caption("Define cats. Probabilities equal unless inferred.")
                      if 'probabilities' in params: st.caption(f"(Using inferred probabilities for {len(params.get('probabilities',[]))} categories)")
                 elif col_type == "Date": # ... (Date inputs) ...
                      today = datetime.now().date(); default_start = today-timedelta(days=365); default_end = today
                      start_val = params.get('start_date', default_start); end_val = params.get('end_date', default_end)
                      try: start_val = date.fromisoformat(start_val) if isinstance(start_val, str) else (start_val if isinstance(start_val, date) else default_start)
                      except: start_val = default_start
                      try: end_val = date.fromisoformat(end_val) if isinstance(end_val, str) else (end_val if isinstance(end_val, date) else default_end)
                      except: end_val = default_end
                      params['start_date'] = st.date_input("Start Date", value=start_val, key=f"{unique_key}_p_start")
                      params['end_date'] = st.date_input("End Date", value=end_val, min_value=params['start_date'], key=f"{unique_key}_p_end")
                 elif col_type == "Boolean": st.caption("No parameters needed.")
                 else: st.caption(f"Parameters not applicable for type: {col_type}")

    if cols_to_remove_indices:
        for index in sorted(cols_to_remove_indices, reverse=True):
            if 0 <= index < len(columns_state_list): del columns_state_list[index]
            else: st.warning(f"Failed removal index {index}.")
        st.rerun() # Rerun AFTER list modification


# --- Callback Function for Adding Column ---
def _add_column_callback(columns_list_ref, name_widget_key, type_widget_key):
    """
    Callback function executed when 'Add Column' button is clicked.
    Modifies the state list directly and clears the input.
    """
    new_col_name = st.session_state.get(name_widget_key, "")
    new_col_type = st.session_state.get(type_widget_key, COLUMN_DATA_TYPES_UI[0]) # Default type

    clean_name = new_col_name.strip() if new_col_name else ""
    if not clean_name:
        st.warning("Column Name is required.") # Show warning (will appear on next rerun)
        return # Stop callback execution

    existing_names = [c.get('name') for c in columns_list_ref]
    if clean_name in existing_names:
        st.warning(f"Column '{clean_name}' already exists.") # Show warning
        return # Stop callback execution

    # Add basic definition
    new_col_def = {"name": clean_name, "data_type": new_col_type, "params": {}}
    if new_col_type in ["Integer", "Float"]:
        new_col_def['distribution'] = 'uniform'

    # --- State Modification happens HERE ---
    columns_list_ref.append(new_col_def)

    # --- Clear the input field state ---
    # Note: We clear the state value. The widget will reflect this on the *next* rerun.
    st.session_state[name_widget_key] = ""
    # Resetting selectbox value in state is less critical/easy, rerun handles default

    st.success(f"Added column '{clean_name}'.") # Show success message


# --- Shared UI Function for Adding New Column (REVISED - Use Callback) ---
def add_new_column_ui(columns_state_list, key_prefix=""):
    """Renders UI for adding column, using on_click callback."""
    st.subheader("Add New Manual Column")

    input_key_name = f"{key_prefix}_new_name_input"
    select_key_type = f"{key_prefix}_new_type_select"
    button_key_add = f"{key_prefix}_add_col_button"

    # Widgets remain the same
    st.text_input("Column Name*", key=input_key_name, help="Unique name.")
    st.selectbox("Data Type", COLUMN_DATA_TYPES_UI, key=select_key_type, index=COLUMN_DATA_TYPES_UI.index("String (Faker)"))

    # Button now uses on_click and args
    st.button(
        "➕ Add Column",
        key=button_key_add,
        on_click=_add_column_callback, # Reference the callback function
        args=(
            columns_state_list, # Pass the actual list reference
            input_key_name,     # Pass the key to get the name value
            select_key_type     # Pass the key to get the type value
        )
    )
    # NO st.rerun() here - Streamlit handles rerun after callback finishes
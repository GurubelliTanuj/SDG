import streamlit as st
import pandas as pd
import numpy as np
from faker import Faker
import random
import string
from datetime import datetime, timedelta, date, time
import re
import io
import zipfile
from PIL import Image, ImageDraw
import json

from constants import (
    COLUMN_DATA_TYPES_UI, NUMERICAL_DISTS, PANDAS_TYPE_MAP,
    COMMON_FAKER_PROVIDERS_FOR_NER
)

try: import rstr
except ImportError: rstr = None
try: import scipy.stats as stats
except ImportError: stats = None
try:
    import networkx as nx
    import matplotlib.pyplot as plt
except ImportError: nx = None; plt = None

fake = Faker()

# --- Image/Graph Helpers (Unchanged) ---
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    if width < 1 or height < 1: return None
    try:
        img = Image.new('RGB', (width, height), color=bg_color); draw = ImageDraw.Draw(img)
        m = int(min(width, height)*0.15); x1,y1,x2,y2 = m,m,width-m,height-m
        if x1 >= x2 or y1 >= y2: x1,y1,x2,y2 = 0,0,width-1,height-1
        if shape == 'rectangle': draw.rectangle([x1,y1,x2,y2], fill=shape_color)
        elif shape == 'ellipse': draw.ellipse([x1,y1,x2,y2], fill=shape_color)
        elif shape == 'triangle': draw.polygon([(width//2,y1),(x1,y2),(x2,y2)], fill=shape_color)
        return img
    except: return None

def image_to_bytes(img, format='PNG'):
    if not isinstance(img, Image.Image): return None
    try: buf = io.BytesIO(); img.save(buf, format=format); return buf.getvalue()
    except: return None

def generate_graph_basic(num_nodes, num_edges, directed=False):
    if not nx or num_nodes < 0 or num_edges < 0: return None
    max_edges = num_nodes*(num_nodes-1) // (1 if directed else 2)
    if num_edges > max_edges and num_nodes > 0: num_edges = max_edges
    try: return nx.gnm_random_graph(num_nodes, num_edges, directed=directed)
    except: return None

def draw_graph(G):
    if not plt or not nx or not isinstance(G, nx.Graph): return None
    try:
        fig, ax = plt.subplots(); nx.draw(G, ax=ax, with_labels=True, node_color='skyblue', edge_color='gray')
        buf = io.BytesIO(); fig.savefig(buf, format='png'); plt.close(fig); buf.seek(0); return buf
    except: return None

# --- Tabular Value Generation ---
def generate_tabular_value(col_def):
    if not isinstance(col_def, dict): return None
    item_type = col_def.get('data_type')
    dist = col_def.get('distribution')
    params = col_def.get('params', {})
    try:
        if item_type == "Integer":
            min_v, max_v = int(params.get('min', 0)), int(params.get('max', 100))
            if min_v > max_v: min_v, max_v = max_v, min_v
            mean_v, std_v, mu_v = float(params.get('mean', (min_v+max_v)/2)), float(params.get('std', (max_v-min_v)/4 if max_v > min_v else 10)), float(params.get('mu', 10))
            if dist == "uniform": return random.randint(min_v, max_v)
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=mean_v, scale=max(0.1, std_v)))
                bm, bx = params.get('min'), params.get('max')
                if bm is not None: val = max(val, int(bm))
                if bx is not None: val = min(val, int(bx))
                return val
            elif dist == "poisson" and stats: return stats.poisson.rvs(mu=max(0, mu_v))
            else: return random.randint(min_v, max_v)
        elif item_type == "Float":
             min_v, max_v = float(params.get('min', 0.0)), float(params.get('max', 1.0))
             if min_v > max_v: min_v, max_v = max_v, min_v
             mean_v,std_v,sh_v,sc_v,a_v,b_v = map(float, [params.get('mean', (min_v+max_v)/2), params.get('std', (max_v-min_v)/4 if max_v > min_v else 0.1), params.get('shape',2.0), params.get('scale',1.0), params.get('a',2.0), params.get('b',2.0)])
             if dist == "uniform": return random.uniform(min_v, max_v)
             elif dist == "normal" and stats:
                 val = stats.norm.rvs(loc=mean_v, scale=max(0.01, std_v))
                 bm, bx = params.get('min'), params.get('max')
                 if bm is not None: val = max(val, float(bm))
                 if bx is not None: val = min(val, float(bx))
                 return val
             elif dist == "gamma" and stats: return stats.gamma.rvs(a=max(0.01, sh_v), scale=max(0.01, sc_v))
             elif dist == "beta" and stats: return stats.beta.rvs(a=max(0.01, a_v), b=max(0.01, b_v))
             else: return random.uniform(min_v, max_v)
        elif item_type == "String (Faker)":
            faker_type = params.get('faker_type', 'word')
            if not isinstance(faker_type, str) or not hasattr(fake, faker_type) or not callable(getattr(fake, faker_type)): faker_type = 'word'
            return getattr(fake, faker_type)()
        elif item_type == "String (Regex)":
            if not rstr: return "RSTR_MISSING"
            regex = params.get('regex', r'\w{5}')
            if not isinstance(regex, str) or not regex: regex = r'\w{5}'
            try: return rstr.xeger(regex)
            except: return "".join(random.choices(string.ascii_letters + string.digits, k=5))
        elif item_type == "Categorical":
            choices = [c for c in params.get('choices', []) if c is not None and str(c).strip() != ""]
            if not choices: return None
            probs_raw = params.get('probabilities'); valid_probs = None
            if isinstance(probs_raw, list) and len(probs_raw) == len(choices):
                 try:
                     probs_f = [float(p) for p in probs_raw]; prob_sum = sum(probs_f)
                     if prob_sum > 0 and not np.isclose(prob_sum, 1.0): valid_probs = [p/prob_sum for p in probs_f]
                     elif np.isclose(prob_sum, 1.0): valid_probs = probs_f
                 except: pass
            return np.random.choice(choices, p=valid_probs) if valid_probs else random.choice(choices)
        elif item_type == "Date":
            start_dt_raw, end_dt_raw = params.get('start_date', date.today()-timedelta(days=365)), params.get('end_date', date.today())
            start_dt, end_dt = start_dt_raw, end_dt_raw
            for var_name, raw_val in [('start_dt', start_dt_raw), ('end_dt', end_dt_raw)]:
                val_to_set = raw_val
                if isinstance(raw_val, str):
                    try: val_to_set = date.fromisoformat(raw_val)
                    except ValueError: pass
                elif isinstance(raw_val, datetime): val_to_set = raw_val.date()
                if var_name == 'start_dt': start_dt = val_to_set
                else: end_dt = val_to_set
            if isinstance(start_dt,date) and isinstance(end_dt,date) and start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            elif not (isinstance(start_dt,date) and isinstance(end_dt,date)): start_dt, end_dt = date.today()-timedelta(days=365),date.today()
            return fake.date_between_dates(date_start=start_dt, date_end=end_dt)
        elif item_type == "DateTime (dd-mm-yyyy HH:MM:SS)":
            start_dt_raw = params.get('start_datetime', datetime.now() - timedelta(days=365))
            end_dt_raw = params.get('end_datetime', datetime.now())
            start_dt, end_dt = start_dt_raw, end_dt_raw
            if isinstance(start_dt_raw, str):
                try: start_dt = datetime.fromisoformat(start_dt_raw)
                except ValueError: start_dt = datetime.now() - timedelta(days=365)
            if isinstance(end_dt_raw, str):
                try: end_dt = datetime.fromisoformat(end_dt_raw)
                except ValueError: end_dt = datetime.now()
            if not isinstance(start_dt, datetime): start_dt = datetime.now() - timedelta(days=365) # Ensure datetime
            if not isinstance(end_dt, datetime): end_dt = datetime.now() # Ensure datetime
            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            fake_dt = fake.date_time_between(start_date=start_dt, end_date=end_dt)
            return fake_dt.strftime("%d-%m-%Y %H:%M:%S")
        # --- MODIFICATION: Generate Time (HH:MM) ---
        elif item_type == "Time (HH:MM)":
            fake_time_obj = fake.time_object()
            return fake_time_obj.strftime("%H:%M")
        # --- END MODIFICATION ---
        elif item_type == "Boolean": return random.choice([True, False])
        else: return None
    except Exception as e: st.error(f"ValGenErr ({item_type}/{dist}): {e}"); return None


# --- Schema Inference (Unchanged) ---
def infer_schema_and_convert_for_editing(df):
    inferred_cols = []
    if not isinstance(df, pd.DataFrame) or df.empty: return []
    sample = df.sample(n=min(len(df),5000), random_state=42) if len(df)>5000 else df
    for col_name_orig in df.columns:
        col_name = str(col_name_orig); series, s_sample = df[col_name], sample[col_name].dropna()
        n_unique = s_sample.nunique(); dtype_obj_str = str(series.dtype)
        col_def = {'name': col_name, 'data_type': PANDAS_TYPE_MAP.get(dtype_obj_str, 'String (Faker)'), 'params': {}, 'distribution': None}
        try:
            if col_def['data_type'] == 'Integer':
                num_sample = pd.to_numeric(s_sample, errors='coerce').dropna()
                if not num_sample.empty:
                    min_v,max_v = int(num_sample.min()), int(num_sample.max())
                    col_def['params'].update({'min':min_v, 'max':max_v})
                    if n_unique<=30 or (len(s_sample)>0 and n_unique/len(s_sample)<0.05):
                        col_def['data_type'] = 'Categorical'
                        unq = sorted([int(x) for x in pd.to_numeric(series.unique(),errors='coerce').dropna()])
                        counts = num_sample.value_counts(normalize=True)
                        col_def['params'].update({'choices':unq, 'probabilities':[counts.get(c,0) for c in unq]})
                        col_def['params'].pop('min',None); col_def['params'].pop('max',None)
                    else: col_def.update({'distribution':'uniform', 'params':{**col_def['params'], 'mean':float(num_sample.mean()),'std':float(num_sample.std())}})
                else: col_def.update({'params':{'min':0,'max':100}, 'distribution':'uniform'})
            elif col_def['data_type'] == 'Float':
                num_sample = pd.to_numeric(s_sample, errors='coerce').dropna()
                if not num_sample.empty: col_def.update({'distribution':'uniform', 'params':{'min':float(num_sample.min()),'max':float(num_sample.max()),'mean':float(num_sample.mean()),'std':float(num_sample.std())}})
                else: col_def.update({'params':{'min':0.0,'max':1.0}, 'distribution':'uniform'})
            elif col_def['data_type'] == 'Date':
                date_sample = pd.to_datetime(s_sample,errors='coerce').dropna()
                d_start,d_end = date.today()-timedelta(days=365),date.today()
                if not date_sample.empty:
                    try: col_def['params'].update({'start_date':date_sample.min().date(),'end_date':date_sample.max().date()})
                    except: col_def['params'].update({'start_date':d_start,'end_date':d_end})
                else: col_def['params'].update({'start_date':d_start,'end_date':d_end})
            elif col_def['data_type'] == 'Categorical':
                 choices = list(series.dtype.categories) if hasattr(series.dtype,'categories') else list(s_sample.unique())
                 counts = s_sample.value_counts(normalize=True)
                 col_def['params'].update({'choices':choices,'probabilities':[counts.get(c,0) for c in choices]})
            elif col_def['data_type'] == 'String (Faker)':
                if n_unique<=50 or (len(s_sample)>0 and n_unique/len(s_sample)<0.1):
                    col_def['data_type'] = 'Categorical'
                    choices = sorted([str(x) for x in s_sample.unique()])
                    counts = s_sample.value_counts(normalize=True)
                    col_def['params'].update({'choices':choices,'probabilities':[counts.get(c,0) for c in choices]})
                else:
                    first_val = str(s_sample.iloc[0]) if not s_sample.empty else ""
                    f_type='word';
                    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+",first_val): f_type='email'
                    elif re.match(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",first_val): f_type='name'
                    col_def['params']['faker_type'] = f_type
            col_def['params']['inferred_dtype'] = dtype_obj_str
        except Exception as e: col_def.update({'data_type':'String (Faker)','params':{'faker_type':'word','error':str(e)}})
        if not (col_def['data_type'] in ['Integer','Float'] and col_def['data_type']!='Categorical'): col_def.pop('distribution',None)
        inferred_cols.append(col_def)
    st.info(f"Schema inference: {len(inferred_cols)} columns. Review/edit."); return inferred_cols


# --- Generic Item/Column Editor UI (Unchanged) ---
def column_editor_ui(
    columns_state_list, item_type_options, render_item_params_func,
    item_name_key="name", item_type_key="data_type", item_distribution_key="distribution",
    enable_distribution_select=True, key_prefix=""
):
    if not columns_state_list or not isinstance(columns_state_list, list):
        st.caption("No items defined yet.")
        return
    cols_to_remove_indices = []
    for i in range(len(columns_state_list)):
        item_def = columns_state_list[i]; item_name = item_def.get(item_name_key, f'item_{i}'); unique_key = f"{key_prefix}_item_{i}"
        with st.container(border=True):
            c1,c2,c3,c4 = st.columns([2,1.5,1.5,0.5])
            with c1: st.markdown(f"**`{item_name}`**")
            with c2:
                current_type = item_def.get(item_type_key, item_type_options[0] if item_type_options else None)
                if item_type_options:
                    if current_type not in item_type_options: current_type = item_type_options[0]
                    new_type = st.selectbox("Type", item_type_options, index=item_type_options.index(current_type), key=f"{unique_key}_type", label_visibility="collapsed")
                    if new_type != current_type:
                        item_def[item_type_key] = new_type; item_def['params'] = {}
                        if item_distribution_key in item_def: item_def[item_distribution_key] = None
                        st.rerun()
                else: st.caption("Type N/A")
            with c3:
                if enable_distribution_select and item_def.get(item_type_key) in ["Integer", "Float"]:
                    dist_options = NUMERICAL_DISTS
                    current_dist = item_def.get(item_distribution_key, dist_options[0])
                    if current_dist not in dist_options: current_dist = dist_options[0]
                    new_dist = st.selectbox("Dist", dist_options, index=dist_options.index(current_dist), key=f"{unique_key}_dist", label_visibility="collapsed")
                    if new_dist != current_dist: item_def[item_distribution_key] = new_dist; st.rerun()
                else:
                    if enable_distribution_select: st.caption("Dist N/A")
            with c4:
                if st.button("❌", key=f"{unique_key}_remove", help=f"Remove '{item_name}'"): cols_to_remove_indices.append(i)
            with st.expander(f"Parameters for `{item_name}`"): render_item_params_func(item_def, unique_key)
    if cols_to_remove_indices:
        for index in sorted(cols_to_remove_indices, reverse=True):
            if 0 <= index < len(columns_state_list): del columns_state_list[index]
        st.rerun()

# --- Generic Add New Item UI (Unchanged after previous fix) ---
def _add_new_item_callback(
    actual_columns_list_in_state, name_widget_key, type_widget_key,
    item_name_key, item_type_key, item_distribution_key, default_dist_if_applicable
):
    new_item_name = st.session_state.get(name_widget_key, "").strip()
    new_item_type = st.session_state.get(type_widget_key)
    if not new_item_name: st.warning("Item Name/Label is required."); return
    if new_item_name in [c.get(item_name_key) for c in actual_columns_list_in_state]:
        st.warning(f"Item '{new_item_name}' already exists."); return
    new_item_def = {item_name_key: new_item_name, item_type_key: new_item_type, "params": {}}
    if default_dist_if_applicable and new_item_type in ["Integer", "Float"]:
        new_item_def[item_distribution_key] = default_dist_if_applicable
    actual_columns_list_in_state.append(new_item_def)
    st.session_state[name_widget_key] = ""
    st.success(f"Added item '{new_item_name}'.")

def add_new_column_ui(
    columns_state_list, item_type_options, default_item_type,
    item_name_label="Column Name*", item_name_key="name", item_type_key="data_type",
    item_distribution_key="distribution", default_dist_if_applicable="uniform", key_prefix=""
):
    st.subheader("Add New Manual Item")
    input_key_name = f"{key_prefix}_new_name_input"; select_key_type = f"{key_prefix}_new_type_select"
    st.text_input(item_name_label, key=input_key_name, help="Unique name or label.")
    default_idx = item_type_options.index(default_item_type) if default_item_type and item_type_options and default_item_type in item_type_options else 0
    st.selectbox("Item Type", item_type_options, key=select_key_type, index=default_idx)
    st.button("➕ Add Item", key=f"{key_prefix}_add_item_button", on_click=_add_new_item_callback,
        args=(columns_state_list, input_key_name, select_key_type, item_name_key, item_type_key, item_distribution_key, default_dist_if_applicable))

# --- Parameter UI Renderer for Tabular/Excel ---
def render_tabular_excel_params_ui(item_def, unique_key_prefix):
    col_type = item_def.get('data_type')
    params = item_def.setdefault('params', {})

    if col_type in ["Integer", "Float"]:
        fmt = "%.6f" if col_type=="Float" else "%d"; d_min,d_max=(0.0,1.0)if col_type=="Float"else(0,100)
        params['min'] = st.number_input("Min/Lower", value=params.get('min', d_min), key=f"{unique_key_prefix}_p_min", format=fmt)
        params['max'] = st.number_input("Max/Upper", value=params.get('max', d_max), key=f"{unique_key_prefix}_p_max", format=fmt)
        dist = item_def.get('distribution')
        if dist == "normal":
            params['mean'] = st.number_input("Mean (μ)", value=params.get('mean', (params['min']+params['max'])/2), key=f"{unique_key_prefix}_p_mean", format="%.2f")
            params['std'] = st.number_input("Std Dev (σ)", value=params.get('std', (params['max']-params['min'])/4 if params['max']>params['min'] else 1.0), key=f"{unique_key_prefix}_p_std", format="%.2f",min_value=0.01)
        elif dist == "poisson" and col_type=="Integer": params['mu'] = st.number_input("Rate (μ)", value=params.get('mu',10.0),key=f"{unique_key_prefix}_p_mu_poisson",format="%.2f",min_value=0.1)
        elif dist == "gamma" and col_type=="Float":
            params['shape'] = st.number_input("Shape (k/α)",value=params.get('shape',2.0),key=f"{unique_key_prefix}_p_gamma_shape",format="%.2f",min_value=0.01)
            params['scale'] = st.number_input("Scale (θ/β)",value=params.get('scale',1.0),key=f"{unique_key_prefix}_p_gamma_scale",format="%.2f",min_value=0.01)
        elif dist == "beta" and col_type=="Float":
            params['a'] = st.number_input("Alpha (α)",value=params.get('a',2.0),key=f"{unique_key_prefix}_p_beta_a",format="%.2f",min_value=0.01)
            params['b'] = st.number_input("Beta (β)",value=params.get('b',2.0),key=f"{unique_key_prefix}_p_beta_b",format="%.2f",min_value=0.01)
    elif col_type == "String (Faker)":
        f_prov = COMMON_FAKER_PROVIDERS_FOR_NER
        cur_f = params.get('faker_type','word'); f_idx = f_prov.index(cur_f) if cur_f in f_prov else 0
        params['faker_type'] = st.selectbox("Faker Type",f_prov,index=f_idx,key=f"{unique_key_prefix}_p_faker")
    elif col_type == "String (Regex)":
        if rstr: params['regex'] = st.text_input("Regex Pattern",value=params.get('regex',r"^\w{5}$"),key=f"{unique_key_prefix}_p_regex")
        else: st.warning("`rstr` not found. `pip install rstr`")
    elif col_type == "Categorical":
        choices_l = params.get('choices',[]); choices_s = "\n".join(map(str,choices_l))
        choices_new_s = st.text_area("Choices (one/line)",value=choices_s,key=f"{unique_key_prefix}_p_choices",height=max(80,len(choices_l)*20+20))
        params['choices'] = [c.strip() for c in choices_new_s.splitlines() if c.strip()]
        if 'probabilities' in params and params['probabilities']: st.caption(f"Using inferred probabilities for {len(params['probabilities'])} cats.")
    elif col_type == "Date":
        td = datetime.now().date(); d_s, d_e = td-timedelta(days=365), td
        start_raw, end_raw = params.get('start_date',d_s), params.get('end_date',d_e)
        start_v = date.fromisoformat(start_raw) if isinstance(start_raw,str) else (start_raw if isinstance(start_raw,date) else d_s)
        end_v = date.fromisoformat(end_raw) if isinstance(end_raw,str) else (end_raw if isinstance(end_raw,date) else d_e)
        params['start_date'] = st.date_input("Start Date",value=start_v,key=f"{unique_key_prefix}_p_start_date")
        params['end_date'] = st.date_input("End Date",value=end_v,min_value=params['start_date'],key=f"{unique_key_prefix}_p_end_date")
    elif col_type == "DateTime (dd-mm-yyyy HH:MM:SS)":
        now = datetime.now(); default_start_dt = now - timedelta(days=30); default_end_dt = now
        start_dt_val_raw = params.get('start_datetime', default_start_dt)
        end_dt_val_raw = params.get('end_datetime', default_end_dt)

        start_dt_val = start_dt_val_raw
        if isinstance(start_dt_val_raw, str):
            try: start_dt_val = datetime.fromisoformat(start_dt_val_raw)
            except ValueError: start_dt_val = default_start_dt
        elif not isinstance(start_dt_val_raw, datetime): start_dt_val = default_start_dt

        end_dt_val = end_dt_val_raw
        if isinstance(end_dt_val_raw, str):
            try: end_dt_val = datetime.fromisoformat(end_dt_val_raw)
            except ValueError: end_dt_val = default_end_dt
        elif not isinstance(end_dt_val_raw, datetime): end_dt_val = default_end_dt

        # Use separate date and time inputs for better UI, then combine
        input_start_date = st.date_input("Start Date component", value=start_dt_val.date(), key=f"{unique_key_prefix}_p_start_dt_date_comp")
        input_start_time = st.time_input("Start Time component", value=start_dt_val.time(), key=f"{unique_key_prefix}_p_start_dt_time_comp")
        input_end_date = st.date_input("End Date component", value=end_dt_val.date(), min_value=input_start_date, key=f"{unique_key_prefix}_p_end_dt_date_comp")
        input_end_time = st.time_input("End Time component", value=end_dt_val.time(), key=f"{unique_key_prefix}_p_end_dt_time_comp")

        params['start_datetime'] = datetime.combine(input_start_date, input_start_time)
        params['end_datetime'] = datetime.combine(input_end_date, input_end_time)
        if params['start_datetime'] > params['end_datetime']:
            st.warning("Start DateTime is after End DateTime. Swapping them for generation.")

    # --- MODIFICATION: Parameter UI for Time (HH:MM) ---
    elif col_type == "Time (HH:MM)":
        st.caption("Generates random time in HH:MM format using Faker. No specific start/end time parameters are used for generation with `fake.time_object()`.")
        # If you wanted to add input for a specific time (though generation doesn't use it yet without custom logic):
        # current_time_str = params.get('specific_time', "10:30")
        # try:
        #     current_time_obj = datetime.strptime(current_time_str, "%H:%M").time()
        # except ValueError:
        #     current_time_obj = time(10, 30) # Default if parsing fails
        #
        # new_time_obj = st.time_input("Specific Time (HH:MM) (Optional)", value=current_time_obj, step=60, key=f"{unique_key_prefix}_p_specific_time")
        # params['specific_time'] = new_time_obj.strftime("%H:%M")
    # --- END MODIFICATION ---
    elif col_type == "Boolean": st.caption("No parameters needed.")
    else: st.caption(f"Params not applicable for type: {col_type}")


# --- File Reading Utility (Unchanged) ---
def read_text_from_file(uploaded_file, text_column=None, file_type_hint=None):
    if uploaded_file is None: return []
    content = []; file_name = uploaded_file.name.lower()
    actual_file_type = file_type_hint
    if not actual_file_type:
        if file_name.endswith(".txt"): actual_file_type = "txt"
        elif file_name.endswith(".csv"): actual_file_type = "csv"
        elif file_name.endswith(".jsonl") or file_name.endswith(".json"): actual_file_type = "jsonl"
        else: st.error(f"Unsupported file type: {file_name}."); return []
    try:
        if actual_file_type == "txt":
            raw_bytes = uploaded_file.read()
            try: text_data = raw_bytes.decode('utf-8')
            except UnicodeDecodeError: text_data = raw_bytes.decode('latin-1')
            content = [line for line in text_data.splitlines() if line.strip()]
        elif actual_file_type == "csv":
            df = pd.read_csv(uploaded_file)
            if text_column and text_column in df.columns: content = df[text_column].astype(str).dropna().tolist()
            elif not text_column and len(df.columns)==1: content = df.iloc[:,0].astype(str).dropna().tolist(); st.info(f"Using only column '{df.columns[0]}' from CSV.")
            elif not text_column: st.error("CSV has multiple columns. Specify text column."); return None
            else: st.error(f"Column '{text_column}' not in CSV. Available: {', '.join(df.columns)}"); return None
        elif actual_file_type == "jsonl":
            lines = uploaded_file.read().decode('utf-8').splitlines()
            if not text_column: st.error("For JSONL, specify field with text."); return None
            for line in lines:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if text_column in record and isinstance(record[text_column],str): content.append(record[text_column])
                    except json.JSONDecodeError: st.warning(f"Skipping invalid JSON: {line[:100]}...")
            if not content and lines: st.warning(f"No text extracted from JSONL. Check field '{text_column}'.")
    except Exception as e: st.error(f"Error reading {uploaded_file.name}: {e}"); return []
    if not content: st.warning("No text content extracted."); return []
    return content
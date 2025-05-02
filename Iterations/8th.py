# synthetic_app_integrated.py
import streamlit as st
import pandas as pd
import numpy as np
from faker import Faker
import random
import string # Added for fallback generation
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import re # Added for schema inference guessing
import datetime # Import datetime (ensure date/time types are handled)
from datetime import date, timedelta # Specific imports

# --- Optional Libs ---
try:
    import rstr
except ImportError:
    rstr = None
try:
    from scipy import stats
except ImportError:
    stats = None

fake = Faker()

# --- Constants ---
PANDAS_TYPE_MAP = { # Mapping for inference
    'int64': 'Integer', 'Int64': 'Integer',
    'float64': 'Float', 'Float64': 'Float',
    'datetime64[ns]': 'Date',
    'timedelta64[ns]': 'Date', # Treat timedelta as date range for simplicity
    'bool': 'Boolean', 'boolean': 'Boolean',
    'object': 'String (Faker)', # Default for object
    'category': 'Categorical'
}
DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"]
NUMERICAL_DISTS = ["uniform", "normal"] # Simplified list, add more if needed
if stats: NUMERICAL_DISTS.extend(["poisson", "gamma", "beta"]) # Add scipy dists if available


# --- Helper Functions ---

# Function to generate a single value based on column definition
# (Adapted from 5th.py, aligned with 7th.py's types/dists)
def generate_tabular_value(col_def):
    col_type = col_def.get('type') # Use 'type' as used in 7th.py's config
    dist = col_def.get('distribution')
    params = col_def # Inferred schema passes params directly in col_def

    try:
        if col_type == 'integer':
            min_v = params.get('min', 0)
            max_v = params.get('max', 100)
            mean_v = params.get('mean', (min_v+max_v)/2)
            std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 10)
            mu_v = params.get('mu', 10) # For poisson

            if dist == "uniform":
                return random.randint(int(min_v), int(max_v))
            elif dist == "normal" and stats:
                val = int(stats.norm.rvs(loc=mean_v, scale=max(0.1, std_v)))
                if 'min' in params: val = max(val, int(min_v))
                if 'max' in params: val = min(val, int(max_v))
                return val
            elif dist == "poisson" and stats:
                return stats.poisson.rvs(mu=max(0, mu_v))
            else: # Fallback to uniform
                return random.randint(int(min_v), int(max_v))

        elif col_type == 'float':
            min_v = params.get('min', 0.0)
            max_v = params.get('max', 1.0)
            mean_v = params.get('mean', (min_v+max_v)/2)
            std_v = params.get('std', (max_v-min_v)/4 if max_v > min_v else 0.1)
            shape_v = params.get('shape', 2.0) # gamma, beta
            scale_v = params.get('scale', 1.0) # gamma
            a_v = params.get('a', 2.0) # beta
            b_v = params.get('b', 2.0) # beta

            if dist == "uniform":
                return random.uniform(min_v, max_v)
            elif dist == "normal" and stats:
                val = stats.norm.rvs(loc=mean_v, scale=max(0.01, std_v))
                if 'min' in params: val = max(val, min_v)
                if 'max' in params: val = min(val, max_v)
                return val
            elif dist == "gamma" and stats:
                 return stats.gamma.rvs(a=max(0.01, shape_v), scale=max(0.01, scale_v))
            elif dist == "beta" and stats:
                  return stats.beta.rvs(a=max(0.01, a_v), b=max(0.01, b_v))
            else: # Fallback to uniform
                 return random.uniform(min_v, max_v)

        elif col_type == 'string':
            faker_type = params.get('faker_type', 'word') # Infer schema might add this
            regex = params.get('regex')
            choices = params.get('choices') # Infer schema might add this
            probs = params.get('probabilities') # Infer schema might add this

            if dist == 'choice' and choices:
                 if probs and len(probs) == len(choices):
                     try:
                         probs_f = [float(p) for p in probs]
                         if not np.isclose(sum(probs_f), 1.0): # Normalize if not sum to 1
                             probs_f = np.array(probs_f) / np.sum(probs_f)
                         return np.random.choice(choices, p=probs_f)
                     except (ValueError, TypeError):
                         return random.choice(choices) # Fallback on error
                 else:
                      return random.choice(choices)
            elif dist == 'name': return fake.name()
            elif dist == 'city': return fake.city()
            elif dist == 'email': return fake.email()
            elif dist == 'text': return fake.sentence(nb_words=params.get('num_words', 6))
            elif dist == 'uuid': return str(fake.uuid4())
            elif dist == 'custom_regex' and regex and rstr:
                 try: return rstr.xeger(regex)
                 except Exception: return "".join(random.choices(string.ascii_letters + string.digits, k=8)) # Fallback
            elif faker_type: # Handle inferred faker type
                try: return getattr(fake, faker_type)()
                except AttributeError: return fake.word() # Fallback
            else: # General fallback
                 return fake.word()


        elif col_type == 'date':
            start_dt = params.get('start_date', date.today() - timedelta(days=365))
            end_dt = params.get('end_date', date.today())
            # Ensure they are date objects
            if isinstance(start_dt, str): start_dt = date.fromisoformat(start_dt)
            if isinstance(end_dt, str): end_dt = date.fromisoformat(end_dt)
            if isinstance(start_dt, datetime.datetime): start_dt = start_dt.date()
            if isinstance(end_dt, datetime.datetime): end_dt = end_dt.date()
            if not isinstance(start_dt, date) or not isinstance(end_dt, date):
                 raise TypeError("Invalid date objects for generation.")

            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt
            try: return fake.date_between_dates(date_start=start_dt, date_end=end_dt)
            except Exception: return start_dt # Fallback

        elif col_type == 'boolean':
            return random.choice([True, False])

        elif col_type == 'Categorical': # Handle inferred categorical
             choices = params.get('choices', ['A'])
             probs = params.get('probabilities')
             if not choices: return None
             if probs and len(probs) == len(choices):
                 # ... (probability logic same as string/choice) ...
                 try:
                     probs_f = [float(p) for p in probs]
                     if not np.isclose(sum(probs_f), 1.0):
                         probs_f = np.array(probs_f) / np.sum(probs_f)
                     return np.random.choice(choices, p=probs_f)
                 except (ValueError, TypeError): return random.choice(choices)
             else: return random.choice(choices)

        else: return None
    except Exception as e:
        st.error(f"Error generating value for col_def {col_def}: {e}")
        return None


# --- Schema Inference Function (from 5th.py) ---
# This function infers schema AND formats it for generate_tabular_value
def infer_schema_from_df(df):
    inferred_columns = []
    row_count = len(df)
    if row_count == 0:
        st.warning("Uploaded file has no data rows to infer schema from.")
        return []

    # Use a larger sample for inference if dataset is large
    sample_size = min(row_count, 5000)
    df_sample = df.sample(sample_size) if row_count > sample_size else df

    for col_name in df.columns:
        # Use sample for unique checks and stats, but use original dtype
        col_data = df_sample[col_name].dropna()
        num_unique = col_data.nunique()
        dtype_obj = df[col_name].dtype # Get dtype from original DF

        col_def = {'name': str(col_name)} # Store config directly here
        base_type_str = str(dtype_obj)
        col_def['type'] = PANDAS_TYPE_MAP.get(base_type_str, 'string') # Map pandas type to our type
        col_def['distribution'] = None # Default distribution

        try:
            # --- Integer Handling ---
            if pd.api.types.is_integer_dtype(dtype_obj):
                col_def['type'] = 'integer'
                if not col_data.empty:
                    min_v = int(col_data.min())
                    max_v = int(col_data.max())
                    col_def['min'] = min_v; col_def['max'] = max_v
                    # Check if it looks categorical (few unique ints relative to sample size)
                    if num_unique <= 30 or (sample_size > 0 and num_unique / sample_size < 0.05):
                        col_def['type'] = 'Categorical' # Override type
                        col_def['choices'] = sorted([int(x) for x in col_data.unique()])
                        # Calculate probabilities based on sample frequency
                        counts = col_data.value_counts(normalize=True)
                        col_def['probabilities'] = [counts.get(choice, 0) for choice in col_def['choices']]
                        col_def.pop('min', None); col_def.pop('max', None) # Remove numeric params
                        col_def['distribution'] = 'choice' # Indicate choice dist
                    else: # Treat as numerical integer
                        col_def['distribution'] = 'uniform' # Default dist for inferred numeric
                        col_def['mean'] = float(col_data.mean())
                        col_def['std'] = float(col_data.std())
                else:
                    col_def['min'] = 0; col_def['max'] = 100; col_def['distribution'] = 'uniform'

            # --- Float Handling ---
            elif pd.api.types.is_float_dtype(dtype_obj):
                col_def['type'] = 'float'
                if not col_data.empty:
                    min_v = float(col_data.min()); max_v = float(col_data.max())
                    col_def['min'] = min_v; col_def['max'] = max_v
                    col_def['distribution'] = 'uniform' # Default dist
                    col_def['mean'] = float(col_data.mean())
                    col_def['std'] = float(col_data.std())
                else:
                    col_def['min'] = 0.0; col_def['max'] = 1.0; col_def['distribution'] = 'uniform'

            # --- Datetime Handling ---
            elif pd.api.types.is_datetime64_any_dtype(dtype_obj) or pd.api.types.is_timedelta64_dtype(dtype_obj):
                col_def['type'] = 'date'
                if not col_data.empty:
                    try: # Ensure conversion to date works
                        min_d = pd.to_datetime(col_data.min()).date()
                        max_d = pd.to_datetime(col_data.max()).date()
                        col_def['start_date'] = min_d
                        col_def['end_date'] = max_d
                    except Exception:
                        st.warning(f"Could not parse date range for '{col_name}'. Using defaults.")
                        col_def['start_date'] = date.today() - timedelta(days=365)
                        col_def['end_date'] = date.today()
                else:
                     col_def['start_date'] = date.today() - timedelta(days=365)
                     col_def['end_date'] = date.today()
                col_def['distribution'] = 'date_range' # Specific distribution

            # --- Boolean Handling ---
            elif pd.api.types.is_bool_dtype(dtype_obj):
                col_def['type'] = 'boolean'
                col_def['distribution'] = 'random' # Only choice

            # --- Categorical Handling (Pandas Type) ---
            elif pd.api.types.is_categorical_dtype(dtype_obj):
                 col_def['type'] = 'Categorical' # Use our Categorical type
                 col_def['choices'] = list(df[col_name].cat.categories) # Get categories from original DF
                 # Calculate probabilities from sample
                 counts = col_data.value_counts(normalize=True)
                 col_def['probabilities'] = [counts.get(choice, 0) for choice in col_def['choices']]
                 col_def['distribution'] = 'choice'

            # --- Object (String) Handling ---
            elif pd.api.types.is_object_dtype(dtype_obj):
                # Check if it looks categorical
                if num_unique <= 50 or (sample_size > 0 and num_unique / sample_size < 0.1):
                    col_def['type'] = 'Categorical'
                    choices = sorted([str(x) for x in col_data.unique()])
                    col_def['choices'] = choices
                    counts = col_data.value_counts(normalize=True)
                    col_def['probabilities'] = [counts.get(choice, 0) for choice in choices]
                    col_def['distribution'] = 'choice'
                else: # Treat as general string, guess Faker type
                    col_def['type'] = 'string'
                    first_val = str(col_data.iloc[0]) if not col_data.empty else ""
                    # Simple pattern guessing (enhance as needed)
                    if re.match(r"[^@]+@[^@]+\.[^@]+", first_val): col_def['faker_type'] = 'email'; col_def['distribution'] = 'email'
                    elif re.match(r"[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z]\.)?", first_val): col_def['faker_type'] = 'name'; col_def['distribution'] = 'name'
                    elif re.match(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", first_val): col_def['faker_type'] = 'word'; col_def['distribution'] = 'word' # Avoid number-like strings
                    elif re.match(r"https?://[^\s]+", first_val): col_def['faker_type'] = 'url'; col_def['distribution'] = 'text' # Treat URL as text?
                    elif len(first_val.split()) > 3: col_def['faker_type'] = 'sentence'; col_def['distribution'] = 'text'
                    else: col_def['faker_type'] = 'word'; col_def['distribution'] = 'word' # Default faker/dist

            # Store the inferred pandas type for reference if needed
            col_def['inferred_dtype'] = base_type_str

        except Exception as e:
            st.error(f"Error inferring schema for column '{col_name}': {e}")
            # Fallback to simple string on error
            col_def['type'] = 'string'; col_def['distribution'] = 'word'; col_def['error'] = str(e)

        inferred_columns.append(col_def)

    st.info("Schema inference complete. Generation in 'Excel Augmentation' mode will use these settings.")
    return inferred_columns


# --- [generate_synthetic_data function from 7th.py - UNCHANGED] ---
# This function is used ONLY by the "Tabular Data" mode with manual config
def generate_synthetic_data(num_rows, columns_info, relationships):
    # ... (implementation from 7th.py - verified it uses generate_tabular_value indirectly via its internal logic) ...
    # Slight modification: Ensure generate_tabular_value is called correctly if possible,
    # otherwise keep the original detailed logic. Let's keep the original detailed logic
    # of generate_synthetic_data from 7th.py for robustness in Tabular mode.
    data = {}
    # Initialize data dictionary based on columns_info (manual config)
    for col_name in columns_info.keys(): data[col_name] = []

    for _ in range(num_rows):
        row = {}
        # Generate base data for the row using manual config
        for col_name, col_info in columns_info.items():
            # Use the generation logic specific to the MANUAL config format
            # This part IS DIFFERENT from generate_tabular_value as it expects
            # the structure from the manual UI (e.g., nested params, specific dist names)
            data_type = col_info.get('type')
            distribution = col_info.get('distribution')
            # --- [Logic from 7th.py's generate_synthetic_data - START] ---
            # (This section needs the detailed generation based on the structure
            #  defined in the *Tabular Mode UI* - integer, float, string, date, boolean
            #  with their respective distributions like 'uniform', 'normal', 'choice',
            #  'name', 'city', 'email', 'text', 'uuid', 'custom_regex', 'date_range', 'random')
            try:
                if data_type == 'integer':
                    min_val = col_info.get('min', 0)
                    max_val = col_info.get('max', 100)
                    mean_val = col_info.get('mean', 50)
                    std_val = col_info.get('std', 10)
                    if distribution == 'uniform': row[col_name] = random.randint(min_val, max_val)
                    elif distribution == 'normal':
                        std_val = max(0.1, std_val); val = int(np.random.normal(mean_val, std_val))
                        if 'min' in col_info or 'max' in col_info: val = max(min_val, min(max_val, val))
                        row[col_name] = val
                    else: row[col_name] = random.randint(min_val, max_val)
                elif data_type == 'float':
                    min_val = col_info.get('min', 0.0); max_val = col_info.get('max', 100.0)
                    mean_val = col_info.get('mean', 50.0); std_val = col_info.get('std', 10.0)
                    if distribution == 'uniform': row[col_name] = random.uniform(min_val, max_val)
                    elif distribution == 'normal':
                        std_val = max(0.1, std_val); val = np.random.normal(mean_val, std_val)
                        if 'min' in col_info or 'max' in col_info: val = max(min_val, min(max_val, val))
                        row[col_name] = val
                    else: row[col_name] = random.uniform(min_val, max_val)
                elif data_type == 'string':
                    choices = col_info.get('choices') # Check for choices first
                    if distribution == 'choice' and choices: row[col_name] = random.choice(choices)
                    elif distribution == 'name': row[col_name] = fake.name()
                    elif distribution == 'city': row[col_name] = fake.city()
                    elif distribution == 'email': row[col_name] = fake.email()
                    elif distribution == 'text': row[col_name] = fake.sentence(nb_words=col_info.get('num_words', 6))
                    elif distribution == 'uuid': row[col_name] = str(fake.uuid4())
                    elif distribution == 'custom_regex' and 'regex' in col_info and rstr:
                        try: row[col_name] = rstr.xeger(col_info['regex'])
                        except Exception as e: st.warning(f"Regex error for {col_name}: {e}"); row[col_name] = None
                    elif distribution == 'word': row[col_name] = fake.word() # Explicit word dist
                    else: row[col_name] = fake.word() # Fallback
                elif data_type == 'date':
                    start_date_obj = col_info.get('start_date', datetime.date.today() - timedelta(days=30*365))
                    end_date_obj = col_info.get('end_date', datetime.date.today())
                    if isinstance(start_date_obj, datetime.datetime): start_date_obj = start_date_obj.date()
                    if isinstance(end_date_obj, datetime.datetime): end_date_obj = end_date_obj.date()
                    if not isinstance(start_date_obj, date): start_date_obj = date.today() - timedelta(days=30*365)
                    if not isinstance(end_date_obj, date): end_date_obj = date.today()
                    if start_date_obj > end_date_obj: start_date_obj, end_date_obj = end_date_obj, start_date_obj
                    try: row[col_name] = fake.date_between_dates(date_start=start_date_obj, date_end=end_date_obj)
                    except Exception as e: st.error(f"Date gen error for {col_name}: {e}"); row[col_name] = start_date_obj
                elif data_type == 'boolean': row[col_name] = random.choice([True, False])
                else: row[col_name] = None
            except Exception as e: st.error(f"Error generating data for column '{col_name}': {e}"); row[col_name] = None
            # --- [Logic from 7th.py's generate_synthetic_data - END] ---

        # Apply Relationships (only in Tabular mode)
        cols_to_update = {}
        for rel in relationships:
             # ... (Relationship logic from 7th.py - Start) ...
            try:
                if rel['type'] == 'dependency':
                    condition_col = rel['condition_col']; dependent_col = rel['dependent_col']
                    if condition_col not in row or row[condition_col] is None: continue

                    condition_met = False; condition_val_orig = rel['condition_value']
                    row_val = row[condition_col]; condition_val_parsed = condition_val_orig

                    # --- Type Coercion & Comparison (Simplified from 7th.py - Check original for full detail if needed) ---
                    target_type = type(row_val)
                    is_list_condition = rel['condition'] in ['in list', 'not in list'] # Use updated conditions
                    try:
                        if is_list_condition: # Handle list coercion
                            if isinstance(condition_val_orig, str): # Expect comma separated string from UI
                                list_vals_str = [v.strip() for v in condition_val_orig.split(',') if v.strip()]
                                # Coerce items in list based on row_val type
                                coerced_list = []
                                for item_str in list_vals_str:
                                    try: coerced_list.append(target_type(item_str))
                                    except (ValueError, TypeError): coerced_list.append(item_str) # Keep as string if fails
                                condition_val_parsed = coerced_list
                            elif isinstance(condition_val_orig, list): condition_val_parsed = condition_val_orig # Already a list
                            else: condition_val_parsed = [condition_val_orig] # Treat as single item list
                        elif isinstance(row_val, date) and isinstance(condition_val_orig, str): condition_val_parsed = date.fromisoformat(condition_val_orig)
                        elif isinstance(row_val, bool) and isinstance(condition_val_orig, str): condition_val_parsed = condition_val_orig.lower() in ['true','1','yes']
                        elif not isinstance(condition_val_orig, target_type): condition_val_parsed = target_type(condition_val_orig) # General coercion
                    except (ValueError, TypeError): pass # Keep original on coercion error

                    # Perform comparison
                    try:
                         if rel['condition'] == 'equals' and row_val == condition_val_parsed: condition_met = True
                         elif rel['condition'] == 'not equals' and row_val != condition_val_parsed: condition_met = True
                         elif rel['condition'] == 'greater than' and row_val > condition_val_parsed: condition_met = True
                         elif rel['condition'] == 'less than' and row_val < condition_val_parsed: condition_met = True
                         elif rel['condition'] == 'in list' and isinstance(condition_val_parsed, list) and row_val in condition_val_parsed: condition_met = True
                         elif rel['condition'] == 'not in list' and isinstance(condition_val_parsed, list) and row_val not in condition_val_parsed: condition_met = True
                    except TypeError: condition_met = False # Incomparable types

                    if condition_met: cols_to_update[dependent_col] = rel['dependent_value'] # Store the raw dependent value string
            except Exception as e: st.error(f"Error processing relationship ({rel}): {e}")
            # ... (Relationship logic from 7th.py - End) ...


        # Apply the stored updates
        for col, val_to_assign_str in cols_to_update.items():
             if col not in columns_info: continue
             target_type_str = columns_info[col]['type']; final_assigned_val = val_to_assign_str
             try: # Cast dependent value based on target column's type
                 if val_to_assign_str is None: final_assigned_val = None
                 elif target_type_str == 'integer': final_assigned_val = int(val_to_assign_str)
                 elif target_type_str == 'float': final_assigned_val = float(val_to_assign_str)
                 elif target_type_str == 'boolean': final_assigned_val = str(val_to_assign_str).lower() in ['true', '1', 'yes']
                 elif target_type_str == 'date': final_assigned_val = date.fromisoformat(str(val_to_assign_str))
                 elif target_type_str == 'string': final_assigned_val = str(val_to_assign_str)
                 row[col] = final_assigned_val
             except (ValueError, TypeError):
                 st.warning(f"Could not cast dependent value '{val_to_assign_str}' to type '{target_type_str}' for column '{col}'. Assigning as string.")
                 row[col] = str(val_to_assign_str) # Fallback to string

        # Append the final row data
        for col_name in data.keys(): data[col_name].append(row.get(col_name))

    # Final processing (same as 7th.py)
    # ... (Validation, DataFrame creation, final type conversion) ...
    expected_len = num_rows; final_data = {}
    for col_name, values in data.items():
        if len(values) != expected_len:
             st.error(f"Length mismatch in '{col_name}'. Padding with None.")
             final_data[col_name] = values + [None] * (expected_len - len(values))
        else: final_data[col_name] = values
    try:
        df = pd.DataFrame(final_data)
        # Final type conversions (use nullable types)
        for col_name, col_info in columns_info.items():
            if col_name in df.columns:
                 target_type = col_info.get('type')
                 try:
                     if target_type == 'integer': df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
                     elif target_type == 'float': df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Float64')
                     elif target_type == 'date': df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date
                     elif target_type == 'boolean': df[col_name] = df[col_name].astype('boolean')
                 except Exception as e: st.warning(f"Final type conversion failed for {col_name} to {target_type}: {e}")
        return df
    except Exception as e: st.error(f"Error creating DataFrame: {e}"); return pd.DataFrame()


# --- Image/Bytes Helpers (Unchanged from 7th.py) ---
def generate_simple_image(width, height, bg_color, shape, shape_color, text=""):
    img = Image.new('RGB', (width, height), color=bg_color); draw = ImageDraw.Draw(img)
    m = int(min(width, height)*0.15); x1,y1,x2,y2 = m,m,width-m,height-m
    try:
        if shape == 'rectangle': draw.rectangle([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'ellipse': draw.ellipse([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'line': draw.line([x1, y1, x2, y2], fill=shape_color, width=5); draw.line([x1, y2, x2, y1], fill=shape_color, width=5)
        elif shape == 'triangle': draw.polygon([(width//2, y1), (x1, y2), (x2, y2)], fill=shape_color)
        if text:
            try: font_size=int(min(width,height)*0.1); font=ImageFont.truetype("arial.ttf", font_size)
            except IOError: font = ImageFont.load_default()
            tbox = draw.textbbox((0,0), text, font=font); tw, th = tbox[2]-tbox[0], tbox[3]-tbox[1]; tx, ty = (width-tw)/2, (height-th)/2
            try: bg_lum = sum(int(bg_color[i:i+2], 16) * w for i, w in zip([1, 3, 5], [0.299, 0.587, 0.114])); fill = "black" if bg_lum > 128 else "white"
            except: fill = "black"
            draw.text((tx, ty), text, fill=fill, font=font)
    except Exception as e: st.error(f"Error drawing image: {e}")
    return img

def image_to_bytes(img):
    buf = io.BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()

# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("📊 Enhanced Synthetic Data Generator 🛠️")

# --- Initialize Session State ---
# Add keys for Excel Augmentation mode
default_state_integrated = {
    'app_mode': "Tabular Data", # Default mode
    # Tabular Mode State
    'columns_info': {}, 'relationships': [], 'generated_df': None,
    'config_source': 'manual', 'show_config_section': True,
    'excel_processed_filename_tab': None, # For tabular init
    'num_rows_generate': 100,
    # Excel Augmentation Mode State
    'excel_aug_df_preview': None, 'excel_aug_schema': None, 'excel_aug_selected_sheet': None,
    'excel_aug_num_rows': 100, 'excel_aug_file_uploader_key': 0,
    'excel_processed_filename_aug': None, # For augmentation
    # Image Mode State
    'generated_images': [], 'num_images': 10, 'img_width': 128, 'img_height': 128,
    'img_bg_color': '#DDDDDD', 'img_shape': 'rectangle', 'img_shape_color': '#FF0000', 'img_add_text': False, 'img_text': 'Synth',
    # Combined Mode State
    'generated_combined': None, 'num_combined': 20, 'img_c_width': 64, 'img_c_height': 64,
    'img_c_bg_color': '#EEEEEE', 'label_options': ["rectangle", "ellipse"],
    # General Results State
    'results_data': None, 'results_message': None, 'results_error': None, 'is_generating': False
}
for key, value in default_state_integrated.items():
    if key not in st.session_state: st.session_state[key] = value


# --- Sidebar: Mode Selection ---
# Use 'app_mode' from the integrated state
mode = st.sidebar.radio(
    "Select Generation Mode",
    ("Tabular Data", "Excel Augmentation", "Image Data", "Combined (Image + Label)"), # Added Excel Augmentation
    key="app_mode_selector", # Use a dedicated key
    index=["Tabular Data", "Excel Augmentation", "Image Data", "Combined (Image + Label)"].index(st.session_state.app_mode)
)
# Update state if mode changes
if mode != st.session_state.app_mode:
    st.session_state.app_mode = mode
    # Optional: Clear results when switching modes
    st.session_state.results_data = None
    st.session_state.results_message = None
    st.session_state.results_error = None
    st.rerun()

# =========================
# === TABULAR DATA MODE ===
# =========================
if st.session_state.app_mode == "Tabular Data":
    st.header("Tabular Data Generation (Manual Configuration)")
    st.info("Define columns and rules manually, or load from Excel to *initialize* the configuration for editing.")

    # --- Configuration Source Selection (Manual vs Load for Init) ---
    st.subheader("1. Configure Columns")
    if st.button("Clear & Reset Tabular Configuration", key="clear_tabular_config"):
        # Reset only tabular specific state
        st.session_state.columns_info = {}; st.session_state.relationships = []; st.session_state.generated_df = None
        st.session_state.config_source = 'manual'; st.session_state.excel_processed_filename_tab = None
        st.rerun()

    config_load_options = ["Manually Define Columns", "Load Initial Config from Excel"]
    load_choice = st.radio( "Choose Configuration Method:", config_load_options,
        index=config_load_options.index(st.session_state.config_source), key="config_load_choice", horizontal=True )
    if load_choice != st.session_state.config_source:
        st.session_state.config_source = load_choice
        if load_choice == "Load Initial Config from Excel": st.session_state.columns_info = {}; st.session_state.relationships = [] # Clear before loading
        st.rerun()

    # --- Excel Loader for Tabular Initialization ---
    if st.session_state.config_source == "Load Initial Config from Excel":
        uploaded_file_tab = st.file_uploader( "Upload Excel File (.xlsx, .xls) to initialize config",
            type=["xlsx", "xls"], key="excel_uploader_tab" )
        if uploaded_file_tab is not None:
            if uploaded_file_tab.name != st.session_state.get('excel_processed_filename_tab'):
                try:
                    xls = pd.ExcelFile(uploaded_file_tab); sheet_names = xls.sheet_names
                    selected_sheet_tab = None
                    if len(sheet_names) > 1: selected_sheet_tab = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_tab_init", index=None)
                    else: selected_sheet_tab = sheet_names[0]

                    if selected_sheet_tab:
                        with st.spinner("Reading Excel and inferring schema for initialization..."):
                            df_uploaded = pd.read_excel(uploaded_file_tab, sheet_name=selected_sheet_tab)
                            # Use infer_schema but adapt its output for the manual config structure
                            inferred_schema = infer_schema_from_df(df_uploaded)
                            # Convert inferred schema to the columns_info structure
                            initial_columns_info = {}
                            for col_def in inferred_schema:
                                # Map inferred types/params back to the manual config structure
                                manual_col_info = {
                                    'type': col_def.get('type', 'string'),
                                    'distribution': col_def.get('distribution', 'word'), # Needs better mapping potentially
                                }
                                # Add params based on inferred structure
                                manual_col_info.update({k: v for k, v in col_def.items() if k not in ['name', 'type', 'distribution', 'inferred_dtype', 'error']})
                                # Specific mappings if needed (e.g., inferred 'faker_type' to a specific distribution)
                                if manual_col_info['type'] == 'string' and 'faker_type' in manual_col_info:
                                    f_type = manual_col_info['faker_type']
                                    if f_type in ['name', 'city', 'email', 'uuid']: manual_col_info['distribution'] = f_type
                                    elif f_type in ['sentence', 'paragraph']: manual_col_info['distribution'] = 'text'
                                    else: manual_col_info['distribution'] = 'word' # Default
                                    # Keep choices if inferred as categorical string
                                    if 'choices' in col_def:
                                         manual_col_info['distribution'] = 'choice'
                                         manual_col_info['choices'] = col_def['choices']

                                elif manual_col_info['type'] == 'date': manual_col_info['distribution'] = 'date_range'
                                elif manual_col_info['type'] == 'boolean': manual_col_info['distribution'] = 'random'
                                elif manual_col_info['type'] == 'Categorical': # Handle inferred Categorical
                                     manual_col_info['type'] = 'string' # Treat as string choice in manual UI
                                     manual_col_info['distribution'] = 'choice'
                                     # Keep choices/probs if available
                                     if 'choices' in col_def: manual_col_info['choices'] = col_def['choices']
                                     # Note: Manual UI doesn't directly support probabilities easily here

                                initial_columns_info[col_def['name']] = manual_col_info

                        st.session_state.columns_info = initial_columns_info # Set the editable config
                        st.session_state.relationships = [] # Clear relationships
                        st.session_state.generated_df = None # Clear results
                        st.session_state.excel_processed_filename_tab = uploaded_file_tab.name
                        st.success(f"Initialized configuration from '{uploaded_file_tab.name}'. Review and edit below.")
                        st.rerun()
                except Exception as e: st.error(f"Error processing Excel for init: {e}")


    # --- Manual Column Definition / Editing Area (From 7th.py) ---
    # Uses st.session_state.columns_info
    st.subheader("2. Review and Edit Column Configurations")
    if not st.session_state.columns_info and st.session_state.config_source == 'manual':
         st.info("👇 Use the 'Add New Column' section below to start defining columns manually.")
    elif not st.session_state.columns_info and st.session_state.config_source == 'Load Initial Config from Excel':
         st.info("☝️ Upload an Excel file above to initialize the configuration.")

    if st.session_state.columns_info:
         # ... [Display/Edit area from 7th.py - pasted and verified - START] ...
        col_config_headers = st.columns([2, 1, 1, 1])
        with col_config_headers[0]: st.markdown("**Column Name**")
        with col_config_headers[1]: st.markdown("**Data Type**")
        with col_config_headers[2]: st.markdown("**Distribution/Method**")
        with col_config_headers[3]: st.markdown("**Action**")
        column_names_list = list(st.session_state.columns_info.keys())
        for i, col_name in enumerate(column_names_list):
            if col_name not in st.session_state.columns_info: continue
            col_info = st.session_state.columns_info[col_name]
            unique_key_prefix = f"col_{i}_{col_name.replace(' ', '_').replace('.', '_')}"
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1: st.markdown(f"**`{col_name}`**")
                with col2: # EDIT TYPE
                    current_type = col_info.get('type', 'string'); type_options = ["integer", "float", "string", "date", "boolean"]
                    try: type_index = type_options.index(current_type)
                    except ValueError: type_index = 2
                    col_type = st.selectbox(f"Type", type_options, index=type_index, key=f"{unique_key_prefix}_type", label_visibility="collapsed")
                    if st.session_state.columns_info[col_name].get('type') != col_type:
                        st.session_state.columns_info[col_name]['type'] = col_type; st.rerun()
                with col3: # EDIT DISTRIBUTION
                    col_type = st.session_state.columns_info[col_name].get('type', 'string')
                    if col_type == 'integer' or col_type == 'float': dist_options = ["uniform", "normal"]
                    elif col_type == 'string': dist_options = ["choice", "name", "city", "email", "text", "uuid", "custom_regex", "word"]
                    elif col_type == 'date': dist_options = ["date_range"]
                    elif col_type == 'boolean': dist_options = ["random"]
                    else: dist_options = []
                    if dist_options:
                        current_dist = col_info.get('distribution');
                        if current_dist not in dist_options: current_dist = dist_options[0]; st.session_state.columns_info[col_name]['distribution'] = current_dist
                        try: dist_index = dist_options.index(current_dist)
                        except ValueError: dist_index = 0
                        distribution = st.selectbox(f"Dist.", dist_options, index=dist_index, key=f"{unique_key_prefix}_dist", label_visibility="collapsed")
                        if st.session_state.columns_info[col_name].get('distribution') != distribution:
                            st.session_state.columns_info[col_name]['distribution'] = distribution; st.rerun()
                    else: st.write("-"); st.session_state.columns_info[col_name]['distribution'] = None
                with col4: # REMOVE COLUMN
                    if st.button("Remove", key=f"{unique_key_prefix}_remove", help=f"Remove column '{col_name}'"):
                        del st.session_state.columns_info[col_name]
                        st.session_state.relationships = [r for r in st.session_state.relationships if r['condition_col'] != col_name and r['dependent_col'] != col_name]
                        st.rerun()
                # --- EDIT PARAMETERS (Expander) ---
                distribution = st.session_state.columns_info[col_name].get('distribution')
                col_type = st.session_state.columns_info[col_name].get('type')
                with st.expander(f"Configure Parameters for `{col_name}` ({distribution or 'N/A'})"):
                    # ... [Parameter editing UI from 7th.py - verified - START] ...
                    if col_type in ['integer', 'float']:
                        default_min = 0.0 if col_type == 'float' else 0; default_max = 100.0 if col_type == 'float' else 100
                        default_mean = 50.0 if col_type == 'float' else 50; default_std = 10.0 if col_type == 'float' else 10
                        format_str = "%g" if col_type=='float' else "%d"
                        if distribution == 'uniform':
                            min_val = st.number_input(f"Min Value", value=col_info.get('min', default_min), key=f"{unique_key_prefix}_min", format=format_str)
                            max_val = st.number_input(f"Max Value", value=col_info.get('max', default_max), key=f"{unique_key_prefix}_max", format=format_str)
                            st.session_state.columns_info[col_name]['min'] = min_val; st.session_state.columns_info[col_name]['max'] = max_val
                        elif distribution == 'normal':
                            mean_val = st.number_input(f"Mean", value=col_info.get('mean', default_mean), key=f"{unique_key_prefix}_mean", format="%g")
                            std_val = st.number_input(f"Std Dev", value=col_info.get('std', default_std), min_value=0.01, key=f"{unique_key_prefix}_std", format="%g")
                            st.session_state.columns_info[col_name]['mean'] = mean_val; st.session_state.columns_info[col_name]['std'] = std_val
                            use_bounds = st.checkbox("Set Min/Max Bounds?", key=f"{unique_key_prefix}_normal_bounds", value=('min' in col_info or 'max' in col_info))
                            if use_bounds:
                                min_b = st.number_input(f"Min Bound", value=col_info.get('min', default_min), key=f"{unique_key_prefix}_min_bound", format=format_str)
                                max_b = st.number_input(f"Max Bound", value=col_info.get('max', default_max), key=f"{unique_key_prefix}_max_bound", format=format_str)
                                st.session_state.columns_info[col_name]['min'] = min_b; st.session_state.columns_info[col_name]['max'] = max_b
                            else: st.session_state.columns_info[col_name].pop('min', None); st.session_state.columns_info[col_name].pop('max', None)
                        else: st.caption("Distribution parameters not applicable.")
                    elif col_type == 'string':
                        if distribution == 'choice':
                            choices_list = col_info.get('choices', []); choices_str = "\n".join(map(str, choices_list))
                            choices_new_str = st.text_area(f"Choices (one per line)", value=choices_str, key=f"{unique_key_prefix}_choices", height=max(100, len(choices_list)*20))
                            st.session_state.columns_info[col_name]['choices'] = [c.strip() for c in choices_new_str.split('\n') if c.strip()]
                        elif distribution == 'text':
                            n_words = st.slider(f"Approx Words", 1, 50, col_info.get('num_words', 6), key=f"{unique_key_prefix}_num_words")
                            st.session_state.columns_info[col_name]['num_words'] = n_words
                        elif distribution == 'custom_regex':
                            if not rstr: st.warning("'rstr' library not installed. Regex generation disabled.")
                            else:
                                regex_pat = st.text_input(f"Regex Pattern", value=col_info.get('regex', r'^\w{5}$'), key=f"{unique_key_prefix}_regex")
                                st.session_state.columns_info[col_name]['regex'] = regex_pat
                        else: st.caption(f"No parameters for '{distribution}'.")
                    elif col_type == 'date':
                        if distribution == 'date_range':
                            default_start = date.today() - timedelta(days=365); default_end = date.today()
                            start_val = col_info.get('start_date', default_start); end_val = col_info.get('end_date', default_end)
                            if isinstance(start_val, datetime.datetime): start_val = start_val.date()
                            if isinstance(end_val, datetime.datetime): end_val = end_val.date()
                            if not isinstance(start_val, date): start_val = default_start
                            if not isinstance(end_val, date): end_val = default_end
                            start_date = st.date_input(f"Start Date", value=start_val, key=f"{unique_key_prefix}_start_date")
                            end_date = st.date_input(f"End Date", value=end_val, key=f"{unique_key_prefix}_end_date")
                            if end_date < start_date: st.warning("End Date < Start Date."); end_date = start_date
                            st.session_state.columns_info[col_name]['start_date'] = start_date; st.session_state.columns_info[col_name]['end_date'] = end_date
                        else: st.caption("Parameters not applicable.")
                    elif col_type == 'boolean': st.caption("No parameters needed.")
                    else: st.caption("Unknown type/parameters.")
                    # ... [Parameter editing UI from 7th.py - verified - END] ...
        st.markdown("---")
         # ... [Display/Edit area from 7th.py - pasted and verified - END] ...

    # --- Add New Column Form (From 7th.py) ---
    with st.form("add_column_form", clear_on_submit=True):
        st.subheader("Add a New Manual Column")
        new_col_name = st.text_input("New Column Name", key="new_col_name_input")
        submitted = st.form_submit_button("Add Column")
        if submitted:
            if new_col_name:
                clean_name = new_col_name.strip()
                if clean_name and clean_name not in st.session_state.columns_info:
                    st.session_state.columns_info[clean_name] = {'type': 'string', 'distribution': 'word'} # Default
                    st.success(f"Added column: '{clean_name}'"); st.rerun()
                elif clean_name in st.session_state.columns_info: st.warning(f"Column '{clean_name}' already exists.")
                else: st.warning("Enter a valid column name.")
            else: st.warning("Enter a column name.")
    st.markdown("---")


    # --- Define Relationships (From 7th.py, uses manual columns_info) ---
    if st.session_state.columns_info:
        st.subheader("3. Define Relationships (Optional)")
        available_columns = list(st.session_state.columns_info.keys())
        # ... [Relationship Display/Add/Remove UI from 7th.py - verified - START] ...
        rels_to_remove = [];
        for i, rel in enumerate(st.session_state.relationships):
            rel_key_prefix = f"rel_{i}"
            if rel['condition_col'] not in available_columns or rel['dependent_col'] not in available_columns:
                 st.warning(f"Rel {i+1} involves removed column. Deleting."); rels_to_remove.append(i); continue
            with st.container(border=True):
                cond_val_display = rel['condition_value'];
                if isinstance(cond_val_display, list): cond_val_display = f"[{', '.join(map(str, cond_val_display))}]"
                # Use the correct relationship conditions from constant
                cond_str = rel.get('condition', 'equals') # Default if missing key somehow
                dep_val_str = rel.get('dependent_value', '') # Use .get for safety
                st.markdown(f"IF `{rel['condition_col']}` {cond_str} `{cond_val_display}` THEN SET `{rel['dependent_col']}` TO `{dep_val_str}`")
                if st.button("Remove Rule", key=f"{rel_key_prefix}_remove_rel", type="secondary"): rels_to_remove.append(i)
        if rels_to_remove:
            for index in sorted(rels_to_remove, reverse=True): del st.session_state.relationships[index];
            st.rerun()
        # Add new relationship expander
        with st.expander("Add New Dependency Relationship"):
            rel_type = "dependency" # Default type
            cond_col = st.selectbox("IF Column...", available_columns, index=None, key="new_rel_cond_col_tab", placeholder="Select...")
            selected_col_type = st.session_state.columns_info[cond_col].get('type') if cond_col else None
            cond_options = DEPENDENCY_CONDITIONS # Use defined conditions
            cond_val_input_widget = st.text_input # Default to text, adjust based on type/cond
            cond_val_kwargs = {"key": "new_rel_cond_val_tab"}

            cond = st.selectbox("Is...", cond_options, index=None, key="new_rel_cond_tab", placeholder="Select...")

            if cond: # Adjust input based on condition/type
                 if cond in ['in list', 'not in list']: cond_val_kwargs["placeholder"] = "e.g., value1, value2"
                 elif selected_col_type == 'boolean': cond_val_input_widget = st.selectbox; cond_val_kwargs["options"] = [True, False]; cond_val_kwargs["index"]=None
                 elif selected_col_type == 'date': cond_val_input_widget = st.date_input; cond_val_kwargs["value"]=None
                 elif selected_col_type in ['integer', 'float']: cond_val_input_widget = st.number_input; cond_val_kwargs["value"]=None; cond_val_kwargs["format"]=("%g" if selected_col_type=='float' else "%d")
                 else: cond_val_kwargs["placeholder"] = "Enter value"

            cond_val_raw = cond_val_input_widget("Condition Value...", **cond_val_kwargs)
            dep_col = st.selectbox("THEN Set Column...", available_columns, index=None, key="new_rel_dep_col_tab", placeholder="Select...")
            dep_val_str = st.text_input("To Value...", key="new_rel_dep_val_tab", placeholder="Value to assign")

            if st.button("Add Relationship", key="add_rel_button_tab"):
                error_msg = ""
                if not all([cond_col, cond, dep_col]) or cond_val_raw is None:
                     if not (isinstance(cond_val_raw, str) and cond_val_raw == ""): error_msg="Fill all fields."
                elif cond_col == dep_col: error_msg = "Condition/Dependent cols must be different."
                elif cond in ['in list', 'not in list'] and not isinstance(cond_val_raw, str): error_msg = "'In List' value must be comma-separated string."

                if error_msg: st.error(error_msg)
                else:
                    parsed_cond_val = cond_val_raw # Keep raw value from widget
                    # In generate_synthetic_data, we'll parse the string/list/date/bool as needed
                    st.session_state.relationships.append({
                        'type': rel_type, 'condition_col': cond_col, 'condition': cond,
                        'condition_value': parsed_cond_val, # Store raw value from widget
                        'dependent_col': dep_col, 'dependent_value': dep_val_str # Store raw string
                    }); st.rerun()
        # ... [Relationship Display/Add/Remove UI from 7th.py - verified - END] ...
        st.markdown("---")


    # --- Generation Settings (Tabular Mode) ---
    st.subheader("4. Generation Settings")
    st.session_state.num_rows_generate = st.number_input(
        "Number of Rows to Generate", min_value=1, max_value=50000,
        value=st.session_state.num_rows_generate, key="num_rows_gen_input"
    )

# --- *** NEW: UI for Excel Augmentation Mode *** ---
elif st.session_state.app_mode == "Excel Augmentation":
    st.header("Excel Augmentation (Generate New Rows Based on File)")
    st.info("Upload an Excel file. The generator will infer the schema and generate new rows based on the inferred distributions and patterns found in your data (focusing on individual columns).")

    # File Uploader with dynamic key to allow reset
    file_uploader_key = f"excel_uploader_aug_{st.session_state.excel_aug_file_uploader_key}"
    uploaded_file_aug = st.file_uploader(
        "Upload Excel File (.xlsx, .xls)", type=['xlsx', 'xls'], key=file_uploader_key
    )

    # Button to clear the current Excel file state
    if st.session_state.excel_aug_schema is not None:
        if st.button("Clear Uploaded Excel and Start Over"):
            # Reset only excel augmentation state
            st.session_state.excel_aug_df_preview = None; st.session_state.excel_aug_schema = None
            st.session_state.excel_aug_selected_sheet = None; st.session_state.excel_processed_filename_aug = None
            st.session_state.excel_aug_file_uploader_key += 1 # Increment key
            # Clear results as well
            st.session_state.results_data = None; st.session_state.results_message = None; st.session_state.results_error = None
            st.rerun()

    if uploaded_file_aug is not None:
        # Process only if the file is new or no schema is currently loaded
        if uploaded_file_aug.name != st.session_state.get('excel_processed_filename_aug'):
            try:
                xls = pd.ExcelFile(uploaded_file_aug); sheet_names = xls.sheet_names
                selected_sheet_aug = None
                if len(sheet_names) > 1:
                    selected_sheet_aug = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_aug", index=None, placeholder="Select sheet...")
                else: selected_sheet_aug = sheet_names[0]

                if selected_sheet_aug:
                    with st.spinner(f"Reading '{selected_sheet_aug}' and inferring schema..."):
                        df_uploaded = pd.read_excel(uploaded_file_aug, sheet_name=selected_sheet_aug)
                        st.session_state.excel_aug_df_preview = df_uploaded.head() # Store preview
                        # Infer schema using the dedicated function
                        inferred_schema = infer_schema_from_df(df_uploaded)
                        st.session_state.excel_aug_schema = inferred_schema
                        st.session_state.excel_aug_selected_sheet = selected_sheet_aug
                        st.session_state.excel_processed_filename_aug = uploaded_file_aug.name
                        st.session_state.results_data = None # Clear previous results
                        st.rerun() # Rerun to display preview/schema

            except Exception as e:
                st.error(f"Error reading or processing Excel file: {e}")
                # Reset state on error
                st.session_state.excel_aug_df_preview = None; st.session_state.excel_aug_schema = None
                st.session_state.excel_aug_selected_sheet = None; st.session_state.excel_processed_filename_aug = None
                st.session_state.excel_aug_file_uploader_key += 1


    # Display preview and schema if loaded
    if st.session_state.excel_aug_df_preview is not None:
        st.subheader(f"Preview of Uploaded Data ('{st.session_state.excel_aug_selected_sheet}')")
        st.dataframe(st.session_state.excel_aug_df_preview)

    if st.session_state.excel_aug_schema is not None:
        st.subheader("Inferred Schema (Read-Only)")
        st.warning("Generation uses this inferred schema. Complex column correlations may not be preserved.")
        # Display inferred schema nicely
        schema_display = []
        for col_def in st.session_state.excel_aug_schema:
            col_name = col_def.get('name', 'Unknown')
            col_type = col_def.get('type', 'Unknown')
            dist = col_def.get('distribution')
            dist_str = f", Dist: `{dist}`" if dist else ""
            # Simplified params display
            params_list = []
            for k, v in col_def.items():
                 if k not in ['name', 'type', 'distribution', 'inferred_dtype', 'error', 'probabilities']: # Hide long probs
                     params_list.append(f"{k}: `{str(v)[:25]}{'...' if len(str(v))>25 else ''}`")
            params_str = f" (Params: {'; '.join(params_list)})" if params_list else ""
            schema_display.append(f"- **{col_name}**: `{col_type}`{dist_str}{params_str}")
        st.markdown("\n".join(schema_display))
        st.markdown("---")

        # Get number of new rows for augmentation
        st.subheader("Generation Settings")
        st.session_state.excel_aug_num_rows = st.number_input(
            "Number of **NEW** Rows to Generate", min_value=1, max_value=100000,
            value=st.session_state.excel_aug_num_rows, key="excel_num_new_rows_input"
        )


# =====================================
# === IMAGE & COMBINED MODES BELOW ===
# =====================================
# --- Image Data Mode UI (Simplified using state vars) ---
elif st.session_state.app_mode == "Image Data":
    st.header("Image Data Generation (Basic Shapes)")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.num_images = c1.number_input("Number of Images", 1, 500, st.session_state.num_images, key="img_num")
        st.session_state.img_width = c1.number_input("Width (px)", 10, 1024, st.session_state.img_width, key="img_w")
        st.session_state.img_height = c1.number_input("Height (px)", 10, 1024, st.session_state.img_height, key="img_h")
    with c2:
        st.session_state.img_bg_color = c2.color_picker("Background Color", st.session_state.img_bg_color, key="img_bg")
        st.session_state.img_shape = c2.selectbox("Shape", ['rectangle', 'ellipse', 'triangle', 'line'], key="img_shape_sel", index=['rectangle', 'ellipse', 'triangle', 'line'].index(st.session_state.img_shape))
        st.session_state.img_shape_color = c2.color_picker("Shape Color", st.session_state.img_shape_color, key="img_fg")
    st.session_state.img_add_text = st.checkbox("Add Text Overlay?", st.session_state.img_add_text, key="img_text_check")
    if st.session_state.img_add_text:
        st.session_state.img_text = st.text_input("Text to Add", st.session_state.img_text, key="img_text_val")


# --- Combined (Image + Label) Mode UI ---
elif st.session_state.app_mode == "Combined (Image + Label)":
    st.header("Combined Data Generation (Image + Label)")
    st.info("Generates simple shape images with corresponding labels.")
    st.session_state.num_combined = st.number_input("Number of Items (Image+Label pairs)", 1, 500, st.session_state.num_combined, key="comb_num")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.img_c_width = c1.number_input("Image Width (px)", 10, 512, st.session_state.img_c_width, key="comb_w")
        st.session_state.img_c_height = c1.number_input("Image Height (px)", 10, 512, st.session_state.img_c_height, key="comb_h")
    with c2:
        st.session_state.img_c_bg_color = c2.color_picker("Background Color", st.session_state.img_c_bg_color, key="comb_bg")
    st.session_state.label_options = st.multiselect("Select Shape Types (Labels)",
        ["rectangle", "ellipse", "triangle"], default=st.session_state.label_options, key="comb_labels")


# ============================
# === GENERATION TRIGGER ===
# ============================
st.divider()
st.header("Generate")

# Determine if generation is possible
generation_possible = False
active_mode = st.session_state.app_mode
if active_mode == "Tabular Data" and st.session_state.columns_info: generation_possible = True
elif active_mode == "Excel Augmentation" and st.session_state.excel_aug_schema: generation_possible = True
elif active_mode == "Image Data": generation_possible = True
elif active_mode == "Combined (Image + Label)" and st.session_state.label_options: generation_possible = True

if generation_possible:
    if st.button(f"🚀 Generate {active_mode} Data", type="primary", key="generate_button", disabled=st.session_state.is_generating):
        st.session_state.is_generating = True
        st.session_state.results_data = None
        st.session_state.results_message = None
        st.session_state.results_error = None
        st.rerun()
elif active_mode in ["Tabular Data", "Excel Augmentation"]:
    st.warning(f"Cannot generate {active_mode} data. Please configure columns or upload a valid Excel file first.")
elif active_mode == "Combined (Image + Label)":
     st.warning("Please select at least one shape type for Combined generation.")


# ========================
# === GENERATION LOGIC ===
# ========================
if st.session_state.is_generating:
    active_mode = st.session_state.app_mode
    # Determine number of items based on mode
    num_items = 0
    if active_mode == "Tabular Data": num_items = st.session_state.num_rows_generate
    elif active_mode == "Excel Augmentation": num_items = st.session_state.excel_aug_num_rows
    elif active_mode == "Image Data": num_items = st.session_state.num_images
    elif active_mode == "Combined (Image + Label)": num_items = st.session_state.num_combined

    with st.spinner(f"Generating {num_items} items of {active_mode}..."):
        try:
            generated_output = None

            # --- Tabular Data Generation (Uses Manual Config) ---
            if active_mode == "Tabular Data":
                if not st.session_state.columns_info: raise ValueError("No columns defined.")
                generated_output = generate_synthetic_data(
                    num_items,
                    st.session_state.columns_info,
                    st.session_state.relationships
                )

            # --- Excel Augmentation Generation (Uses Inferred Schema) ---
            elif active_mode == "Excel Augmentation":
                inferred_schema = st.session_state.excel_aug_schema
                if not inferred_schema: raise ValueError("Inferred schema not available.")
                generated_rows = []
                for i in range(num_items):
                    new_row = {}
                    for col_def in inferred_schema:
                        # Use the single value generator function
                        new_row[col_def['name']] = generate_tabular_value(col_def)
                    generated_rows.append(new_row)
                if generated_rows: generated_output = pd.DataFrame(generated_rows)
                else: generated_output = pd.DataFrame(columns=[c['name'] for c in inferred_schema]) # Empty DF

            # --- Image Data Generation ---
            elif active_mode == "Image Data":
                generated_output = []
                for i in range(num_items):
                    img = generate_simple_image(st.session_state.img_width, st.session_state.img_height,
                                                st.session_state.img_bg_color, st.session_state.img_shape,
                                                st.session_state.img_shape_color,
                                                st.session_state.img_text if st.session_state.img_add_text else "")
                    generated_output.append({'filename': f'image_{i}_{st.session_state.img_shape}.png', 'image': img})

            # --- Combined Data Generation ---
            elif active_mode == "Combined (Image + Label)":
                if not st.session_state.label_options: raise ValueError("No labels selected.")
                combined_data = {'labels': [], 'images': [], 'filenames': []}
                for i in range(num_items):
                    chosen_label = random.choice(st.session_state.label_options)
                    # Simple color mapping
                    if chosen_label == "rectangle": shape_c_color = "#0000FF"
                    elif chosen_label == "ellipse": shape_c_color = "#008000"
                    elif chosen_label == "triangle": shape_c_color = "#FF0000"
                    else: shape_c_color = "#888888"
                    img = generate_simple_image(st.session_state.img_c_width, st.session_state.img_c_height,
                                                st.session_state.img_c_bg_color, chosen_label, shape_c_color, text="")
                    filename = f"item_{i}_{chosen_label}.png"
                    combined_data['labels'].append(chosen_label)
                    combined_data['images'].append(img)
                    combined_data['filenames'].append(filename)
                generated_output = combined_data # Store the dict


            # --- Store Results ---
            st.session_state.results_data = generated_output
            actual_count = 0
            if isinstance(generated_output, (pd.DataFrame)): actual_count = len(generated_output)
            elif isinstance(generated_output, list): actual_count = len(generated_output)
            elif isinstance(generated_output, dict) and 'labels' in generated_output: actual_count = len(generated_output['labels'])
            st.session_state.results_message = f"Successfully generated {actual_count} items."

        except Exception as e:
            st.session_state.results_error = f"Generation failed: {e}"
            st.exception(e) # Log full exception to console/streamlit log
        finally:
            st.session_state.is_generating = False
            st.rerun()


# ========================
# === RESULTS DISPLAY ===
# ========================
st.divider()
st.header("Results")

if st.session_state.results_error: st.error(st.session_state.results_error)
elif st.session_state.results_message: st.success(st.session_state.results_message)

results_data = st.session_state.results_data
active_mode = st.session_state.app_mode # Get mode active during generation

if results_data is not None:
    # --- Display Tabular or Augmented Data ---
    if active_mode in ["Tabular Data", "Excel Augmentation"] and isinstance(results_data, pd.DataFrame):
        st.dataframe(results_data)
        try:
            csv_data = results_data.to_csv(index=False).encode('utf-8')
            fname = f"synthetic_{active_mode.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            st.download_button( label=f"Download Generated Data (CSV)", data=csv_data, file_name=fname, mime='text/csv' )
        except Exception as e: st.error(f"Error preparing CSV: {e}")

    # --- Display Image Data ---
    elif active_mode == "Image Data" and isinstance(results_data, list):
        st.subheader("Image Preview (Max 10)")
        cols = st.columns(5)
        for i, img_data in enumerate(results_data[:10]):
            with cols[i % 5]: st.image(img_data['image'], caption=img_data['filename'], width=100)
        # Zip Download
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for img_data in results_data: zip_file.writestr(img_data["filename"], image_to_bytes(img_data["image"]))
            st.download_button( label="Download All Images (ZIP)", data=zip_buffer.getvalue(),
                file_name=f"synthetic_images_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", mime="application/zip" )
        except Exception as e: st.error(f"Error creating zip file: {e}")

    # --- Display Combined Data ---
    elif active_mode == "Combined (Image + Label)" and isinstance(results_data, dict):
        st.subheader("Generated Items Preview (Max 10)")
        cols = st.columns(5)
        num_preview = min(10, len(results_data['labels']))
        for i in range(num_preview):
            with cols[i % 5]: st.image(results_data['images'][i], caption=f"Label: {results_data['labels'][i]}", width=80)
        # Labels DataFrame
        labels_df = pd.DataFrame({'filename': results_data['filenames'], 'label': results_data['labels']})
        st.subheader("Labels Data"); st.dataframe(labels_df)
        # Download Buttons
        try:
            csv_data_comb = labels_df.to_csv(index=False).encode('utf-8')
            st.download_button( label="Download Labels CSV", data=csv_data_comb, file_name='synthetic_labels.csv', mime='text/csv', key="dl_comb_csv")
        except Exception as e: st.error(f"Error preparing labels CSV: {e}")
        try:
            zip_buffer_comb = io.BytesIO()
            with zipfile.ZipFile(zip_buffer_comb, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, img in enumerate(results_data['images']):
                    zip_file.writestr(results_data['filenames'][i], image_to_bytes(img))
            st.download_button( label="Download Images (ZIP)", data=zip_buffer_comb.getvalue(),
                file_name=f"synthetic_combined_images_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", mime="application/zip", key="dl_comb_zip")
        except Exception as e: st.error(f"Error creating combined images zip: {e}")

# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.info("Select mode, configure, generate!")
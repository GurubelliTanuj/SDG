# synthetic_app_excel_edit.py
import streamlit as st
import pandas as pd
import numpy as np
from faker import Faker
import random
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import datetime # Import datetime

fake = Faker()

# --- Helper Functions ---

# (generate_synthetic_data function remains the same as the previous version)
# --- [PASTED generate_synthetic_data function from previous answer] ---
def generate_synthetic_data(num_rows, columns_info, relationships):
    data = {}
    # Initialize data dictionary
    for col_name in columns_info.keys():
        data[col_name] = []

    # Pre-calculate choices for efficiency if needed
    precalculated_choices = {}
    for col_name, col_info in columns_info.items():
        if col_info.get('distribution') == 'choice':
             precalculated_choices[col_name] = col_info.get('choices', [])
             if not precalculated_choices[col_name]: # Handle empty choices
                 st.warning(f"Warning: Column '{col_name}' has 'choice' distribution but no choices defined. Setting to None.")


    for _ in range(num_rows):
        row = {}
        # Generate base data for the row
        for col_name, col_info in columns_info.items():
            data_type = col_info.get('type')
            distribution = col_info.get('distribution')

            try:
                if data_type == 'integer':
                    min_val = col_info.get('min', 0)
                    max_val = col_info.get('max', 100)
                    mean_val = col_info.get('mean', 50)
                    std_val = col_info.get('std', 10)
                    if distribution == 'uniform':
                        row[col_name] = random.randint(min_val, max_val)
                    elif distribution == 'normal':
                        # Ensure std dev is positive
                        std_val = max(0.1, std_val)
                        val = int(np.random.normal(mean_val, std_val))
                        # Optional: clamp value within min/max if also provided for normal
                        if 'min' in col_info or 'max' in col_info:
                           val = max(min_val, min(max_val, val))
                        row[col_name] = val
                    else: # Default or unrecognized distribution
                         row[col_name] = random.randint(min_val, max_val)

                elif data_type == 'float':
                    min_val = col_info.get('min', 0.0)
                    max_val = col_info.get('max', 100.0)
                    mean_val = col_info.get('mean', 50.0)
                    std_val = col_info.get('std', 10.0)
                    if distribution == 'uniform':
                        row[col_name] = random.uniform(min_val, max_val)
                    elif distribution == 'normal':
                         # Ensure std dev is positive
                        std_val = max(0.1, std_val)
                        val = np.random.normal(mean_val, std_val)
                        # Optional: clamp value within min/max if also provided for normal
                        if 'min' in col_info or 'max' in col_info:
                           val = max(min_val, min(max_val, val))
                        row[col_name] = val
                    else: # Default or unrecognized distribution
                        row[col_name] = random.uniform(min_val, max_val)

                elif data_type == 'string':
                    choices = precalculated_choices.get(col_name)
                    if distribution == 'choice' and choices:
                         row[col_name] = random.choice(choices)
                    elif distribution == 'name':
                        row[col_name] = fake.name()
                    elif distribution == 'city':
                        row[col_name] = fake.city()
                    elif distribution == 'email':
                        row[col_name] = fake.email()
                    elif distribution == 'text':
                        row[col_name] = fake.sentence(nb_words=col_info.get('num_words', 6))
                    elif distribution == 'uuid':
                        row[col_name] = str(fake.uuid4())
                    elif distribution == 'custom_regex' and 'regex' in col_info:
                        # Ensure 'rstr' library is installed: pip install rstr
                        try:
                            import rstr
                            row[col_name] = rstr.xeger(col_info['regex'])
                        except ImportError:
                            st.error("The 'rstr' library is required for regex generation. Please install it (`pip install rstr`).")
                            row[col_name] = None
                        except Exception as e:
                            st.error(f"Regex error for {col_name}: {e}")
                            row[col_name] = None
                    else: # Default to word or first choice if available
                        row[col_name] = random.choice(choices) if choices else fake.word()


                elif data_type == 'date':
                    # Use datetime.date objects for consistency
                    start_date_obj = col_info.get('start_date', datetime.date.today() - datetime.timedelta(days=30*365))
                    end_date_obj = col_info.get('end_date', datetime.date.today())

                    # Ensure they are date objects before proceeding
                    if isinstance(start_date_obj, datetime.datetime): start_date_obj = start_date_obj.date()
                    if isinstance(end_date_obj, datetime.datetime): end_date_obj = end_date_obj.date()

                    if not isinstance(start_date_obj, datetime.date): start_date_obj = datetime.date.min # Fallback
                    if not isinstance(end_date_obj, datetime.date): end_date_obj = datetime.date.max   # Fallback

                    # Ensure start_date is not after end_date
                    if start_date_obj > end_date_obj:
                        start_date_obj, end_date_obj = end_date_obj, start_date_obj # Swap if needed

                    try:
                       row[col_name] = fake.date_between_dates(date_start=start_date_obj, date_end=end_date_obj)
                    except Exception as e: # Catch broader exceptions like TypeError if dates are bad
                       st.error(f"Date generation error for {col_name} (start: {start_date_obj}, end: {end_date_obj}): {e}")
                       row[col_name] = start_date_obj # Default to start date on error

                elif data_type == 'boolean':
                     row[col_name] = random.choice([True, False])

                else:
                    row[col_name] = None
            except Exception as e:
                 st.error(f"Error generating data for column '{col_name}' with config {col_info}: {e}")
                 row[col_name] = None # Assign None if generation fails


        # Apply Relationships
        cols_to_update = {}
        for rel in relationships:
            try:
                if rel['type'] == 'dependency':
                    condition_col = rel['condition_col']
                    dependent_col = rel['dependent_col']

                    if condition_col not in row: # Check if condition column exists in the generated row data
                        st.warning(f"Relationship condition column '{condition_col}' not found in generated row. Skipping relationship.")
                        continue
                    if row[condition_col] is None: # Check if the value is None
                         # Decide how to handle None comparison based on condition? Generally skip.
                         continue

                    condition_met = False
                    condition_val_orig = rel['condition_value']
                    row_val = row[condition_col]
                    condition_val_parsed = condition_val_orig # Start with original

                    # --- Type Coercion for Comparison ---
                    target_type = type(row_val)
                    try:
                        if isinstance(row_val, (int, float)):
                           if condition_val_orig is not None: condition_val_parsed = target_type(condition_val_orig)
                        elif isinstance(row_val, datetime.date):
                           if isinstance(condition_val_orig, str):
                               try: condition_val_parsed = datetime.datetime.strptime(condition_val_orig, "%Y-%m-%d").date()
                               except ValueError: pass
                           elif isinstance(condition_val_orig, datetime.datetime): condition_val_parsed = condition_val_orig.date()
                           elif isinstance(condition_val_orig, datetime.date): condition_val_parsed = condition_val_orig
                           # else: comparison might fail if types incompatible
                        elif isinstance(row_val, bool):
                            if isinstance(condition_val_orig, str): condition_val_parsed = condition_val_orig.lower() in ['true', '1', 'yes']
                            else: condition_val_parsed = bool(condition_val_orig)
                        elif isinstance(row_val, str):
                           if rel['condition'] not in ['in', 'not_in']: condition_val_parsed = str(condition_val_orig)
                           else: # For 'in'/'not_in', condition_val_orig should be a list
                               if isinstance(condition_val_orig, list): condition_val_parsed = [str(item) for item in condition_val_orig]
                               else: condition_val_parsed = [str(condition_val_orig)] # Treat single value as list of one? Or error?

                        # Check list type for in/not_in
                        if rel['condition'] in ['in', 'not_in'] and not isinstance(condition_val_parsed, (list, tuple, set)):
                            st.warning(f"Condition value for '{rel['condition']}' on column '{condition_col}' should be a list/iterable. Found: {type(condition_val_parsed)}. Trying to compare with single value.")
                            # Maybe try converting the single item to a list for the check?
                            # condition_val_parsed = [condition_val_parsed]
                            # Or skip:
                            # continue


                    except (ValueError, TypeError) as e:
                        st.warning(f"Type mismatch comparing '{condition_col}' ({type(row_val)}) with value '{condition_val_orig}'. Comparison may be unreliable. Error: {e}")
                        condition_val_parsed = condition_val_orig # Use original if conversion fails

                    # --- Perform comparison ---
                    try:
                        if rel['condition'] == 'greater' and row_val > condition_val_parsed: condition_met = True
                        elif rel['condition'] == 'less' and row_val < condition_val_parsed: condition_met = True
                        elif rel['condition'] == 'equals' and row_val == condition_val_parsed: condition_met = True
                        elif rel['condition'] == 'not_equals' and row_val != condition_val_parsed: condition_met = True
                        elif rel['condition'] == 'in' and isinstance(condition_val_parsed, (list, tuple, set)) and row_val in condition_val_parsed: condition_met = True
                        elif rel['condition'] == 'not_in' and isinstance(condition_val_parsed, (list, tuple, set)) and row_val not in condition_val_parsed: condition_met = True
                    except TypeError as e:
                        st.warning(f"Cannot compare value '{row_val}' ({type(row_val)}) with condition value '{condition_val_parsed}' ({type(condition_val_parsed)}) for column '{condition_col}'. Skipping condition. Error: {e}")
                        condition_met = False

                    if condition_met:
                        cols_to_update[dependent_col] = rel['dependent_value'] # Store the *original* intended value string

            except Exception as e:
                st.error(f"Error processing relationship ({rel}): {e}")


        # Apply the stored updates
        for col, val_to_assign_str in cols_to_update.items():
             if col not in columns_info: # Check if dependent column still exists
                 st.warning(f"Dependent column '{col}' from relationship not found in final column configuration. Skipping assignment.")
                 continue

             # Try to cast the *original* dependent_value string to the target column type
             target_type_str = columns_info[col]['type']
             final_assigned_val = val_to_assign_str # Default to the string value

             try:
                 if val_to_assign_str is None: # Handle explicit None assignment
                      final_assigned_val = None
                 elif target_type_str == 'integer': final_assigned_val = int(val_to_assign_str)
                 elif target_type_str == 'float': final_assigned_val = float(val_to_assign_str)
                 elif target_type_str == 'string': final_assigned_val = str(val_to_assign_str)
                 elif target_type_str == 'boolean': final_assigned_val = str(val_to_assign_str).lower() in ['true', '1', 'yes']
                 elif target_type_str == 'date':
                     try: final_assigned_val = datetime.datetime.strptime(str(val_to_assign_str), "%Y-%m-%d").date()
                     except (ValueError, TypeError):
                         st.warning(f"Could not parse dependent date value '{val_to_assign_str}' to YYYY-MM-DD format for column '{col}'. Assigning as string.")
                         final_assigned_val = str(val_to_assign_str) # Keep as string if parse fails
                 # Assign the potentially type-casted value
                 row[col] = final_assigned_val
             except (ValueError, TypeError):
                 st.warning(f"Could not cast dependent value '{val_to_assign_str}' to target type '{target_type_str}' for column '{col}'. Assigning original string value.")
                 row[col] = val_to_assign_str # Assign original string if casting fails


        # Append the final row data to the main data dictionary
        for col_name in data.keys():
            data[col_name].append(row.get(col_name)) # Use get for safety

    # Validate data lengths
    expected_len = num_rows
    final_data = {}
    for col_name, values in data.items():
        if len(values) != expected_len:
            st.error(f"Length mismatch in column '{col_name}'. Expected {expected_len}, got {len(values)}. Padding with None.")
            padded_values = values + [None] * (expected_len - len(values))
            final_data[col_name] = padded_values
        else:
            final_data[col_name] = values

    try:
        # Create DataFrame from the validated 'final_data'
        df = pd.DataFrame(final_data)
        # Attempt type conversion post-DataFrame creation (safer for mixed types/errors)
        for col_name, col_info in columns_info.items():
            if col_name in df.columns:
                target_type = col_info.get('type')
                try:
                    if target_type == 'integer':
                       # Convert floats resulting from 'normal' dist to int, handle errors
                       df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64') # Use nullable Int64
                    elif target_type == 'float':
                       df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Float64') # Use nullable Float64
                    elif target_type == 'date' and df[col_name].dtype != 'object': # Avoid converting if already date/datetime
                         pass # Already handled by generation or pre-conversion likely
                    elif target_type == 'date':
                        df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date # Convert object/string dates
                    elif target_type == 'boolean':
                       # Convert potential strings/numbers if needed, careful with interpretation
                       # Example: df[col_name] = df[col_name].apply(lambda x: bool(x) if pd.notna(x) else None).astype('boolean')
                       df[col_name] = df[col_name].astype('boolean') # Use nullable boolean
                    # String conversion usually not needed unless cleaning required
                except Exception as e:
                     st.warning(f"Could not perform final type conversion for column '{col_name}' to {target_type}: {e}")
        return df
    except Exception as e:
        st.error(f"Error creating or processing DataFrame: {e}")
        st.write("Generated data dictionary (pre-DataFrame):")
        st.write(final_data)
        return pd.DataFrame()

# --- [PASTED generate_simple_image and image_to_bytes functions] ---
def generate_simple_image(width, height, bg_color, shape, shape_color, text):
    """Generates a simple image with a shape and optional text."""
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw shape
    shape_margin = int(min(width, height) * 0.15) # Margin for the shape
    x1 = shape_margin
    y1 = shape_margin
    x2 = width - shape_margin
    y2 = height - shape_margin

    try:
        if shape == 'rectangle':
            draw.rectangle([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'ellipse':
            draw.ellipse([x1, y1, x2, y2], fill=shape_color)
        elif shape == 'line':
             # Draw a diagonal line
             draw.line([x1, y1, x2, y2], fill=shape_color, width=5)
             draw.line([x1, y2, x2, y1], fill=shape_color, width=5) # Cross line
        elif shape == 'triangle':
             point1 = (width // 2, y1)
             point2 = (x1, y2)
             point3 = (x2, y2)
             draw.polygon([point1, point2, point3], fill=shape_color)
        # Add more shapes if needed (triangle, etc.)

        # Add text
        if text:
            try:
                # Try loading a default font, provide path if needed
                # On some systems, you might need: font = ImageFont.truetype("arial.ttf", size)
                font_size = int(min(width, height) * 0.1)
                try:
                     font = ImageFont.truetype("arial.ttf", font_size) # Try common arial first
                except IOError:
                    try:
                       font = ImageFont.load_default(size=font_size) # Try loading a system default
                    except IOError:
                       st.warning("Default fonts not found. Using basic PIL font.")
                       font = ImageFont.load_default() # Basic PIL font

            except Exception as e:
                 st.warning(f"Error loading font: {e}. Using basic PIL font.")
                 font = ImageFont.load_default()


            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            text_x = (width - text_width) / 2
            text_y = (height - text_height) / 2
            # Determine text color based on background brightness (simple heuristic)
            try: # Add try-except for hex color parsing
                bg_lum = 0.299*int(bg_color[1:3], 16) + 0.587*int(bg_color[3:5], 16) + 0.114*int(bg_color[5:7], 16)
                text_fill = "black" if bg_lum > 128 else "white"
            except:
                text_fill = "black" # Default if color parsing fails

            draw.text((text_x, text_y), text, fill=text_fill, font=font)

    except Exception as e:
        st.error(f"Error drawing on image: {e}")

    return img

def image_to_bytes(img):
    """Converts PIL Image to bytes."""
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    byte_im = buf.getvalue()
    return byte_im

# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("🎨 Synthetic Data Generator 📊")

# Initialize Session State (Ensure all keys used are initialized)
default_state = {
    'columns_info': {},
    'relationships': [],
    'generated_df': None,
    'generated_images': [],
    'generated_combined': None,
    'config_source': 'manual', # Default to manual
    'show_config_section': True, # Show config by default for manual
    'excel_processed_filename': None # Track the name of the processed file
}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --- Mode Selection ---
mode = st.sidebar.radio(
    "Select Generation Mode",
    ("Tabular Data", "Image Data", "Combined (Image + Label)"),
    key="app_mode"
)

# =========================
# === TABULAR DATA MODE ===
# =========================
if mode == "Tabular Data":
    st.header("Tabular Data Generation")

    # --- Step 1: Load Configuration ---
    st.subheader("1. Load/Define Column Configuration")

    # Button to clear current configuration
    if st.button("Clear & Reset Configuration", key="clear_config"):
        for key, value in default_state.items(): # Reset to defaults
             st.session_state[key] = value
        # Clear uploader state implicitly by rerunning after reset
        st.rerun()

    config_load_options = ["Manually Define Columns", "Load Columns from Excel"]
    # Use the session state to keep track of the choice
    current_choice_index = config_load_options.index(st.session_state.config_source) \
                           if st.session_state.config_source in config_load_options else 0

    load_choice = st.radio(
        "Choose Configuration Method:",
        config_load_options,
        index=current_choice_index,
        key = "config_load_choice",
        horizontal=True,
        # label_visibility="collapsed"
    )

    # Update state based on radio button choice
    if load_choice != st.session_state.config_source:
        st.session_state.config_source = load_choice
        # Decide if we clear config when switching: typically yes when switching TO excel,
        # maybe not when switching FROM excel TO manual (keep columns for editing).
        # Let's clear only when switching TO Excel explicitly.
        if load_choice == "Load Columns from Excel":
             st.session_state.columns_info = {} # Clear previous manual/excel columns
             st.session_state.relationships = []
             st.session_state.excel_processed_filename = None # Reset processed file tracker
        st.session_state.show_config_section = True # Always show config after choice
        st.rerun()


    excel_columns_loaded_this_run = False # Flag for UI messages
    if st.session_state.config_source == "Load Columns from Excel":
        uploaded_file = st.file_uploader(
            "Upload Excel File (.xlsx, .xls). Uploading a new file will replace current columns.",
            type=["xlsx", "xls"],
            key="excel_uploader" # Use a consistent key
        )
        if uploaded_file is not None:
            # Check if this specific file has already been processed in this session
            if uploaded_file.name != st.session_state.get('excel_processed_filename'):
                try:
                    with st.spinner("Reading Excel file and inferring types..."):
                        # Read only the header or first few rows to get columns and infer types
                        excel_df = pd.read_excel(uploaded_file, nrows=50) # Infer types from first 50 rows
                        excel_cols = excel_df.columns

                        inferred_columns_info = {}
                        default_start_date = datetime.date.today() - datetime.timedelta(days=365)
                        default_end_date = datetime.date.today()

                        for col in excel_cols:
                            col_name = str(col) # Ensure column name is string
                            # Prevent duplicate columns if Excel has them (use first occurrence)
                            if col_name in inferred_columns_info:
                                st.warning(f"Duplicate column name '{col_name}' found in Excel. Using first occurrence.")
                                continue

                            dtype = excel_df[col].dtype
                            col_config = {}

                            # --- Infer Type and Assign DEFAULT Distribution/Params ---
                            # User MUST review and adjust these defaults.
                            if pd.api.types.is_integer_dtype(dtype):
                                col_config = {'type': 'integer', 'distribution': 'uniform', 'min': int(excel_df[col].min(skipna=True)) if excel_df[col].notna().any() else 0, 'max': int(excel_df[col].max(skipna=True)) if excel_df[col].notna().any() else 1000}
                            elif pd.api.types.is_float_dtype(dtype):
                                col_config = {'type': 'float', 'distribution': 'uniform', 'min': float(excel_df[col].min(skipna=True)) if excel_df[col].notna().any() else 0.0, 'max': float(excel_df[col].max(skipna=True)) if excel_df[col].notna().any() else 1000.0}
                            elif pd.api.types.is_bool_dtype(dtype):
                                col_config = {'type': 'boolean', 'distribution': 'random'}
                            elif pd.api.types.is_datetime64_any_dtype(dtype) or pd.api.types.is_timedelta64_dtype(dtype):
                                start_dt = default_start_date
                                end_dt = default_end_date
                                try: # Try getting min/max from sample data
                                    valid_dates = pd.to_datetime(excel_df[col], errors='coerce').dropna()
                                    if not valid_dates.empty:
                                        start_dt = valid_dates.min().date()
                                        end_dt = valid_dates.max().date()
                                except Exception: pass # Keep defaults if error
                                col_config = {'type': 'date', 'distribution': 'date_range', 'start_date': start_dt, 'end_date': end_dt}
                            else: # Default to string for object or other types
                                # Try to infer 'choice' if cardinality is low in sample
                                unique_vals = excel_df[col].dropna().unique()
                                if 1 < len(unique_vals) <= 15: # Arbitrary threshold for choices
                                     col_config = {'type': 'string', 'distribution': 'choice', 'choices': [str(v) for v in unique_vals]}
                                else:
                                     col_config = {'type': 'string', 'distribution': 'word'} # Default string distribution

                            inferred_columns_info[col_name] = col_config

                    # --- Update session state ---
                    st.session_state.columns_info = inferred_columns_info # Replace current config
                    st.session_state.relationships = [] # Clear relationships
                    st.session_state.generated_df = None # Clear results
                    st.session_state.excel_processed_filename = uploaded_file.name # Mark this file as processed
                    st.session_state.show_config_section = True
                    excel_columns_loaded_this_run = True # Set flag for message
                    st.success(f"Extracted {len(inferred_columns_info)} columns from '{uploaded_file.name}'.")
                    st.rerun() # Rerun NOW to update the UI below with the new columns

                except Exception as e:
                    st.error(f"Error reading or processing Excel file: {e}")
                    st.session_state.excel_processed_filename = None # Ensure file not marked processed on error
                    st.session_state.show_config_section = False
            # else: The file is the same as the one already processed, do nothing, UI will show existing config


    # --- Step 2: Configure Columns (Displayed if show_config_section is True) ---
    if st.session_state.show_config_section:
        st.subheader("2. Review and Edit Column Configurations")

        if st.session_state.config_source == "Load Columns from Excel" and st.session_state.columns_info:
             st.info("👇 Below are the columns loaded from Excel with inferred settings. **Please review each column and adjust the Type, Distribution, and Parameters as needed for accurate data generation.**")
        elif st.session_state.config_source == "Manually Define Columns" and not st.session_state.columns_info:
             st.info("👇 Use the 'Add New Column' section below to start defining columns manually.")
        elif not st.session_state.columns_info:
             st.warning("No columns defined yet. Either load from Excel or add columns manually.")


        # --- Display Area for Existing Columns (Loaded or Manual) - This IS the EDITING area ---
        if st.session_state.columns_info:
            col_config_headers = st.columns([2, 1, 1, 1])
            with col_config_headers[0]: st.markdown("**Column Name**")
            with col_config_headers[1]: st.markdown("**Data Type**")
            with col_config_headers[2]: st.markdown("**Distribution/Method**")
            with col_config_headers[3]: st.markdown("**Action**")

            column_names_list = list(st.session_state.columns_info.keys()) # Get current keys

            for i, col_name in enumerate(column_names_list):
                # Ensure col_info exists, might be removed in loop by user action
                if col_name not in st.session_state.columns_info:
                    continue
                col_info = st.session_state.columns_info[col_name]
                unique_key_prefix = f"col_{i}_{col_name.replace(' ', '_').replace('.', '_')}" # Make key safer

                with st.container(border=True): # Use border to visually separate columns
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.markdown(f"**`{col_name}`**") # Display column name clearly
                    with col2:
                        # --- EDIT TYPE ---
                        current_type = col_info.get('type', 'string') # Default to string if missing
                        try:
                            type_index = ["integer", "float", "string", "date", "boolean"].index(current_type)
                        except ValueError:
                            type_index = 2 # Default to string index if current type is invalid
                        col_type = st.selectbox(f"Type", ["integer", "float", "string", "date", "boolean"],
                                                index=type_index,
                                                key=f"{unique_key_prefix}_type", label_visibility="collapsed")
                        # Update state and potentially rerun if type changes affecting distributions
                        if st.session_state.columns_info[col_name].get('type') != col_type:
                            st.session_state.columns_info[col_name]['type'] = col_type
                            # Reset distribution to a sensible default for the new type? Optional.
                            # Example: if col_type == 'integer': st.session_state.columns_info[col_name]['distribution'] = 'uniform'
                            st.rerun()

                    with col3:
                         # --- EDIT DISTRIBUTION ---
                        col_type = st.session_state.columns_info[col_name].get('type', 'string') # Get current type
                        if col_type == 'integer' or col_type == 'float': dist_options = ["uniform", "normal"]
                        elif col_type == 'string': dist_options = ["choice", "name", "city", "email", "text", "uuid", "custom_regex", "word"]
                        elif col_type == 'date': dist_options = ["date_range"]
                        elif col_type == 'boolean': dist_options = ["random"]
                        else: dist_options = []

                        if dist_options:
                           current_dist = col_info.get('distribution')
                           # Auto-correct distribution if invalid for current type
                           if current_dist not in dist_options:
                               current_dist = dist_options[0] # Default to first valid option
                               st.session_state.columns_info[col_name]['distribution'] = current_dist
                           try:
                               dist_index = dist_options.index(current_dist)
                           except ValueError:
                                dist_index = 0 # Fallback

                           distribution = st.selectbox(f"Dist.", dist_options, index=dist_index, key=f"{unique_key_prefix}_dist", label_visibility="collapsed")
                           # Update state if distribution changes (may affect params needed)
                           if st.session_state.columns_info[col_name].get('distribution') != distribution:
                                st.session_state.columns_info[col_name]['distribution'] = distribution
                                # Clear old params when dist changes? Maybe safer.
                                # e.g. clear min/max if switching from uniform to normal
                                st.rerun()
                        else:
                            st.write("-")
                            st.session_state.columns_info[col_name]['distribution'] = None

                    with col4:
                        # --- REMOVE COLUMN ---
                        if st.button("Remove", key=f"{unique_key_prefix}_remove", help=f"Remove column '{col_name}'"):
                            del st.session_state.columns_info[col_name]
                            # Also remove relationships involving this column
                            st.session_state.relationships = [
                                r for r in st.session_state.relationships
                                if r['condition_col'] != col_name and r['dependent_col'] != col_name
                            ]
                            st.rerun()

                    # --- EDIT PARAMETERS (inside expander) ---
                    distribution = st.session_state.columns_info[col_name].get('distribution') # Get current distribution
                    col_type = st.session_state.columns_info[col_name].get('type') # Get current type

                    with st.expander(f"Configure Parameters for `{col_name}` ({distribution})"):
                        # (Parameter configuration UI - ensure it reads default values correctly using .get)
                        # --- Integer/Float Params ---
                        if col_type == 'integer' or col_type == 'float':
                            default_min = 0.0 if col_type == 'float' else 0
                            default_max = 100.0 if col_type == 'float' else 100
                            default_mean = 50.0 if col_type == 'float' else 50
                            default_std = 10.0 if col_type == 'float' else 10

                            if distribution == 'uniform':
                                min_val = st.number_input(f"Min Value", value=col_info.get('min', default_min), key=f"{unique_key_prefix}_min", format="%g" if col_type=='float' else "%d")
                                max_val = st.number_input(f"Max Value", value=col_info.get('max', default_max), key=f"{unique_key_prefix}_max", format="%g" if col_type=='float' else "%d")
                                st.session_state.columns_info[col_name]['min'] = min_val
                                st.session_state.columns_info[col_name]['max'] = max_val
                            elif distribution == 'normal':
                                mean_val = st.number_input(f"Mean", value=col_info.get('mean', default_mean), key=f"{unique_key_prefix}_mean", format="%g")
                                std_val = st.number_input(f"Std Dev", value=col_info.get('std', default_std), min_value=0.01, key=f"{unique_key_prefix}_std", format="%g")
                                st.session_state.columns_info[col_name]['mean'] = mean_val
                                st.session_state.columns_info[col_name]['std'] = std_val
                                # Bounds for Normal
                                use_bounds = st.checkbox("Set Min/Max Bounds for Normal?", key=f"{unique_key_prefix}_normal_bounds", value=('min' in col_info or 'max' in col_info))
                                if use_bounds:
                                    min_val_bound = st.number_input(f"Min Bound", value=col_info.get('min', default_min), key=f"{unique_key_prefix}_min_bound", format="%g" if col_type=='float' else "%d")
                                    max_val_bound = st.number_input(f"Max Bound", value=col_info.get('max', default_max), key=f"{unique_key_prefix}_max_bound", format="%g" if col_type=='float' else "%d")
                                    st.session_state.columns_info[col_name]['min'] = min_val_bound
                                    st.session_state.columns_info[col_name]['max'] = max_val_bound
                                else:
                                    st.session_state.columns_info[col_name].pop('min', None)
                                    st.session_state.columns_info[col_name].pop('max', None)
                            else:
                                st.caption("No parameters for this distribution.")

                        # --- String Params ---
                        elif col_type == 'string':
                            if distribution == 'choice':
                                choices_list = col_info.get('choices', [])
                                # Display existing choices clearly, handle potential large lists
                                choices_str = "\n".join(choices_list) if choices_list else ""
                                choices_new_str = st.text_area(f"Choices (one per line)", value=choices_str, key=f"{unique_key_prefix}_choices", height=max(100, len(choices_list)*20)) # Adjust height
                                st.session_state.columns_info[col_name]['choices'] = [c.strip() for c in choices_new_str.split('\n') if c.strip()]
                            elif distribution == 'text':
                                 num_words = st.slider(f"Approx Number of Words", min_value=1, max_value=50, value=col_info.get('num_words', 6), key=f"{unique_key_prefix}_num_words")
                                 st.session_state.columns_info[col_name]['num_words'] = num_words
                            elif distribution == 'custom_regex':
                                 regex = st.text_input(f"Regular Expression", value=col_info.get('regex', r'^[A-Z]{3}\d{3}$'), key=f"{unique_key_prefix}_regex", help="Example: ^[A-Z]{3}\\d{3}$ for ABC123 format. Requires 'rstr' library.")
                                 st.session_state.columns_info[col_name]['regex'] = regex
                            else:
                                 st.caption(f"No parameters needed for '{distribution}'.")

                        # --- Date Params ---
                        elif col_type == "date":
                             if distribution == 'date_range':
                                default_start = datetime.date.today() - datetime.timedelta(days=30*365)
                                default_end = datetime.date.today()
                                start_val = col_info.get('start_date', default_start)
                                end_val = col_info.get('end_date', default_end)
                                # Ensure dates are date objects
                                if isinstance(start_val, datetime.datetime): start_val = start_val.date()
                                if isinstance(end_val, datetime.datetime): end_val = end_val.date()
                                if not isinstance(start_val, datetime.date): start_val = default_start
                                if not isinstance(end_val, datetime.date): end_val = default_end

                                start_date = st.date_input(f"Start Date", value=start_val, key=f"{unique_key_prefix}_start_date")
                                end_date = st.date_input(f"End Date", value=end_val, key=f"{unique_key_prefix}_end_date")
                                if end_date < start_date:
                                    st.warning("End Date cannot be before Start Date.")
                                    end_date = start_date
                                st.session_state.columns_info[col_name]['start_date'] = start_date
                                st.session_state.columns_info[col_name]['end_date'] = end_date
                             else:
                                st.caption("No parameters for this distribution.")
                        # --- Boolean Params ---
                        elif col_type == 'boolean':
                             st.caption("No parameters needed for boolean generation.")
                        else:
                             st.caption("Unknown type or no parameters applicable.")

            st.markdown("---") # Separator after listing columns

        # --- Add New Column Manually ---
        # Use st.form for adding new columns to prevent reruns on text input
        with st.form("add_column_form", clear_on_submit=True):
            st.subheader("Add a New Manual Column")
            new_col_name = st.text_input("New Column Name", key="new_col_name_input")
            submitted = st.form_submit_button("Add Column")
            if submitted:
                if new_col_name:
                    clean_new_col_name = new_col_name.strip()
                    if clean_new_col_name and clean_new_col_name not in st.session_state.columns_info:
                        # Add with default settings (string type, word distribution)
                        st.session_state.columns_info[clean_new_col_name] = {'type': 'string', 'distribution': 'word'}
                        st.success(f"Added new column: '{clean_new_col_name}'")
                        # No rerun needed here, form submission handles it implicitly IF state changes affect widgets outside form
                        # However, to see the new column appear immediately in the list above, a rerun IS needed.
                        st.rerun()
                    elif clean_new_col_name in st.session_state.columns_info:
                        st.warning(f"Column '{clean_new_col_name}' already exists.")
                    else:
                         st.warning("Please enter a valid name for the new column.")
                else:
                     st.warning("Please enter a name for the new column.")


        st.markdown("---")

        # --- Define Relationships (Only if columns exist) ---
        if st.session_state.columns_info:
            st.subheader("3. Define Relationships (Optional)")
            # (Relationship UI remains the same as previous version - it uses the current columns in session state)
            available_columns = list(st.session_state.columns_info.keys())

            # Display existing relationships
            rels_to_remove = []
            for i, rel in enumerate(st.session_state.relationships):
                rel_key_prefix = f"rel_{i}"
                # Check if columns involved still exist
                if rel['condition_col'] not in available_columns or rel['dependent_col'] not in available_columns:
                     st.warning(f"Relationship {i+1} involves a removed column. It will be deleted.")
                     rels_to_remove.append(i)
                     continue

                with st.container(border=True):
                    st.write(f"**Relationship {i+1}**")
                    # Displaying the relationship details (simplified)
                    cond_val_display = rel['condition_value']
                    if isinstance(cond_val_display, list): # Nicer display for lists
                        cond_val_display = f"[{', '.join(map(str, cond_val_display))}]"

                    st.markdown(f"IF `{rel['condition_col']}` {rel['condition']} `{cond_val_display}` THEN SET `{rel['dependent_col']}` TO `{rel['dependent_value']}`")

                    if st.button("Remove Relationship", key=f"{rel_key_prefix}_remove_rel", type="secondary"):
                        rels_to_remove.append(i) # Mark for removal

            # Remove marked relationships outside the loop (modifying list while iterating)
            if rels_to_remove:
                 # Remove in reverse order to avoid index issues
                 for index in sorted(rels_to_remove, reverse=True):
                     del st.session_state.relationships[index]
                 st.rerun()


            # Add new relationship UI
            with st.expander("Add New Dependency Relationship"):
                 # (Relationship adding UI is the same)
                rel_type = "dependency"
                cond_col = st.selectbox("IF Column...", available_columns, index=None, key="new_rel_cond_col", placeholder="Select Condition Column")

                cond_val_input_widget = None; cond_options = []; selected_col_type = None
                if cond_col and cond_col in st.session_state.columns_info: selected_col_type = st.session_state.columns_info[cond_col].get('type')

                # Determine appropriate input based on condition column type
                if selected_col_type in ['integer', 'float']: cond_options = ["greater", "less", "equals", "not_equals"]; cond_val_input_widget = st.number_input
                elif selected_col_type == 'date': cond_options = ["greater", "less", "equals", "not_equals"]; cond_val_input_widget = st.date_input
                elif selected_col_type == 'string': cond_options = ["equals", "not_equals", "in", "not_in"]; cond_val_input_widget = st.text_input
                elif selected_col_type == 'boolean': cond_options = ["equals", "not_equals"]; cond_val_input_widget = st.selectbox
                else: cond_options = ["equals", "not_equals"]; cond_val_input_widget = st.text_input # Fallback

                cond = st.selectbox("Is...", cond_options, index=None, key="new_rel_cond", placeholder="Select Condition")

                cond_val_raw = None
                if cond_val_input_widget and cond:
                    cond_val_help = ""; input_kwargs = {"key": "new_rel_cond_val"}
                    if cond in ['in', 'not_in']: cond_val_help = "Enter comma-separated values"; input_kwargs["placeholder"] = "e.g., value1, value2"
                    elif selected_col_type == 'boolean': cond_val_help = "Select True or False"; input_kwargs["options"] = [True, False]; input_kwargs["index"] = None; input_kwargs["placeholder"] = "Select..."
                    elif selected_col_type == 'date': input_kwargs["value"] = None
                    elif selected_col_type in ['integer', 'float']: input_kwargs["value"] = None; input_kwargs["step"] = None if selected_col_type == 'float' else 1; input_kwargs["format"] = "%g" if selected_col_type == 'float' else "%d"; input_kwargs["placeholder"] = "Enter number"
                    else: input_kwargs["placeholder"] = "Enter value"
                    input_kwargs["help"] = cond_val_help

                    cond_val_raw = cond_val_input_widget("Value...", **input_kwargs)

                dep_col = st.selectbox("THEN Set Column...", available_columns, index=None, key="new_rel_dep_col", placeholder="Select Dependent Column")
                dep_val_str = st.text_input("To Value...", key="new_rel_dep_val", placeholder="Enter value to assign", help="This value will be assigned. Type casting attempted during generation.")

                if st.button("Add Relationship", key="add_rel_button"):
                    # Validation logic remains same
                    error_msg = ""
                    if not all([cond_col, cond, dep_col]) or cond_val_raw is None:
                        if isinstance(cond_val_raw, str) and cond_val_raw == "": pass # Allow empty string
                        elif cond_val_raw is None: error_msg = "Please fill all relationship fields, including the condition value."
                    # ... [Other validation checks: same column, 'in' format] ...
                    elif cond_col == dep_col: error_msg = "Condition column and Dependent column cannot be the same."
                    elif cond in ['in', 'not_in'] and (not isinstance(cond_val_raw, str) or not cond_val_raw.strip()): error_msg = "Please provide comma-separated values for 'in'/'not_in' condition."


                    if error_msg: st.error(error_msg)
                    else:
                        # Parsing logic remains same
                        parsed_cond_val = cond_val_raw
                        if cond in ['in', 'not_in']: parsed_cond_val = [v.strip() for v in cond_val_raw.split(',') if v.strip()]

                        st.session_state.relationships.append({
                            'type': rel_type, 'condition_col': cond_col, 'condition': cond,
                            'condition_value': parsed_cond_val, 'dependent_col': dep_col,
                            'dependent_value': dep_val_str
                        })
                        st.rerun()

            st.markdown("---")

        # --- Generate Button and Display ---
        st.subheader("4. Generate and Download")

        num_rows = st.number_input("Number of Rows to Generate", min_value=1, max_value=50000, value=st.session_state.get('num_rows_generate', 100), key="num_rows_generate")
        # st.session_state['num_rows_generate'] = num_rows # Store value for persistence


        if st.button("Generate Tabular Data", type="primary"):
            if not st.session_state.columns_info:
                st.error("No columns configured. Please load from Excel or add columns manually.")
            else:
                # --- Final Validation Before Generation (Enhanced) ---
                valid_config = True
                for col_name, col_info in st.session_state.columns_info.items():
                     dist = col_info.get('distribution')
                     col_type = col_info.get('type')
                     if dist == 'choice' and not col_info.get('choices'):
                         st.error(f"Column '{col_name}': 'choice' distribution selected, but no choices provided in parameters.")
                         valid_config = False
                     if dist == 'custom_regex' and not col_info.get('regex'):
                         st.error(f"Column '{col_name}': 'custom_regex' distribution selected, but no regex pattern provided.")
                         valid_config = False
                     if col_type in ['integer', 'float'] and dist == 'uniform':
                         if col_info.get('min') is None or col_info.get('max') is None:
                              st.error(f"Column '{col_name}': 'uniform' distribution requires Min and Max values.")
                              valid_config = False
                         elif col_info.get('max') < col_info.get('min'):
                              st.error(f"Column '{col_name}': Max value cannot be less than Min value for 'uniform' distribution.")
                              valid_config = False
                     if col_type in ['integer', 'float'] and dist == 'normal':
                          if col_info.get('mean') is None or col_info.get('std') is None:
                               st.error(f"Column '{col_name}': 'normal' distribution requires Mean and Std Dev values.")
                               valid_config = False
                          elif col_info.get('std', 1) <= 0:
                               st.error(f"Column '{col_name}': Standard Deviation must be positive for 'normal' distribution.")
                               valid_config = False
                     # Add more validation rules (e.g., date range validity)

                if valid_config:
                    with st.spinner(f"Generating {num_rows} rows of synthetic data..."):
                        st.session_state.generated_df = generate_synthetic_data(
                            num_rows,
                            st.session_state.columns_info,
                            st.session_state.relationships
                        )
                    if st.session_state.generated_df is not None and not st.session_state.generated_df.empty:
                         st.success(f"Successfully generated {len(st.session_state.generated_df)} rows!")
                    elif st.session_state.generated_df is not None: # Generated but empty
                         st.warning("Generation process completed, but the resulting DataFrame is empty. Check configurations, relationships, and potential errors during generation.")
                    # If generate_synthetic_data returned None, errors were likely shown within it.

    # Display DataFrame and Download Button (outside the main config block, depends only on generated_df state)
    if st.session_state.generated_df is not None and not st.session_state.generated_df.empty:
        st.subheader("Generated Data Preview")
        st.dataframe(st.session_state.generated_df)
        try:
            # Prepare CSV data safely
            csv_data = st.session_state.generated_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Generated Data (CSV)",
                data=csv_data,
                file_name=f'synthetic_tabular_data_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
            )
        except Exception as e:
             st.error(f"Error preparing CSV for download: {e}")
    elif st.session_state.generated_df is not None: # Handles the case where it generated an empty DF
         st.info("Generated DataFrame is empty.")


# =====================================
# === IMAGE & COMBINED MODES BELOW ===
# =====================================
# (Code for Image Data and Combined Data modes remains unchanged)
# =======================
# === IMAGE DATA MODE ===
# =======================
elif mode == "Image Data":
    # [PASTED Image Data Mode Code from previous answer]
    st.header("1. Configure Image Generation")

    num_images = st.number_input("Number of Images", min_value=1, max_value=500, value=10, key="num_images") # Limit for performance

    img_cols = st.columns(2)
    with img_cols[0]:
        img_width = st.number_input("Image Width (px)", min_value=10, max_value=1024, value=128)
        img_height = st.number_input("Image Height (px)", min_value=10, max_value=1024, value=128)
    with img_cols[1]:
        bg_color = st.color_picker("Background Color", value="#DDDDDD")
        shape_color = st.color_picker("Shape Color", value="#FF0000")

    shape = st.selectbox("Shape Type", ["rectangle", "ellipse", "line", "triangle"])
    add_text = st.checkbox("Add Text Overlay?")
    img_text = ""
    if add_text:
        img_text = st.text_input("Text to Add", "Synth")

    st.header("2. Generate and Download Images")

    if st.button("Generate Images", type="primary"):
        st.session_state.generated_images = [] # Clear previous images
        with st.spinner("Generating images..."):
            for i in range(num_images):
                img = generate_simple_image(img_width, img_height, bg_color, shape, shape_color, img_text)
                st.session_state.generated_images.append({
                    "id": i,
                    "image": img,
                    "filename": f"image_{i}_{shape}.png"
                 })
        st.success(f"Generated {len(st.session_state.generated_images)} images.")

    if st.session_state.generated_images:
        st.subheader("Generated Images Preview (Max 10)")
        cols = st.columns(5) # Adjust number of columns for display
        for i, img_data in enumerate(st.session_state.generated_images[:10]):
             with cols[i % 5]:
                 st.image(img_data["image"], caption=img_data["filename"], width=100) # Use smaller width for preview

        # --- Download Images as Zip ---
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for img_data in st.session_state.generated_images:
                 img_bytes = image_to_bytes(img_data["image"])
                 zip_file.writestr(img_data["filename"], img_bytes)

        st.download_button(
             label="Download All Images (ZIP)",
             data=zip_buffer.getvalue(),
             file_name="synthetic_images.zip",
             mime="application/zip"
         )


# ======================================
# === COMBINED (IMAGE+LABEL) MODE ===
# ======================================
elif mode == "Combined (Image + Label)":
    #[PASTED Combined Data Mode Code from previous answer]
    st.header("1. Configure Combined Data Generation")
    st.info("This mode generates simple shapes with corresponding labels.")

    num_combined = st.number_input("Number of Items (Image+Label pairs)", min_value=1, max_value=500, value=20, key="num_combined")

    img_comb_cols = st.columns(2)
    with img_comb_cols[0]:
        img_c_width = st.number_input("Image Width (px)", min_value=10, max_value=512, value=64, key="img_c_width")
        img_c_height = st.number_input("Image Height (px)", min_value=10, max_value=512, value=64, key="img_c_height")
    with img_comb_cols[1]:
         bg_c_color = st.color_picker("Background Color", value="#EEEEEE", key="bg_c_color")
         # Shape color could be randomized per shape type later

    # Define the possible labels (which will determine the shape)
    label_options = st.multiselect(
        "Select Shape Types (Labels)",
        ["rectangle", "ellipse", "triangle"], # Add more shapes here
        default=["rectangle", "ellipse"]
    )

    st.header("2. Generate and Download Combined Data")

    if st.button("Generate Combined Data", type="primary"):
         if not label_options:
             st.error("Please select at least one shape type.")
         else:
             st.session_state.generated_combined = {'labels': [], 'images': [], 'filenames': []} # Reset
             with st.spinner("Generating combined data..."):
                 for i in range(num_combined):
                     # 1. Generate Label
                     chosen_label = random.choice(label_options)
                     st.session_state.generated_combined['labels'].append(chosen_label)

                     # 2. Generate Image based on Label
                     # Define shape-specific colors or use random ones
                     if chosen_label == "rectangle":   shape_c_color = "#0000FF" # Blue
                     elif chosen_label == "ellipse":   shape_c_color = "#008000" # Green
                     elif chosen_label == "triangle":  shape_c_color = "#FF0000" # Red
                     else:                             shape_c_color = "#888888" # Grey fallback

                     # Generate image using the helper function
                     img = generate_simple_image(img_c_width, img_c_height, bg_c_color, chosen_label, shape_c_color, text="")

                     filename = f"item_{i}_{chosen_label}.png"
                     st.session_state.generated_combined['images'].append(img)
                     st.session_state.generated_combined['filenames'].append(filename)

             st.success(f"Generated {len(st.session_state.generated_combined['labels'])} items.")


    if st.session_state.generated_combined and st.session_state.generated_combined['labels']:
         st.subheader("Generated Items Preview (Max 10)")
         cols = st.columns(5)
         for i in range(min(10, len(st.session_state.generated_combined['labels']))):
             with cols[i % 5]:
                 st.image(st.session_state.generated_combined['images'][i],
                           caption=f"Label: {st.session_state.generated_combined['labels'][i]}",
                           width=80)

         # Create DataFrame for labels
         labels_df = pd.DataFrame({
             'filename': st.session_state.generated_combined['filenames'],
             'label': st.session_state.generated_combined['labels']
             })

         st.subheader("Labels Data")
         st.dataframe(labels_df)

         # --- Download Combined Data ---
         # 1. Download Labels CSV
         csv_data_comb = labels_df.to_csv(index=False).encode('utf-8')
         st.download_button(
             label="Download Labels CSV",
             data=csv_data_comb,
             file_name='synthetic_labels.csv',
             mime='text/csv',
             key="download_csv_combined"
         )

         # 2. Download Images as Zip
         zip_buffer_comb = io.BytesIO()
         with zipfile.ZipFile(zip_buffer_comb, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
             for i, img in enumerate(st.session_state.generated_combined['images']):
                 filename = st.session_state.generated_combined['filenames'][i]
                 img_bytes = image_to_bytes(img)
                 zip_file.writestr(filename, img_bytes)

         st.download_button(
             label="Download Images (ZIP)",
             data=zip_buffer_comb.getvalue(),
             file_name="synthetic_combined_images.zip",
             mime="application/zip",
             key="download_zip_combined"
         )
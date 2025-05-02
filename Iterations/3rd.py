import streamlit as st
import pandas as pd
import random
import string
from datetime import datetime, timedelta
import re # For camel case conversion help

# --- Helper Functions (Keep these the same) ---

def to_camel_case(s):
    """Converts a string to CamelCase."""
    s = re.sub(r"(_|-)+", " ", str(s)).title().replace(" ", "")
    return s[0].upper() + s[1:] if s else "" # Added check for empty string

def to_title_case(s):
    """Converts a string to Title Case (handles spaces)."""
    return string.capwords(str(s))

def to_sentence_case(s):
    """Converts a string to Sentence case."""
    s = str(s).lower()
    if s:
        return s[0].upper() + s[1:]
    return ""

def generate_random_string(length=10, case='lower'):
    """Generates a random string of specified length and case."""
    characters = string.ascii_letters + string.digits
    base_string = ''.join(random.choice(characters) for i in range(length))

    if case == 'lower':
        return base_string.lower()
    elif case == 'upper':
        return base_string.upper()
    elif case == 'camel':
        return to_camel_case(base_string.lower().replace(" ","_"))
    elif case == 'title':
        words = [ ''.join(random.choice(string.ascii_lowercase) for i in range(random.randint(3, 7))) for _ in range(random.randint(1,3))]
        return to_title_case(" ".join(words))
    elif case == 'sentence':
        words = [ ''.join(random.choice(string.ascii_lowercase) for i in range(random.randint(2,5))) for _ in range(random.randint(2,5))]
        sentence = " ".join(words) + random.choice(['.', '?', '!'])
        return to_sentence_case(sentence)
    else:
        return base_string.lower()

def generate_value(col_def):
    """Generates a single random value based on column definition."""
    col_type = col_def['type']

    try:
        if col_type == "Numerical (Integer)":
            min_val = int(col_def.get('min', 0))
            max_val = int(col_def.get('max', 100))
            if min_val > max_val: min_val, max_val = max_val, min_val
            return random.randint(min_val, max_val)

        elif col_type == "Numerical (Float)":
            min_val = float(col_def.get('min', 0.0))
            max_val = float(col_def.get('max', 100.0))
            if min_val > max_val: min_val, max_val = max_val, min_val
            return random.uniform(min_val, max_val)

        elif col_type == "Text":
            case = col_def.get('case', 'lower')
            min_len = int(col_def.get('min_len', 5))
            max_len = int(col_def.get('max_len', 15))
            if min_len < 1: min_len = 1
            if max_len < min_len: max_len = min_len
            length = random.randint(min_len, max_len)
            return generate_random_string(length, case)

        elif col_type == "Categorical":
            options = [opt.strip() for opt in col_def.get('categories', 'A,B,C').split(',') if opt.strip()]
            if not options: return None
            return random.choice(options)

        elif col_type == "Boolean":
            return random.choice([True, False])

        elif col_type == "Datetime":
            start_date = col_def.get('start_date', datetime.now().date() - timedelta(days=365)) # Get date part
            end_date = col_def.get('end_date', datetime.now().date()) # Get date part

            # Ensure they are datetime objects for comparison and calculation
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time()) # Use max time for end date

            if start_dt > end_dt: start_dt, end_dt = end_dt, start_dt # Swap if needed

            time_between_dates = end_dt - start_dt
            seconds_between_dates = time_between_dates.total_seconds()
            random_number_of_seconds = random.uniform(0, seconds_between_dates)
            return start_dt + timedelta(seconds=random_number_of_seconds)

        else:
            return None
    except Exception as e:
        st.error(f"Error generating data for column '{col_def.get('name', 'Unknown')}': {e}")
        return None


# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("📊 Synthetic Data Generator")

# Initialize session state
if 'column_definitions' not in st.session_state:
    st.session_state.column_definitions = []
# Use session state to hold current widget values if needed, especially for complex interactions
# For this fix, we don't strictly need more session state, as reading widget values directly works.

# --- Column Definition Input Area ---
st.sidebar.header("Define New Column")

# --- CORRECTION POINT 1: Moved Column Type Selector OUTSIDE the form ---
# This selector now triggers an immediate rerun when changed, allowing the
# conditional inputs below it to update instantly.
col_type = st.sidebar.selectbox(
    "Column Data Type*",
    ["Numerical (Integer)", "Numerical (Float)", "Text", "Categorical", "Boolean", "Datetime"],
    key="col_type_selector" # Use a unique key outside the form
)

# --- CORRECTION POINT 2: Moved Conditional Inputs OUTSIDE the form ---
# These inputs are now rendered based on the *current* value of the col_type_selector above.
# Store the constraints temporarily in a dictionary.
constraints_input = {}
if col_type == "Numerical (Integer)":
    num_cols = st.sidebar.columns(2)
    with num_cols[0]:
        # Use unique keys to avoid conflicts if the form is rebuilt
        constraints_input['min'] = st.number_input("Min Value", key="num_min_input", value=0)
    with num_cols[1]:
        constraints_input['max'] = st.number_input("Max Value", key="num_max_input", value=100)
elif col_type == "Numerical (Float)":
     num_cols = st.sidebar.columns(2)
     with num_cols[0]:
        constraints_input['min'] = st.number_input("Min Value", key="float_min_input", value=0.0, format="%.2f")
     with num_cols[1]:
        constraints_input['max'] = st.number_input("Max Value", key="float_max_input", value=100.0, format="%.2f")
elif col_type == "Text":
    constraints_input['case'] = st.sidebar.selectbox(
        "Text Case",
        ['lower', 'upper', 'camel', 'title', 'sentence'],
        key="text_case_input"
    )
    len_cols = st.sidebar.columns(2)
    with len_cols[0]:
         constraints_input['min_len'] = st.number_input("Min Length", min_value=1, value=5, key="text_min_len_input")
    with len_cols[1]:
         constraints_input['max_len'] = st.number_input("Max Length", min_value=1, value=15, key="text_max_len_input")
elif col_type == "Categorical":
    constraints_input['categories'] = st.sidebar.text_area(
        "Categories (comma-separated)*",
        "Option A, Option B, Option C",
        key="cat_options_input"
        )
elif col_type == "Datetime":
    date_cols = st.sidebar.columns(2)
    today = datetime.now().date()
    with date_cols[0]:
        # The value returned by st.date_input is a datetime.date object
        constraints_input['start_date'] = st.date_input("Start Date", value=today - timedelta(days=365), key="date_start_input")
    with date_cols[1]:
        constraints_input['end_date'] = st.date_input("End Date", value=today, key="date_end_input")
# No specific inputs needed for Boolean

# --- CORRECTION POINT 3: Form now contains only the button and non-conditional inputs ---
# The form's main purpose is now just to trigger the "Add Column" action.
# We keep col_name here for simplicity, but it could also be moved outside.
with st.sidebar.form("column_form", clear_on_submit=True):
    col_name = st.text_input("Column Name*", key="col_name_input") # Unique key if needed

    submitted = st.form_submit_button("➕ Add Column Definition")
    if submitted:
        # --- Input Validation ---
        error = False
        if not col_name:
            st.error("Column Name cannot be empty.")
            error = True
        # Check for duplicate names
        if any(d['name'] == col_name for d in st.session_state.column_definitions):
             st.error(f"Column name '{col_name}' already exists.")
             error = True
        # Validate constraints based on the type selected *outside* the form
        if col_type == "Categorical" and not constraints_input.get('categories'):
             st.error("Categories cannot be empty for Categorical type.")
             error = True
        # Add more specific validation if needed (e.g., min <= max)
        if col_type in ["Numerical (Integer)", "Numerical (Float)"]:
             if constraints_input.get('min') > constraints_input.get('max'):
                 st.warning(f"Min value ({constraints_input.get('min')}) is greater than Max value ({constraints_input.get('max')}). They will be swapped during generation if needed, but you might want to correct the input.")
                 # You could make this an error = True if you prefer strict validation
        if col_type == "Text":
             if constraints_input.get('min_len') > constraints_input.get('max_len'):
                 st.warning(f"Min Length ({constraints_input.get('min_len')}) is greater than Max Length ({constraints_input.get('max_len')}). Max length will be used.")
                 # You could make this an error = True

        if not error:
            # --- CORRECTION POINT 4: Assemble definition using inputs from *outside* and *inside* form ---
            new_col_def = {
                "name": col_name, # From inside the form
                "type": col_type, # Read from the selector outside the form
                **constraints_input # Add the constraints collected outside the form
            }
            st.session_state.column_definitions.append(new_col_def)
            st.sidebar.success(f"Column '{col_name}' ({col_type}) added!")
            # Optional: Reset conditional input fields manually if needed,
            # because clear_on_submit only clears form elements.
            # However, since they re-render based on col_type selector,
            # they might appear correct on the next interaction anyway.
            # st.experimental_rerun() # Use st.rerun() in newer versions if needed

# --- Display Defined Columns (Keep this section the same) ---
st.header("Defined Columns")
if not st.session_state.column_definitions:
    st.info("No columns defined yet. Use the sidebar to add column definitions.")
else:
    # Adjust number of columns dynamically or use a container
    num_defined_cols = len(st.session_state.column_definitions)
    cols_per_row = 4 # Adjust how many column details fit comfortably
    rows_needed = (num_defined_cols + cols_per_row -1) // cols_per_row

    col_index = 0
    for r in range(rows_needed):
        cols_display = st.columns(cols_per_row)
        for c in range(cols_per_row):
            if col_index < num_defined_cols:
                col_def = st.session_state.column_definitions[col_index]
                i = col_index # Keep track of original index for removal
                with cols_display[c]:
                    with st.expander(f"**{col_def['name']}** ({col_def['type']})", expanded=False):
                        st.write(f"**Type:** {col_def['type']}")
                        # Display relevant constraints based on type
                        if col_def['type'] in ["Numerical (Integer)", "Numerical (Float)"]:
                            st.write(f"**Min:** {col_def.get('min', 'N/A')}")
                            st.write(f"**Max:** {col_def.get('max', 'N/A')}")
                        elif col_def['type'] == "Text":
                            st.write(f"**Case:** {col_def.get('case', 'N/A')}")
                            st.write(f"**Min Len:** {col_def.get('min_len', 'N/A')}")
                            st.write(f"**Max Len:** {col_def.get('max_len', 'N/A')}")
                        elif col_def['type'] == "Categorical":
                            # Truncate long category lists for display
                            cats = col_def.get('categories', 'N/A')
                            display_cats = (cats[:75] + '...') if len(cats) > 75 else cats
                            st.write(f"**Categories:** {display_cats}")
                        elif col_def['type'] == "Datetime":
                             # Format dates for display
                             start_disp = col_def.get('start_date', 'N/A')
                             if isinstance(start_disp, datetime.date): start_disp = start_disp.strftime('%Y-%m-%d')
                             end_disp = col_def.get('end_date', 'N/A')
                             if isinstance(end_disp, datetime.date): end_disp = end_disp.strftime('%Y-%m-%d')
                             st.write(f"**Start:** {start_disp}")
                             st.write(f"**End:** {end_disp}")

                        # --- Remove Button ---
                        if st.button(f"Remove", key=f"remove_{i}_{col_def['name']}"):
                            del st.session_state.column_definitions[i]
                            st.rerun() # Rerun to update display
                col_index += 1


# --- Data Generation Section (Keep this section the same) ---
st.header("Generate Data")

if st.session_state.column_definitions:
    num_rows = st.number_input("Number of Rows to Generate", min_value=1, max_value=100000, value=100, key="num_rows")

    if st.button("🚀 Generate Data", key="generate_button"):
        st.write("Generating data...")
        progress_bar = st.progress(0)
        generated_data = {}
        total_cols = len(st.session_state.column_definitions)
        all_data = [] # Store rows as dicts

        with st.spinner('Generating rows...'):
            for r in range(num_rows):
                row_data = {}
                for i, col_def in enumerate(st.session_state.column_definitions):
                    row_data[col_def['name']] = generate_value(col_def)
                all_data.append(row_data)
                if (r + 1) % (num_rows // 20 + 1) == 0: # Update progress roughly 20 times
                     progress_bar.progress((r + 1) / num_rows)

        df_generated = pd.DataFrame(all_data)
        progress_bar.progress(1.0) # Ensure it reaches 100%

        st.success(f"Data generated successfully! ({num_rows} rows)")
        st.dataframe(df_generated)

        # --- Download Button ---
        @st.cache_data # Cache the conversion
        def convert_df(df):
           return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df_generated)

        st.download_button(
           label="📥 Download data as CSV",
           data=csv,
           file_name=f'synthetic_data_{num_rows}rows_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
           mime='text/csv',
           key="download_csv"
        )
else:
    st.warning("Please define at least one column before generating data.")

# --- Footer/Info (Keep this the same) ---
st.sidebar.markdown("---")
st.sidebar.info("Select data type first, then fill details. Add columns using the button. Finally, set row count and generate.")
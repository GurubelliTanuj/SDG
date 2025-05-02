import streamlit as st
import pandas as pd
import random
import string
from datetime import datetime, timedelta
import re # For camel case conversion help

# --- Helper Functions ---

def to_camel_case(s):
    """Converts a string to CamelCase."""
    s = re.sub(r"(_|-)+", " ", str(s)).title().replace(" ", "")
    return s[0].upper() + s[1:]

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
        # Simple approach: generate lower, then convert a part
        return to_camel_case(base_string.lower().replace(" ","_")) # Use helper
    elif case == 'title':
         # Simple approach: generate lower words and title case
        words = [ ''.join(random.choice(string.ascii_lowercase) for i in range(random.randint(3, 7))) for _ in range(random.randint(1,3))]
        return to_title_case(" ".join(words))
    elif case == 'sentence':
         # Simple approach: generate lower words and sentence case
        words = [ ''.join(random.choice(string.ascii_lowercase) for i in range(random.randint(3, 7))) for _ in range(random.randint(2,5))]
        sentence = " ".join(words) + random.choice(['.', '?', '!'])
        return to_sentence_case(sentence)
    else: # Default to lower
        return base_string.lower()

def generate_value(col_def):
    """Generates a single random value based on column definition."""
    col_type = col_def['type']

    try:
        if col_type == "Numerical (Integer)":
            min_val = int(col_def.get('min', 0))
            max_val = int(col_def.get('max', 100))
            if min_val > max_val: min_val, max_val = max_val, min_val # Swap if needed
            return random.randint(min_val, max_val)

        elif col_type == "Numerical (Float)":
            min_val = float(col_def.get('min', 0.0))
            max_val = float(col_def.get('max', 100.0))
            if min_val > max_val: min_val, max_val = max_val, min_val # Swap if needed
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
            if not options: return None # Handle empty categories
            return random.choice(options)

        elif col_type == "Boolean":
            return random.choice([True, False])

        elif col_type == "Datetime":
            start_date = col_def.get('start_date', datetime.now() - timedelta(days=365))
            end_date = col_def.get('end_date', datetime.now())

            # Ensure they are datetime objects if they came from st.date_input
            if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime):
                 start_date = datetime.combine(start_date, datetime.min.time())
            if isinstance(end_date, datetime.date) and not isinstance(end_date, datetime):
                 end_date = datetime.combine(end_date, datetime.max.time())

            if start_date > end_date: start_date, end_date = end_date, start_date # Swap if needed

            time_between_dates = end_date - start_date
            seconds_between_dates = time_between_dates.total_seconds()
            random_number_of_seconds = random.uniform(0, seconds_between_dates)
            return start_date + timedelta(seconds=random_number_of_seconds)

        else:
            return None # Unknown type
    except Exception as e:
        st.error(f"Error generating data for column '{col_def.get('name', 'Unknown')}': {e}")
        return None


# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("📊 Synthetic Data Generator")

# Initialize session state for column definitions
if 'column_definitions' not in st.session_state:
    st.session_state.column_definitions = []

# --- Column Definition Input Area ---
st.sidebar.header("Define New Column")
with st.sidebar.form("column_form", clear_on_submit=True):
    col_name = st.text_input("Column Name*", key="col_name")
    col_type = st.selectbox(
        "Column Data Type*",
        ["Numerical (Integer)", "Numerical (Float)", "Text", "Categorical", "Boolean", "Datetime"],
        key="col_type"
    )

    # --- Conditional Constraints ---
    constraints = {}
    if col_type in ["Numerical (Integer)", "Numerical (Float)"]:
        num_cols = st.columns(2)
        with num_cols[0]:
            constraints['min'] = st.number_input("Min Value", key="num_min", value=0 if col_type == "Numerical (Integer)" else 0.0)
        with num_cols[1]:
             constraints['max'] = st.number_input("Max Value", key="num_max", value=100 if col_type == "Numerical (Integer)" else 100.0)

    elif col_type == "Text":
        constraints['case'] = st.selectbox(
            "Text Case",
            ['lower', 'upper', 'camel', 'title', 'sentence'],
            key="text_case"
        )
        len_cols = st.columns(2)
        with len_cols[0]:
             constraints['min_len'] = st.number_input("Min Length", min_value=1, value=5, key="text_min_len")
        with len_cols[1]:
             constraints['max_len'] = st.number_input("Max Length", min_value=1, value=15, key="text_max_len")


    elif col_type == "Categorical":
        constraints['categories'] = st.text_area(
            "Categories (comma-separated)*",
            "Option A, Option B, Option C",
            key="cat_options"
            )

    elif col_type == "Datetime":
        date_cols = st.columns(2)
        today = datetime.now().date()
        with date_cols[0]:
            constraints['start_date'] = st.date_input("Start Date", value=today - timedelta(days=365), key="date_start")
        with date_cols[1]:
            constraints['end_date'] = st.date_input("End Date", value=today, key="date_end")

    # --- Add Column Button ---
    submitted = st.form_submit_button("➕ Add Column Definition")
    if submitted:
        # --- Input Validation ---
        error = False
        if not col_name:
            st.error("Column Name cannot be empty.")
            error = True
        if col_type == "Categorical" and not constraints['categories']:
            st.error("Categories cannot be empty for Categorical type.")
            error = True
        # Check if column name already exists
        if any(d['name'] == col_name for d in st.session_state.column_definitions):
             st.error(f"Column name '{col_name}' already exists.")
             error = True

        if not error:
            new_col_def = {
                "name": col_name,
                "type": col_type,
                **constraints # Add specific constraints
            }
            st.session_state.column_definitions.append(new_col_def)
            st.sidebar.success(f"Column '{col_name}' added!")
            # Force rerun to update the display immediately (optional, but good UX)
            # st.experimental_rerun() # Use st.rerun() for newer Streamlit versions

# --- Display Defined Columns ---
st.header("Defined Columns")
if not st.session_state.column_definitions:
    st.info("No columns defined yet. Use the sidebar to add column definitions.")
else:
    cols_display = st.columns(len(st.session_state.column_definitions) + 1) # +1 for remove buttons slightly offset

    for i, col_def in enumerate(st.session_state.column_definitions):
        with cols_display[i]:
             with st.expander(f"**{col_def['name']}** ({col_def['type']})", expanded=False):
                st.write(f"**Type:** {col_def['type']}")
                if col_def['type'] in ["Numerical (Integer)", "Numerical (Float)"]:
                    st.write(f"**Min:** {col_def.get('min', 'N/A')}")
                    st.write(f"**Max:** {col_def.get('max', 'N/A')}")
                elif col_def['type'] == "Text":
                    st.write(f"**Case:** {col_def.get('case', 'N/A')}")
                    st.write(f"**Min Len:** {col_def.get('min_len', 'N/A')}")
                    st.write(f"**Max Len:** {col_def.get('max_len', 'N/A')}")
                elif col_def['type'] == "Categorical":
                    st.write(f"**Categories:** {col_def.get('categories', 'N/A')}")
                elif col_def['type'] == "Datetime":
                    st.write(f"**Start:** {col_def.get('start_date', 'N/A')}")
                    st.write(f"**End:** {col_def.get('end_date', 'N/A')}")

                # --- Remove Button ---
                if st.button(f"Remove '{col_def['name']}'", key=f"remove_{i}_{col_def['name']}"):
                    del st.session_state.column_definitions[i]
                    st.rerun() # Rerun to update display

# --- Data Generation Section ---
st.header("Generate Data")

if st.session_state.column_definitions:
    num_rows = st.number_input("Number of Rows to Generate", min_value=1, max_value=100000, value=100, key="num_rows")

    if st.button("🚀 Generate Data", key="generate_button"):
        st.write("Generating data...")
        progress_bar = st.progress(0)
        generated_data = {}
        total_cols = len(st.session_state.column_definitions)

        for i, col_def in enumerate(st.session_state.column_definitions):
            col_name = col_def['name']
            generated_data[col_name] = [generate_value(col_def) for _ in range(num_rows)]
            progress_bar.progress((i + 1) / total_cols) # Update progress bar

        df_generated = pd.DataFrame(generated_data)

        st.success("Data generated successfully!")
        st.dataframe(df_generated)

        # --- Download Button ---
        csv = df_generated.to_csv(index=False).encode('utf-8')
        st.download_button(
           label="📥 Download data as CSV",
           data=csv,
           file_name='synthetic_data.csv',
           mime='text/csv',
           key="download_csv"
        )
else:
    st.warning("Please define at least one column before generating data.")

# --- Footer/Info ---
st.sidebar.markdown("---")
st.sidebar.info("Define columns using the form above. Add them using the 'Add Column' button. Then, set the number of rows and click 'Generate Data'.")
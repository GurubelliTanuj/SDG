# constants.py
import streamlit as st # Keep streamlit import if used for warnings related to optional libs

# --- Optional Libraries Check (For NUMERICAL_DISTS) ---
# We still need the check here to define the constant correctly
try:
    from scipy import stats
except ImportError:
    stats = None
    # Optional: Show warning once if needed, maybe better placed in utils or main
    # st.sidebar.warning("`scipy` library not found. Some statistical distributions disabled.", icon="⚠️")

# --- Constant Definitions (Moved from utils.py) ---
DATA_TYPES = ["Tabular", "Excel Augmentation", "Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)"]
COLUMN_DATA_TYPES_UI = ["Integer", "Float", "Categorical", "String (Faker)", "String (Regex)", "Date", "Boolean"]
TABULAR_METHODS = ["Rule-Based (Faker/Random/Regex/Deps)", "Statistical (NumPy/SciPy Dist)"]
EXCEL_AUG_METHODS = ["Inferred Schema Generation (Editable)"]
IMAGE_METHODS = ["Rule-Based (Pillow Shapes)"]
TEXT_METHODS = ["Rule-Based (Faker)"]
GRAPH_METHODS = ["Rule-Based (NetworkX Random)"]
PRIVACY_METHODS = ["None", "Differential Privacy (Conceptual Placeholder)"]
USE_CASES = ["General Purpose / Testing", "Model Training (Consider Fidelity)", "Instruct Dataset", "Privacy Preservation (Requires Method)"]

NUMERICAL_DISTS = ["uniform", "normal"] # Base list
if stats: NUMERICAL_DISTS.extend(["poisson", "gamma", "beta"]) # Conditionally add scipy dists

DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"] # For Tabular mode

PANDAS_TYPE_MAP = {
    'int64': 'Integer', 'Int64': 'Integer',
    'float64': 'Float', 'Float64': 'Float',
    'datetime64[ns]': 'Date', 'timedelta[ns]': 'Date', # Handle timedelta too
    'bool': 'Boolean', 'boolean': 'Boolean',
    'object': 'String (Faker)', 'string': 'String (Faker)', # Handle pandas string type
    'category': 'Categorical'
}
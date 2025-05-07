# constants.py
import streamlit as st # Keep streamlit import if used for warnings related to optional libs

# --- Optional Libraries Check (For NUMERICAL_DISTS) ---
try:
    from scipy import stats
except ImportError:
    stats = None

# --- Constant Definitions ---
DATA_TYPES = ["Tabular", "Excel Augmentation", "NER Augmentation", "Image (Basic Shapes)", "Text (Basic)", "Graph (Basic Random)", "Tabular - Prompt"]

# --- MODIFICATION: Adjust Time type ---
COLUMN_DATA_TYPES_UI = [
    "Integer", "Float", "Categorical",
    "String (Faker)", "String (Regex)",
    "Date", "DateTime (dd-mm-yyyy HH:MM:SS)", #"Time (HH:MM)", # Changed HH:MM:SS to HH:MM
    "Boolean"
]
# --- END MODIFICATION ---

TABULAR_METHODS = ["Rule-Based (Faker/Random/Regex/Deps)", "Statistical (NumPy/SciPy Dist)"]
EXCEL_AUG_METHODS = ["Inferred Schema Generation (Editable)"]
IMAGE_METHODS = ["Rule-Based (Pillow Shapes)"]
TEXT_METHODS = ["Rule-Based (Faker)"]
GRAPH_METHODS = ["Rule-Based (NetworkX Random)"]
PRIVACY_METHODS = ["None", "Differential Privacy (Conceptual Placeholder)"]
USE_CASES = ["General Purpose / Testing", "Model Training (Consider Fidelity)", "Instruct Dataset", "Privacy Preservation (Requires Method)"]

NUMERICAL_DISTS = ["uniform", "normal"]
if stats: NUMERICAL_DISTS.extend(["poisson", "gamma", "beta"])

DEPENDENCY_CONDITIONS = ["equals", "not equals", "greater than", "less than", "in list", "not in list"]

PANDAS_TYPE_MAP = {
    'int64': 'Integer', 'Int64': 'Integer',
    'float64': 'Float', 'Float64': 'Float',
    'datetime64[ns]': 'Date', 'timedelta[ns]': 'Date',
    'bool': 'Boolean', 'boolean': 'Boolean',
    'object': 'String (Faker)', 'string': 'String (Faker)',
    'category': 'Categorical'
}

NER_AUG_METHODS = ["Entity-Based Rule Augmentation (Placeholder)"]
NER_ENTITY_ACTIONS = [
    "Replace Matched Text with Faker",
    "Inject New Entity into Template String",
    "Anonymize Matched Text"
]
COMMON_FAKER_PROVIDERS_FOR_NER = sorted([
    'name', 'name_male', 'name_female', 'first_name', 'last_name',
    'company', 'job', 'bs', 'catch_phrase',
    'city', 'country', 'street_address', 'zipcode',
    'date_of_birth', 'date_this_century', 'date_time_this_decade', 'time_object',
    'email', 'phone_number', 'license_plate', 'ssn',
    'credit_card_number', 'iban',
    'word', 'sentence', 'paragraph',
    'color_name', 'hex_color',
    'file_name', 'uri', 'url', 'ipv4', 'mac_address'
])

# state_manager.py
import streamlit as st
import pandas as pd

from constants import DATA_TYPES, USE_CASES, PRIVACY_METHODS, EXCEL_AUG_METHODS

def initialize_state():
    """Initializes st.session_state."""
    default_state = {
        'config': { # ... (config defaults remain same) ...
             'data_type': DATA_TYPES[0], 'use_case': USE_CASES[0],
             'privacy_level': PRIVACY_METHODS[0], 'privacy_epsilon': 1.0,
             'generation_method': None, 'num_rows': 100
        },
        'tabular': {
            'columns': [],
            'relationships': [],
            # --- MODIFICATION: Add key for instruct template ---
            'instruct_template': "Instruction: {instruction_col}\nOutput: {output_col}" # Default example
            # --- END MODIFICATION ---
        },
        'excel_mode': { # ... (excel_mode defaults remain same) ...
            'base_df_preview': None, 'excel_aug_editable_columns': [],
            'selected_sheet': None, 'num_new_rows': 100,
            'file_uploader_key': 0, 'processed_filename': None
        },
        'image': { # ... (image defaults remain same) ...
            'count': 10, 'width': 128, 'height': 128,
            'bg_color': '#DDDDDD', 'shape': 'rectangle', 'shape_color': '#FF0000'
        },
        'text': { # ... (text defaults remain same) ...
             'count': 10, 'faker_method': 'sentence'
        },
        'graph':{ # ... (graph defaults remain same) ...
             'num_nodes': 10, 'num_edges': 15, 'directed': False
        },
        'results': { # ... (results defaults remain same) ...
             'data': None, 'message': None, 'error': None, 'is_generating': False
        }
    }
    # ... (rest of initialization logic remains same) ...
    for key, value in default_state.items():
        if key not in st.session_state: st.session_state[key] = value
    for mode_key, mode_defaults in default_state.items():
        if isinstance(mode_defaults, dict):
            current_mode_state = st.session_state.setdefault(mode_key, {})
            for sub_key, sub_value in mode_defaults.items():
                 current_mode_state.setdefault(sub_key, sub_value)
    initial_data_type = st.session_state.config.get('data_type')
    if st.session_state.config.get('generation_method') is None:
        if initial_data_type == "Excel Augmentation":
            st.session_state.config['generation_method'] = EXCEL_AUG_METHODS[0]
import streamlit as st
from constants import DATA_TYPES, USE_CASES, PRIVACY_METHODS, EXCEL_AUG_METHODS, NER_AUG_METHODS, TABULAR_METHODS

def initialize_state():
    default_state = {
        'config': { 
             'data_type': DATA_TYPES[0], 'use_case': USE_CASES[0],
             'privacy_level': PRIVACY_METHODS[0], 'privacy_epsilon': 1.0,
             'generation_method': None, 'num_rows': 100 
        },
        'tabular': { # File upload keys remain but are unused by tabular_generator.py UI
            'columns': [], 'relationships': [],
            'instruct_template': "Instruction: {instruction_col}\nOutput: {output_col}",
            'base_df_preview': None, 'file_uploader_key': 0, 
            'processed_filename': None, 'selected_sheet': None, 'is_csv_upload': False
        },
        'excel_mode': { 
            'base_df_preview': None, 'excel_aug_editable_columns': [],
            'selected_sheet': None, 'num_new_rows': 100,
            'file_uploader_key': 0, 'processed_filename': None
        },
        'ner_mode': {
            'editable_entity_rules': [], 'original_text_samples': [],
            'base_text_preview': None, 'text_column_name': None,   
            'file_uploader_key': 0, 'processed_filename': None,
            'num_augmented_samples': 10, 'file_type_hint': None       
        },
        'image': { 
            'count': 10, 'width': 128, 'height': 128,
            'bg_color': '#DDDDDD', 'shape': 'rectangle', 'shape_color': '#FF0000'
        },
        'text': { 'count': 10, 'faker_method': 'sentence' },
        'graph':{ 'num_nodes': 10, 'num_edges': 15, 'directed': False },
        'results': { 'data': None, 'message': None, 'error': None, 'is_generating': False }
    }
    for key, value in default_state.items():
        if key not in st.session_state: st.session_state[key] = value
    for mode_key, mode_defaults in default_state.items():
        if isinstance(mode_defaults, dict):
            current_mode_state = st.session_state.setdefault(mode_key, {})
            for sub_key, sub_value in mode_defaults.items():
                 current_mode_state.setdefault(sub_key, sub_value)
    
    initial_data_type = st.session_state.config.get('data_type')
    if st.session_state.config.get('generation_method') is None:
        if initial_data_type == "Tabular" and TABULAR_METHODS: # Default for Tabular
            st.session_state.config['generation_method'] = TABULAR_METHODS[0]
        elif initial_data_type == "Excel Augmentation" and EXCEL_AUG_METHODS:
            st.session_state.config['generation_method'] = EXCEL_AUG_METHODS[0]
        elif initial_data_type == "NER Augmentation" and NER_AUG_METHODS: 
            st.session_state.config['generation_method'] = NER_AUG_METHODS[0]
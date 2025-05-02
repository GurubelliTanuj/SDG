# excel_generator.py
import streamlit as st
import pandas as pd
from datetime import date # Added for final type coercion if needed

# Import shared utilities (no constants needed directly in render/action)
from utils import (
    infer_schema_and_convert_for_editing,
    column_editor_ui, add_new_column_ui,
    generate_tabular_value
)

def render_excel_page():
    """Renders the UI elements specific to the Excel Augmentation mode."""
    st.info("Upload Excel -> Review/Edit Inferred Schema -> Add New Columns (Optional) -> Generate New Rows")
    excel_state = st.session_state.excel_mode
    file_uploader_key = f"excel_uploader_aug_{excel_state['file_uploader_key']}"
    uploaded_file_aug = st.file_uploader("Upload Excel File (.xlsx, .xls)", type=['xlsx', 'xls'], key=file_uploader_key)
    if excel_state.get('excel_aug_editable_columns') or excel_state.get('processed_filename'):
         if st.button("Clear Config & Upload New File", key="clear_excel_config"):
             st.session_state.excel_mode = {'base_df_preview': None, 'excel_aug_editable_columns': [], 'selected_sheet': None, 'num_new_rows': 100, 'file_uploader_key': excel_state['file_uploader_key'] + 1, 'processed_filename': None}
             st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}; st.rerun()
    if uploaded_file_aug:
        is_new_file = uploaded_file_aug.name != excel_state.get('processed_filename'); needs_processing = not excel_state.get('excel_aug_editable_columns')
        if is_new_file or needs_processing:
            try:
                xls = pd.ExcelFile(uploaded_file_aug); sheet_names = xls.sheet_names; selected_sheet = None
                if len(sheet_names) > 1: selected_sheet = st.selectbox("Select Sheet", sheet_names, key="sheet_selector_aug", index=None, placeholder="Choose...")
                elif len(sheet_names) == 1: selected_sheet = sheet_names[0]; st.caption(f"Using sheet: '{selected_sheet}'")
                else: st.warning("No sheets found.")
                if selected_sheet:
                    if selected_sheet != excel_state.get('selected_sheet') or is_new_file:
                         with st.spinner(f"Processing '{selected_sheet}'..."):
                            df_uploaded = pd.read_excel(uploaded_file_aug, sheet_name=selected_sheet)
                            excel_state['base_df_preview'] = df_uploaded.head()
                            editable_schema = infer_schema_and_convert_for_editing(df_uploaded) # Util function
                            excel_state['excel_aug_editable_columns'] = editable_schema
                            excel_state['selected_sheet'] = selected_sheet
                            excel_state['processed_filename'] = uploaded_file_aug.name
                            st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}; st.rerun()
            except Exception as e: st.error(f"Error processing Excel: {e}")
    if excel_state.get('base_df_preview') is not None:
         st.subheader(f"Preview ('{excel_state.get('selected_sheet', 'N/A')}')")
         st.dataframe(excel_state['base_df_preview'])
    st.divider()
    if excel_state.get('excel_aug_editable_columns'):
        st.subheader("Review / Edit / Add Columns for Generation")
        column_editor_ui(excel_state['excel_aug_editable_columns'], key_prefix="excel_aug") # Shared UI
        st.divider()
        add_new_column_ui(excel_state['excel_aug_editable_columns'], key_prefix="excel_aug") # Shared UI
        st.divider()
        excel_state['num_new_rows'] = st.number_input( "Number of NEW Rows", min_value=1, max_value=100000, value=excel_state.get('num_new_rows', 100), key="excel_num_rows_input" )
    elif not uploaded_file_aug : st.info("Upload Excel file to begin.")

def generate_excel_data_action():
    # ... (function definition remains the same as previous answer) ...
    results = {'data': None, 'message': None, 'error': None}
    try:
        column_config_list = st.session_state.excel_mode.get('excel_aug_editable_columns', [])
        row_count = st.session_state.excel_mode.get('num_new_rows', 100)
        if not column_config_list: raise ValueError("No editable columns defined.")
        all_rows_data = []
        for i_row in range(row_count):
            row = {col['name']: generate_tabular_value(col) for col in column_config_list if 'name' in col}
            all_rows_data.append(row)
        df = pd.DataFrame(all_rows_data)
        for col_def in column_config_list: # Final type coercion loop
             col_name = col_def.get('name'); target_ui_type = col_def.get('data_type')
             if col_name and target_ui_type and col_name in df.columns:
                  try:
                      current_dtype = df[col_name].dtype
                      if target_ui_type == "Integer" and not pd.api.types.is_integer_dtype(current_dtype): df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
                      elif target_ui_type == "Float" and not pd.api.types.is_float_dtype(current_dtype): df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Float64')
                      elif target_ui_type == "Date" and not pd.api.types.is_datetime64_any_dtype(current_dtype): df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date
                      elif target_ui_type == "Boolean" and not pd.api.types.is_bool_dtype(current_dtype):
                           if pd.api.types.is_string_dtype(current_dtype): bool_map = {'true': True, '1': True, 'yes': True, 'false': False, '0': False, 'no': False}; df[col_name] = df[col_name].str.lower().map(bool_map)
                           df[col_name] = df[col_name].astype('boolean')
                      elif target_ui_type == "Categorical" and not pd.api.types.is_categorical_dtype(current_dtype): df[col_name] = df[col_name].astype('category')
                  except Exception as e_final_conv: st.warning(f"FinalConvWarn '{col_name}': {e_final_conv}")
        results['data'] = df; results['message'] = f"Generated {len(df)} new rows (Excel Augmentation)."
    except Exception as e: results['error'] = f"Excel Augmentation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
# excel_generator.py
import streamlit as st
import pandas as pd
from datetime import date 

from utils import (
    infer_schema_and_convert_for_editing,
    column_editor_ui, add_new_column_ui,
    generate_tabular_value,
    render_tabular_excel_params_ui 
)
from constants import COLUMN_DATA_TYPES_UI 

def render_excel_page():
    st.info("Upload Excel -> Review/Edit Inferred Schema -> Add New Columns (Optional) -> Generate New Rows")
    excel_state = st.session_state.excel_mode
    file_uploader_key = f"excel_uploader_aug_{excel_state['file_uploader_key']}"
    uploaded_file_aug = st.file_uploader("Upload Excel File (.xlsx, .xls)", type=['xlsx', 'xls'], key=file_uploader_key)
    
    if excel_state.get('excel_aug_editable_columns') or excel_state.get('processed_filename'):
         if st.button("Clear Config & Upload New File", key="clear_excel_config"):
             st.session_state.excel_mode = {
                 'base_df_preview': None, 'excel_aug_editable_columns': [], 
                 'selected_sheet': None, 'num_new_rows': 100, 
                 'file_uploader_key': excel_state.get('file_uploader_key', 0) + 1, 
                 'processed_filename': None
             }
             st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}
             st.rerun()

    if uploaded_file_aug:
        is_new_file = uploaded_file_aug.name != excel_state.get('processed_filename')
        needs_processing_due_to_empty_schema = not excel_state.get('excel_aug_editable_columns')

        if is_new_file or needs_processing_due_to_empty_schema:
            try:
                xls = pd.ExcelFile(uploaded_file_aug); sheet_names = xls.sheet_names
                selected_sheet_for_processing = None
                if not sheet_names: st.warning("No sheets found.")
                elif len(sheet_names) == 1:
                    selected_sheet_for_processing = sheet_names[0]; st.caption(f"Using sheet: '{selected_sheet_for_processing}'")
                else:
                    current_selected = excel_state.get('selected_sheet')
                    idx = sheet_names.index(current_selected) if current_selected in sheet_names else None
                    selected_sheet_for_processing = st.selectbox("Select Sheet to Augment", sheet_names, index=idx, key="sheet_selector_aug", placeholder="Choose...")
                
                if selected_sheet_for_processing and (selected_sheet_for_processing != excel_state.get('selected_sheet') or is_new_file or needs_processing_due_to_empty_schema):
                     with st.spinner(f"Processing sheet '{selected_sheet_for_processing}'..."):
                        df_uploaded = pd.read_excel(uploaded_file_aug, sheet_name=selected_sheet_for_processing)
                        excel_state['base_df_preview'] = df_uploaded.head()
                        excel_state['excel_aug_editable_columns'] = infer_schema_and_convert_for_editing(df_uploaded) 
                        excel_state['selected_sheet'] = selected_sheet_for_processing
                        excel_state['processed_filename'] = uploaded_file_aug.name
                        st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}; st.rerun()
            except Exception as e: 
                st.error(f"Error processing Excel file: {e}")
                excel_state.update({'processed_filename': None, 'excel_aug_editable_columns': [], 'base_df_preview': None})

    if excel_state.get('base_df_preview') is not None:
         st.subheader(f"Preview of '{excel_state.get('selected_sheet', 'N/A')}' (First 5 Rows)")
         st.dataframe(excel_state['base_df_preview'])
    
    st.divider()

    if excel_state.get('excel_aug_editable_columns'):
        st.subheader("Review / Edit / Add Columns for Generation")
        column_editor_ui(
            columns_state_list=excel_state['excel_aug_editable_columns'],
            item_type_options=COLUMN_DATA_TYPES_UI, 
            render_item_params_func=render_tabular_excel_params_ui, 
            key_prefix="excel_aug"
        )
        st.divider()
        add_new_column_ui(
            columns_state_list=excel_state['excel_aug_editable_columns'],
            item_type_options=COLUMN_DATA_TYPES_UI,
            default_item_type="String (Faker)",
            key_prefix="excel_aug"
        )
        st.divider()
        excel_state['num_new_rows'] = st.number_input("Number of NEW Rows to Generate", min_value=1, max_value=100000, value=excel_state.get('num_new_rows', 100), key="excel_num_rows_input")
    elif not uploaded_file_aug : 
        st.info("Upload an Excel file to begin schema inference and augmentation.")
    elif uploaded_file_aug and not excel_state.get('selected_sheet') and len(pd.ExcelFile(uploaded_file_aug).sheet_names) > 1:
        st.info("Please select a sheet from the uploaded Excel file to proceed.")


def generate_excel_data_action():
    results = {'data': None, 'message': None, 'error': None}
    try:
        column_config_list = st.session_state.excel_mode.get('excel_aug_editable_columns', [])
        row_count = st.session_state.excel_mode.get('num_new_rows', 100)
        if not column_config_list: raise ValueError("No editable columns defined.")
        all_rows_data = [{col['name']: generate_tabular_value(col) for col in column_config_list if 'name' in col} for _ in range(row_count)]
        df = pd.DataFrame(all_rows_data)
        for col_def in column_config_list: 
             col_name = col_def.get('name'); target_ui_type = col_def.get('data_type') 
             if col_name and target_ui_type and col_name in df.columns:
                  try:
                      current_dtype = df[col_name].dtype
                      # Standard types
                      if target_ui_type == "Integer" and not pd.api.types.is_integer_dtype(current_dtype): df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
                      elif target_ui_type == "Float" and not pd.api.types.is_float_dtype(current_dtype): df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Float64')
                      elif target_ui_type == "Boolean" and not pd.api.types.is_bool_dtype(current_dtype):
                           if pd.api.types.is_string_dtype(current_dtype): df[col_name] = df[col_name].str.lower().map({'true': True, '1': True, 'yes': True, 'false': False, '0': False, 'no': False})
                           df[col_name] = df[col_name].astype('boolean')
                      elif target_ui_type == "Categorical" and not pd.api.types.is_categorical_dtype(current_dtype): df[col_name] = df[col_name].astype('category')
                      # Date/DateTime/Time handling - generated as objects/strings, then convert
                      elif target_ui_type == "Date": 
                          df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date
                      elif target_ui_type == "DateTime (dd-mm-yyyy HH:MM:SS)":
                          df[col_name] = pd.to_datetime(df[col_name], errors='coerce') # Keep as datetime object
                      elif target_ui_type == "Time (HH:MM:SS)":
                          # pd.to_datetime can convert time strings, then extract time. Or keep as string if format is strict.
                          # For simplicity, if it's already a string from faker, it might be fine.
                          # If it was a datetime.time object, convert to string for consistency in DataFrame unless specifically needed as time objects.
                          if df[col_name].apply(lambda x: isinstance(x, pd.Timestamp) or isinstance(x, pd.NaT.__class__)).all(): # if it became timestamp
                                df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.strftime('%H:%M:%S')
                          # else it's likely already a string in the correct format or datetime.time object
                  except Exception as e_final_conv: st.warning(f"FinalTypeConvWarn '{col_name}' to '{target_ui_type}': {e_final_conv}")
        results['data'] = df; results['message'] = f"Generated {len(df)} new rows (Excel Augmentation)."
    except Exception as e: results['error'] = f"Excel Augmentation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False


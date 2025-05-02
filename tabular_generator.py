# tabular_generator.py
import streamlit as st
import pandas as pd
from datetime import date

# Import constants and shared utilities
from constants import DEPENDENCY_CONDITIONS
from utils import (
    column_editor_ui, add_new_column_ui,
    generate_tabular_value
)

def render_tabular_page():
    """Renders the UI elements specific to the Tabular Data mode."""

    # --- Explicitly check the current use case from session state ---
    current_use_case = st.session_state.config.get('use_case')
    is_instruct_mode = (current_use_case == "Instruct Dataset")
    # st.write(f"[Debug] Current Use Case: {current_use_case}") # Optional: for debugging

    if is_instruct_mode:
        # --- UI for Instruct Dataset Mode ---
        st.info("1. Define 'columns' below (like variables).\n2. Configure each column's generation (e.g., set Type to 'String (Faker)' and choose 'sentence'/'paragraph' in Parameters).\n3. Define the output format using `{column_name}` placeholders in the template.")
        st.subheader("Define Instruction Format Template")
        template_help = "Use curly braces `{column_name}` to insert generated column values. Ensure column names match those defined below."
        # Ensure the key exists before accessing, provide default from state_manager if needed
        default_template = st.session_state.tabular.get('instruct_template', "Instruction: {instruction_col}\nOutput: {output_col}")
        st.session_state.tabular['instruct_template'] = st.text_area(
            "Template String:",
            value=default_template,
            height=150,
            key="instruct_template_input",
            help=template_help
        )
        st.caption(template_help)
        st.divider()
        st.subheader("Define Columns (Template Variables)")
        # --- End Instruct Specific UI ---

    else:
        # --- UI for Standard Tabular Mode ---
        st.info("Define columns and (optionally) relationships manually for rule-based generation.")
        st.subheader("Define Columns")
        # --- End Standard Specific UI ---


    # --- Shared UI for Column Definitions (Both Modes) ---
    if st.button("Clear Tabular Config", key="clear_tab_config"):
         # Reset state including the template
         st.session_state.tabular = {'columns': [], 'relationships': [], 'instruct_template': "Instruction: {instruction_col}\nOutput: {output_col}"}
         st.rerun()

    # Column Editor UI (Shared)
    column_editor_ui(st.session_state.tabular['columns'], key_prefix="tab")
    st.divider()
    # Add New Column UI (Shared)
    add_new_column_ui(st.session_state.tabular['columns'], key_prefix="tab")
    st.divider()
    # --- End Shared Column UI ---


    # --- Define Dependencies (ONLY if NOT Instruct Mode) ---
    if not is_instruct_mode:
        st.subheader("Define Dependencies (Standard Tabular Mode Only)")
        column_names = [c.get('name') for c in st.session_state.tabular.get('columns', []) if c.get('name')]
        if not column_names: st.info("Add columns before defining dependencies.")
        else:
            # --- Dependency UI (Same as before) ---
            with st.expander("Add New Dependency"):
                 rel_cols = st.columns(3)
                 with rel_cols[0]: dep_cond_col = st.selectbox("IF Column:", column_names, key="tab_dep_cond_col", index=None, placeholder="Select...")
                 with rel_cols[1]: dep_condition = st.selectbox("Condition:", DEPENDENCY_CONDITIONS, key="tab_dep_condition", index=None, placeholder="Select...")
                 with rel_cols[2]: dep_cond_val_str = st.text_input("Condition Value:", key="tab_dep_cond_val", help="For 'in list', use comma-sep")
                 set_cols = st.columns(2)
                 with set_cols[0]: dep_dependent_col = st.selectbox("THEN Set Column:", column_names, key="tab_dep_dep_col", index=None, placeholder="Select...")
                 with set_cols[1]: dep_dependent_val_str = st.text_input("To Value:", key="tab_dep_dep_val")
                 if st.button("➕ Add Dependency", key="tab_add_dep_btn"):
                      if dep_cond_col and dep_condition and dep_dependent_col and dep_dependent_val_str is not None:
                           if dep_cond_col == dep_dependent_col: st.error("Condition/Dependent cols must be different.")
                           else:
                               new_rel = {'condition_col': dep_cond_col, 'condition': dep_condition, 'condition_value_str': dep_cond_val_str, 'dependent_col': dep_dependent_col, 'dependent_value_str': dep_dependent_val_str}
                               st.session_state.tabular.setdefault('relationships', []).append(new_rel); st.success("Dependency added."); st.rerun()
                      else: st.warning("Fill all dependency fields.")
            st.subheader("Defined Dependencies")
            if not st.session_state.tabular.get('relationships'): st.caption("No dependencies defined.")
            else:
                 rels_to_remove = []
                 for i in reversed(range(len(st.session_state.tabular['relationships']))):
                     rel = st.session_state.tabular['relationships'][i]
                     with st.container(border=True):
                         st.write(f"**Rule {i+1}:** IF `{rel.get('condition_col')}` {rel.get('condition')} `{rel.get('condition_value_str')}` THEN SET `{rel.get('dependent_col')}` TO `{rel.get('dependent_value_str')}`")
                         if st.button("❌ Remove", key=f"tab_rel_{i}_remove"): rels_to_remove.append(i)
                 if rels_to_remove:
                     for idx in rels_to_remove: del st.session_state.tabular['relationships'][idx]; st.rerun()
            # --- End Dependency UI ---
    # --- End Conditional Dependency Section ---


# --- Generation Action Function (No change needed here, already handles both modes) ---
def generate_tabular_data_action():
    """Handles data generation for Tabular mode, including Instruct Dataset variation."""
    # ... (Function logic remains exactly the same as the previous correct version) ...
    results = {'data': None, 'message': None, 'error': None}
    try:
        is_instruct_mode = (st.session_state.config.get('use_case') == "Instruct Dataset")
        column_config_list = st.session_state.tabular.get('columns', [])
        row_count = st.session_state.config.get('num_rows', 100)
        if not column_config_list: raise ValueError("No columns defined.")
        if is_instruct_mode:
            template = st.session_state.tabular.get('instruct_template', "")
            if not template: raise ValueError("Instruct template empty.")
            generated_instructions = []
            for i_row in range(row_count):
                placeholder_values = {}
                for col_def in column_config_list:
                    col_name = col_def.get('name')
                    if col_name: placeholder_values[col_name] = generate_tabular_value(col_def)
                try: formatted_string = template.format(**placeholder_values); generated_instructions.append(formatted_string)
                except KeyError as e: results['error'] = f"Template error: Placeholder {e} not found in columns."; st.session_state.results.update(results); st.session_state.results['is_generating'] = False; return
                except Exception as e_fmt: results['error'] = f"Template formatting error: {e_fmt}"; st.session_state.results.update(results); st.session_state.results['is_generating'] = False; return
            results['data'] = generated_instructions; results['message'] = f"Generated {len(generated_instructions)} instructions."
        else: # Standard Tabular with Dependencies
            relationships_to_apply = st.session_state.tabular.get('relationships', [])
            all_rows_data = []; col_type_lookup = {col['name']: col['data_type'] for col in column_config_list if 'name' in col and 'data_type' in col}
            for i_row in range(row_count):
                row = {col['name']: generate_tabular_value(col) for col in column_config_list if 'name' in col}
                cols_to_update = {} # Dependency Logic (same as before)
                for rel in relationships_to_apply:
                     try: # ... (Innermost try-except for relationship eval remains same) ...
                         cond_col = rel['condition_col']; dep_col = rel['dependent_col']; cond_val_str = rel['condition_value_str']; dep_val_str = rel['dependent_value_str']; condition = rel['condition']
                         if cond_col not in row or row[cond_col] is None: continue
                         actual_value = row[cond_col]; condition_met = False; compare_value = None
                         try: # ... (Type coercion logic remains same) ...
                             target_type = type(actual_value); is_list_condition = condition in ["in list", "not in list"]
                             if is_list_condition:
                                  list_vals_str = [v.strip() for v in cond_val_str.split(',') if v.strip()]; compare_value = []
                                  for item_str in list_vals_str:
                                       try: compare_value.append(target_type(item_str))
                                       except (ValueError, TypeError): compare_value.append(item_str)
                             elif target_type is date and isinstance(cond_val_str, str): compare_value = date.fromisoformat(cond_val_str)
                             elif target_type is bool and isinstance(cond_val_str, str): compare_value = cond_val_str.lower() in ['true', '1', 'yes']
                             elif target_type not in [list, dict, set, type(None)] and cond_val_str is not None and not isinstance(cond_val_str, target_type): compare_value = target_type(cond_val_str)
                             else: compare_value = cond_val_str
                         except (ValueError, TypeError) as e_conv: st.warning(f"RelConv{i_row+1}: {e_conv}", icon="⚠️"); compare_value = cond_val_str
                         try: # ... (Comparison logic remains same) ...
                             if condition == "equals": condition_met = (actual_value == compare_value)
                             elif condition == "not equals": condition_met = (actual_value != compare_value)
                             elif condition == "greater than": condition_met = (actual_value > compare_value)
                             elif condition == "less than": condition_met = (actual_value < compare_value)
                             elif condition == "in list" and isinstance(compare_value, list): condition_met = (actual_value in compare_value)
                             elif condition == "not in list" and isinstance(compare_value, list): condition_met = (actual_value not in compare_value)
                         except TypeError: condition_met = False
                     except Exception as e_eval: st.warning(f"RelEval{i_row+1}: {e_eval}", icon="⚠️"); condition_met = False
                     if condition_met: cols_to_update[dep_col] = dep_val_str
                for col_to_set, val_str_to_set in cols_to_update.items(): # Apply updates logic (same as before)
                     try: # ... (Casting logic remains same) ...
                         target_dep_ui_type = col_type_lookup.get(col_to_set, 'String (Faker)'); final_dep_val = val_str_to_set
                         if target_dep_ui_type == "Integer": final_dep_val = int(val_str_to_set)
                         elif target_dep_ui_type == "Float": final_dep_val = float(val_str_to_set)
                         elif target_dep_ui_type == "Boolean": final_dep_val = val_str_to_set.lower() in ['true', '1', 'yes']
                         elif target_dep_ui_type == "Date": final_dep_val = date.fromisoformat(val_str_to_set)
                         row[col_to_set] = final_dep_val
                     except (ValueError, TypeError) as e_dep_conv: st.warning(f"DepSetConv{i_row+1}: {e_dep_conv}", icon="⚠️"); row[col_to_set] = val_str_to_set
                all_rows_data.append(row)
            df = pd.DataFrame(all_rows_data) # Final DF creation & cleanup (same as before)
            for col_def in column_config_list: # ... (Type coercion loop remains same) ...
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
            results['data'] = df; results['message'] = f"Generated {len(df)} rows (Tabular)."
    except Exception as e: results['error'] = f"Tabular generation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
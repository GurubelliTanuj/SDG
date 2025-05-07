# tabular_generator.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, time # Added datetime, time

from constants import DEPENDENCY_CONDITIONS, COLUMN_DATA_TYPES_UI
from utils import (
    column_editor_ui, add_new_column_ui,
    generate_tabular_value,
    render_tabular_excel_params_ui
)

def render_tabular_page():
    tabular_state = st.session_state.tabular
    current_use_case = st.session_state.config.get('use_case')
    is_instruct_mode = (current_use_case == "Instruct Dataset")

    st.info("Define columns and (optionally) relationships or an instruction template. Click 'Generate Data' when ready.")

    if tabular_state.get('columns') or tabular_state.get('relationships') or \
       (is_instruct_mode and tabular_state.get('instruct_template') != "Instruction: {instruction_col}\nOutput: {output_col}"):
        if st.button("Clear All Tabular Configuration", key="clear_tabular_all_config"):
            st.session_state.tabular = {
                'columns': [],
                'relationships': [],
                'instruct_template': "Instruction: {instruction_col}\nOutput: {output_col}",
                'base_df_preview': None, 'file_uploader_key': tabular_state.get('file_uploader_key',0),
                'processed_filename': None, 'selected_sheet': None, 'is_csv_upload': False
            }
            st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}
            st.rerun()

    st.divider()
    st.subheader("1. Define Columns for Generation")
    column_editor_ui(
        columns_state_list=tabular_state['columns'],
        item_type_options=COLUMN_DATA_TYPES_UI,
        render_item_params_func=render_tabular_excel_params_ui,
        key_prefix="tab_col_edit"
    )
    st.divider()
    add_new_column_ui(
        columns_state_list=tabular_state['columns'],
        item_type_options=COLUMN_DATA_TYPES_UI,
        default_item_type="String (Faker)",
        item_name_label="Column Name*",
        key_prefix="tab_col_add"
    )
    st.divider()

    section_number = 2
    if is_instruct_mode:
        st.subheader(f"{section_number}. Define Instruction Format Template")
        help_txt = "Use `{col_name}` for placeholders. Match defined column names."
        def_tmpl = tabular_state.get('instruct_template', "Instruction: {instruction_col}\nOutput: {output_col}")
        tabular_state['instruct_template'] = st.text_area("Template:", value=def_tmpl, height=100, key="instr_tmpl_in", help=help_txt)
        st.caption(help_txt)
    else:
        st.subheader(f"{section_number}. Define Dependencies (Optional)")
        col_names = [c.get('name') for c in tabular_state.get('columns', []) if c.get('name')]
        if not col_names: st.info("Add columns before defining dependencies.")
        else:
            with st.expander("Add New Dependency"):
                 c = st.columns(3); s = st.columns(2)
                 dep_cond_col = c[0].selectbox("IF Column:", col_names, key="tab_dep_cnd_col",placeholder="Select...", index=None)
                 dep_cond = c[1].selectbox("Condition:", DEPENDENCY_CONDITIONS, key="tab_dep_cnd",placeholder="Select...", index=None)
                 dep_cval_str = c[2].text_input("Cond Value:", key="tab_dep_cval", help="Comma-sep for lists")
                 dep_dep_col = s[0].selectbox("THEN Set Column:", col_names, key="tab_dep_depcol",placeholder="Select...", index=None)
                 dep_dval_str = s[1].text_input("To Value:", key="tab_dep_dval")
                 if st.button("➕ Add Dependency", key="tab_add_dep"):
                      if all([dep_cond_col, dep_cond, dep_dep_col, dep_dval_str is not None]):
                           if dep_cond_col == dep_dep_col: st.error("Cond/Dep cols must differ.")
                           else:
                               tabular_state.setdefault('relationships', []).append(
                                   {'condition_col':dep_cond_col,'condition':dep_cond,'condition_value_str':dep_cval_str,
                                    'dependent_col':dep_dep_col,'dependent_value_str':dep_dval_str})
                               st.success("Dep added."); st.rerun()
                      else: st.warning("Fill all dependency fields.")
            if tabular_state.get('relationships'):
                st.markdown("**Defined Dependencies**"); to_remove = []
                for i, rel in reversed(list(enumerate(tabular_state['relationships']))):
                    with st.container(border=True):
                        st.write(f"**R{i+1}:** IF `{rel.get('condition_col')}` {rel.get('condition')} `{rel.get('condition_value_str')}` THEN SET `{rel.get('dependent_col')}` TO `{rel.get('dependent_value_str')}`")
                        if st.button("❌ Remove", key=f"tab_rel_{i}_rem"): to_remove.append(i)
                if to_remove:
                    for idx in to_remove: del tabular_state['relationships'][idx]
                    st.rerun()
            else: st.caption("No dependencies defined.")

def generate_tabular_data_action():
    results = {'data': None, 'message': None, 'error': None}
    try:
        is_instruct = (st.session_state.config.get('use_case') == "Instruct Dataset")
        col_configs = st.session_state.tabular.get('columns', [])
        num_rows = st.session_state.config.get('num_rows', 100)
        if not col_configs: raise ValueError("No columns defined.")

        if is_instruct:
            tmpl = st.session_state.tabular.get('instruct_template', "")
            if not tmpl: raise ValueError("Instruct template empty.")
            out_instr = []
            for _ in range(num_rows):
                placeholders = {col.get('name'): generate_tabular_value(col) for col in col_configs if col.get('name')}
                try: out_instr.append(tmpl.format(**placeholders))
                except KeyError as e: results['error'] = f"Template Error: Placeholder {e} not found in defined columns."; break
                except Exception as e_fmt: results['error'] = f"Template Format Error: {e_fmt}"; break
            if 'error' not in results or not results['error']:
                results.update({'data': out_instr, 'message': f"Generated {len(out_instr)} instructions."})
        else:
            rels = st.session_state.tabular.get('relationships', [])
            all_rows = []; col_type_map = {c['name']:c['data_type'] for c in col_configs if 'name' in c and 'data_type' in c}
            for _ in range(num_rows):
                row = {col['name']: generate_tabular_value(col) for col in col_configs if 'name' in col}
                updates = {}
                for r_def in rels:
                    try:
                        cc,dc,cv_s,dv_s,cond = r_def['condition_col'],r_def['dependent_col'],r_def['condition_value_str'],r_def['dependent_value_str'],r_def['condition']
                        if cc not in row or row[cc] is None: continue
                        act_v, met, cmp_v = row[cc], False, None
                        try:
                            tgt_t = type(act_v); is_list_c = cond in ["in list","not in list"]
                            if is_list_c:
                                list_vals_str = [v.strip() for v in cv_s.split(',') if v.strip()]
                                cmp_v = []
                                for item_str in list_vals_str:
                                    try: cmp_v.append(tgt_t(item_str))
                                    except (ValueError, TypeError): cmp_v.append(item_str)
                            elif tgt_t is date and isinstance(cv_s,str): cmp_v=date.fromisoformat(cv_s)
                            elif tgt_t is bool and isinstance(cv_s,str): cmp_v=cv_s.lower() in ['true','1','yes']
                            elif isinstance(act_v, datetime) and isinstance(cv_s, str): cmp_v = datetime.fromisoformat(cv_s)
                            elif isinstance(act_v, time) and isinstance(cv_s, str): cmp_v = time.fromisoformat(cv_s) # Comparing HH:MM with HH:MM[:SS]
                            elif tgt_t not in [list,dict,set,type(None)] and cv_s is not None: cmp_v=tgt_t(cv_s)
                            else: cmp_v=cv_s
                        except: cmp_v=cv_s
                        try:
                            if cond=="equals": met=(act_v==cmp_v)
                            elif cond=="not equals": met=(act_v!=cmp_v)
                            elif cond=="greater than": met=(act_v > cmp_v)
                            elif cond=="less than": met=(act_v < cmp_v)
                            elif cond=="in list" and isinstance(cmp_v,list): met=(act_v in cmp_v)
                            elif cond=="not in list" and isinstance(cmp_v,list): met=(act_v not in cmp_v)
                        except TypeError: met=False
                    except: met=False
                    if met: updates[dc]=dv_s
                for col_set, val_s_set in updates.items():
                    try:
                        dep_ui_t = col_type_map.get(col_set,'String (Faker)'); final_dv = val_s_set
                        if dep_ui_t=="Integer": final_dv=int(val_s_set)
                        elif dep_ui_t=="Float": final_dv=float(val_s_set)
                        elif dep_ui_t=="Boolean": final_dv=val_s_set.lower() in ['true','1','yes']
                        elif dep_ui_t=="Date": final_dv=date.fromisoformat(val_s_set)
                        elif dep_ui_t=="DateTime (dd-mm-yyyy HH:MM:SS)": final_dv=datetime.strptime(val_s_set, "%d-%m-%Y %H:%M:%S")
                        elif dep_ui_t=="Time (HH:MM)": final_dv=datetime.strptime(val_s_set, "%H:%M").time()
                        row[col_set]=final_dv
                    except: row[col_set]=val_s_set
                all_rows.append(row)
            df = pd.DataFrame(all_rows)
            for col_def in col_configs: # Final type coercion loop
                 col_n, tgt_ui_t = col_def.get('name'), col_def.get('data_type')
                 if col_n and tgt_ui_t and col_n in df.columns:
                      try:
                          cur_dt = df[col_n].dtype
                          if tgt_ui_t=="Integer" and not pd.api.types.is_integer_dtype(cur_dt): df[col_n]=pd.to_numeric(df[col_n],errors='coerce').astype('Int64')
                          elif tgt_ui_t=="Float" and not pd.api.types.is_float_dtype(cur_dt): df[col_n]=pd.to_numeric(df[col_n],errors='coerce').astype('Float64')
                          elif tgt_ui_t=="Date": df[col_n]=pd.to_datetime(df[col_n],errors='coerce').dt.date
                          elif tgt_ui_t=="DateTime (dd-mm-yyyy HH:MM:SS)":
                                df[col_n]=pd.to_datetime(df[col_n], format="%d-%m-%Y %H:%M:%S", errors='coerce')
                          elif tgt_ui_t=="Time (HH:MM)":
                                # Values are HH:MM strings, convert to datetime.time objects for the DataFrame
                                df[col_n] = pd.to_datetime(df[col_n], format="%H:%M", errors='coerce').dt.time
                          elif tgt_ui_t=="Boolean" and not pd.api.types.is_bool_dtype(cur_dt):
                               if pd.api.types.is_string_dtype(cur_dt): df[col_n]=df[col_n].str.lower().map({'true':True,'1':True,'false':False,'0':False})
                               df[col_n]=df[col_n].astype('boolean')
                          elif tgt_ui_t=="Categorical" and not pd.api.types.is_categorical_dtype(cur_dt): df[col_n]=df[col_n].astype('category')
                      except Exception as e_fconv: st.warning(f"FinalConvWarn '{col_n}' to '{tgt_ui_t}': {e_fconv}")
            results.update({'data':df, 'message':f"Generated {len(df)} Tabular rows."})
    except Exception as e: results['error'] = f"Tabular generation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import io
import zipfile
import json 

from state_manager import initialize_state
from constants import ( 
    DATA_TYPES, USE_CASES, PRIVACY_METHODS,
    TABULAR_METHODS, EXCEL_AUG_METHODS, NER_AUG_METHODS, 
    IMAGE_METHODS, TEXT_METHODS, GRAPH_METHODS
)
from utils import draw_graph, image_to_bytes, nx

from tabular_generator import render_tabular_page, generate_tabular_data_action
from excel_generator import render_excel_page, generate_excel_data_action
from ner_generator import render_ner_page, generate_ner_data_action 
from image_generator import render_image_page, generate_image_data_action
from text_generator import render_text_page, generate_text_data_action
from graph_generator import render_graph_page, generate_graph_data_action

initialize_state()

st.set_page_config(layout="wide", page_title="Synthetic Data Generator")
st.title("Synthetic Data Generator")

st.sidebar.header("1. Define Target Data")
selected_data_type = st.sidebar.selectbox( "Select Data Type", DATA_TYPES, index=DATA_TYPES.index(st.session_state.config.get('data_type', DATA_TYPES[0])), key="data_type_selector" )
if selected_data_type != st.session_state.config.get('data_type'):
    st.session_state.config['data_type'] = selected_data_type
    st.session_state.results = {'data': None, 'message': None, 'error': None, 'is_generating': False}
    st.rerun()

st.session_state.config['use_case'] = st.sidebar.selectbox( "Intended Use Case", USE_CASES, index=USE_CASES.index(st.session_state.config.get('use_case', USE_CASES[0])) )
st.sidebar.header("2. Determine Privacy (Optional)")
st.session_state.config['privacy_level'] = st.sidebar.selectbox( "Privacy Method", PRIVACY_METHODS, index=PRIVACY_METHODS.index(st.session_state.config.get('privacy_level', PRIVACY_METHODS[0])) )
if st.session_state.config['privacy_level'] != "None": st.session_state.config['privacy_epsilon'] = st.sidebar.number_input( "Epsilon (ε)", 0.1, 10.0, st.session_state.config.get('privacy_epsilon', 1.0), 0.1 )

st.sidebar.header("3. Generation Method")
current_data_type = st.session_state.config['data_type']
available_methods = []
if current_data_type == "Tabular": available_methods = TABULAR_METHODS
elif current_data_type == "Excel Augmentation": available_methods = EXCEL_AUG_METHODS
elif current_data_type == "NER Augmentation": available_methods = NER_AUG_METHODS 
elif current_data_type == "Image (Basic Shapes)": available_methods = IMAGE_METHODS
elif current_data_type == "Text (Basic)": available_methods = TEXT_METHODS
elif current_data_type == "Graph (Basic Random)": available_methods = GRAPH_METHODS

current_method = st.session_state.config.get('generation_method')
method_disabled = (current_data_type in ["Excel Augmentation", "NER Augmentation", "Tabular"]) # Tabular also has one method now effectively

if not available_methods: st.session_state.config['generation_method'] = None
elif current_method not in available_methods: st.session_state.config['generation_method'] = available_methods[0]
if st.session_state.config['generation_method'] is None and available_methods: st.session_state.config['generation_method'] = available_methods[0]

st.session_state.config['generation_method'] = st.sidebar.selectbox(
    "Select Method", available_methods,
    index=available_methods.index(st.session_state.config['generation_method']) if st.session_state.config['generation_method'] in available_methods else 0,
    disabled=method_disabled, key="gen_method_selector"
)

st.header(f"Configure: {current_data_type}")
if current_data_type == "Tabular": render_tabular_page()
elif current_data_type == "Excel Augmentation": render_excel_page()
elif current_data_type == "NER Augmentation": render_ner_page() 
elif current_data_type == "Image (Basic Shapes)": render_image_page()
elif current_data_type == "Text (Basic)": render_text_page()
elif current_data_type == "Graph (Basic Random)": render_graph_page()
else: st.warning("Config UI not implemented yet.")

st.divider(); st.header("4. Generate Data")
generation_possible = False; num_items_to_gen = 0
is_instruct_and_tabular = (current_data_type == "Tabular" and st.session_state.config.get('use_case') == "Instruct Dataset")

if current_data_type == "Tabular" and st.session_state.tabular.get('columns'):
    generation_possible = True; num_items_to_gen = st.session_state.config.get('num_rows', 100)
elif current_data_type == "Excel Augmentation" and st.session_state.excel_mode.get('excel_aug_editable_columns'):
    generation_possible = True; num_items_to_gen = st.session_state.excel_mode.get('num_new_rows', 100)
elif current_data_type == "NER Augmentation" and st.session_state.ner_mode.get('editable_entity_rules') and (st.session_state.ner_mode.get('original_text_samples') or any(rule.get('action') == "Inject New Entity into Template String" for rule in st.session_state.ner_mode.get('editable_entity_rules', []))): # Allow NER gen if injection rules exist even without base text
    generation_possible = True; num_items_to_gen = st.session_state.ner_mode.get('num_augmented_samples', 10) 
elif current_data_type == "Image (Basic Shapes)":
    generation_possible = True; num_items_to_gen = st.session_state.image.get('count', 10)
elif current_data_type == "Text (Basic)":
    generation_possible = True; num_items_to_gen = st.session_state.text.get('count', 10)
elif current_data_type == "Graph (Basic Random)":
    if nx: generation_possible = True; num_items_to_gen = st.session_state.graph.get('num_nodes', 10)
    else: st.error("Cannot generate Graph: NetworkX missing.", icon="⚠️")

if generation_possible:
    button_label = f"🚀 Generate {num_items_to_gen} items" if num_items_to_gen > 0 else "🚀 Generate Data"
    if st.button(button_label, key="generate_data", type="primary", disabled=st.session_state.results['is_generating']):
        st.session_state.results.update({'is_generating': True, 'data': None, 'message': None, 'error': None})
        st.rerun() 
elif current_data_type in ["Tabular", "Excel Augmentation", "NER Augmentation"]:
     st.warning(f"Cannot generate: Please define/upload configuration for {current_data_type}.")

if st.session_state.results['is_generating']:
    data_type_to_generate = st.session_state.config.get('data_type')
    row_count_display = 0
    if data_type_to_generate == "Tabular": row_count_display = st.session_state.config.get('num_rows', 100)
    elif data_type_to_generate == "Excel Augmentation": row_count_display = st.session_state.excel_mode.get('num_new_rows', 100)
    elif data_type_to_generate == "NER Augmentation": row_count_display = st.session_state.ner_mode.get('num_augmented_samples', 10) 
    elif data_type_to_generate == "Image (Basic Shapes)": row_count_display = st.session_state.image.get('count', 10)
    elif data_type_to_generate == "Text (Basic)": row_count_display = st.session_state.text.get('count', 10)
    
    spinner_label = f"Generating {row_count_display} items..." if row_count_display > 0 else "Generating data..."
    if data_type_to_generate == "Graph (Basic Random)": spinner_label = "Generating Graph..."

    with st.spinner(spinner_label):
        if data_type_to_generate == "Tabular": generate_tabular_data_action()
        elif data_type_to_generate == "Excel Augmentation": generate_excel_data_action()
        elif data_type_to_generate == "NER Augmentation": generate_ner_data_action() 
        elif data_type_to_generate == "Image (Basic Shapes)": generate_image_data_action()
        elif data_type_to_generate == "Text (Basic)": generate_text_data_action()
        elif data_type_to_generate == "Graph (Basic Random)": generate_graph_data_action()
        else:
            st.session_state.results.update({'error': f"Gen action not found for: {data_type_to_generate}", 'is_generating': False})
    st.rerun() 

if st.session_state.results['data'] is not None or st.session_state.results['message'] or st.session_state.results['error']:
    st.divider(); st.header("5. Results")
    if st.session_state.results['error']: st.error(st.session_state.results['error'], icon="🚨")
    elif st.session_state.results['message']: st.success(st.session_state.results['message'], icon="✅")

    results_data = st.session_state.results.get('data')
    if results_data is not None:
        current_data_type = st.session_state.config.get('data_type')
        download_format = None
        if isinstance(results_data, pd.DataFrame) and current_data_type in ["Tabular", "Excel Augmentation"]:
            st.dataframe(results_data); download_format = st.radio("Download Format:", ("CSV", "JSON"), key="df_dl_fmt", horizontal=True)
            try:
                data_bytes, mime, ext = (None,)*3; f_name = "tabular" if current_data_type == "Tabular" else "excel_augmented"
                df_copy = results_data.copy()

                # Convert special types to string for CSV/JSON that might cause issues
                for col in df_copy.columns:
                    # Check if column contains datetime.time objects (which are 'object' dtype in pandas)
                    if df_copy[col].dtype == 'object' and df_copy[col].apply(lambda x: isinstance(x, time)).any():
                        df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%H:%M') if isinstance(x, time) and pd.notnull(x) else x)
                    # Check if column contains datetime.date objects (also 'object' dtype)
                    elif df_copy[col].dtype == 'object' and df_copy[col].apply(lambda x: isinstance(x, date) and not isinstance(x, datetime)).any(): # Exclude full datetime
                         df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if isinstance(x, date) and pd.notnull(x) else x)

                if download_format == "CSV":
                    # For CSV, ensure datetime objects are also in a consistent string format if not already handled
                    for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]', 'datetimetz']).columns:
                        df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S') # Or desired format
                    data_bytes, mime, ext = df_copy.to_csv(index=False).encode('utf-8'), "text/csv", "csv"
                elif download_format == "JSON":
                    # Convert actual pandas datetime64 objects to ISO format string for JSON
                    for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]', 'datetimetz']).columns:
                        df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
                    # Python date and time objects were already converted to strings above for general compatibility
                    
                    json_string = df_copy.to_json(orient="records", indent=4) # date_format="iso" is less critical now
                    data_bytes, mime, ext = json_string.encode('utf-8'), "application/json", "json"

                if data_bytes: st.download_button(f"Download ({download_format})", data_bytes, f"synth_{f_name}_{datetime.now():%Y%m%d_%H%M%S}.{ext}", mime, key=f"dl_df_{ext}")
            except Exception as e: st.error(f"Error preparing {download_format} download: {e}")

        elif isinstance(results_data, list) and results_data and isinstance(results_data[0], str) and current_data_type in ["Text (Basic)", "Tabular", "NER Augmentation"]: 
             is_instruct = (current_data_type == "Tabular" and st.session_state.config.get('use_case') == "Instruct Dataset")
             is_ner = (current_data_type == "NER Augmentation")
             preview_title = "Instruction Samples (First 10)" if is_instruct else ("Augmented Text Samples (First 10)" if is_ner else "Text Samples (First 10)")
             st.subheader(preview_title)
             for i, sample in enumerate(results_data[:10]): st.code(sample, language="text" if is_ner else None, line_numbers=False) 
             
             download_format = st.radio("Download Format:", ("TXT", "JSON"), key="txt_dl_fmt", horizontal=True)
             try:
                data_bytes, mime, ext = (None,)*3
                f_name = "instruct" if is_instruct else ("ner_augmented" if is_ner else "text")
                if download_format == "TXT": data_bytes, mime, ext = "\n\n".join(results_data).encode('utf-8'), "text/plain", "txt"
                elif download_format == "JSON": data_bytes, mime, ext = json.dumps(results_data, indent=4).encode('utf-8'), "application/json", "json"
                if data_bytes: st.download_button(f"Download Samples ({download_format})", data_bytes, f"synth_{f_name}_{datetime.now():%Y%m%d_%H%M%S}.{ext}", mime, key=f"dl_txt_{ext}")
             except Exception as e: st.error(f"Error preparing {download_format} download: {e}")

        elif isinstance(results_data, list) and results_data and isinstance(results_data[0], dict) and 'image' in results_data[0] and current_data_type == "Image (Basic Shapes)":
            st.subheader("Preview (First 10 Images)"); cols = st.columns(5)
            for i, img_data in enumerate(results_data[:10]):
                with cols[i % 5]: st.image(img_data.get('image'), caption=img_data.get('filename', f'img_{i}.png'), width=100)
            try:
                zip_buf = io.BytesIO(); count = 0
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, d in enumerate(results_data):
                        b = image_to_bytes(d.get('image')); fname = d.get('filename', f'img_{i}.png')
                        if b: zf.writestr(fname, b); count +=1
                if count > 0: st.download_button(f"Download Images ({count}) (ZIP)", zip_buf.getvalue(), f"synth_imgs_{datetime.now():%Y%m%d_%H%M%S}.zip", "application/zip", key="dl_img_zip")
            except Exception as e: st.error(f"Error creating image ZIP: {e}")

        elif nx and isinstance(results_data, nx.Graph) and current_data_type == "Graph (Basic Random)":
            st.subheader("Graph Info"); st.text(f"Nodes: {results_data.number_of_nodes()}, Edges: {results_data.number_of_edges()}")
            st.subheader("Visualization"); img_buf = draw_graph(results_data)
            if img_buf:
                st.image(img_buf); st.download_button("DL Graph Image (PNG)", img_buf.getvalue(), f"synth_graph_{datetime.now():%Y%m%d_%H%M%S}.png", "image/png", key="dl_g_png")
            try:
                csv_g = nx.to_pandas_edgelist(results_data).to_csv(index=False).encode('utf-8')
                st.download_button("DL Edge List (CSV)", csv_g, f"synth_graph_edges_{datetime.now():%Y%m%d_%H%M%S}.csv", "text/csv", key="dl_g_csv")
            except Exception as e: st.error(f"Error preparing graph edge list CSV: {e}")
        else:
            if results_data is not None: st.warning("Unrecognized result format."); st.write(results_data)
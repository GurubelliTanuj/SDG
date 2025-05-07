import streamlit as st
import pandas as pd 
import json 
import re 

from utils import (
    column_editor_ui, add_new_column_ui,
    read_text_from_file, fake 
)
from constants import NER_ENTITY_ACTIONS, COMMON_FAKER_PROVIDERS_FOR_NER

def render_ner_params_ui(item_def, unique_key_prefix):
    action_type = item_def.get('action') 
    params = item_def.setdefault('params', {})
    params['entity_label_pattern'] = st.text_input( "Entity Label/Regex Pattern to Match", value=params.get('entity_label_pattern', "PERSON|[Pp]eople"), key=f"{unique_key_prefix}_p_label_pattern", help="Regex. E.g., `PERSON` or `(LOC|LOCATION)` or `\b[A-Z]{3,}\b`.")
    if action_type == "Replace Matched Text with Faker":
        current_faker = params.get('faker_provider', 'name')
        faker_idx = COMMON_FAKER_PROVIDERS_FOR_NER.index(current_faker) if current_faker in COMMON_FAKER_PROVIDERS_FOR_NER else 0
        params['faker_provider'] = st.selectbox("Faker Provider for Replacement", COMMON_FAKER_PROVIDERS_FOR_NER, index=faker_idx, key=f"{unique_key_prefix}_p_faker_provider")
    elif action_type == "Inject New Entity into Template String":
        params['injection_template'] = st.text_area("Template for Injection (use `{ENTITY}` placeholder)", value=params.get('injection_template', "A new entity, {ENTITY}, was mentioned."), key=f"{unique_key_prefix}_p_injection_template", help="`{ENTITY}` replaced by Faker provider below.")
        current_faker_inject = params.get('faker_provider_inject', 'company')
        faker_idx_inject = COMMON_FAKER_PROVIDERS_FOR_NER.index(current_faker_inject) if current_faker_inject in COMMON_FAKER_PROVIDERS_FOR_NER else 0
        params['faker_provider_inject'] = st.selectbox("Faker Provider for {ENTITY}", COMMON_FAKER_PROVIDERS_FOR_NER, index=faker_idx_inject, key=f"{unique_key_prefix}_p_faker_provider_inject")
        params['injection_count'] = st.number_input("Number of Injections per Sample", min_value=1, max_value=10, value=params.get('injection_count', 1), key=f"{unique_key_prefix}_p_injection_count")
    elif action_type == "Anonymize Matched Text":
        params['anonymization_string'] = st.text_input("Replacement String for Anonymization", value=params.get('anonymization_string', "[REDACTED]"), key=f"{unique_key_prefix}_p_anonym_string")
    else: st.caption(f"Parameters not applicable for action: {action_type}")

def render_ner_page():
    st.info("Upload text (TXT, CSV, JSONL) -> Define Entity Augmentation Rules -> Generate Augmented Text Samples.")
    ner_state = st.session_state.ner_mode
    st.subheader("1. Upload Text Data")
    file_uploader_key = f"ner_uploader_{ner_state.get('file_uploader_key', 0)}"
    uploaded_file = st.file_uploader("Upload Text File (.txt, .csv, .jsonl)", type=['txt','csv','jsonl','json'], key=file_uploader_key)
    
    text_data_source_configured = False
    if uploaded_file:
        file_name_lower = uploaded_file.name.lower()
        if file_name_lower.endswith(".csv"):
            ner_state['file_type_hint'] = 'csv'
            try:
                df_peek = pd.read_csv(uploaded_file, nrows=5); uploaded_file.seek(0) 
                ner_state['text_column_name'] = st.selectbox("Select Text Column from CSV", df_peek.columns, index=df_peek.columns.get_loc(ner_state['text_column_name']) if ner_state['text_column_name'] in df_peek.columns else 0, key="ner_csv_text_col")
                text_data_source_configured = True
            except Exception as e: st.error(f"Could not read CSV columns: {e}")
        elif file_name_lower.endswith((".jsonl", ".json")):
            ner_state['file_type_hint'] = 'jsonl'
            ner_state['text_column_name'] = st.text_input("Enter JSON Field Name for Text", value=ner_state.get('text_column_name', 'text'), key="ner_jsonl_text_field", help="Key in JSON object with text string.")
            text_data_source_configured = bool(ner_state['text_column_name'])
        elif file_name_lower.endswith(".txt"):
            ner_state['file_type_hint'] = 'txt'; ner_state['text_column_name'] = None
            text_data_source_configured = True
        else: 
            st.warning("Uploaded file type not fully determined. Assuming .txt."); ner_state['file_type_hint'] = 'txt'
            text_data_source_configured = True

    if ner_state.get('processed_filename') or ner_state.get('editable_entity_rules'):
        if st.button("Clear All Config & Upload New File", key="clear_ner_config_all"):
            st.session_state.ner_mode = {'editable_entity_rules':[],'original_text_samples':[],'base_text_preview':None,'text_column_name':None,'file_uploader_key':ner_state.get('file_uploader_key',0)+1,'processed_filename':None,'num_augmented_samples':10,'file_type_hint':None}
            st.session_state.results = {'data':None,'message':None,'error':None,'is_generating':False}; st.rerun()

    if uploaded_file and text_data_source_configured:
        is_new_file = uploaded_file.name != ner_state.get('processed_filename')
        if is_new_file or not ner_state.get('original_text_samples'):
            with st.spinner(f"Reading text from {uploaded_file.name}..."):
                raw_texts = read_text_from_file(uploaded_file, ner_state.get('text_column_name'), ner_state.get('file_type_hint'))
                if raw_texts is not None : 
                    ner_state['original_text_samples'] = raw_texts
                    ner_state['base_text_preview'] = raw_texts[0] if raw_texts else "No text found in file."
                    ner_state['processed_filename'] = uploaded_file.name
                    if is_new_file: st.session_state.results = {'data':None,'message':None,'error':None,'is_generating':False}; st.rerun() 
                else: ner_state.update({'original_text_samples':[],'base_text_preview':"Error reading file.",'processed_filename':None})

    if ner_state.get('base_text_preview'):
        st.subheader("Preview of Original Text (First Sample)")
        st.text_area("Original Text Sample:", ner_state['base_text_preview'], height=100, disabled=True, key="ner_base_text_preview_area")
    st.divider()

    st.subheader("2. Define Entity Augmentation Rules")
    if not ner_state.get('original_text_samples') and not uploaded_file: st.info("Upload text file or add rules manually.")
    column_editor_ui(columns_state_list=ner_state['editable_entity_rules'], item_type_options=NER_ENTITY_ACTIONS, render_item_params_func=render_ner_params_ui, item_name_key="rule_name", item_type_key="action", enable_distribution_select=False, key_prefix="ner_rule_edit")
    st.divider()
    add_new_column_ui(columns_state_list=ner_state['editable_entity_rules'], item_type_options=NER_ENTITY_ACTIONS, default_item_type=NER_ENTITY_ACTIONS[0], item_name_label="Rule Name*", item_name_key="rule_name", item_type_key="action", default_dist_if_applicable=None, key_prefix="ner_rule_add")
    st.divider()

    st.subheader("3. Configure Generation")
    ner_state['num_augmented_samples'] = st.number_input("Number of Augmented Text Samples to Generate", min_value=1, max_value=1000, value=ner_state.get('num_augmented_samples', 10), key="ner_num_samples_gen", help="Each original text sample might be augmented, or new samples generated.")

def generate_ner_data_action():
    results = {'data': None, 'message': None, 'error': None}
    ner_state = st.session_state.ner_mode
    rules, original_texts, num_to_gen = ner_state.get('editable_entity_rules',[]), ner_state.get('original_text_samples',[]), ner_state.get('num_augmented_samples',10)
    
    if not rules: results['error'] = "No NER rules defined.";
    elif not original_texts and not any(r.get('action') == "Inject New Entity into Template String" for r in rules):
        results['error'] = "No original text and no rules to generate from scratch."
    
    if results['error']:
        st.session_state.results.update(results); st.session_state.results['is_generating'] = False; return

    if not original_texts: original_texts = [""] * num_to_gen # For injection-only case

    augmented_texts, placeholder_text = [], "(Placeholder: Actual NER not implemented)"
    try:
        for i in range(num_to_gen):
            base_text = original_texts[i % len(original_texts)] if original_texts else ""
            current_aug_text, log = base_text, [f"Sample {i+1} (Base: '{base_text[:50]}...'):"]
            for rule_idx, rule in enumerate(rules):
                r_name, action, params = rule.get('rule_name',f"R{rule_idx+1}"), rule.get('action'), rule.get('params',{})
                pattern = params.get('entity_label_pattern')
                applied_msg = ""
                if not pattern and action != "Inject New Entity into Template String": log.append(f"  - Skipped '{r_name}': Missing pattern."); continue
                
                if action == "Replace Matched Text with Faker":
                    f_prov = params.get('faker_provider','word')
                    applied_msg = f"would replace matching '{pattern}' with Faker '{f_prov}'."
                elif action == "Inject New Entity into Template String":
                    tmpl, f_prov_inj, count = params.get('injection_template',"{ENTITY}"), params.get('faker_provider_inject','bs'), params.get('injection_count',1)
                    injections = []
                    for _ in range(count):
                        try: injections.append(tmpl.replace("{ENTITY}", str(getattr(fake,f_prov_inj)())))
                        except AttributeError: injections.append(tmpl.replace("{ENTITY}", f"[ERR: Bad Faker {f_prov_inj}]"))
                    current_aug_text += " " + " ".join(injections)
                    applied_msg = f"would inject {count} instances via template & Faker '{f_prov_inj}'."
                elif action == "Anonymize Matched Text":
                    anon_str = params.get('anonymization_string','[REDACTED]')
                    applied_msg = f"would anonymize matching '{pattern}' with '{anon_str}'."
                else: applied_msg = "has unknown action."
                log.append(f"  - Rule '{r_name}' ({action}): {applied_msg} {placeholder_text}")
            augmented_texts.append("\n".join(log) + f"\nFinal (placeholder): {current_aug_text}")
        results.update({'data': augmented_texts, 'message': f"Generated {len(augmented_texts)} NER augmented samples (Placeholder Output)."})
    except Exception as e: results['error'] = f"NER Augmentation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
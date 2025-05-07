import streamlit as st
from utils import fake

def render_text_page():
    st.info("Generate basic text samples using Faker.")
    txt_cfg = st.session_state.text
    txt_cfg['count'] = st.number_input("Num Samples", 1, 5000, txt_cfg.get('count', 10), key="txt_count")
    common_faker = ['sentence', 'paragraph', 'text', 'bs', 'catch_phrase']
    current_method = txt_cfg.get('faker_method', 'sentence')
    method_idx = common_faker.index(current_method) if current_method in common_faker else 0
    txt_cfg['faker_method'] = st.selectbox("Faker Text Type", common_faker, index=method_idx, key="txt_faker_method")

def generate_text_data_action():
    results = {'data': None, 'message': None, 'error': None}
    try:
        txt_cfg = st.session_state.text; row_count = txt_cfg.get('count', 10); faker_method_name = txt_cfg.get('faker_method', 'sentence')
        if not hasattr(fake, faker_method_name) or not callable(getattr(fake, faker_method_name)): raise ValueError(f"Invalid Faker method: '{faker_method_name}'")
        faker_func = getattr(fake, faker_method_name); generated_output = [faker_func() for _ in range(row_count)]
        results['data'] = generated_output; results['message'] = f"Generated {len(generated_output)} text samples."
    except Exception as e: results['error'] = f"Text generation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
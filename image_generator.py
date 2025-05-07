import streamlit as st
from utils import generate_simple_image

def render_image_page():
    st.info("Generate basic shape images using Pillow.")
    img_cfg = st.session_state.image; img_cols = st.columns(2)
    with img_cols[0]:
        img_cfg['count'] = st.number_input("Num Images", 1, 1000, img_cfg.get('count', 10), key="img_count")
        img_cfg['width'] = st.number_input("Width (px)", 16, 1024, img_cfg.get('width', 128), key="img_width")
        img_cfg['height'] = st.number_input("Height (px)", 16, 1024, img_cfg.get('height', 128), key="img_height")
    with img_cols[1]:
        img_cfg['bg_color'] = st.color_picker("BG Color", img_cfg.get('bg_color', '#DDDDDD'), key="img_bg")
        shape_options = ['rectangle', 'ellipse', 'triangle']; current_shape = img_cfg.get('shape', 'rectangle')
        shape_idx = shape_options.index(current_shape) if current_shape in shape_options else 0
        img_cfg['shape'] = st.selectbox("Shape", shape_options, index=shape_idx, key="img_shape")
        img_cfg['shape_color'] = st.color_picker("Shape Color", img_cfg.get('shape_color', '#FF0000'), key="img_shape_color")

def generate_image_data_action():
    results = {'data': None, 'message': None, 'error': None}
    try:
        img_cfg = st.session_state.image; row_count = img_cfg.get('count', 10); generated_output = []; error_count = 0
        for i in range(row_count):
            img = generate_simple_image(img_cfg['width'], img_cfg['height'], img_cfg['bg_color'], img_cfg['shape'], img_cfg['shape_color'])
            if img: generated_output.append({'filename': f'image_{i}_{img_cfg["shape"]}.png', 'image': img})
            else: error_count += 1
        results['data'] = generated_output
        if error_count > 0: results['message'] = f"Generated {len(generated_output)} images with {error_count} errors."; results['error'] = f"{error_count} failed."
        else: results['message'] = f"Generated {len(generated_output)} images."
    except Exception as e: results['error'] = f"Image generation failed: {e}"; st.exception(e)
    st.session_state.results.update(results); st.session_state.results['is_generating'] = False
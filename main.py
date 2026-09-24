"""Entry point: launches the Gradio calibration dashboard.

The dashboard only starts/stops and tunes the tracker thread (see tracker.py)
-- it never drives the webcam itself, so the tracking loop keeps running even
if this browser tab is backgrounded or closed.
"""

import gradio as gr

from shared_state import SharedState
from tracker import Tracker

state = SharedState()
tracker = Tracker(state)


def start_tracking():
    tracker.start()
    return "running"


def stop_tracking():
    tracker.stop()
    return "stopped"


def set_neutral():
    neutral = state.set_neutral_to_current()
    return f"neutral set to {neutral:.1f} deg"


def update_pink(h_min, s_min, v_min, h_max, s_max, v_max):
    state.set_pink_range([h_min, s_min, v_min, h_max, s_max, v_max])


def update_green(h_min, s_min, v_min, h_max, s_max, v_max):
    state.set_green_range([h_min, s_min, v_min, h_max, s_max, v_max])


def update_dead_zone(value):
    state.set_dead_zone(value)


def update_show_mask(value):
    state.set_show_mask(value)


def poll_preview():
    frame, mask_frame, raw_angle, smoothed_angle, key_state = state.get_frame()
    status = state.get_status()
    if raw_angle is None:
        angle_text = "angle: --"
    else:
        angle_text = f"angle: {smoothed_angle - state.get_neutral():+.1f} deg"
    info = f"status: {status}   {angle_text}   key: {key_state or '-'}"
    shown = mask_frame if state.get_show_mask() else frame
    return shown, info


with gr.Blocks(title="CV Steering Wheel Controller") as demo:
    gr.Markdown("# CV Steering Wheel Controller\nWebcam-based A/D steering for ETS2.")

    with gr.Row():
        start_btn = gr.Button("Start", variant="primary")
        stop_btn = gr.Button("Stop")
        neutral_btn = gr.Button("Set Neutral")

    info_box = gr.Textbox(label="Status", value="stopped", interactive=False)

    preview = gr.Image(label="Preview", interactive=False)
    show_mask_cb = gr.Checkbox(
        label="Show color masks (use this while tuning HSV sliders below)",
        value=False,
    )
    show_mask_cb.change(update_show_mask, inputs=show_mask_cb)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### Left marker (hot pink) HSV range")
            p_h_min = gr.Slider(0, 179, value=130, step=1, label="H min")
            p_s_min = gr.Slider(0, 255, value=100, step=1, label="S min")
            p_v_min = gr.Slider(0, 255, value=50, step=1, label="V min")
            p_h_max = gr.Slider(0, 179, value=179, step=1, label="H max")
            p_s_max = gr.Slider(0, 255, value=255, step=1, label="S max")
            p_v_max = gr.Slider(0, 255, value=255, step=1, label="V max")

        with gr.Column():
            gr.Markdown("### Right marker (neon green) HSV range")
            g_h_min = gr.Slider(0, 179, value=25, step=1, label="H min")
            g_s_min = gr.Slider(0, 255, value=50, step=1, label="S min")
            g_v_min = gr.Slider(0, 255, value=50, step=1, label="V min")
            g_h_max = gr.Slider(0, 179, value=90, step=1, label="H max")
            g_s_max = gr.Slider(0, 255, value=255, step=1, label="S max")
            g_v_max = gr.Slider(0, 255, value=255, step=1, label="V max")

    dead_zone = gr.Slider(0, 45, value=8, step=1, label="Dead zone (degrees)")

    pink_sliders = [p_h_min, p_s_min, p_v_min, p_h_max, p_s_max, p_v_max]
    green_sliders = [g_h_min, g_s_min, g_v_min, g_h_max, g_s_max, g_v_max]

    for slider in pink_sliders:
        slider.change(update_pink, inputs=pink_sliders)
    for slider in green_sliders:
        slider.change(update_green, inputs=green_sliders)
    dead_zone.change(update_dead_zone, inputs=dead_zone)

    start_btn.click(start_tracking, outputs=info_box)
    stop_btn.click(stop_tracking, outputs=info_box)
    neutral_btn.click(set_neutral, outputs=info_box)

    timer = gr.Timer(0.1)
    timer.tick(poll_preview, outputs=[preview, info_box])

demo.queue()

if __name__ == "__main__":
    demo.launch()

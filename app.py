import math

import dearpygui.dearpygui as dpg

from vn_reader import VNReader

# -- colors --
GREEN = (0, 255, 0, 255)
YELLOW = (255, 255, 0, 255)
RED = (255, 80, 80, 255)
GRAY = (150, 150, 150, 255)
WHITE = (255, 255, 255, 255)
CYAN = (0, 200, 255, 255)
ORANGE = (255, 165, 0, 255)

MODE_COLORS = {
    "Not Tracking": RED,
    "Degraded": YELLOW,
    "Healthy": GREEN,
    "GNSS Loss": GRAY,
    "Unknown": GRAY,
}

# compass geometry
CX, CY, CR = 100, 100, 80


def _make_line_theme(r, g, b):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (r, g, b), category=dpg.mvThemeCat_Plots)
    return t


def build_gui():
    dpg.create_context()
    dpg.create_viewport(title="VN-300 Dashboard", width=1400, height=900)

    # try to load a readable font
    try:
        with dpg.font_registry():
            font = dpg.add_font("C:/Windows/Fonts/consola.ttf", 16)
        dpg.bind_font(font)
    except Exception:
        pass

    with dpg.window(tag="main"):
        # ---- Row 1: Device Info + Magnetic ----
        with dpg.group(horizontal=True):
            # Device Info
            with dpg.child_window(width=680, height=280):
                dpg.add_text("Device Information", color=CYAN)
                dpg.add_separator()
                dpg.add_spacer(height=5)
                for label, tag in [
                    ("Model:", "txt_model"),
                    ("Hardware Rev:", "txt_hw_rev"),
                    ("Serial Number:", "txt_serial"),
                    ("Firmware:", "txt_firmware"),
                ]:
                    with dpg.group(horizontal=True):
                        dpg.add_text(label, color=ORANGE)
                        dpg.add_text("--", tag=tag)
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_text("Port:", color=ORANGE)
                    dpg.add_text("COM4 @ 115200")
                    dpg.add_spacer(width=20)
                    dpg.add_text("Status:", color=ORANGE)
                    dpg.add_text("Connecting...", tag="txt_conn_status", color=YELLOW)

            # Magnetic
            with dpg.child_window(width=-1, height=280):
                dpg.add_text("Magnetic Sensor", color=CYAN)
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    with dpg.drawlist(width=200, height=200, tag="compass"):
                        # outer ring
                        dpg.draw_circle((CX, CY), CR, color=WHITE, thickness=2)
                        # tick marks every 30 degrees
                        for deg in range(0, 360, 30):
                            rad = math.radians(90 - deg)
                            inner = CR - 8
                            outer = CR
                            dpg.draw_line(
                                (CX + inner * math.cos(rad), CY - inner * math.sin(rad)),
                                (CX + outer * math.cos(rad), CY - outer * math.sin(rad)),
                                color=GRAY, thickness=1,
                            )
                        # cardinal labels
                        dpg.draw_text((CX - 4, CY - CR - 18), "N", color=RED, size=16)
                        dpg.draw_text((CX + CR + 5, CY - 6), "E", color=WHITE, size=14)
                        dpg.draw_text((CX - 4, CY + CR + 5), "S", color=WHITE, size=14)
                        dpg.draw_text((CX - CR - 16, CY - 6), "W", color=WHITE, size=14)
                        # needle layer (redrawn each frame)
                        with dpg.draw_layer(tag="needle_layer"):
                            pass

                    dpg.add_spacer(width=20)
                    with dpg.group():
                        dpg.add_spacer(height=8)
                        dpg.add_text("Heading:", color=ORANGE)
                        dpg.add_text("  ---.-  deg", tag="txt_heading")
                        dpg.add_spacer(height=8)
                        dpg.add_text("Mag X (Gauss):", color=ORANGE)
                        dpg.add_text("  +0.0000", tag="txt_mag_x")
                        dpg.add_text("Mag Y (Gauss):", color=ORANGE)
                        dpg.add_text("  +0.0000", tag="txt_mag_y")
                        dpg.add_text("Mag Z (Gauss):", color=ORANGE)
                        dpg.add_text("  +0.0000", tag="txt_mag_z")
                        dpg.add_text("Magnitude:", color=ORANGE)
                        dpg.add_text("  +0.0000", tag="txt_mag_mag")

        # ---- Row 2: Attitude + Velocity ----
        with dpg.group(horizontal=True):
            # Attitude
            with dpg.child_window(width=680, height=280):
                dpg.add_text("Attitude (INS)", color=CYAN)
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    for label, tag in [("Yaw:", "txt_yaw"), ("Pitch:", "txt_pitch"), ("Roll:", "txt_roll")]:
                        with dpg.group():
                            dpg.add_text(label, color=ORANGE)
                            dpg.add_text("  +000.000 deg", tag=tag)
                        dpg.add_spacer(width=30)

                with dpg.plot(label="Attitude", width=-1, height=180):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="ax_att_x")
                    with dpg.plot_axis(dpg.mvYAxis, label="Degrees", tag="ax_att_y"):
                        dpg.add_line_series([], [], label="Yaw", tag="s_yaw")
                        dpg.add_line_series([], [], label="Pitch", tag="s_pitch")
                        dpg.add_line_series([], [], label="Roll", tag="s_roll")

            # Velocity
            with dpg.child_window(width=-1, height=280):
                dpg.add_text("Velocity & Position", color=CYAN)
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    for label, tag in [("North:", "txt_vel_n"), ("East:", "txt_vel_e"), ("Down:", "txt_vel_d")]:
                        with dpg.group():
                            dpg.add_text(label, color=ORANGE)
                            dpg.add_text("  +000.000 m/s", tag=tag)
                        dpg.add_spacer(width=20)

                dpg.add_spacer(height=8)
                dpg.add_text("Position:", color=ORANGE)
                dpg.add_text("  Lat: +00.00000000   Lon: +000.00000000   Alt: +00000.000 m", tag="txt_position")

        # ---- Row 3: Status + Mag plot ----
        with dpg.child_window(width=-1, height=-1):
            with dpg.group(horizontal=True):
                dpg.add_text("INS Mode:", color=CYAN)
                dpg.add_text("Unknown", tag="txt_ins_mode", color=GRAY)
                dpg.add_spacer(width=20)
                dpg.add_text("Flags:", color=CYAN)
                dpg.add_text("---", tag="txt_flags")
                dpg.add_spacer(width=20)
                dpg.add_text("Att Unc:", color=CYAN)
                dpg.add_text("--", tag="txt_att_unc")
                dpg.add_spacer(width=10)
                dpg.add_text("Pos Unc:", color=CYAN)
                dpg.add_text("--", tag="txt_pos_unc")
                dpg.add_spacer(width=10)
                dpg.add_text("Vel Unc:", color=CYAN)
                dpg.add_text("--", tag="txt_vel_unc")
                dpg.add_spacer(width=20)
                dpg.add_text("Status Word:", color=CYAN)
                dpg.add_text("0x0000", tag="txt_status_hex")

            with dpg.plot(label="Magnetometer", width=-1, height=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="ax_mag_x")
                with dpg.plot_axis(dpg.mvYAxis, label="Gauss", tag="ax_mag_y"):
                    dpg.add_line_series([], [], label="Mag X", tag="s_mag_x")
                    dpg.add_line_series([], [], label="Mag Y", tag="s_mag_y")
                    dpg.add_line_series([], [], label="Mag Z", tag="s_mag_z")

    # apply line-series colors
    dpg.bind_item_theme("s_yaw", _make_line_theme(255, 255, 0))
    dpg.bind_item_theme("s_pitch", _make_line_theme(0, 255, 0))
    dpg.bind_item_theme("s_roll", _make_line_theme(0, 200, 255))
    dpg.bind_item_theme("s_mag_x", _make_line_theme(255, 80, 80))
    dpg.bind_item_theme("s_mag_y", _make_line_theme(0, 255, 0))
    dpg.bind_item_theme("s_mag_z", _make_line_theme(80, 140, 255))

    dpg.set_primary_window("main", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()


def update_compass(heading: float):
    dpg.delete_item("needle_layer", children_only=True)
    rad = math.radians(90 - heading)
    ex = CX + (CR - 12) * math.cos(rad)
    ey = CY - (CR - 12) * math.sin(rad)
    dpg.draw_line((CX, CY), (ex, ey), color=RED, thickness=3, parent="needle_layer")
    dpg.draw_circle((CX, CY), 4, color=RED, fill=RED, parent="needle_layer")
    # heading text at center bottom
    dpg.draw_text((CX - 20, CY + 20), f"{heading:.1f}", color=WHITE, size=14, parent="needle_layer")


def update_dashboard(reader: VNReader):
    s = reader.get_snapshot()

    # connection
    if s["connected"]:
        dpg.set_value("txt_conn_status", "CONNECTED")
        dpg.configure_item("txt_conn_status", color=GREEN)
    else:
        dpg.set_value("txt_conn_status", f"DISCONNECTED  {s['error_msg']}")
        dpg.configure_item("txt_conn_status", color=RED)

    # device info
    dpg.set_value("txt_model", s["model"] or "--")
    dpg.set_value("txt_hw_rev", s["hw_rev"] or "--")
    dpg.set_value("txt_serial", s["serial_num"] or "--")
    dpg.set_value("txt_firmware", s["firmware"] or "--")

    # magnetic
    dpg.set_value("txt_heading", f"  {s['mag_heading']:>7.1f}  deg")
    dpg.set_value("txt_mag_x", f"  {s['mag_x']:>+.4f}")
    dpg.set_value("txt_mag_y", f"  {s['mag_y']:>+.4f}")
    dpg.set_value("txt_mag_z", f"  {s['mag_z']:>+.4f}")
    mag = math.sqrt(s["mag_x"] ** 2 + s["mag_y"] ** 2 + s["mag_z"] ** 2)
    dpg.set_value("txt_mag_mag", f"  {mag:>+.4f}")
    update_compass(s["mag_heading"])

    # attitude
    dpg.set_value("txt_yaw", f"  {s['yaw']:>+10.3f} deg")
    dpg.set_value("txt_pitch", f"  {s['pitch']:>+10.3f} deg")
    dpg.set_value("txt_roll", f"  {s['roll']:>+10.3f} deg")

    # velocity & position
    dpg.set_value("txt_vel_n", f"  {s['vel_n']:>+10.3f} m/s")
    dpg.set_value("txt_vel_e", f"  {s['vel_e']:>+10.3f} m/s")
    dpg.set_value("txt_vel_d", f"  {s['vel_d']:>+10.3f} m/s")
    dpg.set_value(
        "txt_position",
        f"  Lat: {s['latitude']:>+14.8f}   Lon: {s['longitude']:>+15.8f}   Alt: {s['altitude']:>+11.3f} m",
    )

    # status
    mode = s["ins_mode"]
    dpg.set_value("txt_ins_mode", mode)
    dpg.configure_item("txt_ins_mode", color=MODE_COLORS.get(mode, GRAY))

    flags = []
    if s["ins_error"]:
        flags.append("ERR")
    if s["ins_time_error"]:
        flags.append("TIME")
    if s["ins_imu_error"]:
        flags.append("IMU")
    if s["ins_mag_pres_error"]:
        flags.append("MAG/PRES")
    if s["ins_gnss_error"]:
        flags.append("GNSS")
    dpg.set_value("txt_flags", " | ".join(flags) if flags else "None")
    dpg.configure_item("txt_flags", color=RED if flags else GREEN)

    dpg.set_value("txt_att_unc", f"{s['att_unc']:.2f} deg")
    dpg.set_value("txt_pos_unc", f"{s['pos_unc']:.2f} m")
    dpg.set_value("txt_vel_unc", f"{s['vel_unc']:.3f} m/s")
    dpg.set_value("txt_status_hex", f"0x{s['ins_status']:04X}")

    # attitude plot
    if s["att_time_hist"]:
        dpg.set_value("s_yaw", [s["att_time_hist"], s["yaw_hist"]])
        dpg.set_value("s_pitch", [s["att_time_hist"], s["pitch_hist"]])
        dpg.set_value("s_roll", [s["att_time_hist"], s["roll_hist"]])
        dpg.fit_axis_data("ax_att_x")
        dpg.fit_axis_data("ax_att_y")

    # mag plot
    if s["mag_time_hist"]:
        dpg.set_value("s_mag_x", [s["mag_time_hist"], s["mag_x_hist"]])
        dpg.set_value("s_mag_y", [s["mag_time_hist"], s["mag_y_hist"]])
        dpg.set_value("s_mag_z", [s["mag_time_hist"], s["mag_z_hist"]])
        dpg.fit_axis_data("ax_mag_x")
        dpg.fit_axis_data("ax_mag_y")


def main():
    reader = VNReader(port="COM4", baud=115200)
    reader.start()

    build_gui()

    while dpg.is_dearpygui_running():
        update_dashboard(reader)
        dpg.render_dearpygui_frame()

    reader.stop()
    reader.join(timeout=2)
    dpg.destroy_context()


if __name__ == "__main__":
    main()

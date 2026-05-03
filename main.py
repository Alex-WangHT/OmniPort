import dearpygui.dearpygui as dpg
from typing import Optional
from datetime import datetime
from serial_manager import (
    SerialManager, 
    SerialConfig, 
    DataBits, 
    Parity, 
    StopBits
)


class SerialDebugAssistant:
    def __init__(self):
        self.serial_manager: SerialManager = SerialManager()
        self.is_connected: bool = False
        self.auto_scroll: bool = True
        self.show_timestamp: bool = True
        self.send_newline: bool = True
        self.display_mode: str = "text"
        self.send_encoding: str = "utf-8"
        self.receive_encoding: str = "utf-8"
        
        self._setup_callbacks()
        self._setup_theme()
        
    def _setup_callbacks(self) -> None:
        self.serial_manager.add_data_received_callback(self._on_data_received)
        self.serial_manager.add_connection_status_callback(self._on_connection_status_changed)
        self.serial_manager.add_error_callback(self._on_error)
    
    def _setup_theme(self) -> None:
        with dpg.theme() as self.global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 25, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (70, 70, 70, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 100, 100, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (120, 120, 120, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 40, 40, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (60, 60, 60, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (80, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 4)
                
        dpg.bind_theme(self.global_theme)
    
    def _get_timestamp(self) -> str:
        if self.show_timestamp:
            return f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
        return ""
    
    def _bytes_to_display(self, data: bytes) -> str:
        if self.display_mode == "text":
            try:
                return data.decode(self.receive_encoding, errors='replace')
            except Exception:
                return data.hex()
        elif self.display_mode == "hex":
            return ' '.join(f'{b:02X}' for b in data)
        elif self.display_mode == "binary":
            return ' '.join(f'{b:08b}' for b in data)
        return data.hex()
    
    def _display_to_bytes(self, text: str) -> bytes:
        if self.send_newline:
            text += '\r\n'
        return text.encode(self.send_encoding, errors='replace')
    
    def _on_data_received(self, data: bytes) -> None:
        try:
            display_text = self._bytes_to_display(data)
            timestamp = self._get_timestamp()
            
            full_text = f"{timestamp}{display_text}"
            
            current_text = dpg.get_value("receive_text")
            if current_text:
                current_text += full_text
            else:
                current_text = full_text
            
            dpg.set_value("receive_text", current_text)
            
            if self.auto_scroll:
                dpg.set_y_scroll("receive_window", -1.0)
        except Exception as e:
            self._on_error(e)
    
    def _on_connection_status_changed(self, connected: bool) -> None:
        self.is_connected = connected
        dpg.set_value("connection_status", 
                       f"状态: {'已连接' if connected else '已断开'}")
        dpg.set_value("connection_indicator", 
                       (0, 255, 0, 255) if connected else (255, 0, 0, 255))
        
        dpg.configure_item("connect_button", 
                          label="断开连接" if connected else "打开串口")
        dpg.configure_item("port_combo", enabled=not connected)
        dpg.configure_item("baudrate_combo", enabled=not connected)
        dpg.configure_item("data_bits_combo", enabled=not connected)
        dpg.configure_item("parity_combo", enabled=not connected)
        dpg.configure_item("stop_bits_combo", enabled=not connected)
    
    def _on_error(self, error: Exception) -> None:
        error_msg = f"错误: {str(error)}\n"
        current_text = dpg.get_value("receive_text")
        if current_text:
            current_text += error_msg
        else:
            current_text = error_msg
        dpg.set_value("receive_text", current_text)
    
    def refresh_ports(self) -> None:
        ports = self.serial_manager.get_available_ports()
        dpg.configure_item("port_combo", items=ports)
        if ports and not dpg.get_value("port_combo"):
            dpg.set_value("port_combo", ports[0])
    
    def connect_serial(self, sender, app_data) -> None:
        if self.is_connected:
            self.serial_manager.disconnect()
            return
        
        port = dpg.get_value("port_combo")
        if not port:
            self._on_error(Exception("请选择串口"))
            return
        
        baudrate = int(dpg.get_value("baudrate_combo"))
        data_bits_str = dpg.get_value("data_bits_combo")
        parity_str = dpg.get_value("parity_combo")
        stop_bits_str = dpg.get_value("stop_bits_combo")
        
        data_bits_map = {
            "5": DataBits.FIVE,
            "6": DataBits.SIX,
            "7": DataBits.SEVEN,
            "8": DataBits.EIGHT
        }
        
        parity_map = {
            "无": Parity.NONE,
            "奇校验": Parity.ODD,
            "偶校验": Parity.EVEN,
            "MARK": Parity.MARK,
            "SPACE": Parity.SPACE
        }
        
        stop_bits_map = {
            "1": StopBits.ONE,
            "1.5": StopBits.ONE_POINT_FIVE,
            "2": StopBits.TWO
        }
        
        config = SerialConfig(
            port=port,
            baudrate=baudrate,
            data_bits=data_bits_map.get(data_bits_str, DataBits.EIGHT),
            parity=parity_map.get(parity_str, Parity.NONE),
            stop_bits=stop_bits_map.get(stop_bits_str, StopBits.ONE)
        )
        
        self.serial_manager.connect(config)
    
    def send_data(self, sender, app_data) -> None:
        if not self.is_connected:
            self._on_error(Exception("请先连接串口"))
            return
        
        text = dpg.get_value("send_text")
        if not text:
            return
        
        data = self._display_to_bytes(text)
        if self.serial_manager.send_data(data):
            if self.show_timestamp:
                timestamp = self._get_timestamp()
                sent_text = f"{timestamp}发送: {text}\n" if not self.send_newline else f"{timestamp}发送: {text}"
                current_text = dpg.get_value("receive_text")
                if current_text:
                    current_text += sent_text
                else:
                    current_text = sent_text
                dpg.set_value("receive_text", current_text)
                
                if self.auto_scroll:
                    dpg.set_y_scroll("receive_window", -1.0)
        else:
            self._on_error(Exception("发送失败"))
    
    def clear_receive(self, sender, app_data) -> None:
        dpg.set_value("receive_text", "")
    
    def clear_send(self, sender, app_data) -> None:
        dpg.set_value("send_text", "")
    
    def toggle_auto_scroll(self, sender, app_data) -> None:
        self.auto_scroll = app_data
    
    def toggle_timestamp(self, sender, app_data) -> None:
        self.show_timestamp = app_data
    
    def toggle_newline(self, sender, app_data) -> None:
        self.send_newline = app_data
    
    def change_display_mode(self, sender, app_data) -> None:
        self.display_mode = app_data
    
    def create_ui(self) -> None:
        with dpg.window(tag="main_window", label="串口调试助手", width=900, height=700):
            with dpg.group(horizontal=True):
                with dpg.child_window(tag="config_panel", width=250):
                    dpg.add_text("串口配置")
                    dpg.add_separator()
                    
                    dpg.add_text("端口:")
                    dpg.add_combo(tag="port_combo", width=200)
                    dpg.add_button(label="刷新端口", callback=self.refresh_ports, width=200)
                    
                    dpg.add_text("波特率:")
                    dpg.add_combo(tag="baudrate_combo", 
                                   items=["9600", "19200", "38400", "57600", "115200"],
                                   default_value="9600", width=200)
                    
                    dpg.add_text("数据位:")
                    dpg.add_combo(tag="data_bits_combo",
                                   items=["5", "6", "7", "8"],
                                   default_value="8", width=200)
                    
                    dpg.add_text("校验位:")
                    dpg.add_combo(tag="parity_combo",
                                   items=["无", "奇校验", "偶校验", "MARK", "SPACE"],
                                   default_value="无", width=200)
                    
                    dpg.add_text("停止位:")
                    dpg.add_combo(tag="stop_bits_combo",
                                   items=["1", "1.5", "2"],
                                   default_value="1", width=200)
                    
                    dpg.add_separator()
                    
                    dpg.add_button(tag="connect_button", label="打开串口", 
                                   callback=self.connect_serial, width=200, height=30)
                    
                    dpg.add_separator()
                    
                    dpg.add_text("显示设置")
                    dpg.add_checkbox(label="自动滚动", default_value=True, 
                                     callback=self.toggle_auto_scroll)
                    dpg.add_checkbox(label="显示时间戳", default_value=True,
                                     callback=self.toggle_timestamp)
                    
                    dpg.add_text("显示模式:")
                    dpg.add_radio_button(tag="display_mode",
                                         items=["text", "hex", "binary"],
                                         default_value="text",
                                         callback=self.change_display_mode,
                                         horizontal=True)
                    
                    dpg.add_separator()
                    
                    dpg.add_text("发送设置")
                    dpg.add_checkbox(label="发送后添加换行符", default_value=True,
                                     callback=self.toggle_newline)
                    
                    dpg.add_separator()
                    
                    with dpg.group(horizontal=True):
                        dpg.add_color_edit(tag="connection_indicator", 
                                           default_value=(255, 0, 0, 255),
                                           no_picker=True, no_inputs=True, width=20)
                        dpg.add_text(tag="connection_status", default_value="状态: 已断开")
                
                with dpg.child_window(tag="main_panel", width=-1):
                    with dpg.group():
                        dpg.add_text("接收区域")
                        with dpg.child_window(tag="receive_window", width=-1, height=350):
                            dpg.add_input_text(tag="receive_text", multiline=True,
                                              readonly=True, width=-1, height=-1)
                        
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="清空接收", callback=self.clear_receive)
                            dpg.add_spacer(width=10)
                            dpg.add_text(f"连接状态: {'已连接' if self.is_connected else '已断开'}")
                    
                    dpg.add_separator()
                    
                    with dpg.group():
                        dpg.add_text("发送区域")
                        with dpg.child_window(width=-1, height=150):
                            dpg.add_input_text(tag="send_text", multiline=True,
                                              width=-1, height=-1, default_value="")
                        
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="发送", callback=self.send_data, width=100, height=30)
                            dpg.add_button(label="清空发送", callback=self.clear_send)
    
    def run(self) -> None:
        dpg.create_context()
        dpg.create_viewport(title="串口调试助手 - OmniPort", width=920, height=720)
        dpg.setup_dearpygui()
        
        self.create_ui()
        
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)
        
        self.refresh_ports()
        
        dpg.start_dearpygui()
        dpg.destroy_context()


if __name__ == "__main__":
    app = SerialDebugAssistant()
    app.run()

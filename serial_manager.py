import serial
import serial.tools.list_ports
import threading
from typing import List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Parity(Enum):
    NONE = 'N'
    ODD = 'O'
    EVEN = 'E'
    MARK = 'M'
    SPACE = 'S'


class StopBits(Enum):
    ONE = 1
    ONE_POINT_FIVE = 1.5
    TWO = 2


class DataBits(Enum):
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8


@dataclass
class SerialConfig:
    port: str = ''
    baudrate: int = 9600
    data_bits: DataBits = DataBits.EIGHT
    parity: Parity = Parity.NONE
    stop_bits: StopBits = StopBits.ONE
    timeout: float = 1.0
    write_timeout: float = 1.0
    rtscts: bool = False
    dsrdtr: bool = False


class SerialManager:
    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._config: SerialConfig = SerialConfig()
        self._is_connected: bool = False
        self._receiving_thread: Optional[threading.Thread] = None
        self._stop_receiving: threading.Event = threading.Event()
        
        self._data_received_callbacks: List[Callable[[bytes], Any]] = []
        self._connection_status_callbacks: List[Callable[[bool], Any]] = []
        self._error_callbacks: List[Callable[[Exception], Any]] = []
    
    def get_available_ports(self) -> List[str]:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, config: SerialConfig) -> bool:
        if self._is_connected:
            self.disconnect()
        
        try:
            self._config = config
            
            self._serial = serial.Serial(
                port=config.port,
                baudrate=config.baudrate,
                bytesize=config.data_bits.value,
                parity=config.parity.value,
                stopbits=config.stop_bits.value,
                timeout=config.timeout,
                write_timeout=config.write_timeout,
                rtscts=config.rtscts,
                dsrdtr=config.dsrdtr
            )
            
            self._is_connected = self._serial.is_open
            self._stop_receiving.clear()
            self._start_receiving_thread()
            self._notify_connection_status(True)
            
            return True
            
        except Exception as e:
            self._notify_error(e)
            self._is_connected = False
            return False
    
    def disconnect(self) -> bool:
        try:
            self._stop_receiving.set()
            
            if self._receiving_thread and self._receiving_thread.is_alive():
                self._receiving_thread.join(timeout=2.0)
            
            if self._serial and self._serial.is_open:
                self._serial.close()
            
            self._is_connected = False
            self._notify_connection_status(False)
            
            return True
            
        except Exception as e:
            self._notify_error(e)
            return False
    
    def send_data(self, data: bytes) -> bool:
        if not self._is_connected or not self._serial:
            return False
        
        try:
            bytes_written = self._serial.write(data)
            return bytes_written == len(data)
            
        except Exception as e:
            self._notify_error(e)
            return False
    
    def send_string(self, text: str, encoding: str = 'utf-8') -> bool:
        try:
            data = text.encode(encoding)
            return self.send_data(data)
        except Exception as e:
            self._notify_error(e)
            return False
    
    def is_connected(self) -> bool:
        return self._is_connected
    
    def get_config(self) -> SerialConfig:
        return self._config
    
    def add_data_received_callback(self, callback: Callable[[bytes], Any]) -> None:
        self._data_received_callbacks.append(callback)
    
    def remove_data_received_callback(self, callback: Callable[[bytes], Any]) -> None:
        if callback in self._data_received_callbacks:
            self._data_received_callbacks.remove(callback)
    
    def add_connection_status_callback(self, callback: Callable[[bool], Any]) -> None:
        self._connection_status_callbacks.append(callback)
    
    def remove_connection_status_callback(self, callback: Callable[[bool], Any]) -> None:
        if callback in self._connection_status_callbacks:
            self._connection_status_callbacks.remove(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], Any]) -> None:
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[Exception], Any]) -> None:
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def _start_receiving_thread(self) -> None:
        self._receiving_thread = threading.Thread(target=self._receiving_loop, daemon=True)
        self._receiving_thread.start()
    
    def _receiving_loop(self) -> None:
        while not self._stop_receiving.is_set():
            try:
                if self._serial and self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    self._notify_data_received(data)
            except Exception as e:
                self._notify_error(e)
                self.disconnect()
                break
            
            self._stop_receiving.wait(0.01)
    
    def _notify_data_received(self, data: bytes) -> None:
        for callback in self._data_received_callbacks:
            try:
                callback(data)
            except Exception as e:
                self._notify_error(e)
    
    def _notify_connection_status(self, connected: bool) -> None:
        for callback in self._connection_status_callbacks:
            try:
                callback(connected)
            except Exception as e:
                self._notify_error(e)
    
    def _notify_error(self, error: Exception) -> None:
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception:
                pass

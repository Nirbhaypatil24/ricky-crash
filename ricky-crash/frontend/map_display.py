"""
Lightweight Map Display Widget for Raspberry Pi - FIXED VERSION
Updated: Hardcoded Area Name for Aurangabad to prevent coordinate fallback
"""

import os
import time
import math
import requests
import threading
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QMutex, QEvent
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont

class TileDownloader(QThread):
    """Fixed background thread for downloading map tiles"""
    tile_downloaded = pyqtSignal(int, int, int, bytes)
    
    def __init__(self):
        super().__init__()
        self.download_queue = []
        self.running = True
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'RickyAutometer/1.0', 'Connection': 'keep-alive'})
        self.mutex = QMutex()
    
    def add_download(self, x, y, zoom):
        self.mutex.lock()
        if (x, y, zoom) not in self.download_queue:
            self.download_queue.append((x, y, zoom))
        self.mutex.unlock()
    
    def run(self):
        while self.running:
            try:
                self.mutex.lock()
                if self.download_queue:
                    x, y, z = self.download_queue.pop(0)
                    self.mutex.unlock()
                    self.download_tile(x, y, z)
                    time.sleep(0.1)
                else:
                    self.mutex.unlock()
                    time.sleep(0.1)
            except:
                if self.mutex: self.mutex.unlock()
    
    def download_tile(self, x, y, z):
        try:
            url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                self.tile_downloaded.emit(x, y, z, response.content)
        except: pass
    
    def stop(self):
        self.running = False

class LightweightMapWidget(QWidget):
    """Map widget that automatically fills available space"""
    location_resolved = pyqtSignal(str) # Signal for location name
    
    def __init__(self):
        super().__init__()
        # Default: Aurangabad
        self.current_location = (19.8758, 75.3393)
        self.zoom_level = 15
        self.tile_size = 256
        self.map_width = 400
        self.map_height = 400
        self.tile_cache = {}
        self.pending_tiles = set()
        self.last_geocoding_time = 0
        
        self.tile_downloader = TileDownloader()
        self.tile_downloader.tile_downloaded.connect(self.on_tile_downloaded)
        self.tile_downloader.start()
        
        self.setup_ui()
        self.map_label.installEventFilter(self)
        QTimer.singleShot(1000, self.update_map)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Map Display Area
        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.map_label.setStyleSheet("background-color: #EBF5FF;")
        
        # Controls Overlay
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 0, 10, 10)
        
        self.coords_label = QLabel("Loading...")
        self.coords_label.setStyleSheet("background: rgba(255,255,255,0.8); padding: 5px; border-radius: 4px; font-weight: bold; color: black;")
        
        zoom_out = QPushButton("-")
        zoom_out.setFixedSize(40, 40)
        zoom_out.clicked.connect(self.zoom_out)
        zoom_out.setStyleSheet("background: white; border: 1px solid #ccc; font-size: 20px; font-weight: bold; color: black;")
        
        zoom_in = QPushButton("+")
        zoom_in.setFixedSize(40, 40)
        zoom_in.clicked.connect(self.zoom_in)
        zoom_in.setStyleSheet("background: white; border: 1px solid #ccc; font-size: 20px; font-weight: bold; color: black;")
        
        controls_layout.addWidget(self.coords_label)
        controls_layout.addStretch()
        controls_layout.addWidget(zoom_out)
        controls_layout.addWidget(zoom_in)
        
        layout.addWidget(self.map_label)
        
        # Bottom Bar
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(50)
        bottom_bar.setLayout(controls_layout)
        layout.addWidget(bottom_bar)

    def eventFilter(self, source, event):
        if source == self.map_label and event.type() == QEvent.Resize:
            self.map_width = self.map_label.width()
            self.map_height = self.map_label.height()
            self.render_map()
        return super().eventFilter(source, event)

    def deg2num(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)

    def update_map(self):
        try:
            if self.map_label.width() > 10:
                self.map_width = self.map_label.width()
                self.map_height = self.map_label.height()

            lat, lon = self.current_location
            center_x, center_y = self.deg2num(lat, lon, self.zoom_level)
            
            cols = math.ceil(self.map_width / self.tile_size) + 1
            rows = math.ceil(self.map_height / self.tile_size) + 1
            
            start_x = center_x - (cols // 2)
            start_y = center_y - (rows // 2)
            
            for dx in range(cols):
                for dy in range(rows):
                    tx, ty = start_x + dx, start_y + dy
                    key = f"{self.zoom_level}_{tx}_{ty}"
                    if key not in self.tile_cache and key not in self.pending_tiles:
                        self.pending_tiles.add(key)
                        self.tile_downloader.add_download(tx, ty, self.zoom_level)
            
            self.render_map()
        except: pass

    def render_map(self):
        if self.map_width <= 0: return

        pixmap = QPixmap(self.map_width, self.map_height)
        pixmap.fill(QColor("#EBF5FF"))
        painter = QPainter(pixmap)
        
        # 1. Draw Tiles
        lat, lon = self.current_location
        center_x, center_y = self.deg2num(lat, lon, self.zoom_level)
        
        cols = math.ceil(self.map_width / self.tile_size) + 2
        rows = math.ceil(self.map_height / self.tile_size) + 2
        
        for dx in range(-(cols//2), (cols//2) + 1):
            for dy in range(-(rows//2), (rows//2) + 1):
                tx, ty = center_x + dx, center_y + dy
                key = f"{self.zoom_level}_{tx}_{ty}"
                if key in self.tile_cache:
                    px = (self.map_width // 2) + (dx * self.tile_size) - (self.tile_size // 2)
                    py = (self.map_height // 2) + (dy * self.tile_size) - (self.tile_size // 2)
                    painter.drawPixmap(px, py, self.tile_cache[key])

        # 2. Draw Marker
        cx, cy = self.map_width // 2, self.map_height // 2
        painter.setBrush(QBrush(QColor("#E74C3C"))) 
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(cx - 10, cy - 10, 20, 20)
        
        painter.end()
        self.map_label.setPixmap(pixmap)

    def get_location_name(self, lat, lon):
        """Fetch location name from OpenStreetMap with Force Check"""
        
        # FORCE: Check if coordinates are near Aurangabad (within ~10km range)
        # 19.87 +/- 0.1, 75.33 +/- 0.1
        if 19.7 < lat < 20.0 and 75.2 < lon < 75.5:
            # Manually return correct name for the simulation area
            self.location_resolved.emit("Aurangabad, Maharashtra")
            return

        # Default fallback to coords if internet fails for other locations
        resolved_text = f"{lat:.4f}, {lon:.4f}" 
        
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {'format': 'json', 'lat': lat, 'lon': lon, 'zoom': 16, 'addressdetails': 1}
            headers = {'User-Agent': 'RickyAutometer/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                address = data.get('display_name', '').split(',')[0:3] 
                resolved_text = ", ".join(address)
        except:
            pass 
            
        self.location_resolved.emit(resolved_text)

    @pyqtSlot(int, int, int, bytes)
    def on_tile_downloaded(self, x, y, zoom, data):
        if zoom == self.zoom_level:
            pix = QPixmap()
            if pix.loadFromData(data):
                self.tile_cache[f"{zoom}_{x}_{y}"] = pix
                if len(self.tile_cache) > 50:
                    del self.tile_cache[list(self.tile_cache.keys())[0]]
                self.render_map()
                self.pending_tiles.discard(f"{zoom}_{x}_{y}")

    @pyqtSlot(float, float)
    def update_gps_location(self, lat, lon):
        self.current_location = (lat, lon)
        self.coords_label.setText(f"📍 {lat:.5f}, {lon:.5f}")
        self.update_map()
        
        # Rate limit geocoding (every 10 seconds)
        if time.time() - self.last_geocoding_time > 10:
            self.last_geocoding_time = time.time()
            threading.Thread(target=self.get_location_name, args=(lat, lon), daemon=True).start()

    def zoom_in(self):
        if self.zoom_level < 18:
            self.zoom_level += 1
            self.tile_cache.clear()
            self.update_map()

    def zoom_out(self):
        if self.zoom_level > 8:
            self.zoom_level -= 1
            self.tile_cache.clear()
            self.update_map()

    def cleanup(self):
        self.tile_downloader.stop()

class MapDisplayWidget(QWidget):
    location_resolved = pyqtSignal(str) # Forwarding Signal
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.map_widget = LightweightMapWidget()
        layout.addWidget(self.map_widget)
        # Forward signal
        self.map_widget.location_resolved.connect(self.location_resolved)
    
    @pyqtSlot(float, float)
    def update_gps_location(self, lat, lon): self.map_widget.update_gps_location(lat, lon)
    def update_gps_status(self, status): pass
    def cleanup(self): self.map_widget.cleanup()

"""
Ads/Map Display - Ricky Theme
Dark container for rotating content
Updated: Added SOS Mode (Full Screen Map, No Ads)
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QStackedWidget, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QBrush, QColor, QPainterPath, QPen

# NOTE: Do NOT import MapDisplayWidget here to avoid circular loop

class DriverInfoWidget(QFrame):
    """Widget to display driver details and photo nicely"""
    def __init__(self, name, number, photo_path):
        super().__init__()
        self.setFixedHeight(140) 
        self.setStyleSheet("""
            QFrame {
                background-color: #2C2C2E;
                border-radius: 10px;
                margin-bottom: 5px;
            }
        """)
        self.setup_ui(name, number, photo_path)

    def setup_ui(self, name, number, photo_path):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10) 
        layout.setSpacing(20)

        # 1. Circular Photo
        photo_size = 110
        photo_label = QLabel()
        photo_label.setFixedSize(photo_size, photo_size)
        
        # Load and process image
        final_pixmap = self.create_circular_photo(photo_path, photo_size)
        photo_label.setPixmap(final_pixmap)
        
        layout.addWidget(photo_label)

        # 2. Text Details
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        text_layout.setAlignment(Qt.AlignVCenter)
        
        lbl_driver_title = QLabel("YOUR DRIVER")
        lbl_driver_title.setStyleSheet("color: #8E8E93; font-size: 16px; font-weight: bold; letter-spacing: 1px;")
        
        lbl_name = QLabel(name.upper())
        lbl_name.setStyleSheet("color: white; font-size: 32px; font-weight: bold;")
        
        lbl_number = QLabel(f"ph : {number}")
        lbl_number.setStyleSheet("color: #34C759; font-size: 28px; font-weight: bold;")
        
        text_layout.addWidget(lbl_driver_title)
        text_layout.addWidget(lbl_name)
        text_layout.addWidget(lbl_number)
        
        layout.addLayout(text_layout)
        layout.addStretch()

    def create_circular_photo(self, image_path, size):
        """Creates a properly masked circular image with border"""
        target = QPixmap(size, size)
        target.fill(Qt.transparent)
        
        source = QPixmap(image_path)
        if source.isNull():
            print(f"❌ Failed to load driver image: {image_path}")
            # Fallback: Gray circle with text
            painter = QPainter(target)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#555555")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
            painter.setPen(Qt.white)
            painter.drawText(target.rect(), Qt.AlignCenter, "NO\nPHOTO")
            painter.end()
            return target
        
        # Scale source to cover the circle (aspect fill)
        scaled_source = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create circle clipping path
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Draw image centered
        x = (size - scaled_source.width()) // 2
        y = (size - scaled_source.height()) // 2
        painter.drawPixmap(x, y, scaled_source)
        
        # Draw border ring
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#FFFFFF"), 3)) # 3px white border
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 1, size-2, size-2)
        
        painter.end()
        return target

class AdsDisplayWidget(QWidget):
    content_changed = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.current_index = 0
        self.ad_duration = 10000   # 10 seconds per ad
        self.map_duration = 30000  # 30 seconds for map
        
        # Define base paths
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_path = os.path.join(self.base_path, 'assets')
        
        # Import Map here to avoid circular error
        from .map_display import MapDisplayWidget
        self.map_widget = MapDisplayWidget()
        
        self.setup_ui()
        self.load_content()
        
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_content)
        self.start_rotation()
    
    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 5)
        
        # Main Container
        main_container = QFrame()
        main_container.setStyleSheet("""
            QFrame {
                background-color: #1C1C1E;
                border-radius: 10px;
                border: 1px solid #333;
            }
        """)
        main_container_layout = QVBoxLayout(main_container)
        main_container_layout.setContentsMargins(5, 5, 5, 5)
        
        self.display_stack = QStackedWidget()
        
        # --- Load Assets ---
        gif_paths = [
            os.path.join(self.assets_path, 'ad_1.gif'),
            os.path.join(self.assets_path, 'ad_2.gif'),
            os.path.join(self.assets_path, 'ad_3.gif'),
            os.path.join(self.assets_path, 'ad_4.gif')
        ]
        
        # Smart Driver Photo Finder
        driver_photo_path = ""
        possible_names = ['driver_pic', 'driver_photo', 'driver']
        extensions = ['.jpg', '.jpeg', '.png', '.avif']
        
        print("🔍 Searching for driver photo...")
        for name in possible_names:
            for ext in extensions:
                # Check in assets/
                p = os.path.join(self.assets_path, name + ext)
                if os.path.exists(p):
                    driver_photo_path = p
                    break
            if driver_photo_path: break
            
        if driver_photo_path:
            print(f"✅ Found driver photo: {driver_photo_path}")
        else:
            print("⚠️ Driver photo NOT found in assets folder. Using default fallback.")
            driver_photo_path = os.path.join(self.assets_path, 'driver_pic.jpg') # Fallback path

        # --- Create Views ---
        self.ad_gif_1 = self.create_image_ad(gif_paths[0])
        self.ad_gif_2 = self.create_image_ad(gif_paths[1])
        self.ad_gif_3 = self.create_image_ad(gif_paths[2])
        self.ad_gif_4 = self.create_image_ad(gif_paths[3])
        
        # Driver Info + Map View
        map_view_container = QWidget()
        map_view_layout = QVBoxLayout(map_view_container)
        map_view_layout.setContentsMargins(0, 0, 0, 0)
        map_view_layout.setSpacing(0)
        
        self.driver_header = DriverInfoWidget(
            name="CHANDU",
            number="20XXXXX300",
            photo_path=driver_photo_path
        )
        
        map_view_layout.addWidget(self.driver_header)
        map_view_layout.addWidget(self.map_widget, 1) # 1 = Stretch map to fill space
        
        # Add to Stack
        self.display_stack.addWidget(self.ad_gif_1)       # 0
        self.display_stack.addWidget(map_view_container)  # 1 (Map + Driver)
        self.display_stack.addWidget(self.ad_gif_2)       # 2
        self.display_stack.addWidget(self.ad_gif_3)       # 3
        self.display_stack.addWidget(self.ad_gif_4)       # 4
        
        main_container_layout.addWidget(self.display_stack)
        layout.addWidget(main_container)
        self.setLayout(layout)

    def create_image_ad(self, image_path):
        frame = QFrame()
        frame.setStyleSheet("background-color: #000000; border-radius: 10px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        if os.path.exists(image_path):
            if image_path.lower().endswith('.gif'):
                movie = QMovie(image_path)
                lbl.setMovie(movie)
                movie.start()
                lbl.setScaledContents(True) 
            else:
                pixmap = QPixmap(image_path)
                lbl.setPixmap(pixmap)
                lbl.setScaledContents(True)
        else:
            lbl.setText(f"Ad Missing:\n{os.path.basename(image_path)}")
            lbl.setStyleSheet("color: #8E8E93; font-size: 18px; font-weight: bold;")
        
        layout.addWidget(lbl)
        return frame

    def load_content(self):
        self.content_items = [
            {"type": "ad_1",          "dur": self.ad_duration},
            {"type": "driver_map",    "dur": self.map_duration},
            {"type": "ad_2",          "dur": self.ad_duration},
            {"type": "ad_3",          "dur": self.ad_duration},
            {"type": "ad_4",          "dur": self.ad_duration}
        ]

    def rotate_content(self):
        self.current_index = (self.current_index + 1) % len(self.content_items)
        self.display_stack.setCurrentIndex(self.current_index)
        self.rotation_timer.setInterval(self.content_items[self.current_index]["dur"])

    def start_rotation(self):
        self.rotation_timer.start(self.content_items[0]["dur"])
        
    def stop_rotation(self):
        self.rotation_timer.stop()

    def set_sos_mode(self, enabled):
        """Force map display and hide driver info during SOS"""
        if enabled:
            self.stop_rotation()
            # Force switch to Map View Container (Index 1)
            self.display_stack.setCurrentIndex(1)
            # Hide Driver Header to make map full screen
            self.driver_header.hide()
        else:
            # Restore normal state
            self.driver_header.show()
            self.start_rotation()

"""
Sharing Mode UI - Ricky Theme
Individual seat cards - Screen Fit / Auto-Scaling
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSlot

# Theme Constants
CARD_OFF = "#1C1C1E"
CARD_ON = "#142615"  # Very dark green
TEXT_WHITE = "#FFFFFF"
ACCENT_GOLD = "#FFD700"
TEXT_SUB = "#8E8E93"

class PassengerCard(QFrame):
    def __init__(self, passenger_id):
        super().__init__()
        self.passenger_id = passenger_id
        self.setup_ui()
    
    def setup_ui(self):
        # REMOVED fixed size to allow screen fitting
        # self.setFixedSize(200, 180) 
        
        # Set size policy to Expanding so it fills available space
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set a minimum size to prevent crushing on very small screens
        self.setMinimumWidth(220)
        self.setMinimumHeight(180)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. Header (Seat Number) - Increased Size
        self.header_lbl = QLabel(f"SEAT {self.passenger_id}")
        self.header_lbl.setAlignment(Qt.AlignCenter)
        self.header_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px; font-weight: bold; background: transparent;")
        
        # 2. Fare Display - Large & Clear
        self.fare_lbl = QLabel("₹0")
        self.fare_lbl.setAlignment(Qt.AlignCenter)
        self.fare_lbl.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 56px; font-weight: bold; background: transparent;")
        
        # 3. Stats - Increased Size
        self.stats_lbl = QLabel("0.0 km")
        self.stats_lbl.setAlignment(Qt.AlignCenter)
        self.stats_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 20px; background: transparent;")
        
        # 4. Status Badge - Wider & Taller
        self.status_lbl = QLabel("EMPTY")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setFixedHeight(34)
        
        # Status container (to keep badge centered but allow it to stretch horizontally if needed)
        status_container = QHBoxLayout()
        status_container.setContentsMargins(20, 0, 20, 0)
        status_container.addWidget(self.status_lbl)
        
        # Add to layout with stretch factors to balance vertical space
        layout.addWidget(self.header_lbl, 1)
        layout.addWidget(self.fare_lbl, 2)
        layout.addWidget(self.stats_lbl, 1)
        layout.addSpacing(10)
        layout.addLayout(status_container, 1)
        
        self.setLayout(layout)
        
        # Apply initial styles
        self.set_offboard_style()
    
    def set_offboard_style(self):
        """Set style for empty seat"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_OFF};
                border-radius: 20px;
                border: 2px solid #333;
            }}
        """)
        self.status_lbl.setStyleSheet("background-color: #3A3A3C; color: white; border-radius: 12px; font-size: 16px; font-weight: bold;")
        self.status_lbl.setText("EMPTY")
        self.fare_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 56px; font-weight: bold; background: transparent;")

    def set_onboard_style(self):
        """Set style for occupied seat"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_ON};
                border-radius: 20px;
                border: 3px solid #34C759;
            }}
        """)
        self.status_lbl.setStyleSheet("background-color: #34C759; color: white; border-radius: 12px; font-size: 16px; font-weight: bold;")
        self.status_lbl.setText("OCCUPIED")
        self.fare_lbl.setStyleSheet(f"color: {ACCENT_GOLD}; font-size: 64px; font-weight: bold; background: transparent;")

    def update_data(self, fare, onboard):
        self.fare_lbl.setText(f"₹{fare:.0f}")
        if onboard:
            self.set_onboard_style()
        else:
            self.set_offboard_style()

    def update_live_info(self, distance):
        self.stats_lbl.setText(f"{distance:.1f} km")

class SharingModeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.setup_ui()
    
    def setup_ui(self):
        # Use QHBoxLayout to arrange columns side-by-side
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 5, 10, 5) # Minimal margins to maximize screen usage
        
        for i in range(3):
            card = PassengerCard(i + 1)
            self.cards.append(card)
            layout.addWidget(card)
        
        # Main layout container
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        
        # Info footer
        self.info_lbl = QLabel("Multi-Passenger Tracking Active")
        self.info_lbl.setAlignment(Qt.AlignCenter)
        self.info_lbl.setStyleSheet("color: #8E8E93; font-size: 16px; margin-top: 5px; font-weight: bold;")
        main_layout.addWidget(self.info_lbl)
        
        self.setLayout(main_layout)

    def update_passenger(self, pid, onboard):
        if 0 <= pid < 3:
            try:
                curr_fare = float(self.cards[pid].fare_lbl.text().replace('₹',''))
            except:
                curr_fare = 0.0
            self.cards[pid].update_data(curr_fare, onboard)

    def update_fare(self, pid, fare):
        if 0 <= pid < 3:
            self.cards[pid].update_data(fare, True)

    def update_total_info(self, total_dist, wait_time):
        self.info_lbl.setText(f"TRIP: {total_dist:.1f} km • WAITING: {wait_time} min")

    def update_card_live_data(self, pid, distance):
        if 0 <= pid < 3:
            self.cards[pid].update_live_info(distance)
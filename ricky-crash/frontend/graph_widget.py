"""
Graph Widget - Draws live sensor data (G-Force) with Red Spikes
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtCore import Qt
from collections import deque

class SensorGraphWidget(QWidget):
    def __init__(self, max_points=100):
        super().__init__()
        self.max_points = max_points
        # Initialize with 1.0G (standard gravity)
        self.data = deque([1.0] * max_points, maxlen=max_points)
        self.setMinimumHeight(120)
        self.setStyleSheet("background-color: #000; border-top: 1px solid #333;")

    def update_value(self, value):
        self.data.append(value)
        self.update() # Trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 1. Draw Background
        painter.fillRect(0, 0, w, h, QColor("#000000"))
        
        # 2. Draw Baseline (1.0G)
        mid_y = int(h * 0.75) # 1G line near bottom
        pen_grid = QPen(QColor("#333"))
        pen_grid.setStyle(Qt.DotLine)
        painter.setPen(pen_grid)
        painter.drawLine(0, mid_y, w, mid_y)
        
        # 3. Draw Labels
        painter.setPen(QColor("#666"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(5, 15, "LIVE G-SENSOR")
        painter.drawText(w - 35, mid_y - 5, "1.0 G")

        # 4. Draw Graph Line
        # Y-Axis Scale: 0G (bottom) to 4G (top)
        scale_y = h / 4.0  
        step_x = w / (self.max_points - 1)
        
        # Determine Color (Red if crash spike > 2.5G, else Green)
        current_g = self.data[-1]
        if current_g > 2.5:
            line_color = QColor("#FF0000") # Red Spike
            line_width = 3
        else:
            line_color = QColor("#00FF00") # Normal Green
            line_width = 2

        path_pen = QPen(line_color)
        path_pen.setWidth(line_width)
        painter.setPen(path_pen)
        
        # Draw connected lines
        for i in range(1, len(self.data)):
            x1 = int((i - 1) * step_x)
            x2 = int(i * step_x)
            
            # Invert Y because 0 is top
            val1 = min(self.data[i-1], 4.0)
            val2 = min(self.data[i], 4.0)
            
            y1 = int(h - (val1 * scale_y))
            y2 = int(h - (val2 * scale_y))
            
            painter.drawLine(x1, y1, x2, y2)

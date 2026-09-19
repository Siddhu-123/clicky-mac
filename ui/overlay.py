"""
Transparent full-screen overlay for macOS.
Draws the blue buddy triangle, smooth bezier arc flight, pulsing highlight ring,
and whiteboard annotations ([ARROW], [CIRCLE], [LABEL], [UNDERLINE]).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from config import cfg


@dataclass
class WhiteboardAnnotation:
    kind: str  # "arrow", "circle", "underline", "label"
    created_at: float
    x1: float
    y1: float
    x2: float = 0.0
    y2: float = 0.0
    radius: float = 20.0
    text: str = ""
    duration: float = 4.0


class OverlayWindow(QWidget):
    """
    Transparent, click-through full-screen canvas covering macOS desktop.
    Handles cursor buddy tracking, bezier pointing flight, and annotations.
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Match entire desktop geometry across all screens
        self._update_geometry()

        # Buddy position state
        self.buddy_x: float = 100.0
        self.buddy_y: float = 100.0
        self.resting_offset_x = 35.0
        self.resting_offset_y = 25.0

        # Animation states: "idle", "flying_to_target", "dwelling", "flying_home"
        self.anim_state = "idle"
        self.anim_start_time: float = 0.0
        self.anim_duration: float = 0.6  # seconds for flight

        # Flight endpoints and control points
        self.start_p: QPointF = QPointF(0, 0)
        self.ctrl_p: QPointF = QPointF(0, 0)
        self.target_p: QPointF = QPointF(0, 0)
        self.target_label: str = ""
        self.dwell_until: float = 0.0

        # Whiteboard annotations
        self.annotations: List[WhiteboardAnnotation] = []

        # 60 FPS animation timer (only runs when actively animating)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def _update_geometry(self):
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def _update_geometry_for_point(self, point: QPoint):
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def point_at(self, target_x: float, target_y: float, label: str = "", dwell_ms: int = 3500):
        """Initiates bezier arc flight to target logical point."""
        target_pt = QPoint(int(target_x), int(target_y))
        self._update_geometry_for_point(target_pt)

        cursor_global = QCursor.pos()
        start_local = self.mapFromGlobal(cursor_global)
        target_local = self.mapFromGlobal(target_pt)

        self.start_p = QPointF(start_local.x(), start_local.y())
        self.target_p = QPointF(target_local.x(), target_local.y())
        self.target_label = label
        self.dwell_duration = dwell_ms / 1000.0

        # Compute cubic control point for an arched flight path
        mid_x = (start_local.x() + target_local.x()) / 2.0
        mid_y = (start_local.y() + target_local.y()) / 2.0
        dx = target_local.x() - start_local.x()
        dy = target_local.y() - start_local.y()
        dist = math.hypot(dx, dy)
        arch = min(dist * 0.25, 120.0)
        self.ctrl_p = QPointF(mid_x, mid_y - arch)

        self.buddy_x = self.start_p.x()
        self.buddy_y = self.start_p.y()

        self.anim_duration = max(0.4, min(1.2, dist / 800.0)) / cfg.cursor_speed
        self.anim_start_time = time.time()
        self.anim_state = "flying_to_target"

        if not self.timer.isActive():
            self.timer.start(16)
        self.show()

    def add_arrow(self, x1: float, y1: float, x2: float, y2: float, duration: float = 4.0):
        self._update_geometry_for_point(QPoint(int(x1), int(y1)))
        p1 = self.mapFromGlobal(QPoint(int(x1), int(y1)))
        p2 = self.mapFromGlobal(QPoint(int(x2), int(y2)))
        self.annotations.append(WhiteboardAnnotation(
            kind="arrow", created_at=time.time(), x1=p1.x(), y1=p1.y(), x2=p2.x(), y2=p2.y(), duration=duration
        ))
        if not self.timer.isActive():
            self.timer.start(16)
        self.show()

    def add_circle(self, x: float, y: float, radius: float = 30.0, text: str = "", duration: float = 4.0):
        self._update_geometry_for_point(QPoint(int(x), int(y)))
        p = self.mapFromGlobal(QPoint(int(x), int(y)))
        self.annotations.append(WhiteboardAnnotation(
            kind="circle", created_at=time.time(), x1=p.x(), y1=p.y(), radius=radius, text=text, duration=duration
        ))
        if not self.timer.isActive():
            self.timer.start(16)
        self.show()

    def add_label(self, x: float, y: float, text: str, duration: float = 4.0):
        self._update_geometry_for_point(QPoint(int(x), int(y)))
        p = self.mapFromGlobal(QPoint(int(x), int(y)))
        self.annotations.append(WhiteboardAnnotation(
            kind="label", created_at=time.time(), x1=p.x(), y1=p.y(), text=text, duration=duration
        ))
        if not self.timer.isActive():
            self.timer.start(16)
        self.show()

    def clear_annotations(self):
        self.annotations.clear()
        if self.anim_state == "idle":
            self.timer.stop()
            self.hide()
        self.update()

    def _bezier_point(self, p0: QPointF, p1: QPointF, p2: QPointF, t: float) -> QPointF:
        """Quadratic bezier interpolation with smooth ease-in-out."""
        ease_t = t * t * (3 - 2 * t)
        u = 1 - ease_t
        x = u * u * p0.x() + 2 * u * ease_t * p1.x() + ease_t * ease_t * p2.x()
        y = u * u * p0.y() + 2 * u * ease_t * p1.y() + ease_t * ease_t * p2.y()
        return QPointF(x, y)

    def _on_tick(self):
        now = time.time()

        if self.anim_state == "flying_to_target":
            elapsed = now - self.anim_start_time
            t = min(1.0, elapsed / self.anim_duration)
            pt = self._bezier_point(self.start_p, self.ctrl_p, self.target_p, t)
            self.buddy_x, self.buddy_y = pt.x(), pt.y()

            if t >= 1.0:
                self.anim_state = "dwelling"
                self.dwell_until = now + self.dwell_duration

        elif self.anim_state == "dwelling":
            self.buddy_x, self.buddy_y = self.target_p.x(), self.target_p.y()
            if now >= self.dwell_until:
                # Dwell complete, transition to idle
                self.anim_state = "idle"
                self.target_label = ""
                if not self.annotations:
                    self.timer.stop()
                    self.hide()
                    return

        # Prune expired annotations
        self.annotations = [a for a in self.annotations if now - a.created_at < a.duration]

        if self.anim_state == "idle" and not self.annotations:
            self.timer.stop()
            self.hide()
            return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        now = time.time()

        # ── Draw Whiteboard Annotations ──
        for ann in self.annotations:
            age = now - ann.created_at
            alpha = max(0.0, min(1.0, (ann.duration - age) / 0.8))  # fade out in last 0.8s
            pen_color = QColor(245, 158, 11, int(alpha * 220))  # Amber/gold
            painter.setPen(QPen(pen_color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if ann.kind == "arrow":
                painter.drawLine(QPointF(ann.x1, ann.y1), QPointF(ann.x2, ann.y2))
                # Arrowhead
                angle = math.atan2(ann.y2 - ann.y1, ann.x2 - ann.x1)
                head_len = 14
                p_left = QPointF(
                    ann.x2 - head_len * math.cos(angle - math.pi / 6),
                    ann.y2 - head_len * math.sin(angle - math.pi / 6),
                )
                p_right = QPointF(
                    ann.x2 - head_len * math.cos(angle + math.pi / 6),
                    ann.y2 - head_len * math.sin(angle + math.pi / 6),
                )
                painter.drawLine(QPointF(ann.x2, ann.y2), p_left)
                painter.drawLine(QPointF(ann.x2, ann.y2), p_right)

            elif ann.kind == "circle":
                painter.drawEllipse(QPointF(ann.x1, ann.y1), ann.radius, ann.radius)
                if ann.text:
                    painter.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
                    painter.setPen(QPen(QColor(255, 255, 255, int(alpha * 255))))
                    painter.drawText(
                        QRectF(ann.x1 - 100, ann.y1 + ann.radius + 4, 200, 30),
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                        ann.text,
                    )

            elif ann.kind == "label":
                painter.setFont(QFont("SF Pro Text", 12, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(255, 255, 255, int(alpha * 255))))
                painter.drawText(
                    QRectF(ann.x1, ann.y1 - 25, 300, 30),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                    ann.text,
                )

        # ── Draw Pulsing Highlight Ring during Dwell ──
        if self.anim_state == "dwelling":
            pulse = (math.sin(now * 8) + 1) / 2.0  # 0 to 1
            ring_radius = 24 + pulse * 8
            ring_alpha = int(140 + pulse * 100)
            painter.setPen(QPen(QColor(59, 130, 246, ring_alpha), 3))
            painter.setBrush(QBrush(QColor(59, 130, 246, 35)))
            painter.drawEllipse(self.target_p, ring_radius, ring_radius)

            # Target speech label bubble
            if self.target_label:
                bubble_rect = QRectF(self.target_p.x() + 30, self.target_p.y() - 35, 180, 34)
                painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
                painter.setBrush(QBrush(QColor(15, 23, 42, 230)))  # Slate dark
                painter.drawRoundedRect(bubble_rect, 8, 8)

                painter.setFont(QFont("SF Pro Text", 11, QFont.Weight.Medium))
                painter.setPen(QPen(QColor(248, 250, 252, 240)))
                painter.drawText(
                    bubble_rect.adjusted(8, 0, -8, 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    self.target_label,
                )

        # ── Draw Clicky Blue Buddy Triangle (Only during active pointing flight) ──
        if self.anim_state != "idle":
            bx = self.buddy_x
            by = self.buddy_y

            painter.save()
            painter.translate(bx, by)

            # Soft drop shadow
            shadow_path = QPainterPath()
            shadow_path.moveTo(2, 2)
            shadow_path.lineTo(18, 16)
            shadow_path.lineTo(6, 20)
            shadow_path.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 70)))
            painter.drawPath(shadow_path)

            # Vibrant Clicky Blue Arrow / Triangle
            buddy_path = QPainterPath()
            buddy_path.moveTo(0, 0)
            buddy_path.lineTo(16, 14)
            buddy_path.lineTo(4, 18)
            buddy_path.closeSubpath()

            # Primary blue fill + white border
            painter.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
            painter.setBrush(QBrush(QColor(37, 99, 235)))  # Royal blue
            painter.drawPath(buddy_path)

            # Small cyan inner highlight dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(96, 165, 250)))
            painter.drawEllipse(QPointF(6, 10), 2.5, 2.5)

            painter.restore()

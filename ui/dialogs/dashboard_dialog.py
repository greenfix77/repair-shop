from typing import Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QWidget, QLabel, QPushButton, QFrame,
                               QScrollArea, QSizePolicy,
                               QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor

from services.dashboard_service import DashboardService


class DashboardDialog(QDialog):
    """دیالوگ داشبورد - فقط اسکلت رابط کاربری (فاز ۱).

    این کلاس هیچ منطق تجاری ندارد و فقط چیدمان را برای فازهای آینده فراهم می‌کند.
    """

    def __init__(self, dashboard_service: DashboardService, parent=None):
        super().__init__(parent)
        self._dashboard_service = dashboard_service
        self._snapshot = self._dashboard_service.get_snapshot()
        self.setWindowTitle("داشبورد")
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowSystemMenuHint
        )
        self.setModal(True)
        self.setMinimumSize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        page = QWidget()
        page.setLayoutDirection(Qt.RightToLeft)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        page_layout.addWidget(self._create_header())
        page_layout.addWidget(self._create_status_bar())
        page_layout.addWidget(self._create_cards())
        page_layout.addWidget(self._create_charts())
        page_layout.addWidget(self._create_information_panels())
        page_layout.addWidget(self._create_quick_actions())

        page_layout.addStretch()

        scroll.setWidget(page)
        outer.addWidget(scroll)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(10, 6, 10, 10)
        close_btn = QPushButton("بستن")
        close_btn.setStyleSheet(
            "background-color: #607D8B; color: white; padding: 8px 14px; "
            "border: none; border-radius: 6px; font-size: 10pt;"
        )
        close_btn.clicked.connect(self.accept)
        bottom_bar.addStretch()
        bottom_bar.addWidget(close_btn)
        outer.addLayout(bottom_bar)

        self.setLayout(outer)

    def _panel(self, title: str) -> QFrame:
        """یک قاب ساده برای بخش‌های داشبورد."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: white; "
            "border: 1px solid #E5E7EB; "
            "border-radius: 8px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(8)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #1F2937;"
            " background: transparent; border: none; padding: 0;"
        )
        v.addWidget(title_label)
        frame.setLayout(v)
        return frame

    def _create_header(self) -> QFrame:
        """هدر داشبورد شامل عنوان، تاریخ و دکمه بروزرسانی غیرفعال."""
        header = QFrame()
        header.setStyleSheet(
            "background-color: #F9FAFB; "
            "border: 1px solid #E5E7EB; "
            "border-radius: 8px; "
            "padding: 8px;"
        )
        h = QHBoxLayout()
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(16)

        title = QLabel("📊 داشبورد")
        title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title.setStyleSheet(
            "font-size: 13pt; font-weight: bold; color: #1F2937;"
            " background: transparent; border: none;"
        )
        h.addWidget(title)

        h.addStretch()

        date_placeholder = QLabel("📅 ۱۴۰۳/--/--")
        date_placeholder.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        date_placeholder.setStyleSheet(
            "color: #6B7280; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(date_placeholder)

        update_placeholder = QLabel("🕒 آخرین بروزرسانی: --")
        update_placeholder.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        update_placeholder.setStyleSheet(
            "color: #6B7280; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(update_placeholder)

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 6px 12px;"
            " border: none; border-radius: 5px; font-size: 10pt;"
        )
        refresh_btn.setEnabled(False)
        h.addWidget(refresh_btn)

        header.setLayout(h)
        return header

    def _create_status_bar(self) -> QFrame:
        """نوار افقی وضعیت سیستم - فقط نمایشی بدون عملکرد."""
        bar = QFrame()
        bar.setStyleSheet(
            "background-color: #EEF2FF; "
            "border: 1px solid #C7D2FE; "
            "border-left: 3px solid #4F46E5; "
            "border-radius: 8px; "
            "padding: 6px;"
        )
        h = QHBoxLayout()
        h.setContentsMargins(12, 4, 10, 4)
        h.setSpacing(10)
        label = QLabel("سبد سیستم")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(
            "font-size: 10pt; font-weight: bold; color: #3730A3;"
            " background: transparent; border: none;"
        )
        h.addWidget(label)
        h.addStretch()
        status = QLabel("🟢 همه چیز عادی است")
        status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status.setStyleSheet(
            "color: #065F46; font-weight: normal; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(status)
        bar.setLayout(h)
        return bar

    def _create_cards(self) -> QFrame:
        """شش کارت KPI فقط با متن جای‌نگهدار."""
        container = self._panel("کارت‌های شاخص کلیدی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        titles = [
            "درآمد امروز",
            "درآمد ماه",
            "تعمیرات فعال",
            "آماده تحویل",
            "وظایف امروز",
            "مشتریان",
        ]
        icons = ["💵", "💰", "🔧", "📦", "📝", "👤"]
        accents = [
            "#16A34A",  # Green Accent - درآمد امروز
            "#059669",  # Emerald Accent - درآمد ماه
            "#2563EB",  # Blue Accent - تعمیرات فعال
            "#0891B2",  # Cyan Accent - آماده تحویل
            "#EA580C",  # Orange Accent - وظایف امروز
            "#7C3AED",  # Purple Accent - مشتریان
        ]

        for i, t in enumerate(titles):
            row, col = divmod(i, 3)
            if i == 0:
                inc = self._snapshot.today_income
                val = f"{inc:,} تومان" if inc is not None else None
                hint = None
            elif i == 1:
                inc = self._snapshot.monthly_income
                val = f"{inc:,} تومان" if inc is not None else None
                hint = None
            elif i == 2:
                val = str(self._snapshot.active_repairs) if self._snapshot.active_repairs is not None else None
                hint = None
            elif i == 3:
                val = str(self._snapshot.ready_repairs) if self._snapshot.ready_repairs is not None else None
                hint = None
            elif i == 4:
                val = str(self._snapshot.today_todos) if self._snapshot.today_todos is not None else None
                hint = None
            else:
                val = str(self._snapshot.customer_count) if self._snapshot.customer_count is not None else None
                hint = None
            grid.addWidget(self._kpi_card(t, icons[i], accents[i], val, hint), row, col)

        container.layout().addLayout(grid)
        return container

    def _kpi_card(self, title: str, icon: str = "•", accent: str = "#6B7280",
                  value: Optional[str] = None, hint: Optional[str] = None) -> QFrame:
        """یک کارت KPI با آیکون، عنوان، مقدار بزرگ و زیرنویس.

        accent رنگ ملایم دسته‌بندی کارت است (نوار بالایی، دایره آیکون و سایه).
        """
        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        card.setAttribute(Qt.WA_Hover, True)

        rest_bg = "#FFFFFF"
        hover_bg = "#FFFFFF"
        border_base = "#E5E7EB"
        accent_soft = accent + "22"  # ~13% alpha hex suffix (RRGGBBAA)

        card.setStyleSheet(
            f"QFrame {{"
            f" background-color: {rest_bg};"
            f" border: 1px solid {border_base};"
            f" border-top: 3px solid {accent};"
            f" border-radius: 10px;"
            f" padding: 10px;"
            f"}}"
            f"QFrame:hover {{"
            f" background-color: {hover_bg};"
            f" border: 1px solid {accent};"
            f" border-top: 3px solid {accent};"
            f"}}"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(132)

        # Soft shadow effect (subtle). Hover increases blur radius via a
        # lightweight QPropertyAnimation (no helper classes, no new widgets).
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(8)
        shadow_color = QColor(accent)
        shadow_color.setAlpha(35)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        card._kpi_shadow = shadow  # noqa: SLF001  (keep ref to avoid GC)
        card._kpi_blur_rest = 8
        card._kpi_blur_hover = 18

        def _animate_blur(target_radius: int) -> None:
            anim = QPropertyAnimation(shadow, b"blurRadius", card)
            anim.setDuration(140)
            anim.setStartValue(shadow.blurRadius())
            anim.setEndValue(target_radius)
            anim.setEasingCurve(QEasingCurve.OutQuad)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
            card._kpi_anim = anim  # noqa: SLF001  (keep ref alive mid-flight)

        card.enterEvent = lambda e: _animate_blur(card._kpi_blur_hover)
        card.leaveEvent = lambda e: _animate_blur(card._kpi_blur_rest)

        outer = QVBoxLayout()
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setStyleSheet(
            "font-size: 10pt; color: #374151;"
            " background: transparent; border: none;"
        )
        top_row.addWidget(title_label, 1)

        top_row.addStretch(0)

        icon_box = QLabel(icon)
        icon_box.setFixedSize(48, 48)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(
            f"background-color: {accent_soft};"
            f" border: 1px solid {accent};"
            f" border-radius: 24px;"
            f" font-size: 18pt;"
            f" color: {accent};"
        )
        top_row.addWidget(icon_box, 0)

        outer.addLayout(top_row)

        value_label = QLabel(value if value is not None else "--")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        value_label.setStyleSheet(
            "font-size: 24pt; font-weight: bold; color: #1F2937;"
            " background: transparent; border: none;"
        )
        outer.addWidget(value_label)

        hint = QLabel(hint if hint is not None else "داده‌ای موجود نیست")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hint.setStyleSheet(
            "color: #9CA3AF; font-size: 9pt; font-weight: normal;"
            " background: transparent; border: none;"
        )
        outer.addWidget(hint)
        outer.addStretch()

        card.setLayout(outer)
        return card

    def _create_charts(self) -> QFrame:
        """سه نمودار جای‌نگهدار - هیچ نموداری رسم نمی‌شود."""
        container = self._panel("نمودارها")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        titles = ["روند درآمد", "وضعیت تعمیرات", "فعالیت ماهانه"]
        for i, t in enumerate(titles):
            row, col = divmod(i, 3)
            grid.addWidget(self._chart_placeholder(t), row, col)

        container.layout().addLayout(grid)
        return container

    def _chart_placeholder(self, title: str) -> QFrame:
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        box.setMinimumHeight(140)
        box.setStyleSheet(
            "background-color: #FAFBFC; "
            "border: 1px dashed #C7D2FE; "
            "border-top: 3px dashed #818CF8; "
            "border-radius: 10px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(6)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #374151;"
            " background: transparent; border: none;"
        )
        v.addWidget(t)

        icon = QLabel("📊")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "font-size: 22pt; color: #C7D2FE;"
            " background: transparent; border: none;"
        )
        v.addWidget(icon)

        hint = QLabel("نمودار در فاز بعدی اضافه می‌شود.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "color: #6B7280; font-size: 9pt; font-weight: normal;"
            " background: transparent; border: none;"
        )
        v.addWidget(hint)
        v.addStretch()

        box.setLayout(v)
        return box

    def _create_information_panels(self) -> QFrame:
        """دو پنل اطلاعاتی: فعالیت‌ها و هشدارها."""
        container = self._panel("پنل‌های اطلاعاتی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._info_panel("آخرین فعالیت‌ها", "🕘"), 0, 0)
        grid.addWidget(self._info_panel("هشدارها", "⚠️"), 0, 1)

        container.layout().addLayout(grid)
        return container

    def _info_panel(self, title: str, icon: str) -> QFrame:
        panel = QFrame()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        panel.setMinimumHeight(120)
        panel.setStyleSheet(
            "background-color: #FFFFFF; "
            "border: 1px solid #E5E7EB; "
            "border-radius: 10px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(
            "font-size: 13pt; color: #4B5563;"
            " background: transparent; border: none;"
        )
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(26, 26)
        header_row.addWidget(icon_label)

        t = QLabel(title)
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        t.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #1F2937;"
            " background: transparent; border: none;"
        )
        header_row.addWidget(t)

        header_row.addStretch()
        v.addLayout(header_row)

        placeholder = QLabel("محتوایی برای نمایش وجود ندارد.")
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            "color: #9CA3AF; font-size: 10pt; font-weight: normal;"
            " background: transparent; border: none;"
        )
        v.addWidget(placeholder)
        v.addStretch()

        panel.setLayout(v)
        return panel

    def _create_quick_actions(self) -> QFrame:
        """دکمه‌های میان‌بر غیرفعال - هیچ عملی انجام نمی‌دهند."""
        container = self._panel("اقدامات سریع")
        h = QHBoxLayout()
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(10)
        h.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        actions = [
            ("➕ ثبت تعمیر", "#4CAF50"),
            ("👤 ثبت مشتری", "#2196F3"),
            ("📝 ثبت وظیفه", "#FF9800"),
            ("⚙️ تنظیمات", "#607D8B"),
            ("💾 Backup", "#9C27B0"),
        ]
        for label, color in actions:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{"
                f" background-color: {color};"
                f" color: white;"
                f" padding: 8px 14px;"
                f" border: none;"
                f" border-radius: 8px;"
                f" font-size: 10pt;"
                f"}}"
                f"QPushButton:disabled {{"
                f" background-color: {color};"
                f" color: rgba(255,255,255,0.55);"
                f"}}"
                f"QPushButton:disabled:hover {{"
                f" background-color: {color};"
                f"}}"
            )
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            btn.setEnabled(False)
            h.addWidget(btn)
        h.addStretch()

        container.layout().addLayout(h)
        return container

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QWidget, QLabel, QPushButton, QFrame,
                               QScrollArea)
from PyQt5.QtCore import Qt


class DashboardDialog(QDialog):
    """دیالوگ داشبورد - فقط اسکلت رابط کاربری (فاز ۱).

    این کلاس هیچ منطق تجاری ندارد و فقط چیدمان را برای فازهای آینده فراهم می‌کند.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("داشبورد")
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
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(12)

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
        close_btn.setStyleSheet("background-color: #607D8B; color: white;")
        close_btn.clicked.connect(self.accept)
        bottom_bar.addStretch()
        bottom_bar.addWidget(close_btn)
        outer.addLayout(bottom_bar)

        self.setLayout(outer)

    def _panel(self, title: str) -> QFrame:
        """یک قاب ساده برای بخش‌های داشبورد."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #1F2937;"
        )
        v.addWidget(title_label)
        frame.setLayout(v)
        return frame

    def _create_header(self) -> QFrame:
        """هدر داشبورد شامل عنوان، تاریخ و دکمه بروزرسانی غیرفعال."""
        header = QFrame()
        header.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 10px;"
        )
        h = QHBoxLayout()
        h.setContentsMargins(10, 10, 10, 10)
        h.setSpacing(8)

        title = QLabel("📊 داشبورد")
        title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #1F2937;"
        )
        h.addWidget(title)

        h.addStretch()

        date_placeholder = QLabel("📅 ۱۴۰۳/--/--")
        date_placeholder.setStyleSheet("color: #6B7280;")
        h.addWidget(date_placeholder)

        update_placeholder = QLabel("🕒 آخرین بروزرسانی: --")
        update_placeholder.setStyleSheet("color: #6B7280;")
        h.addWidget(update_placeholder)

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        refresh_btn.setEnabled(False)
        h.addWidget(refresh_btn)

        header.setLayout(h)
        return header

    def _create_status_bar(self) -> QFrame:
        """نوار افقی وضعیت سیستم - فقط نمایشی بدون عملکرد."""
        bar = QFrame()
        bar.setStyleSheet(
            "background-color: #EEF2FF; border: 1px solid #C7D2FE; "
            "border-radius: 5px; padding: 10px;"
        )
        h = QHBoxLayout()
        h.setContentsMargins(10, 8, 10, 8)
        label = QLabel("سبد سیستم")
        label.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #3730A3;"
        )
        h.addWidget(label)
        h.addStretch()
        status = QLabel("🟢 همه چیز عادی است")
        status.setStyleSheet("color: #065F46;")
        h.addWidget(status)
        bar.setLayout(h)
        return bar

    def _create_cards(self) -> QFrame:
        """شش کارت KPI فقط با متن جای‌نگهدار."""
        container = self._panel("کارت‌های شاخص کلیدی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        titles = [
            "درآمد امروز",
            "درآمد ماه",
            "تعمیرات فعال",
            "آماده تحویل",
            "وظایف امروز",
            "مشتریان",
        ]

        for i, t in enumerate(titles):
            row, col = divmod(i, 3)
            grid.addWidget(self._kpi_card(t), row, col)

        container.layout().addLayout(grid)
        return container

    def _kpi_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "background-color: #F9FAFB; border: 1px solid #E5E7EB; "
            "border-radius: 5px; padding: 12px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 10pt; font-weight: bold; color: #374151;"
        )
        v.addWidget(title_label)
        value_label = QLabel("--")
        value_label.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: #1F2937;"
        )
        v.addWidget(value_label)
        hint = QLabel("داده‌ای موجود نیست")
        hint.setStyleSheet("color: #9CA3AF; font-size: 9pt;")
        v.addWidget(hint)
        card.setLayout(v)
        return card

    def _create_charts(self) -> QFrame:
        """سه نمودار جای‌نگهدار - هیچ نموداری رسم نمی‌شود."""
        container = self._panel("نمودارها")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        titles = ["روند درآمد", "وضعیت تعمیرات", "فعالیت ماهانه"]
        for i, t in enumerate(titles):
            row, col = divmod(i, 3)
            grid.addWidget(self._chart_placeholder(t), row, col)

        container.layout().addLayout(grid)
        return container

    def _chart_placeholder(self, title: str) -> QFrame:
        box = QFrame()
        box.setMinimumHeight(160)
        box.setStyleSheet(
            "background-color: #F3F4F6; border: 1px dashed #9CA3AF; "
            "border-radius: 5px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)
        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #374151;"
        )
        v.addWidget(t)
        hint = QLabel("نمودار در فاز بعدی اضافه می‌شود.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #6B7280; font-size: 9pt;")
        v.addWidget(hint)
        v.addStretch()
        box.setLayout(v)
        return box

    def _create_information_panels(self) -> QFrame:
        """دو پنل اطلاعاتی: فعالیت‌ها و هشدارها."""
        container = self._panel("پنل‌های اطلاعاتی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        grid.addWidget(self._info_panel("آخرین فعالیت‌ها"), 0, 0)
        grid.addWidget(self._info_panel("هشدارها"), 0, 1)

        container.layout().addLayout(grid)
        return container

    def _info_panel(self, title: str) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E5E7EB; "
            "border-radius: 5px;"
        )
        panel.setMinimumHeight(150)
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #1F2937;"
        )
        v.addWidget(t)
        placeholder = QLabel("محتوایی برای نمایش وجود ندارد.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #9CA3AF;")
        v.addWidget(placeholder)
        v.addStretch()
        panel.setLayout(v)
        return panel

    def _create_quick_actions(self) -> QFrame:
        """دکمه‌های میان‌بر غیرفعال - هیچ عملی انجام نمی‌دهند."""
        container = self._panel("اقدامات سریع")
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

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
                f"background-color: {color}; color: white; padding: 6px 12px;"
            )
            btn.setEnabled(False)
            h.addWidget(btn)
        h.addStretch()

        container.layout().addLayout(h)
        return container

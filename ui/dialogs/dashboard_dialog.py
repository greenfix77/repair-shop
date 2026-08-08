from datetime import datetime
from typing import Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QWidget, QLabel, QPushButton, QFrame,
                               QScrollArea, QSizePolicy,
                               QGraphicsDropShadowEffect, QToolTip)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QTextOption

from core.status import STATUS_COLORS
from services.dashboard_service import DashboardService
from services.date_service import today_persian


_HINT_NO_DATA = "داده‌ای موجود نیست"

_PRIORITY_KPI_TITLES = {
    "درآمد امروز",
    "درآمد ماه",
    "سود امروز",
    "سود ماه",
}

# Cards that should render lighter than normal KPI cards.
_MINOR_KPI_TITLES = {
    "مشتریان",
    "حاشیه سود",
}

# Warm professional palette (Phase D2).
_BG = "#F6F3EE"          # page background
_CARD_BG = "#FFFDF8"      # card background (warm off-white)
_BORDER = "#E6DED2"       # card border
_TEXT = "#1F2937"         # primary text
_TEXT_SOFT = "#6B7280"    # secondary text
_HINT = "#9AA0AB"         # hint text

# Accent usage is limited to: top border, icon circle, important values.
# Card backgrounds use the warm off-white; accents do NOT tint the card.
_ACCENT = {
    "income": "#2F7D32",   # deep green  - درآمد
    "profit": "#1E40AF",   # deep blue   - سود
    "tasks": "#B45309",    # warm orange - وظایف / تعمیرات فعال
    "ready": "#0E7490",    # teal        - آماده تحویل
    "customers": "#5B21B6",  # indigo    - مشتریان
    "margin": "#B91C1C",   # strong red  - حاشیه سود
}

# Map each KPI title to its accent category.
_KPI_CATEGORY = {
    "درآمد امروز": "income",
    "درآمد ماه": "income",
    "سود امروز": "profit",
    "سود ماه": "profit",
    "وظایف امروز": "tasks",
    "تعمیرات فعال": "tasks",
    "آماده تحویل": "ready",
    "حاشیه سود": "margin",
    "مشتریان": "customers",
}

# Stronger red accent reserved for the margin card.
_MARGIN_ACCENT = "#B91C1C"


def _fmt_count(value: Optional[int]) -> Optional[str]:
    """Return a localized integer for KPI count cards, or ``None`` if missing."""
    if value is None:
        return None
    return _to_persian_digits(value)


def _money_zero_hint(empty_msg: str, value: Optional[int]) -> str:
    """Return a contextual hint for money KPI cards.

    Avoids the generic "no data" placeholder by explaining the zero state.
    """
    if value is None:
        return _HINT_NO_DATA
    if value == 0:
        return empty_msg
    return "بر اساس پرداخت‌های ثبت‌شده"


def _count_zero_hint(
    empty_msg: str,
    value: Optional[int],
    state_phrase: str,
    unit: str = "مورد",
) -> str:
    """Return a contextual hint for count KPI cards.

    Pluralizes the count into a natural Persian sentence when present.
    Format: "<count> <unit> <state_phrase>"
    """
    if value is None:
        return _HINT_NO_DATA
    if value == 0:
        return empty_msg
    return f"{_to_persian_digits(value)} {unit} {state_phrase}"


def _to_persian_digits(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _to_persian_digit_str(value: str) -> str:
    """Localize Latin digits inside a string to Persian numerals."""
    return value.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


class _BarChartWidget(QWidget):
    """Lightweight bar chart rendered with QPainter (no chart library).

    Accepts ``(label, value, color)`` items and paints vertical bars with a
    compact value label above each bar and the Persian-localized label below
    it. Hovering a bar shows a readable native tooltip with the exact value
    (plus an optional unit). An empty item list renders an honest empty-state
    message instead of any fake data. The widget scales to its container
    width so cards stay responsive and nothing clips horizontally.
    """

    def __init__(self, accent: str, unit: str = "", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._unit = unit
        self._items = []
        self._hover_index = -1
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(120)
        self.setMouseTracking(True)

    def set_data(self, items):
        self._items = list(items or [])
        self._hover_index = -1
        self.update()

    def _compact(self, value) -> str:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "۰"
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:.1f}م"
        if abs(v) >= 1_000:
            return f"{v / 1_000:.0f}هزار"
        return str(int(v))

    def _bar_rects(self):
        """Return ``[(QRectF, label, value, color), ...]`` for current geometry."""
        width = self.width()
        height = self.height()
        if not self._items or width <= 16 or height <= 50:
            return []
        margin_l, margin_r, margin_t, margin_b = 8, 8, 26, 36
        plot_w = width - margin_l - margin_r
        plot_h = height - margin_t - margin_b
        count = len(self._items)
        if plot_w <= 0 or plot_h <= 0 or count == 0:
            return []
        max_val = 1.0
        for _, value, _ in self._items:
            try:
                max_val = max(max_val, abs(float(value)))
            except (TypeError, ValueError):
                pass
        gap = 6
        bar_w = max(6.0, (plot_w - gap * (count - 1)) / count)
        rects = []
        for i, (label, value, color) in enumerate(self._items):
            try:
                v = float(value)
            except (TypeError, ValueError):
                v = 0.0
            bar_h = max(0.0, (abs(v) / max_val) * plot_h)
            x = margin_l + i * (bar_w + gap)
            y = margin_t + plot_h - bar_h
            rects.append((QRectF(x, y, bar_w, bar_h), label, value, color))
        return rects

    def _tooltip_text(self, label, value) -> str:
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = 0.0
        if v == int(v):
            num = f"{int(v):,}"
        else:
            num = f"{v:,.1f}"
        text = f"{_to_persian_digit_str(label)}: {_to_persian_digit_str(num)}"
        if self._unit:
            text += f" {self._unit}"
        return text

    def mouseMoveEvent(self, event):
        hover_index = -1
        rects = self._bar_rects()
        for idx, (rect, _label, _value, _color) in enumerate(rects):
            if rect.contains(QPointF(event.pos())):
                hover_index = idx
                break
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            if hover_index >= 0:
                _rect, label, value, _color = rects[hover_index]
                QToolTip.showText(
                    self.mapToGlobal(event.pos()),
                    self._tooltip_text(label, value),
                    self,
                )
            else:
                QToolTip.hideText()

    def leaveEvent(self, event):
        QToolTip.hideText()
        self._hover_index = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        height = self.height()

        if not self._items:
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            painter.setPen(QColor(_HINT))
            painter.drawText(
                self.rect(), Qt.AlignCenter, "داده کافی برای نمایش نمودار وجود ندارد"
            )
            return

        rects = self._bar_rects()
        if not rects:
            return

        margin_b = 36
        label_font = QFont()
        label_font.setPointSize(10)
        painter.setFont(label_font)

        text_opt = QTextOption(Qt.AlignHCenter)
        text_opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        for rect, label, value, color in rects:
            x, y = rect.x(), rect.y()
            bar_w, bar_h = rect.width(), rect.height()

            painter.setPen(QColor(_BORDER))
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(rect, 2, 2)

            painter.setPen(QColor(_TEXT))
            painter.drawText(
                QRectF(x - 6, y - 18, bar_w + 12, 16),
                _to_persian_digit_str(self._compact(value)),
                text_opt,
            )

            painter.setPen(QColor(_TEXT_SOFT))
            painter.drawText(
                QRectF(x - 6, height - margin_b + 2, bar_w + 12, 32),
                _to_persian_digit_str(label),
                text_opt,
            )


class DashboardDialog(QDialog):
    """دیالوگ داشبورد - فقط اسکلت رابط کاربری (فاز ۱).

    این کلاس هیچ منطق تجاری ندارد و فقط چیدمان را برای فازهای آینده فراهم می‌کند.
    """

    def __init__(self, dashboard_service: DashboardService, parent=None):
        super().__init__(parent)
        self._dashboard_service = dashboard_service
        self._snapshot = self._dashboard_service.get_snapshot()
        self._refresh_time = datetime.now().strftime("%H:%M")
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
        page.setStyleSheet(f"background-color: {_BG};")
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {_BG}; border: none; }}")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        page_layout.addWidget(self._create_header())
        page_layout.addWidget(self._create_status_bar(self._refresh_time))
        page_layout.addWidget(self._create_cards())
        page_layout.addWidget(self._create_charts())
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

    def _persian_date_text(self) -> str:
        """Return the current Persian (Jalali) date for the header, formatted YYYY/MM/DD.

        Delegates to :func:`services.date_service.today_persian` so the dialog
        never owns calendar logic. Digits are localized to Persian numerals
        to match the rest of the dashboard copy.
        """
        return "📅 " + _to_persian_digit_str(today_persian())

    def _refresh(self) -> None:
        """Reload dashboard values without closing or rebuilding the dialog.

        Reuses the existing :class:`DashboardService.get_snapshot` and the
        existing widget tree. Only widget texts that reflect snapshot values
        are updated in place; no widgets are recreated.
        """
        self._snapshot = self._dashboard_service.get_snapshot()
        self._refresh_time = datetime.now().strftime("%H:%M")

        if getattr(self, "_date_label", None) is not None:
            self._date_label.setText(self._persian_date_text())
        if getattr(self, "_last_updated_label", None) is not None:
            self._last_updated_label.setText(
                f"آخرین بروزرسانی: {_to_persian_digit_str(self._refresh_time)}"
            )

        for title, card in getattr(self, "_kpi_labels", []):
            value, hint = self._kpi_value(self._snapshot, title)
            value_label = getattr(card, "_kpi_value_label", None)
            hint_label = getattr(card, "_kpi_hint_label", None)
            unit_label = getattr(card, "_kpi_unit_label", None)
            if value_label is not None:
                self._render_kpi_value(value_label, unit_label, value, title)
            if hint_label is not None:
                hint_label.setText(hint if hint is not None else "داده‌ای موجود نیست")

    def _panel(self, title: str) -> QFrame:
        """یک قاب ساده برای بخش‌های داشبورد."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {_CARD_BG}; "
            f"border: 1px solid {_BORDER}; "
            "border-radius: 8px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(8)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {_TEXT};"
            " background: transparent; border: none; padding: 0;"
        )
        v.addWidget(title_label)
        frame.setLayout(v)
        return frame

    def _create_header(self) -> QFrame:
        """هدر داشبورد شامل عنوان، تاریخ شمسی و دکمه بروزرسانی."""
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

        date_label = QLabel(self._persian_date_text())
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        date_label.setStyleSheet(
            "color: #6B7280; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(date_label)
        self._date_label = date_label

        update_label = QLabel(
            f"آخرین بروزرسانی: {_to_persian_digit_str(self._refresh_time)}"
        )
        update_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        update_label.setStyleSheet(
            "color: #6B7280; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(update_label)
        self._last_updated_label = update_label

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 6px 12px;"
            " border: none; border-radius: 5px; font-size: 10pt;"
        )
        refresh_btn.clicked.connect(self._refresh)
        h.addWidget(refresh_btn)

        header.setLayout(h)
        return header

    def _create_status_bar(self, refresh_time: str) -> QFrame:
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
        h.setContentsMargins(12, 6, 10, 6)
        h.setSpacing(10)

        label = QLabel("وضعیت سیستم:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(
            "font-size: 10pt; font-weight: bold; color: #3730A3;"
            " background: transparent; border: none;"
        )
        h.addWidget(label)

        status = QLabel("🟢 عادی")
        status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status.setStyleSheet(
            "color: #065F46; font-weight: bold; font-size: 10pt;"
            " background: transparent; border: none;"
        )
        h.addWidget(status)

        h.addStretch()
        bar.setLayout(h)
        return bar

    def _create_cards(self) -> QFrame:
        """کارت‌های شاخص کلیدی با چیدمان وزن‌دار چند‌ردیفی."""
        container = self._panel("کارت‌های شاخص کلیدی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        # 6 responsive columns, equal weights → no hardcoded pixel sizes.
        for col in range(6):
            grid.setColumnStretch(col, 1)

        # Per-card metadata: title → (icon, size, grid placement).
        # Placement uses (row, col, rowSpan, colSpan) over a responsive
        # 6-column grid. Only horizontal spans change; heights stay uniform.
        # Accent color is derived from the title's KPI category so the
        # warm palette stays consistent across cards.
        layout = [
            # Row 1 — ready card (2 cols), income today + income month
            ("آماده تحویل",   "📦", "medium",
             (0, 0, 1, 2)),
            ("درآمد امروز",   "💵", "medium",
             (0, 2, 1, 2)),
            ("درآمد ماه",     "💰", "large",
             (0, 4, 1, 2)),
            # Row 2 — small + small + medium + large
            ("تعمیرات فعال", "🔧", "small",
             (1, 0, 1, 1)),
            ("مشتریان",       "👤", "small",
             (1, 1, 1, 1)),
            ("سود امروز",     "📈", "medium",
             (1, 2, 1, 2)),
            ("سود ماه",       "💹", "large",
             (1, 4, 1, 2)),
            # Row 3 — task card (wide)
            ("وظایف امروز",   "📝", "wide",
             (2, 0, 1, 4)),
            ("حاشیه سود",     "🎯", "compact",
             (2, 4, 1, 2)),
        ]

        snapshot = self._snapshot
        self._kpi_labels = []

        for title, icon, size, (row, col, rs, cs) in layout:
            val, hint = self._kpi_value(snapshot, title)
            accent = _ACCENT.get(_KPI_CATEGORY.get(title, ""), _TEXT)
            card = self._kpi_card(
                title, icon, accent, val, hint,
                priority=(title in _PRIORITY_KPI_TITLES),
                minor=(title in _MINOR_KPI_TITLES),
                size=size,
                tint=_CARD_BG,
            )
            self._kpi_labels.append((title, card))
            grid.addWidget(card, row, col, rs, cs)

        container.layout().addLayout(grid)
        return container

    def _kpi_value(self, snapshot, title: str):
        """Compute the (value, hint) pair for a KPI card title from a snapshot.

        Shared by :meth:`_create_cards` (initial render) and
        :meth:`_refresh` (refresh without rebuilding widgets). Keeps all
        KPI value/hint logic in a single place so refresh stays in sync
        with the initial layout.
        """
        if title == "درآمد امروز":
            inc = snapshot.today_income
            val = f"{inc:,} تومان" if inc is not None else None
            hint = _money_zero_hint("امروز پرداختی ثبت نشده", inc)
        elif title == "درآمد ماه":
            inc = snapshot.monthly_income
            val = f"{inc:,} تومان" if inc is not None else None
            hint = _money_zero_hint("در این ماه هنوز درآمدی ثبت نشده", inc)
        elif title == "تعمیرات فعال":
            n = snapshot.active_repairs
            val = _fmt_count(n)
            hint = _count_zero_hint(
                "تعمیر فعالی در جریان نیست",
                n,
                state_phrase="تعمیر فعال در جریان است",
                unit="تعمیر",
            )
        elif title == "آماده تحویل":
            n = snapshot.ready_repairs
            val = _fmt_count(n)
            hint = _count_zero_hint(
                "دستگاهی آماده تحویل نیست",
                n,
                state_phrase="آماده تحویل",
                unit="دستگاه",
            )
        elif title == "وظایف امروز":
            n = snapshot.today_todos
            val = _fmt_count(n)
            hint = _count_zero_hint(
                "وظیفه‌ای برای امروز وجود ندارد",
                n,
                state_phrase="وظیفه برای امروز",
                unit="وظیفه",
            )
        elif title == "مشتریان":
            n = snapshot.customer_count
            val = _fmt_count(n)
            hint = _count_zero_hint(
                "هنوز مشتری ثبت نشده",
                n,
                state_phrase="مشتری ثبت شده",
                unit="مشتری",
            )
        elif title == "سود امروز":
            profit = snapshot.today_profit
            val = f"{profit:,} تومان" if profit is not None else None
            hint = _money_zero_hint("امروز سودی ثبت نشده", profit)
        elif title == "سود ماه":
            profit = snapshot.monthly_profit
            val = f"{profit:,} تومان" if profit is not None else None
            hint = _money_zero_hint("در این ماه هنوز سودی محاسبه نشده", profit)
        else:  # حاشیه سود
            margin = snapshot.average_profit_margin
            if margin is None:
                val = None
                hint = _HINT_NO_DATA
            else:
                # Guard: when there is no revenue in the window, the
                # margin is misleading as a percentage. Show an em-dash.
                revenue_total = (snapshot.monthly_revenue or 0)
                if revenue_total == 0:
                    val = "—"
                    hint = "بدون درآمد، حاشیه سود نامعتبر است"
                else:
                    val = f"{margin * 100:.1f} %"
                    hint = "میانگین حاشیه سود تعمیرات تکمیل‌شده"
        return val, hint

    def _render_kpi_value(self, value_label, unit_label, value, title):
        """Apply the presentation-only value rendering to existing widgets.

        Shared by :meth:`_kpi_card` (initial) and :meth:`_refresh` (update)
        so the money/margin visual treatment stays in exactly one place and
        refresh never duplicates styling logic.
        """
        is_money = isinstance(value, str) and value.endswith(" تومان")
        is_margin = (title == "حاشیه سود")
        if is_money and unit_label is not None:
            number_part = value[:-len(" تومان")]
            value_label.setText(_to_persian_digit_str(number_part if number_part else "0"))
            unit_label.setText("تومان")
            unit_label.setVisible(True)
        elif is_margin:
            value_label.setText(
                _to_persian_digit_str(value) if value is not None else "--"
            )
            if unit_label is not None:
                unit_label.setVisible(False)
        else:
            value_label.setText(
                _to_persian_digit_str(value) if value is not None else "--"
            )
            if unit_label is not None:
                unit_label.setVisible(False)

    def _kpi_card(self, title: str, icon: str = "•", accent: str = "#6B7280",
                  value: Optional[str] = None, hint: Optional[str] = None,
                  priority: bool = False, minor: bool = False,
                  size: str = "normal",
                  tint: str = "#FFFFFF") -> QFrame:
        """یک کارت KPI با آیکون، عنوان، مقدار بزرگ و زیرنویس.

        accent رنگ ملایم دسته‌بندی کارت است (نوار بالایی، دایره آیکون و سایه).
        size سلسله‌مراتب بصری را تعیین می‌کند: 'large'، 'medium'، 'small'
        یا 'wide'. priority و minor همچنان برای سازگاری نگه داشته شده‌اند اما
        اکنون size منبع حقیقت تیترهاست.
        tint یک شستن پس‌زمینه دسته‌بندی بسیار ملایم است (سبز/آبی/نارنجی/قرمز).
        """
        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        card.setAttribute(Qt.WA_Hover, True)
        card.setLayoutDirection(Qt.RightToLeft)

        border_base = _BORDER
        accent_soft = accent + "22"  # ~13% alpha hex suffix (RRGGBBAA)

        # ---- Visual-weight tiers (typography / padding / proportions) ----
        # Source of truth is the explicit `size` tier; legacy `priority`/
        # `minor` flags are mapped here for backward compatibility.
        small = (size == "small") or minor
        large = (size == "large") or (priority and size == "normal")
        wide = (size == "wide")
        medium = (size == "medium")
        compact = (size == "compact")

        min_height = 132
        pad_top_bottom = 8
        # Controlled typography tiers. Every KPI value belongs to one of
        # three sizes so cards cannot grow/shrink independently; wide and
        # large cards share the top tier, narrow and normal cards the base.
        if large or wide:
            value_font = "20pt"
            value_max_h = 40
        elif medium or compact:
            value_font = "18pt"
            value_max_h = 36
        else:  # small / normal
            value_font = "16pt"
            value_max_h = 34

        # Narrow cards use a slightly smaller title to stay on one line.
        title_font = "10pt" if small else "11pt"

        card.setStyleSheet(
            f"QFrame {{"
            f" background-color: {tint};"
            f" border: 1px solid {border_base};"
            f" border-top: 3px solid {accent};"
            f" border-radius: 10px;"
            f" padding: {pad_top_bottom}px 14px {pad_top_bottom}px 14px;"
            f"}}"
            f"QFrame:hover {{"
            f" background-color: {tint};"
            f" border: 1px solid {accent};"
            f" border-top: 3px solid {accent};"
            f" border-radius: 10px;"
            f"}}"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(min_height)

        # Soft shadow effect (subtle). Hover softens the shadow via a
        # lightweight QPropertyAnimation on blurRadius only — no movement,
        # no scaling. Border transition is handled by the QSS :hover state.
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(10)
        shadow_color = QColor(accent)
        shadow_color.setAlpha(28 if small else 34)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)
        card._kpi_shadow = shadow  # noqa: SLF001  (keep ref to avoid GC)
        rest_blur = 10
        hover_blur = 26  # softer + larger blur on hover
        card._kpi_blur_rest = rest_blur
        card._kpi_blur_hover = hover_blur

        def _animate_blur(target_radius: int) -> None:
            anim = QPropertyAnimation(shadow, b"blurRadius", card)
            anim.setDuration(170)  # 150–200 ms smoother transition
            anim.setStartValue(shadow.blurRadius())
            anim.setEndValue(target_radius)
            anim.setEasingCurve(QEasingCurve.OutQuad)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
            card._kpi_anim = anim  # noqa: SLF001  (keep ref alive mid-flight)

        card.enterEvent = lambda e: _animate_blur(hover_blur)
        card.leaveEvent = lambda e: _animate_blur(rest_blur)

        outer = QVBoxLayout()
        outer.setDirection(QVBoxLayout.TopToBottom)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setDirection(QHBoxLayout.RightToLeft)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Compact icon circle that fits comfortably in the card.
        if large:
            icon_size, icon_font = 34, "14pt"
        elif wide:
            icon_size, icon_font = 32, "13pt"
        elif medium:
            icon_size, icon_font = 30, "12pt"
        elif compact:
            icon_size, icon_font = 30, "12pt"
        elif small:
            icon_size, icon_font = 26, "11pt"
        else:
            icon_size, icon_font = 30, "12pt"
        icon_box = QLabel(icon)
        icon_box.setFixedSize(icon_size, icon_size)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(
            f"background-color: {accent}14;"  # very soft tint (~8% alpha)
            f" border: 1px solid {accent};"
            f" border-radius: {icon_size // 2}px;"
            f" font-size: {icon_font};"
            f" color: {accent};"
        )

        title_label = QLabel(title)
        title_label.setLayoutDirection(Qt.RightToLeft)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(40)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_label.setStyleSheet(
            f"font-size: {title_font}; font-weight: bold; color: {_TEXT};"
            " background: transparent; border: none;"
        )

        # In RTL the icon sits on the right edge with the title directly to
        # its left, so the pair stays compact even on narrow cards.
        top_row.addWidget(icon_box, 0)
        top_row.addWidget(title_label, 1)

        outer.addLayout(top_row)

        # Presentation-only: money values split number / "تومان" onto two
        # lines; the margin value is emphasized. The text + visibility
        # decisions live in :meth:`_render_kpi_value` (shared with refresh).
        is_money = isinstance(value, str) and value.endswith(" تومان")
        is_margin = (title == "حاشیه سود")

        # Important values (income + profit) carry the accent color so the
        # warm palette reads as a hierarchy without tinting the card bg.
        accent_value_color = accent
        if is_margin:
            value_color = _MARGIN_ACCENT
        elif compact:
            value_color = _TEXT_SOFT
        elif small:
            value_color = _TEXT
        else:
            value_color = accent_value_color
        value_weight = "bold"

        value_label = QLabel()
        value_label.setLayoutDirection(Qt.RightToLeft)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setWordWrap(True)
        value_label.setMaximumHeight(value_max_h)
        value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_label.setStyleSheet(
            f"font-size: {value_font}; font-weight: {value_weight};"
            f" color: {value_color};"
            " background: transparent; border: none;"
        )

        unit_label = QLabel("تومان")
        unit_label.setLayoutDirection(Qt.RightToLeft)
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet(
            "font-size: 9pt; font-weight: normal; color: #6B7280;"
            " background: transparent; border: none; margin-top: 1px;"
        )

        self._render_kpi_value(value_label, unit_label, value, title)

        hint_label = QLabel(hint if hint is not None else "داده‌ای موجود نیست")
        hint_label.setLayoutDirection(Qt.RightToLeft)
        hint_label.setWordWrap(True)
        hint_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        hint_label.setMaximumHeight(40)
        hint_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        hint_label.setStyleSheet(
            f"color: {_HINT}; font-size: 8pt;"
            " font-weight: normal; background: transparent; border: none;"
            " margin-top: 2px;"
        )

        outer.addWidget(value_label)
        outer.addWidget(unit_label)
        outer.addWidget(hint_label)
        outer.addStretch()

        card._kpi_value_label = value_label  # noqa: SLF001  (refresh hook)
        card._kpi_hint_label = hint_label  # noqa: SLF001  (refresh hook)
        card._kpi_unit_label = unit_label  # noqa: SLF001  (refresh hook)

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
        # One restrained accent per chart, drawn from the dashboard's
        # existing palette so the section matches the KPI cards. Data comes
        # from DashboardService chart APIs only — the UI never computes it.
        accents = [_ACCENT["income"], _ACCENT["tasks"], _ACCENT["profit"]]
        series = [
            self._dashboard_service.income_trend(),
            self._dashboard_service.repair_status_breakdown(),
            self._dashboard_service.monthly_activity(),
        ]
        for i, title in enumerate(titles):
            accent = accents[i]
            if i == 1:
                items = [
                    (label, value, STATUS_COLORS.get(label, accent))
                    for label, value in series[i]
                ]
            else:
                items = [
                    (label, value, accent) for label, value in series[i]
                ]
            unit = "تومان" if i == 0 else ""
            row, col = divmod(i, 3)
            grid.addWidget(self._chart_card(title, accent, items, unit), row, col)

        container.layout().addLayout(grid)
        return container

    def _chart_card(self, title: str, accent: str, items, unit: str = "") -> QFrame:
        """کارت نمودار با عنوان، نوار رنگی بالا و نمودار میله‌ای ساده."""
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        box.setMinimumHeight(200)
        box.setStyleSheet(
            f"background-color: {_CARD_BG}; "
            f"border: 1px solid {_BORDER}; "
            f"border-top: 3px solid {accent}; "
            "border-radius: 10px; "
            "padding: 8px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {_TEXT};"
            " background: transparent; border: none;"
        )
        v.addWidget(title_label)

        chart = _BarChartWidget(accent, unit)
        chart.set_data(items)
        v.addWidget(chart, 1)

        box.setLayout(v)
        return box

    def _chart_placeholder(self, title: str, accent: str) -> QFrame:
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        box.setMinimumHeight(140)
        box.setStyleSheet(
            f"background-color: {_CARD_BG}; "
            f"border: 1px solid {_BORDER}; "
            f"border-top: 3px solid {accent}; "
            "border-radius: 10px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(8)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {_TEXT};"
            " background: transparent; border: none;"
        )
        v.addWidget(t)

        icon = QLabel("📊")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"font-size: 22pt; color: {accent};"
            " background: transparent; border: none;"
        )
        v.addWidget(icon)

        hint = QLabel("نمودار در فاز بعدی اضافه می‌شود.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {_TEXT_SOFT}; font-size: 9pt; font-weight: normal;"
            " background: transparent; border: none;"
        )
        v.addWidget(hint)
        v.addStretch()

        box.setLayout(v)
        return box

    def _create_information_panels(self) -> QFrame:
        """دو پنل اطلاعاتی عملیاتی بر پایه داده‌های واقعی snapshot."""
        container = self._panel("پنل‌های اطلاعاتی")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        snap = self._snapshot
        ops_rows = [
            ("تعمیرات فعال", self._count_text(snap.active_repairs)),
            ("آماده تحویل", self._count_text(snap.ready_repairs)),
            ("وظایف امروز", self._count_text(snap.today_todos)),
            ("مشتریان", self._count_text(snap.customer_count)),
        ]
        fin_rows = [
            ("درآمد ناخالص امروز", self._money_text(snap.today_revenue)),
            ("درآمد ناخالص ماه", self._money_text(snap.monthly_revenue)),
            ("سود امروز", self._money_text(snap.today_profit)),
            ("سود ماه", self._money_text(snap.monthly_profit)),
        ]

        grid.addWidget(self._info_panel("وضعیت تعمیرات", "🔧", ops_rows), 0, 0)
        grid.addWidget(self._info_panel("وضعیت مالی خلاصه", "💰", fin_rows), 0, 1)

        container.layout().addLayout(grid)
        return container

    def _count_text(self, value) -> str:
        """Persian-digit text for a count, or an em-dash when missing."""
        text = _fmt_count(value)
        return text if text is not None else "—"

    def _money_text(self, value) -> str:
        """Persian-localized money text with the تومان unit, or an em-dash."""
        if value is None:
            return "—"
        return _to_persian_digit_str(f"{value:,}") + " تومان"

    def _info_panel(self, title: str, icon: str, rows=None) -> QFrame:
        panel = QFrame()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        panel.setMinimumHeight(120)
        panel.setStyleSheet(
            f"background-color: {_CARD_BG}; "
            f"border: 1px solid {_BORDER}; "
            "border-radius: 10px; "
            "padding: 10px;"
        )
        v = QVBoxLayout()
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)

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
            f"font-size: 11pt; font-weight: bold; color: {_TEXT};"
            " background: transparent; border: none;"
        )
        header_row.addWidget(t)

        header_row.addStretch()
        v.addLayout(header_row)

        if rows:
            for label, value in rows:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(8)

                label_widget = QLabel(label)
                label_widget.setWordWrap(True)
                label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label_widget.setStyleSheet(
                    f"font-size: 9pt; color: {_TEXT_SOFT};"
                    " background: transparent; border: none;"
                )
                row.addWidget(label_widget, 1)

                value_widget = QLabel(value)
                value_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                value_widget.setStyleSheet(
                    f"font-size: 10pt; font-weight: bold; color: {_TEXT};"
                    " background: transparent; border: none;"
                )
                row.addWidget(value_widget, 0)
                v.addLayout(row)
        else:
            placeholder = QLabel("داده‌ای برای نمایش وجود ندارد.")
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(
                f"color: {_HINT}; font-size: 10pt; font-weight: normal;"
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
            btn.setMinimumHeight(36)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            btn.setEnabled(False)
            h.addWidget(btn)
        h.addStretch()

        container.layout().addLayout(h)
        return container

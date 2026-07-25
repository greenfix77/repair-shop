import json
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                              QPushButton, QTableWidget, QLabel,
                              QLineEdit, QComboBox, QHeaderView,
                              QAbstractItemView, QFrame, QSizePolicy,
                              QStackedWidget)
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent
from PyQt5.QtGui import QPixmap

from services.logo_service import get_header_logo_pixmap
from ui.customer_view import build_customer_table, build_customer_toolbar
from ui.service_view import build_service_table, build_service_toolbar
from ui.part_view import build_part_table, build_part_toolbar
from ui.charge_view import build_charge_table, build_charge_toolbar
from ui.todo_view import build_todo_table, build_todo_toolbar
from ui.table_renderer import setup_selection_column
from core.status import (
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_DELIVERED,
    ALL_STATUSES_WITH_ALL,
    STATUS_FG_COLORS
)


def _get_shop_name():
    try:
        if Path("shop_settings.json").exists():
            with open("shop_settings.json", "r", encoding="utf-8") as f:
                return json.load(f).get("shop_name", "").strip()
    except:
        pass
    return ""


def _make_title(icon=False):
    shop_name = _get_shop_name()
    prefix = "🔧 " if icon else ""
    if shop_name:
        return f"{prefix}سیستم مدیریت تعمیرگاه {shop_name}"
    return f"{prefix}سیستم مدیریت تعمیرات"


def _get_header_appearance():
    defaults = {
        "header_title_size": 20,
        "header_title_color": "#FFFFFF",
        "header_gradient_start": "#4F46E5",
        "header_gradient_end": "#7C3AED",
        "header_border_radius": 15,
        "header_height": 60,
        "status_popup_background_color": "#FFFFFF",
        "status_popup_border_color": "#D1D5DB",
        "status_popup_border_width": 1,
        "status_popup_border_radius": 12,
        "status_popup_text_color": "#111827",
        "status_popup_datetime_color": "#374151",
    }
    try:
        if Path("shop_settings.json").exists():
            with open("shop_settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                for k in defaults:
                    if k in settings:
                        defaults[k] = settings[k]
    except:
        pass
    return defaults


def build_header(window):
    """ایجاد هدر"""
    app = _get_header_appearance()

    header = QFrame()
    header.setStyleSheet(f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                   stop:0 {app['header_gradient_start']}, stop:1 {app['header_gradient_end']});
        border-radius: {app['header_border_radius']}px;
        min-height: {app['header_height']}px;
        max-height: {app['header_height']}px;
    """)
    
    layout = QHBoxLayout()
    layout.setContentsMargins(4, 0, 0, 0)

    logo_pixmap = get_header_logo_pixmap()
    has_logo = logo_pixmap is not None
    if has_logo:
        logo_label = QLabel()
        logo_label.setPixmap(logo_pixmap)
        logo_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(logo_label)
    
    title = QLabel(_make_title(icon=not has_logo))
    title.setStyleSheet(f"color: {app['header_title_color']}; font-size: {app['header_title_size']}pt; font-weight: bold;")
    layout.addWidget(title)
    
    layout.addStretch()
    
    header.setLayout(layout)
    return header


def build_toolbar(window):
    """ایجاد نوار ابزار"""
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")
    
    layout = QHBoxLayout()
    
    # دکمه افزودن
    add_btn = QPushButton("➕ افزودن تعمیر")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_repair)
    layout.addWidget(add_btn)
    
    # دکمه ویرایش
    edit_btn = QPushButton("✏️ ویرایش")
    edit_btn.setStyleSheet("background-color: #2196F3; color: white;")
    edit_btn.clicked.connect(window.edit_repair)
    layout.addWidget(edit_btn)
    
    # دکمه حذف انتخاب‌شده‌ها
    bulk_delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    bulk_delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    bulk_delete_btn.clicked.connect(window.delete_selected_repairs)
    layout.addWidget(bulk_delete_btn)
    
    # دکمه پیش‌نمایش فاکتور
    invoice_btn = QPushButton("📄 پیش‌نمایش فاکتور")
    invoice_btn.setStyleSheet("background-color: #FF9800; color: white;")
    invoice_btn.clicked.connect(window.preview_invoice)
    layout.addWidget(invoice_btn)

    # دکمه تنظیمات کلی
    settings_btn = QPushButton("⚙️ تنظیمات کلی")
    settings_btn.setStyleSheet("background-color: #607D8B; color: white;")
    settings_btn.clicked.connect(window.open_shop_settings)
    layout.addWidget(settings_btn)

    # دکمه داشبورد (جابه‌جا شده از هدر)
    window.status_btn = QPushButton("📊 داشبورد")
    window.status_btn.setStyleSheet("background-color: #673AB7; color: white;")
    window.status_btn.clicked.connect(window.open_dashboard)
    layout.addWidget(window.status_btn)
    
    layout.addStretch()
    
    # جستجو
    search_label = QLabel("🔍 جستجو:")
    layout.addWidget(search_label)
    
    window.search_input = QLineEdit()
    window.search_input.setPlaceholderText("نام، تلفن، برند یا مدل...")
    window.search_input.setMinimumWidth(250)
    window.search_input.textChanged.connect(window.search_repairs)
    layout.addWidget(window.search_input)
    
    # فیلتر وضعیت
    filter_label = QLabel("فیلتر:")
    layout.addWidget(filter_label)
    
    window.filter_combo = QComboBox()
    window.filter_combo.addItems(ALL_STATUSES_WITH_ALL)
    window.filter_combo.currentTextChanged.connect(window.filter_repairs)
    layout.addWidget(window.filter_combo)
    
    toolbar.setLayout(layout)
    return toolbar


def build_table(window):
    """ایجاد جدول"""
    table = QTableWidget()
    table.setColumnCount(12)
    table.setHorizontalHeaderLabels([
        "", "شناسه", "نام مشتری", "تلفن", "برند", "مدل",
        "ایراد", "وضعیت", "تاریخ دریافت", "تاریخ تحویل",
        "هزینه کل", "عملیات"
    ])
    
    # تنظیمات جدول
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    
    # تنظیم عرض ستون‌ها
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.Stretch)
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(6, QHeaderView.Stretch)
    header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(11, QHeaderView.ResizeToContents)

    # ستون چک‌باکس با هدر select-all
    setup_selection_column(table)
    
    # دابل کلیک برای ویرایش
    table.doubleClicked.connect(window.edit_repair)
    
    return table


def build_status_bar(window):
    """ایجاد نوار وضعیت"""
    status_bar = QFrame()
    status_bar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")
    
    layout = QHBoxLayout()
    
    window.total_label = QLabel("تعداد کل: 0")
    window.total_label.setStyleSheet("font-weight: bold; color: #333;")
    layout.addWidget(window.total_label)
    
    layout.addWidget(QLabel("|"))
    
    window.pending_label = QLabel(f"{STATUS_PENDING}: 0")
    window.pending_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_PENDING]}; font-weight: bold;")
    layout.addWidget(window.pending_label)
    
    layout.addWidget(QLabel("|"))
    
    window.in_progress_label = QLabel(f"{STATUS_IN_PROGRESS}: 0")
    window.in_progress_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_IN_PROGRESS]}; font-weight: bold;")
    layout.addWidget(window.in_progress_label)
    
    layout.addWidget(QLabel("|"))
    
    window.completed_label = QLabel(f"{STATUS_COMPLETED}: 0")
    window.completed_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_COMPLETED]}; font-weight: bold;")
    layout.addWidget(window.completed_label)
    
    layout.addWidget(QLabel("|"))
    
    window.delivered_label = QLabel(f"{STATUS_DELIVERED}: 0")
    window.delivered_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_DELIVERED]}; font-weight: bold;")
    layout.addWidget(window.delivered_label)
    
    layout.addStretch()
    
    window.date_label = QLabel()
    window.update_date_label()
    layout.addWidget(window.date_label)
    
    status_bar.setLayout(layout)
    return status_bar


def create_status_popup(window):
    """ایجاد پاپ‌آپ داشبورد"""
    app = _get_header_appearance()

    popup = QFrame(None, Qt.FramelessWindowHint | Qt.Tool)
    popup.setAttribute(Qt.WA_DeleteOnClose, False)
    popup.setLayoutDirection(Qt.RightToLeft)
    popup.setStyleSheet(f"""
        background-color: {app['status_popup_background_color']};
        border: {app['status_popup_border_width']}px solid {app['status_popup_border_color']};
        border-radius: {app['status_popup_border_radius']}px;
    """)
    popup_layout = QVBoxLayout()
    popup_layout.setSpacing(2)
    popup_layout.setContentsMargins(14, 10, 14, 10)

    text_color = app['status_popup_text_color']

    items_defs = [
        ("فوری", "🔴", "header_pending_count"),
        ("آماده تحویل", "🟢", "header_completed_count"),
        ("در حال تعمیر", "🔵", "header_in_progress_count"),
        ("عادی", "⚪", "header_delivered_count"),
    ]

    for label, icon, attr in items_defs:
        row = QHBoxLayout()
        row.setSpacing(6)

        icn = QLabel(icon)
        icn.setStyleSheet("background: transparent; border: none; font-size: 11pt;")
        row.addWidget(icn)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"background: transparent; border: none; color: {text_color}; font-size: 9pt; font-weight: bold;")
        row.addWidget(lbl)

        row.addStretch()

        cnt = QLabel("0")
        cnt.setStyleSheet(f"background: transparent; border: none; color: {text_color}; font-size: 10pt; font-weight: bold;")
        setattr(window, attr, cnt)
        row.addWidget(cnt)

        popup_layout.addLayout(row)

    # Separator
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {app['status_popup_border_color']}; border: none; margin: 4px 0;")
    popup_layout.addWidget(sep)

    # Datetime with icons
    dt_color = app['status_popup_datetime_color']
    dt_label = QLabel()
    dt_label.setAlignment(Qt.AlignCenter)
    dt_label.setStyleSheet(f"""
        background: transparent;
        border: none;
        color: {dt_color};
        font-size: 9pt;
        font-weight: bold;
    """)
    window.header_datetime_label = dt_label
    popup_layout.addWidget(dt_label)

    popup.setLayout(popup_layout)
    popup.adjustSize()
    return popup


def build_nav_bar(window):
    """ایجاد نوار ناوبری بین نمای تعمیرات و مشتریان"""
    nav = QFrame()
    nav.setStyleSheet("background-color: #f5f5f5; border-radius: 5px; padding: 6px;")
    layout = QHBoxLayout()
    layout.setContentsMargins(4, 4, 4, 4)

    window.repairs_nav_btn = QPushButton("تعمیرات")
    window.repairs_nav_btn.setStyleSheet(
        "background-color: #4F46E5; color: white; font-weight: bold;"
    )
    window.repairs_nav_btn.clicked.connect(window.show_repairs_view)
    layout.addWidget(window.repairs_nav_btn)

    window.customers_nav_btn = QPushButton("مشتریان")
    window.customers_nav_btn.setStyleSheet(
        "background-color: #607D8B; color: white;"
    )
    window.customers_nav_btn.clicked.connect(window.show_customers_view)
    layout.addWidget(window.customers_nav_btn)

    window.services_nav_btn = QPushButton("خدمات")
    window.services_nav_btn.setStyleSheet(
        "background-color: #607D8B; color: white;"
    )
    window.services_nav_btn.clicked.connect(window.show_services_view)
    layout.addWidget(window.services_nav_btn)

    window.parts_nav_btn = QPushButton("قطعات")
    window.parts_nav_btn.setStyleSheet(
        "background-color: #607D8B; color: white;"
    )
    window.parts_nav_btn.clicked.connect(window.show_parts_view)
    layout.addWidget(window.parts_nav_btn)

    window.charges_nav_btn = QPushButton("هزینه‌ها")
    window.charges_nav_btn.setStyleSheet(
        "background-color: #607D8B; color: white;"
    )
    window.charges_nav_btn.clicked.connect(window.show_charges_view)
    layout.addWidget(window.charges_nav_btn)

    window.todos_nav_btn = QPushButton("وظایف")
    window.todos_nav_btn.setStyleSheet(
        "background-color: #607D8B; color: white;"
    )
    window.todos_nav_btn.clicked.connect(window.show_todos_view)
    layout.addWidget(window.todos_nav_btn)

    layout.addStretch()
    nav.setLayout(layout)
    return nav


def build_ui(window):
    """ایجاد رابط کاربری"""
    window.setWindowTitle(_make_title(icon=False))
    window.setGeometry(100, 100, 1200, 700)
    
    # ویجت مرکزی
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # لایه اصلی
    main_layout = QVBoxLayout()
    
    # هدر
    header = build_header(window)
    window.header_widget = header
    main_layout.addWidget(header)
    window.main_layout = main_layout
    
    # Status popup
    window.status_popup = create_status_popup(window)
    
    # نوار ناوبری
    nav_bar = build_nav_bar(window)
    main_layout.addWidget(nav_bar)
    
    # ناحیه نمایش: نمای تعمیرات (صفحه ۰) و نمای مشتریان (صفحه ۱)
    window.view_stack = QStackedWidget()

    # صفحه تعمیرات
    repairs_page = QWidget()
    repairs_layout = QVBoxLayout()
    repairs_layout.setContentsMargins(0, 0, 0, 0)
    repairs_toolbar = build_toolbar(window)
    repairs_layout.addWidget(repairs_toolbar)
    window.table = build_table(window)
    repairs_layout.addWidget(window.table)
    repairs_page.setLayout(repairs_layout)
    window.view_stack.addWidget(repairs_page)

    # صفحه مشتریان
    customers_page = QWidget()
    customers_layout = QVBoxLayout()
    customers_layout.setContentsMargins(0, 0, 0, 0)
    window.customer_toolbar = build_customer_toolbar(window)
    customers_layout.addWidget(window.customer_toolbar)
    window.customer_table = build_customer_table(window)
    customers_layout.addWidget(window.customer_table)
    customers_page.setLayout(customers_layout)
    window.view_stack.addWidget(customers_page)

    # صفحه خدمات
    services_page = QWidget()
    services_layout = QVBoxLayout()
    services_layout.setContentsMargins(0, 0, 0, 0)
    window.service_toolbar = build_service_toolbar(window)
    services_layout.addWidget(window.service_toolbar)
    window.service_table = build_service_table(window)
    services_layout.addWidget(window.service_table)
    services_page.setLayout(services_layout)
    window.view_stack.addWidget(services_page)

    # صفحه قطعات
    parts_page = QWidget()
    parts_layout = QVBoxLayout()
    parts_layout.setContentsMargins(0, 0, 0, 0)
    window.part_toolbar = build_part_toolbar(window)
    parts_layout.addWidget(window.part_toolbar)
    window.part_table = build_part_table(window)
    parts_layout.addWidget(window.part_table)
    parts_page.setLayout(parts_layout)
    window.view_stack.addWidget(parts_page)

    # صفحه هزینه‌ها
    charges_page = QWidget()
    charges_layout = QVBoxLayout()
    charges_layout.setContentsMargins(0, 0, 0, 0)
    window.charge_toolbar = build_charge_toolbar(window)
    charges_layout.addWidget(window.charge_toolbar)
    window.charge_table = build_charge_table(window)
    charges_layout.addWidget(window.charge_table)
    charges_page.setLayout(charges_layout)
    window.view_stack.addWidget(charges_page)

    # صفحه وظایف (صفحه ۵)
    todos_page = QWidget()
    todos_layout = QVBoxLayout()
    todos_layout.setContentsMargins(0, 0, 0, 0)
    window.todo_toolbar = build_todo_toolbar(window)
    todos_layout.addWidget(window.todo_toolbar)
    window.todo_table = build_todo_table(window)
    todos_layout.addWidget(window.todo_table)
    todos_page.setLayout(todos_layout)
    window.view_stack.addWidget(todos_page)

    main_layout.addWidget(window.view_stack)
    
    # نوار وضعیت
    window.status_bar = build_status_bar(window)
    main_layout.addWidget(window.status_bar)
    
    central_widget.setLayout(main_layout)
    
    # استایل کلی
    window.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QPushButton {
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 10pt;
            font-weight: bold;
        }
        QPushButton:hover {
            opacity: 0.8;
        }
        QTableWidget {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        QHeaderView::section {
            background-color: #667eea;
            color: white;
            padding: 10px;
            font-weight: bold;
            border: none;
        }
    """)

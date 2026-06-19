import json
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                              QPushButton, QTableWidget, QLabel,
                              QLineEdit, QComboBox, QHeaderView,
                              QAbstractItemView, QFrame)
from PyQt5.QtCore import Qt
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


def build_header(window):
    """ایجاد هدر"""
    header = QFrame()
    header.setStyleSheet("""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                   stop:0 #667eea, stop:1 #764ba2);
        border-radius: 10px;
        padding: 20px;
    """)
    
    layout = QHBoxLayout()
    
    title = QLabel(_make_title(icon=True))
    title.setStyleSheet("color: white; font-size: 20pt; font-weight: bold;")
    layout.addWidget(title)
    
    layout.addStretch()
    
    # دکمه تنظیمات کلی
    settings_btn = QPushButton("⚙️ تنظیمات کلی")
    settings_btn.setStyleSheet("""
        background-color: rgba(255, 255, 255, 0.2);
        color: white;
        border: 2px solid white;
    """)
    settings_btn.clicked.connect(window.open_shop_settings)
    layout.addWidget(settings_btn)
    
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
    
    # دکمه حذف
    delete_btn = QPushButton("🗑️ حذف")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_repair)
    layout.addWidget(delete_btn)
    
    # دکمه پیش‌نمایش فاکتور
    invoice_btn = QPushButton("📄 پیش‌نمایش فاکتور")
    invoice_btn.setStyleSheet("background-color: #FF9800; color: white;")
    invoice_btn.clicked.connect(window.preview_invoice)
    layout.addWidget(invoice_btn)
    
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
    table.setColumnCount(11)
    table.setHorizontalHeaderLabels([
        "شناسه", "نام مشتری", "تلفن", "برند", "مدل", 
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
    header.setSectionResizeMode(1, QHeaderView.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.Stretch)
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
    
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
    main_layout.addWidget(header)
    
    # نوار ابزار
    toolbar = build_toolbar(window)
    main_layout.addWidget(toolbar)
    
    # جدول
    window.table = build_table(window)
    main_layout.addWidget(window.table)
    
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

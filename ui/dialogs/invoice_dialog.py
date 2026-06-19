from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTextEdit, QLabel,
                              QRadioButton, QButtonGroup, QFileDialog,
                              QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from services.invoice_generator import generate_print_invoice_html, generate_web_invoice_html


class InvoicePreviewDialog(QDialog):
    """دیالوگ پیش‌نمایش و چاپ فاکتور"""

    def __init__(self, repair_data, parent=None):
        super().__init__(parent)
        self.repair_data = repair_data
        from app import ShopSettingsDialog
        self.shop_settings = ShopSettingsDialog.get_settings()

        self.setWindowTitle("پیش‌نمایش فاکتور")
        self.setMinimumSize(900, 700)

        self.init_ui()

    def init_ui(self):
        """ایجاد رابط کاربری"""
        layout = QVBoxLayout()

        # انتخاب نوع فاکتور
        type_layout = QHBoxLayout()
        type_label = QLabel("نوع فاکتور:")
        type_label.setFont(QFont("Segoe UI", 10, QFont.Bold))

        self.type_group = QButtonGroup()
        self.print_radio = QRadioButton("چاپی (سیاه و سفید)")
        self.web_radio = QRadioButton("وب (رنگی)")

        self.type_group.addButton(self.print_radio)
        self.type_group.addButton(self.web_radio)
        self.print_radio.setChecked(True)

        self.print_radio.toggled.connect(self.update_preview)

        type_layout.addWidget(type_label)
        type_layout.addWidget(self.print_radio)
        type_layout.addWidget(self.web_radio)
        type_layout.addStretch()

        layout.addLayout(type_layout)

        # پیش‌نمایش
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

        # دکمه‌ها
        btn_layout = QHBoxLayout()

        print_btn = QPushButton("چاپ")
        print_btn.setIcon(self.style().standardIcon(self.style().SP_FileDialogDetailedView))
        print_btn.clicked.connect(self.print_invoice)

        save_btn = QPushButton("ذخیره PDF")
        save_btn.clicked.connect(self.save_pdf)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(print_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # نمایش پیش‌نمایش اولیه
        self.update_preview()

    def print_invoice(self):
        """چاپ فاکتور"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec_() == QDialog.Accepted:
            self.preview.document().print_(printer)

    def save_pdf(self):
        """ذخیره به صورت PDF"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره PDF",
            f"invoice_{self.repair_data.get('id', 'new')}.pdf",
            "PDF Files (*.pdf)"
        )

        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self.preview.document().print_(printer)
            QMessageBox.information(self, "موفق", "فایل PDF با موفقیت ذخیره شد.")

    def update_preview(self):
        """به‌روزرسانی پیش‌نمایش فاکتور"""
        if self.print_radio.isChecked():
            html = generate_print_invoice_html(self.repair_data, self.shop_settings)
        else:
            html = generate_web_invoice_html(self.repair_data, self.shop_settings)

        self.preview.setHtml(html)

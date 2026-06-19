from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from services.notification_service import show_info


def print_invoice_content(html_content):
    """چاپ فاکتور"""
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer)
    if dialog.exec_() == QDialog.Accepted:
        doc = QTextDocument()
        doc.setHtml(html_content)
        doc.print_(printer)


def save_invoice_to_pdf(html_content, file_path):
    """ذخیره به صورت PDF"""
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(file_path)
    doc = QTextDocument()
    doc.setHtml(html_content)
    doc.print_(printer)
    show_info(None, "موفق", "فایل PDF با موفقیت ذخیره شد.")

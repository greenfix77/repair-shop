from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView


class WebInvoiceView(QWidget):
    """Invoice preview widget using QWebEngineView"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        self.setLayout(layout)

    def set_html(self, html: str):
        self.web_view.setHtml(html)

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import LibraryError, LibraryService, User


class BookEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        title: str,
        book: tuple[str, str, str] = ("", "", ""),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_input = QLineEdit(book[0])
        self.author_input = QLineEdit(book[1])
        self.isbn_input = QLineEdit(book[2])
        form.addRow("Title", self.title_input)
        form.addRow("Author", self.author_input)
        form.addRow("ISBN", self.isbn_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str]:
        return self.title_input.text(), self.author_input.text(), self.isbn_input.text()


class CatalogueManagerDialog(QDialog):
    def __init__(self, service: LibraryService, user: User, parent: QWidget) -> None:
        super().__init__(parent)
        self.service = service
        self.user = user
        self.setWindowTitle("Manage catalogue")
        self.resize(820, 520)

        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, author, or ISBN")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.refresh)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(("Title", "Author", "ISBN"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 220)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_selected())
        self.table.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.table)

        self.feedback_label = QLabel()
        layout.addWidget(self.feedback_label)

        action_row = QHBoxLayout()
        self.add_button = QPushButton("Add book")
        self.add_button.clicked.connect(self.add_book)
        action_row.addWidget(self.add_button)
        self.edit_button = QPushButton("Edit selected")
        self.edit_button.clicked.connect(self.edit_selected)
        action_row.addWidget(self.edit_button)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        action_row.addWidget(self.remove_button)
        action_row.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)

        self.refresh()

    def refresh(self, _text: str = "") -> None:
        books = self.service.search_books(self.search_input.text())
        self.table.setRowCount(len(books))
        for row_index, book in enumerate(books):
            title = QTableWidgetItem(book["title"])
            title.setData(Qt.ItemDataRole.UserRole, book["id"])
            self.table.setItem(row_index, 0, title)
            self.table.setItem(row_index, 1, QTableWidgetItem(book["author"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(book["isbn"]))
        self._update_actions()

    def _selected_rows(self) -> list[int]:
        return sorted(index.row() for index in self.table.selectionModel().selectedRows())

    def _update_actions(self) -> None:
        selected_count = len(self._selected_rows())
        self.edit_button.setEnabled(selected_count == 1)
        self.remove_button.setEnabled(selected_count > 0)

    def add_book(self) -> None:
        dialog = BookEditorDialog(self, "Add book")
        while dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.add_book(self.user.id, *dialog.values())
            except LibraryError as error:
                QMessageBox.warning(self, "Cannot add book", str(error))
                continue
            self.feedback_label.setText("Book added successfully.")
            self.refresh()
            break

    def edit_selected(self) -> None:
        selected_rows = self._selected_rows()
        if len(selected_rows) != 1:
            return
        row = selected_rows[0]
        book_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        values = tuple(self.table.item(row, column).text() for column in range(3))
        dialog = BookEditorDialog(self, "Edit book", values)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.update_book(self.user.id, book_id, *dialog.values())
            except LibraryError as error:
                QMessageBox.warning(self, "Cannot update book", str(error))
                continue
            self.feedback_label.setText("Book updated successfully.")
            self.refresh()
            break

    def remove_selected(self) -> None:
        selected_rows = self._selected_rows()
        if not selected_rows:
            return
        count = len(selected_rows)
        noun = "entry" if count == 1 else "entries"
        answer = QMessageBox.question(
            self,
            "Remove catalogue entries",
            f"Remove {count} selected catalogue {noun}? Loan history will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        book_ids = [
            self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in selected_rows
        ]
        try:
            removed = self.service.archive_books(self.user.id, book_ids)
        except LibraryError as error:
            QMessageBox.warning(self, "Cannot remove books", str(error))
            return
        self.feedback_label.setText(f"Removed {removed} catalogue {noun}.")
        self.refresh()


class LibraryWindow(QMainWindow):
    def __init__(self, service: LibraryService) -> None:
        super().__init__()
        self.service = service
        self.current_user: User | None = None
        self.setWindowTitle("Library Simulator")
        self.resize(900, 600)

        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)
        self.login_page = self._build_login_page()
        self.library_page = self._build_library_page()
        self.pages.addWidget(self.login_page)
        self.pages.addWidget(self.library_page)
        self.statusBar().showMessage("Enter your library-card ID and password.")

    def _build_login_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch()

        title = QLabel("Library Simulator")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        outer.addWidget(title)

        form = QFormLayout()
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("CARD1001")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.login)
        form.addRow("Library-card ID", self.card_input)
        form.addRow("Password", self.password_input)

        form_holder = QWidget()
        form_holder.setMaximumWidth(420)
        form_holder.setLayout(form)
        centered = QHBoxLayout()
        centered.addStretch()
        centered.addWidget(form_holder)
        centered.addStretch()
        outer.addLayout(centered)

        login_button = QPushButton("Log in")
        login_button.setDefault(True)
        login_button.clicked.connect(self.login)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(login_button)
        button_row.addStretch()
        outer.addLayout(button_row)
        outer.addStretch()
        return page

    def _build_library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QHBoxLayout()
        self.user_label = QLabel()
        header.addWidget(self.user_label)
        header.addStretch()
        self.manage_button = QPushButton("Manage catalogue")
        self.manage_button.clicked.connect(self.manage_catalogue)
        self.manage_button.hide()
        header.addWidget(self.manage_button)
        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        header.addWidget(logout_button)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_catalogue_tab(), "Catalogue")
        self.tabs.addTab(self._build_loans_tab(), "My Loans")
        self.tabs.currentChanged.connect(lambda _index: self.refresh_loans())
        layout.addWidget(self.tabs)
        return page

    def _build_catalogue_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, author, or ISBN")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.refresh_catalogue)
        layout.addWidget(self.search_input)

        self.catalogue_table = self._make_table(("Title", "Author", "ISBN", "Availability"))
        self.catalogue_table.setColumnWidth(0, 260)
        self.catalogue_table.setColumnWidth(1, 190)
        self.catalogue_table.setColumnWidth(2, 150)
        self.catalogue_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.catalogue_table)

        borrow_button = QPushButton("Borrow selected book")
        borrow_button.clicked.connect(self.borrow_selected)
        layout.addWidget(borrow_button, alignment=Qt.AlignmentFlag.AlignRight)
        return tab

    def _build_loans_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.loans_table = self._make_table(("Title", "Borrowed", "Due"))
        self.loans_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.loans_table)
        return_button = QPushButton("Return selected book")
        return_button.clicked.connect(self.return_selected)
        layout.addWidget(return_button, alignment=Qt.AlignmentFlag.AlignRight)
        return tab

    @staticmethod
    def _make_table(headers: tuple[str, ...]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        return table

    def login(self) -> None:
        user = self.service.authenticate(self.card_input.text(), self.password_input.text())
        if user is None:
            self.password_input.clear()
            self.statusBar().showMessage("Invalid card ID or password. Please try again.", 5000)
            QMessageBox.warning(self, "Login failed", "The card ID or password is incorrect.")
            return
        self.current_user = user
        role = " — Administrator" if user.is_admin else ""
        self.user_label.setText(f"Signed in as {user.name} ({user.card_id}){role}")
        self.manage_button.setVisible(user.is_admin)
        self.password_input.clear()
        self.search_input.clear()
        self.refresh_all()
        self.pages.setCurrentWidget(self.library_page)
        self.statusBar().showMessage(f"Welcome, {user.name}.", 4000)

    def logout(self) -> None:
        self.current_user = None
        self.manage_button.hide()
        self.card_input.clear()
        self.password_input.clear()
        self.pages.setCurrentWidget(self.login_page)
        self.card_input.setFocus()
        self.statusBar().showMessage("You have been logged out.", 4000)

    def manage_catalogue(self) -> None:
        if self.current_user is None or not self.current_user.is_admin:
            return
        CatalogueManagerDialog(self.service, self.current_user, self).exec()
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_catalogue()
        self.refresh_loans()

    def refresh_catalogue(self, _text: str = "") -> None:
        books = self.service.search_books(self.search_input.text())
        self.catalogue_table.setRowCount(len(books))
        for row_index, book in enumerate(books):
            title = QTableWidgetItem(book["title"])
            title.setData(Qt.ItemDataRole.UserRole, book["id"])
            self.catalogue_table.setItem(row_index, 0, title)
            self.catalogue_table.setItem(row_index, 1, QTableWidgetItem(book["author"]))
            self.catalogue_table.setItem(row_index, 2, QTableWidgetItem(book["isbn"]))
            availability = "Available" if book["available"] else "On loan"
            self.catalogue_table.setItem(row_index, 3, QTableWidgetItem(availability))

    def refresh_loans(self) -> None:
        if self.current_user is None:
            self.loans_table.setRowCount(0)
            return
        loans = self.service.active_loans(self.current_user.id)
        self.loans_table.setRowCount(len(loans))
        for row_index, loan in enumerate(loans):
            title = QTableWidgetItem(loan["title"])
            title.setData(Qt.ItemDataRole.UserRole, loan["id"])
            self.loans_table.setItem(row_index, 0, title)
            self.loans_table.setItem(row_index, 1, QTableWidgetItem(loan["borrowed_at"]))
            self.loans_table.setItem(row_index, 2, QTableWidgetItem(loan["due_at"]))

    def borrow_selected(self) -> None:
        if self.current_user is None:
            return
        row = self.catalogue_table.currentRow()
        if row < 0:
            self.statusBar().showMessage("Select an available book first.", 4000)
            return
        book_id = self.catalogue_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.service.borrow_book(self.current_user.id, book_id)
        except LibraryError as error:
            self.statusBar().showMessage(str(error), 5000)
            QMessageBox.information(self, "Cannot borrow book", str(error))
            return
        self.refresh_all()
        self.statusBar().showMessage("Book borrowed successfully. It is due in 14 days.", 5000)

    def return_selected(self) -> None:
        if self.current_user is None:
            return
        row = self.loans_table.currentRow()
        if row < 0:
            self.statusBar().showMessage("Select an active loan first.", 4000)
            return
        loan_id = self.loans_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.service.return_loan(self.current_user.id, loan_id)
        except LibraryError as error:
            self.statusBar().showMessage(str(error), 5000)
            return
        self.refresh_all()
        self.statusBar().showMessage("Book returned successfully.", 5000)


def run_application(service: LibraryService) -> int:
    application = QApplication.instance() or QApplication([])
    window = LibraryWindow(service)
    window.show()
    return application.exec()

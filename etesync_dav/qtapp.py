try:
    from PySide2.QtWidgets import (QApplication, QPushButton, QListWidget, QStackedLayout, QFormLayout, QLineEdit,
                                   QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QGroupBox)
    from PySide2.QtCore import Slot, Signal, QObject, Qt, QTimer
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

from etesync_dav.manage import Manager

manager = Manager()


# FIXME: Instead of this, just run the mainloop on the same binary in a different thread - so running is always tied.
def check_service_running():
    import socket
    s = socket.socket()
    address = '127.0.0.1'
    port = 37358
    try:
        s.connect((address, port))
        return True
    except Exception:
        return False


if HAS_GUI:
    # FIXME: Meant to be QThread but manager is not multithreaded atm
    class AddUserBackground(QObject):
        add_user_signal = Signal(bool)

        def __init__(self, username, login_password, encryption_password):
            super().__init__()
            self.username = username
            self.login_password = login_password
            self.encryption_password = encryption_password

        def run(self):
            manager.add(self.username, self.login_password, self.encryption_password)
            self.add_user_signal.emit(True)

        def start(self):
            self.run()

    class AddUser(QWidget):
        def __init__(self, done_cb):
            super().__init__()

            self.done_cb = done_cb

            self.button_cancel = QPushButton("Cancel")
            self.button_cancel.clicked.connect(self.cancel)

            self.button_add = QPushButton("Add")
            self.button_add.clicked.connect(self.add_user)

            self.username_field = QLineEdit()
            self.login_password_field = QLineEdit()
            self.login_password_field.setEchoMode(QLineEdit.Password)
            self.encryption_password_field = QLineEdit()
            self.encryption_password_field.setEchoMode(QLineEdit.Password)

            form = QWidget()
            form_layout = QFormLayout()
            form_layout.addRow("Username", self.username_field)
            form_layout.addRow("Login password", self.login_password_field)
            form_layout.addRow("Encryption password", self.encryption_password_field)
            form.setLayout(form_layout)
            form.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            buttons = QWidget()
            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(self.button_add)
            buttons_layout.addWidget(self.button_cancel)
            buttons.setLayout(buttons_layout)

            self.information = QLabel()
            self.information.setAlignment(Qt.AlignCenter)
            self.information.setStyleSheet("QLabel {color: red; font-size: 40px; font-weight: bold;}")

            self.layout = QVBoxLayout()
            self.layout.addWidget(form)
            self.layout.addWidget(self.information)
            self.layout.addWidget(buttons)

            self.setLayout(self.layout)

        @Slot()
        def add_user(self):
            username = self.username_field.text()
            login_password = self.login_password_field.text()
            encryption_password = self.encryption_password_field.text()

            if not username or not login_password or not encryption_password:
                self.information.setText("All fields are required!")
                return

            self.information.setText("Working...\nApplication may be unresponsive until completion.")

            # FIXME: Hack to make sure we render before blocking
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.add_user_delayed)
            timer.start(1)

        @Slot()
        def add_user_delayed(self):
            username = self.username_field.text()
            login_password = self.login_password_field.text()
            encryption_password = self.encryption_password_field.text()

            thread = AddUserBackground(username, login_password, encryption_password)
            thread.add_user_signal.connect(self.add_user_done)
            thread.start()

        @Slot()
        def add_user_done(self):
            self.done_cb(True)

        @Slot()
        def cancel(self):
            self.done_cb(False)

    class MainWindow(QWidget):
        def __init__(self, app, set_run_service_cb):
            super().__init__()

            self.app = app
            self.set_run_service_cb = set_run_service_cb

            self.button_add = QPushButton("Add")
            self.button_add.clicked.connect(self.add_user)

            self.button_del = QPushButton("Remove")
            self.button_del.clicked.connect(self.delete_user)
            self.button_del.setDisabled(True)

            self.button_copy = QPushButton("Copy Password")
            self.button_copy.clicked.connect(self.copy_password)
            self.button_copy.setDisabled(True)

            self.list = QListWidget()
            self.list.itemSelectionChanged.connect(self.selection_changed)
            self.repopulate_list()

            service_running = check_service_running()
            status_label = QLabel()
            status_label.setText("EteSync DAV is running" if service_running else "EteSync DAV is not running")
            status_start = QPushButton("Run background service")
            status_start.clicked.connect(self.run_service)
            status_start.setDisabled(service_running)

            status = QGroupBox()
            status.setTitle("Service Status")
            status_layout = QHBoxLayout()
            status_layout.addWidget(status_label)
            status_layout.addWidget(status_start)
            status.setLayout(status_layout)

            buttons = QWidget()
            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(self.button_add)
            buttons_layout.addWidget(self.button_del)
            buttons_layout.addWidget(self.button_copy)
            buttons.setLayout(buttons_layout)

            layout = QWidget()
            self.layout = QVBoxLayout()
            self.layout.addWidget(status)
            self.layout.addWidget(self.list)
            self.layout.addWidget(buttons)
            layout.setLayout(self.layout)

            self.main_stack = QStackedLayout()
            self.main_stack.addWidget(layout)
            self.setLayout(self.main_stack)

        def repopulate_list(self):
            self.list.clear()
            for item in manager.list():
                self.list.addItem(item)

        def add_user_done(self, success):
            self.main_stack.removeWidget(self.main_stack.currentWidget())
            if success:
                self.repopulate_list()

        @Slot()
        def add_user(self):
            add_widget = AddUser(self.add_user_done)
            self.main_stack.addWidget(add_widget)
            self.main_stack.setCurrentWidget(add_widget)

        @Slot()
        def delete_user(self):
            item = self.list.selectedItems()[0]
            username = item.text()
            manager.delete(username)
            self.repopulate_list()

        @Slot()
        def copy_password(self):
            item = self.list.selectedItems()[0]
            username = item.text()
            password = manager.get(username)
            self.app.clipboard().setText(password)

        @Slot()
        def selection_changed(self):
            empty = len(self.list.selectedItems()) == 0
            self.button_del.setDisabled(empty)
            self.button_copy.setDisabled(empty)

        @Slot()
        def run_service(self):
            self.set_run_service_cb()
            self.app.exit()


def run(set_run_service_cb):
    app = QApplication(["EteSync DAV - Manager"])
    widget = MainWindow(app, set_run_service_cb)
    widget.resize(800, 600)
    widget.show()

    return app.exec_()

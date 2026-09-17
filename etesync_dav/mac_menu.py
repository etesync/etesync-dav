"""macOS menu-bar integration for the standalone application."""

import json
import logging
import os
import signal
import socket
import threading
import webbrowser

import objc
from AppKit import (
    NSAppleEventManager,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSControlStateValueOff,
    NSControlStateValueOn,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWorkspace,
)
from Foundation import NSURL, NSObject
from PyObjCTools import AppHelper

from etesync_dav.config import DATA_DIR

logger = logging.getLogger("etesync-dav")
SETTINGS_FILE = os.path.join(DATA_DIR, "macos-settings.json")

# Apple Event four-character codes from AppleEvents.h.
AE_CORE_EVENT_CLASS = 0x61657674  # 'aevt'
AE_OPEN_APPLICATION = 0x6F617070  # 'oapp'
AE_PROPERTY_DATA = 0x70726474  # 'prdt'
AE_LAUNCHED_AS_LOGIN_ITEM = 0x6C676974  # 'lgit'


def launched_as_login_item(event):
    """Return whether an open-application event came from a login item."""
    if event is None or event.eventID() != AE_OPEN_APPLICATION:
        return False
    property_data = event.paramDescriptorForKeyword_(AE_PROPERTY_DATA)
    return property_data is not None and property_data.enumCodeValue() == AE_LAUNCHED_AS_LOGIN_ITEM


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file_handle:
        json.dump(settings, file_handle, indent=2)
        file_handle.write("\n")


def _login_service():
    try:
        from ServiceManagement import SMAppService

        return SMAppService.mainAppService()
    except Exception:
        logger.exception("Unable to access the macOS login-item service")
        return None


def _call_service(service, method):
    try:
        result = getattr(service, method)(None)
        return result[0] if isinstance(result, tuple) else bool(result)
    except Exception:
        logger.exception("Unable to update the macOS login-item setting")
        return False


class MenuBarController(NSObject):
    def initWithURL_logFile_shutdown_(self, url, log_file, shutdown):
        self = objc.super(MenuBarController, self).init()
        if self is None:
            return None
        self.url = url
        self.log_file = log_file
        self.shutdown = shutdown
        self.settings = load_settings()
        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = None
        return self

    def show_status_item(self):
        if self.status_item is not None:
            return
        self.status_item = self.status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        self.status_item.button().setTitle_("E")

        menu = NSMenu.alloc().init()
        menu.addItemWithTitle_action_keyEquivalent_("Open EteSync DAV", "openWebUI:", "o").setTarget_(self)
        if self.log_file:
            menu.addItemWithTitle_action_keyEquivalent_("Open Log", "openLog:", "l").setTarget_(self)

        settings_menu = NSMenu.alloc().init()
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Settings", None, "")
        settings_item.setSubmenu_(settings_menu)
        menu.addItem_(settings_item)

        login_item = settings_menu.addItemWithTitle_action_keyEquivalent_("Start at Login", "toggleStartAtLogin:", "")
        login_item.setTarget_(self)
        login_item.setState_(NSControlStateValueOn if self.login_item_enabled() else NSControlStateValueOff)

        hide_item = settings_menu.addItemWithTitle_action_keyEquivalent_("Hide from Menu Bar", "toggleMenuBar:", "")
        hide_item.setTarget_(self)
        hide_item.setState_(
            NSControlStateValueOn if self.settings.get("hide_menu_bar", False) else NSControlStateValueOff
        )

        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItemWithTitle_action_keyEquivalent_("Quit EteSync DAV", "quit:", "q").setTarget_(self)
        self.status_item.setMenu_(menu)

    def login_item_enabled(self):
        service = _login_service()
        if service is None:
            return False
        try:
            return service.status() == 1
        except Exception:
            logger.exception("Unable to read the macOS login-item status")
            return False

    def openWebUI_(self, sender):
        webbrowser.open(self.url)

    def openLog_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(self.log_file))

    def toggleStartAtLogin_(self, sender):
        service = _login_service()
        if service is None:
            return
        method = "unregisterAndReturnError_" if self.login_item_enabled() else "registerAndReturnError_"
        if _call_service(service, method):
            sender.setState_(NSControlStateValueOff if self.login_item_enabled() is False else NSControlStateValueOn)

    def toggleMenuBar_(self, sender):
        hidden = not self.settings.get("hide_menu_bar", False)
        self.settings["hide_menu_bar"] = hidden
        save_settings(self.settings)
        sender.setState_(NSControlStateValueOn if hidden else NSControlStateValueOff)
        if hidden:
            self.status_bar.removeStatusItem_(self.status_item)
            self.status_item = None

    def quit_(self, sender):
        self.shutdown()


class ApplicationDelegate(NSObject):
    def initWithController_(self, controller):
        self = objc.super(ApplicationDelegate, self).init()
        if self is None:
            return None
        self.controller = controller
        return self

    def applicationWillFinishLaunching_(self, notification):
        NSAppleEventManager.sharedAppleEventManager().setEventHandler_andSelector_forEventClass_andEventID_(
            self,
            "handleOpenApplication:withReplyEvent:",
            AE_CORE_EVENT_CLASS,
            AE_OPEN_APPLICATION,
        )

    def handleOpenApplication_withReplyEvent_(self, event, reply_event):
        if not (launched_as_login_item(event) and self.controller.settings.get("hide_menu_bar", False)):
            self.controller.show_status_item()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, application, has_visible_windows):
        self.controller.show_status_item()
        return True


def run_menu_bar(url, server_runner, log_file=None):
    """Run the server with a menu-bar control surface and no Dock icon."""
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    shutdown_socket, server_shutdown_socket = socket.socketpair()

    def shutdown(signal_number=None, stack_frame=None):
        try:
            shutdown_socket.close()
        except OSError:
            pass

    previous_signal_handlers = {
        signal_number: signal.signal(signal_number, shutdown) for signal_number in (signal.SIGTERM, signal.SIGINT)
    }

    controller = MenuBarController.alloc().initWithURL_logFile_shutdown_(url, log_file, shutdown)
    delegate = ApplicationDelegate.alloc().initWithController_(controller)
    app.setDelegate_(delegate)

    server_error = []

    def run_server():
        try:
            server_runner(server_shutdown_socket)
        except BaseException as error:
            server_error.append(error)
        finally:
            try:
                server_shutdown_socket.close()
            except OSError:
                pass
            # The server exiting (including startup failure) must not leave a
            # non-functional menu-bar application behind.
            AppHelper.callAfter(app.terminate_, None)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    try:
        AppHelper.runEventLoop()
        # The event loop can also be stopped by macOS rather than our menu.
        shutdown()
        server_thread.join()
    finally:
        for signal_number, previous_handler in previous_signal_handlers.items():
            signal.signal(signal_number, previous_handler)
        # Keep the controller and delegate alive until the event loop exits.
        del controller
        del delegate

    if server_error:
        raise server_error[0]

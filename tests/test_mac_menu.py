import sys
import unittest
from unittest.mock import Mock, patch

if sys.platform == "darwin":
    from etesync_dav import mac_menu


@unittest.skipUnless(sys.platform == "darwin", "macOS-only menu-bar integration")
class LoginItemEventTests(unittest.TestCase):
    def login_item_event(self):
        property_data = Mock()
        property_data.enumCodeValue.return_value = mac_menu.AE_LAUNCHED_AS_LOGIN_ITEM
        event = Mock()
        event.eventID.return_value = mac_menu.AE_OPEN_APPLICATION
        event.paramDescriptorForKeyword_.return_value = property_data
        return event

    def test_detects_login_item_open_application_event(self):
        event = self.login_item_event()

        self.assertTrue(mac_menu.launched_as_login_item(event))
        event.paramDescriptorForKeyword_.assert_called_once_with(mac_menu.AE_PROPERTY_DATA)

    def test_rejects_other_events(self):
        event = Mock()
        event.eventID.return_value = 0

        self.assertFalse(mac_menu.launched_as_login_item(event))
        event.paramDescriptorForKeyword_.assert_not_called()

    def test_login_launch_stays_hidden_when_configured(self):
        controller = Mock()
        controller.settings = {"hide_menu_bar": True}
        delegate = mac_menu.ApplicationDelegate.alloc().initWithController_(controller)

        delegate.handleOpenApplication_withReplyEvent_(self.login_item_event(), None)

        controller.show_status_item.assert_not_called()

    def test_registers_open_application_handler_before_launch_finishes(self):
        controller = Mock()
        delegate = mac_menu.ApplicationDelegate.alloc().initWithController_(controller)
        manager = Mock()

        with patch.object(mac_menu, "NSAppleEventManager") as event_manager:
            event_manager.sharedAppleEventManager.return_value = manager
            delegate.applicationWillFinishLaunching_(None)

        manager.setEventHandler_andSelector_forEventClass_andEventID_.assert_called_once_with(
            delegate,
            "handleOpenApplication:withReplyEvent:",
            mac_menu.AE_CORE_EVENT_CLASS,
            mac_menu.AE_OPEN_APPLICATION,
        )

    def test_regular_launch_shows_status_item(self):
        controller = Mock()
        controller.settings = {"hide_menu_bar": True}
        delegate = mac_menu.ApplicationDelegate.alloc().initWithController_(controller)
        event = Mock()
        event.eventID.return_value = mac_menu.AE_OPEN_APPLICATION
        event.paramDescriptorForKeyword_.return_value = None

        delegate.handleOpenApplication_withReplyEvent_(event, None)

        controller.show_status_item.assert_called_once_with()

    def test_rejects_open_event_without_login_item_property(self):
        event = Mock()
        event.eventID.return_value = mac_menu.AE_OPEN_APPLICATION
        event.paramDescriptorForKeyword_.return_value = None

        self.assertFalse(mac_menu.launched_as_login_item(event))

    def test_open_log_uses_default_application(self):
        log_url = Mock()

        with (
            patch.object(mac_menu, "NSStatusBar"),
            patch.object(mac_menu, "load_settings", return_value={}),
            patch.object(mac_menu, "NSWorkspace") as workspace_class,
            patch.object(mac_menu, "NSURL") as url_class,
        ):
            controller = mac_menu.MenuBarController.alloc().initWithURL_logFile_shutdown_(
                "http://example.test", "/tmp/etesync-dav.log", Mock()
            )
            url_class.fileURLWithPath_.return_value = log_url
            controller.openLog_(None)

        url_class.fileURLWithPath_.assert_called_once_with(controller.log_file)
        workspace_class.sharedWorkspace.return_value.openURL_.assert_called_once_with(log_url)


@unittest.skipUnless(sys.platform == "darwin", "macOS-only menu-bar integration")
class MenuBarRunnerTests(unittest.TestCase):
    def run_menu_bar(self, server_runner):
        app = Mock()
        controller = Mock()
        delegate = Mock()
        shutdown_socket = Mock()
        server_shutdown_socket = Mock()
        signal_handlers = {}

        class DeferredThread:
            def __init__(self, target, daemon):
                self.target = target

            def start(self):
                pass

            def join(self):
                self.target()

        def install_signal_handler(signal_number, handler):
            signal_handlers.setdefault(signal_number, handler)
            return Mock()

        with (
            patch.object(mac_menu, "NSApplication") as application_class,
            patch.object(mac_menu, "MenuBarController") as controller_class,
            patch.object(mac_menu, "ApplicationDelegate") as delegate_class,
            patch.object(mac_menu.socket, "socketpair", return_value=(shutdown_socket, server_shutdown_socket)),
            patch.object(mac_menu.signal, "signal", side_effect=install_signal_handler),
            patch.object(mac_menu.threading, "Thread", DeferredThread),
            patch.object(mac_menu.AppHelper, "runEventLoop"),
            patch.object(mac_menu.AppHelper, "callAfter") as call_after,
        ):
            application_class.sharedApplication.return_value = app
            controller_class.alloc.return_value.initWithURL_logFile_shutdown_.return_value = controller
            delegate_class.alloc.return_value.initWithController_.return_value = delegate
            try:
                mac_menu.run_menu_bar("http://example.test", server_runner)
            finally:
                # Exercise the installed handler directly, including repeated
                # delivery after the event loop requested shutdown.
                signal_handlers[mac_menu.signal.SIGTERM](None, None)

        return app, shutdown_socket, server_shutdown_socket, call_after

    def test_main_thread_signals_request_graceful_server_shutdown(self):
        server_runner = Mock()

        app, shutdown_socket, server_shutdown_socket, call_after = self.run_menu_bar(server_runner)

        server_runner.assert_called_once_with(server_shutdown_socket)
        self.assertGreaterEqual(shutdown_socket.close.call_count, 2)
        server_shutdown_socket.close.assert_called_once_with()
        call_after.assert_called_once_with(app.terminate_, None)

    def test_worker_system_exit_is_propagated(self):
        def fail(server_shutdown_socket):
            raise SystemExit(7)

        with self.assertRaisesRegex(SystemExit, "7"):
            self.run_menu_bar(fail)


if __name__ == "__main__":
    unittest.main()

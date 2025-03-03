import rumps
import threading
from pydexcom import Dexcom
from pydexcom.errors import AccountError

# Import Cocoa classes from PyObjC for custom UI
from Cocoa import (
    NSAlert,
    NSTextField,
    NSSecureTextField,
    NSPopUpButton,
    NSView,
    NSMakeRect,
    NSModalResponseOK,
    NSApplication,
    NSAlertFirstButtonReturn,
)

def get_credentials():
    """
    Show a custom Cocoa dialog with three fields:
      - Username (text field)
      - Password (secure text field)
      - Region (popup button with "us", "ous", "jp")
    Returns a tuple (username, password, region) if OK is pressed,
    or (None, None, None) if cancelled.
    """
    # Activate the app to ensure the alert is in focus.
    app = NSApplication.sharedApplication()
    app.activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Enter Dexcom Credentials")
    alert.setInformativeText_("Please enter your username, password, and select your region.")
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")
    
    # Create accessory view with enough space for our fields
    width, height = 300, 120
    accessory = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
    
    # Username label and text field
    username_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 80, 80, 22))
    username_label.setStringValue_("Username:")
    username_label.setEditable_(False)
    username_label.setBezeled_(False)
    username_label.setDrawsBackground_(False)
    
    username_field = NSTextField.alloc().initWithFrame_(NSMakeRect(90, 80, 200, 22))
    username_field.setEditable_(True)
    username_field.setStringValue_("")
    username_field.becomeFirstResponder()  # set focus on username field
    
    # Password label and secure text field
    password_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 50, 80, 22))
    password_label.setStringValue_("Password:")
    password_label.setEditable_(False)
    password_label.setBezeled_(False)
    password_label.setDrawsBackground_(False)
    
    password_field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(90, 50, 200, 22))
    password_field.setEditable_(True)
    password_field.setStringValue_("")
    
    # Region label and popup button
    region_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 20, 80, 22))
    region_label.setStringValue_("Region:")
    region_label.setEditable_(False)
    region_label.setBezeled_(False)
    region_label.setDrawsBackground_(False)
    
    region_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(90, 20, 200, 22))
    region_popup.addItemsWithTitles_(["us", "ous", "jp"])
    region_popup.selectItemAtIndex_(0)  # default to "us"
    
    # Add subviews to the accessory view
    accessory.addSubview_(username_label)
    accessory.addSubview_(username_field)
    accessory.addSubview_(password_label)
    accessory.addSubview_(password_field)
    accessory.addSubview_(region_label)
    accessory.addSubview_(region_popup)
    
    alert.setAccessoryView_(accessory)
    
    response = alert.runModal()
    if response == NSAlertFirstButtonReturn:
        # Convert returned values to Python strings
        username = str(username_field.stringValue())
        password = str(password_field.stringValue())
        region = str(region_popup.titleOfSelectedItem())
        return username, password, region
    else:
        return None, None, None

class DexcomMenuApp(rumps.App):
    def __init__(self):
        super(DexcomMenuApp, self).__init__("Dexcom")
        # In-memory credentials; consider persisting these securely.
        self.username = None
        self.password = None
        self.region = "us"  # Valid values: "us", "ous", "jp"
        self.dexcom = None

        # Variables for displaying data.
        self.current_value = None
        self.current_trend_arrow = None

        # Build menu items using rumps methods.
        self.menu.clear()
        self.menu.add("Update Now")
        self.menu["Update Now"].set_callback(self.manual_update)
        self.menu.add("Settings")
        self.menu["Settings"].set_callback(self.open_settings)
        self.menu.add("Quit")
        self.menu["Quit"].set_callback(lambda _: rumps.quit_application())

        # Show custom sign-in dialog if credentials are missing.
        if not self.username or not self.password:
            self.initial_setup()
        else:
            self.authenticate()

        # Fetch data immediately.
        self.update_data()
        # Create and start a timer that calls update_data every 300 seconds.
        timer = rumps.Timer(self.update_data, 300)
        timer.start()

    def initial_setup(self):
        """Display the custom sign-in UI for credentials."""
        creds = get_credentials()
        if creds[0] is None or creds[1] == "":
            print("DEBUG: Username:", creds[0], "Password length:", len(creds[1]) if creds[1] else 0, "Region:", creds[2])
            rumps.alert("Setup Cancelled", "Credentials are required.")
            rumps.quit_application()
        self.username, self.password, self.region = creds
        self.authenticate()

    def open_settings(self, _):
        """Display the custom dialog for updating credentials."""
        creds = get_credentials()
        if creds[0] is not None and creds[1] != "":
            self.username, self.password, self.region = creds
            self.authenticate()

    def authenticate(self):
        """Instantiate the Dexcom object using pydexcom."""
        try:
            self.dexcom = Dexcom(username=self.username, password=self.password, region=self.region)
        except AccountError as e:
            rumps.alert("Authentication Error", str(e))
            self.dexcom = None

    def manual_update(self, _):
        """Trigger a manual update of the glucose data."""
        self.update_data()

    def update_data(self, _=None):
        """Fetch the latest glucose reading in a background thread."""
        threading.Thread(target=self.fetch_data).start()

    def fetch_data(self):
        if not self.dexcom:
            self.authenticate()
            if not self.dexcom:
                return
        try:
            reading = self.dexcom.get_current_glucose_reading()
            if reading is not None:
                self.current_value = reading.value
                self.current_trend_arrow = reading.trend_arrow
            else:
                self.current_value = "N/A"
                self.current_trend_arrow = "?"
        except Exception as e:
            print("Error fetching Dexcom data:", e)
            self.current_value = "Err"
            self.current_trend_arrow = "?"
        # Update the display on the main thread.
        from Cocoa import NSOperationQueue
        NSOperationQueue.mainQueue().addOperationWithBlock_(self.refresh_display)

    def refresh_display(self):
        """Update the menu bar title with the current glucose reading."""
        self.title = f"[{self.current_value}][{self.current_trend_arrow}]"

if __name__ == "__main__":
    DexcomMenuApp().run()

import rumps
import threading
import json
import os
from pydexcom import Dexcom
from pydexcom.errors import AccountError

# Import Cocoa classes for custom dialogs and to hide the dock icon.
from Cocoa import (
    NSAlert,
    NSTextField,
    NSSecureTextField,
    NSPopUpButton,
    NSView,
    NSMakeRect,
    NSAlertFirstButtonReturn,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSColor,
    NSAttributedString,
    NSFont,
    NSAlertStyleInformational,
)

SETTINGS_FILE = "settings.json"

# ----- Persistent Settings Functions -----

def load_settings():
    """Load settings from SETTINGS_FILE, or return defaults if file not found."""
    defaults = {
        "username": "",
        "password": "",
        "region": "us",
        "style_settings": {
            "number_low": "Low: %s",
            "number_normal": "Normal: %s",
            "number_high": "High: %s",
            "arrow_steady": "→",
            "arrow_rising": "↑",
            "arrow_falling": "↓",
            "show_brackets": True
        },
        "preferences": {
            "low_threshold": 70.0,
            "high_threshold": 180.0,
            "notifications": True
        }
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading settings:", e)
            return defaults
    return defaults

def save_settings(settings):
    """Save settings to SETTINGS_FILE."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception as e:
        print("Error saving settings:", e)

# ----- Custom Dialogs -----

def get_credentials():
    """
    Display a custom sign‐in dialog with three separate fields (Account settings):
      - Username (text field)
      - Password (secure text field)
      - Region (popup with "us", "ous", "jp")
    Returns a tuple (username, password, region) if OK is pressed, or (None, None, None) if cancelled.
    """
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Account Settings")
    alert.setInformativeText_("Please enter your Dexcom username, password, and select your region.")
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")
    
    width = 300
    height = 120
    accessory = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
    
    # Layout coordinates
    username_y = 80
    password_y = 50
    region_y   = 20

    # Username
    username_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, username_y, 80, 22))
    username_label.setStringValue_("Username:")
    username_label.setEditable_(False)
    username_label.setBezeled_(False)
    username_label.setDrawsBackground_(False)
    
    username_field = NSTextField.alloc().initWithFrame_(NSMakeRect(90, username_y, 200, 22))
    username_field.setEditable_(True)
    username_field.setStringValue_("")
    username_field.becomeFirstResponder()  # Focus
    
    # Password
    password_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, password_y, 80, 22))
    password_label.setStringValue_("Password:")
    password_label.setEditable_(False)
    password_label.setBezeled_(False)
    password_label.setDrawsBackground_(False)
    
    password_field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(90, password_y, 200, 22))
    password_field.setEditable_(True)
    password_field.setStringValue_("")
    
    # Region
    region_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, region_y, 80, 22))
    region_label.setStringValue_("Region:")
    region_label.setEditable_(False)
    region_label.setBezeled_(False)
    region_label.setDrawsBackground_(False)
    
    region_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(90, region_y, 200, 22))
    region_popup.addItemsWithTitles_(["us", "ous", "jp"])
    region_popup.selectItemAtIndex_(0)
    
    accessory.addSubview_(username_label)
    accessory.addSubview_(username_field)
    accessory.addSubview_(password_label)
    accessory.addSubview_(password_field)
    accessory.addSubview_(region_label)
    accessory.addSubview_(region_popup)
    
    alert.setAccessoryView_(accessory)
    
    response = alert.runModal()
    if response == NSAlertFirstButtonReturn:
        username = str(username_field.stringValue())
        password = str(password_field.stringValue())
        region = str(region_popup.titleOfSelectedItem())
        return username, password, region
    else:
        return None, None, None

def get_style_settings(current_style):
    """
    Display a custom dialog for Style settings.
    Fields:
      - Low Number Style
      - Normal Number Style
      - High Number Style
      - Steady Arrow
      - Rising Arrow
      - Falling Arrow
      - Show Brackets (true/false)
    current_style is a dict with current values.
    Returns a dict of style settings if OK is pressed, else None.
    """
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Style Settings")
    alert.setInformativeText_("Configure the display style. Use %s as a placeholder for the number.")
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")
    
    width = 350
    height = 200
    accessory = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
    
    labels = ["Low Number Style:", "Normal Number Style:", "High Number Style:",
              "Steady Arrow:", "Rising Arrow:", "Falling Arrow:", "Show Brackets (true/false):"]
    keys = ["number_low", "number_normal", "number_high",
            "arrow_steady", "arrow_rising", "arrow_falling", "show_brackets"]
    fields = {}
    
    y_start = 160
    delta = 25
    for i, label_text in enumerate(labels):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, y_start - i*delta, 150, 22))
        label.setStringValue_(label_text)
        label.setEditable_(False)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(160, y_start - i*delta, 180, 22))
        default = current_style.get(keys[i], "") if current_style else ""
        field.setStringValue_(default)
        accessory.addSubview_(label)
        accessory.addSubview_(field)
        fields[keys[i]] = field

    alert.setAccessoryView_(accessory)
    response = alert.runModal()
    if response == NSAlertFirstButtonReturn:
        new_style = {}
        for key, field in fields.items():
            val = str(field.stringValue())
            if key == "show_brackets":
                new_style[key] = (val.lower() == "true")
            else:
                new_style[key] = val
        return new_style
    else:
        return None

def get_preferences(current_prefs):
    """
    Display a custom dialog for Preferences.
    Fields:
      - Low Threshold (numeric)
      - High Threshold (numeric)
      - Notifications (true/false)
    Returns a dict of preferences if OK is pressed, else None.
    """
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Preferences")
    alert.setInformativeText_("Set acceptable ranges and notifications.")
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")
    
    width = 350
    height = 120
    accessory = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
    
    labels = ["Low Threshold:", "High Threshold:", "Notifications (true/false):"]
    keys = ["low_threshold", "high_threshold", "notifications"]
    fields = {}
    
    y_start = 90
    delta = 30
    for i, label_text in enumerate(labels):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, y_start - i*delta, 150, 22))
        label.setStringValue_(label_text)
        label.setEditable_(False)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(160, y_start - i*delta, 180, 22))
        default = str(current_prefs.get(keys[i], "")) if current_prefs else ""
        field.setStringValue_(default)
        accessory.addSubview_(label)
        accessory.addSubview_(field)
        fields[keys[i]] = field

    alert.setAccessoryView_(accessory)
    response = alert.runModal()
    if response == NSAlertFirstButtonReturn:
        new_prefs = {}
        try:
            new_prefs["low_threshold"] = float(str(fields["low_threshold"].stringValue()))
        except:
            new_prefs["low_threshold"] = 70.0
        try:
            new_prefs["high_threshold"] = float(str(fields["high_threshold"].stringValue()))
        except:
            new_prefs["high_threshold"] = 180.0
        new_prefs["notifications"] = (str(fields["notifications"].stringValue()).lower() == "true")
        return new_prefs
    else:
        return None

# ----- Main Application -----

class DexcomMenuApp(rumps.App):
    def __init__(self):
        # Hide Dock icon.
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        super(DexcomMenuApp, self).__init__("Dexcom")
        # Load settings or use defaults.
        settings = load_settings()
        self.username = settings.get("username", "")
        self.password = settings.get("password", "")
        self.region = settings.get("region", "us")
        self.style_settings = settings.get("style_settings", {
            "number_low": "Low: %s",
            "number_normal": "Normal: %s",
            "number_high": "High: %s",
            "arrow_steady": "→",
            "arrow_rising": "↑",
            "arrow_falling": "↓",
            "show_brackets": True
        })
        self.preferences = settings.get("preferences", {
            "low_threshold": 70.0,
            "high_threshold": 180.0,
            "notifications": True
        })
        self.dexcom = None

        # Data display
        self.current_value = None
        self.current_trend_arrow = None

        # Build menu items
        self.menu.clear()
        self.menu.add("Update Now")
        self.menu["Update Now"].set_callback(self.manual_update)
        self.menu.add("Account")
        self.menu["Account"].set_callback(self.open_account_settings)
        self.menu.add("Style")
        self.menu["Style"].set_callback(self.open_style_settings)
        self.menu.add("Preferences")
        self.menu["Preferences"].set_callback(self.open_preferences)

        # If no account info, prompt for it.
        if not self.username or not self.password:
            self.open_account_settings(None)
        else:
            self.authenticate()

        # Fetch data immediately and start a timer to update every 5 minutes.
        self.update_data()
        timer = rumps.Timer(self.update_data, 300)
        timer.start()

    def open_account_settings(self, _):
        creds = get_credentials()
        if creds[0] is None or creds[1] == "":
            rumps.alert("Setup Cancelled", "Credentials are required.")
            return
        self.username, self.password, self.region = creds
        self.authenticate()
        self.persist_settings()

    def open_style_settings(self, _):
        new_style = get_style_settings(self.style_settings)
        if new_style:
            self.style_settings = new_style
            rumps.alert("Style Updated", "New style settings have been applied.")
            self.refresh_display()
            self.persist_settings()

    def open_preferences(self, _):
        new_prefs = get_preferences(self.preferences)
        if new_prefs:
            self.preferences = new_prefs
            rumps.alert("Preferences Updated", "New preferences have been applied.")
            self.refresh_display()
            self.persist_settings()

    def authenticate(self):
        try:
            self.dexcom = Dexcom(username=self.username, password=self.password, region=self.region)
        except AccountError as e:
            rumps.alert("Authentication Error", str(e))
            self.dexcom = None

    def manual_update(self, _):
        self.update_data()

    def update_data(self, _=None):
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
                try:
                    value = float(self.current_value)
                except:
                    value = 0
                if value < self.preferences["low_threshold"]:
                    number_format = self.style_settings["number_low"]
                    arrow_override = self.style_settings["arrow_falling"]
                elif value > self.preferences["high_threshold"]:
                    number_format = self.style_settings["number_high"]
                    arrow_override = self.style_settings["arrow_rising"]
                else:
                    number_format = self.style_settings["number_normal"]
                    arrow_override = self.style_settings["arrow_steady"]
                number_text = number_format % self.current_value
                if self.style_settings.get("show_brackets", True):
                    display_text = f"[{number_text}][{arrow_override}]"
                else:
                    display_text = f"{number_text} {arrow_override}"
            else:
                display_text = "[N/A][?]"
        except Exception as e:
            print("Error fetching Dexcom data:", e)
            display_text = "[Err][?]"
        from Cocoa import NSOperationQueue
        NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: self.refresh_display_with_text(display_text))

    def refresh_display_with_text(self, text):
        try:
            value = float(self.current_value)
        except:
            value = 0
        color = NSColor.redColor() if value > self.preferences["high_threshold"] or value < self.preferences["low_threshold"] else NSColor.blackColor()
        attributes = {"NSForegroundColorAttributeName": color,
                      "NSFont": NSFont.systemFontOfSize_(12)}
        attributed_title = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
        if hasattr(self, '_status_item') and self._status_item.button:
            self._status_item.button.setAttributedTitle_(attributed_title)
        else:
            self.title = text

    def persist_settings(self):
        settings = {
            "username": self.username,
            "password": self.password,
            "region": self.region,
            "style_settings": self.style_settings,
            "preferences": self.preferences
        }
        save_settings(settings)

if __name__ == "__main__":
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    DexcomMenuApp().run()

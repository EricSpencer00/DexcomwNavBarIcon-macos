import rumps
import threading
from pydexcom import Dexcom
from pydexcom.errors import AccountError
from Cocoa import NSOperationQueue

class DexcomMenuApp(rumps.App):
    def __init__(self):
        super(DexcomMenuApp, self).__init__("Dexcom")
        # In-memory credentials (consider persisting these securely for production)
        self.username = None
        self.password = None
        self.region = "us"  # Valid values: "us", "ous", "jp"
        self.dexcom = None

        # Variables for displaying data.
        self.current_value = None
        self.current_trend_arrow = None

        # Build menu items.
        self.menu.clear()
        self.menu.add("Update Now")
        self.menu["Update Now"].set_callback(self.manual_update)
        self.menu.add("Settings")
        self.menu["Settings"].set_callback(self.open_settings)
        self.menu.add("Quit")
        self.menu["Quit"].set_callback(lambda _: rumps.quit_application())

        # Combined sign-in UI if credentials are missing.
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
        """
        Display a single-window sign-in UI.
        Enter credentials in the format:
          username,password,region
        For example:
          user@example.com,mysecret,us
        """
        prompt = ("Enter Dexcom credentials as: username,password,region\n"
                  "(e.g., user@example.com,mysecret,us)")
        credentials_win = rumps.Window(message=prompt,
                                       title="Initial Setup",
                                       default_text="")
        response = credentials_win.run()
        if response.clicked and response.text.strip():
            parts = response.text.strip().split(",")
            if len(parts) != 3:
                rumps.alert("Invalid Format",
                            "Please enter credentials in the format: username,password,region")
                rumps.quit_application()
            self.username = parts[0].strip()
            self.password = parts[1].strip()
            self.region = parts[2].strip().lower()
        else:
            rumps.alert("Setup Cancelled", "Credentials are required.")
            rumps.quit_application()
        self.authenticate()

    def open_settings(self, _):
        """
        Allow updating credentials using a single-window UI.
        The prompt displays the current username and region.
        """
        prompt = (f"Current credentials:\nUsername: {self.username}\nRegion: {self.region}\n\n"
                  "Enter new credentials as: username,password,region")
        credentials_win = rumps.Window(message=prompt,
                                       title="Settings",
                                       default_text="")
        response = credentials_win.run()
        if response.clicked and response.text.strip():
            parts = response.text.strip().split(",")
            if len(parts) != 3:
                rumps.alert("Invalid Format",
                            "Please enter credentials in the format: username,password,region")
                return
            self.username = parts[0].strip()
            self.password = parts[1].strip()
            self.region = parts[2].strip().lower()
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
        # Schedule refresh_display to run on the main thread.
        NSOperationQueue.mainQueue().addOperationWithBlock_(self.refresh_display)

    def refresh_display(self):
        """Update the menu bar title to display the glucose reading."""
        self.title = f"[{self.current_value}][{self.current_trend_arrow}]"

if __name__ == "__main__":
    DexcomMenuApp().run()

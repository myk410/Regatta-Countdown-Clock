#!/home/myk410/countdownenv/bin/python3

import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import Toplevel, Label, Button
from threading import Thread, Event
import re
import socket
import ntplib
from datetime import datetime, timedelta
import time
import threading
import RPi.GPIO as GPIO

# Initialize global variables
green = "#00FF00"
original_start_time = None
countdown_time = [0]  # Stores the countdown time in seconds
countdown_stop_event = Event()
countdown_thread = None
start_time_label = None
last_button_press_time = 0
keypad_context = "main"
dialog = None
custom_message_box = None

#time.sleep(15)

class CustomMessageBox(tk.Toplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("Message")
        self.geometry("400x200")  # Adjust size as needed
        self.message_label = tk.Label(self, text=message, wraplength=350)
        self.message_label.pack(pady=20)
        self.ok_button = tk.Button(self, text="OK", command=self.destroy)
        self.ok_button.pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.destroy)  # Handle window close button
        self.transient(parent)  # Show above the parent window
        self.grab_set()  # Block input to other windows until this one is closed

    # Method to programmatically close the message box
    def close(self):
        global custom_message_box
        custom_message_box = None  # Reset the global reference
        self.destroy()

# Setup GPIO for keypad
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
keypad = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]
ROWS = [5, 6, 13, 19]
COLUMNS = [26, 16, 20, 21]

for row in ROWS:
    GPIO.setup(row, GPIO.OUT, initial=GPIO.LOW)

for col in COLUMNS:
    GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
def read_keypad():
    for row_index, row_pin in enumerate(ROWS):
        GPIO.output(row_pin, GPIO.HIGH)
        
        for column_index, column_pin in enumerate(COLUMNS):
            if GPIO.input(column_pin) == GPIO.HIGH:
                GPIO.output(row_pin, GPIO.LOW)  # Reset the current row before returning
                return keypad[row_index][column_index]
        
        GPIO.output(row_pin, GPIO.LOW)  # Reset the row before moving to the next one
    
    return None  # No key press detected

def keypad_handler():
    global last_button_press_time, custom_message_box, keypad_context
    while True:
        key = read_keypad()
        if key and time.time() - last_button_press_time > 0.3:  # Debounce
            last_button_press_time = time.time()

            # If a custom message box is displayed, any key press should close it
            if custom_message_box is not None:
                custom_message_box.close()
                custom_message_box = None
                continue  # Skip further processing to avoid unwanted actions

            # Process keypress based on the current context
            if keypad_context == "main":
                process_main_window_key(key)
            elif keypad_context == "dialog":
                process_dialog_key(key)
                
        time.sleep(0.1)

def process_main_window_key(key):
    if key == "*":
        root.after(0, lambda: set_time_button.invoke())
    elif key == "A":
        root.after(0, lambda: back_five_minutes_button.invoke())
    elif key == "B":
        root.after(0, lambda: back_minute_button.invoke())
    elif key == "C":
        root.after(0, lambda: next_minute_button.invoke())
    elif key == "D":
        root.after(0, lambda: next_five_minutes_button.invoke())

def process_dialog_key(key):
    global dialog
    if dialog is not None:
        if key == "*":
            root.after(0, lambda: dialog.set_input_mode("hour"))
        elif key == "#":
            root.after(0, lambda: dialog.set_input_mode("minute"))
        elif key == "A":
            root.after(0, dialog.on_set)
        elif key == "B":
            root.after(0, dialog.clear_input)
        elif key == "C":
            root.after(0, dialog.on_cancel)
        elif key == "D":
            root.after(0, dialog.toggle_am_pm)
        elif key.isdigit():
            root.after(0, lambda: dialog.append_digit(int(key)))

# Initialize threading for keypad handling
threading.Thread(target=keypad_handler, daemon=True).start()

class TouchTimeDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        global keypad_context
        keypad_context = "dialog"
        self.attributes('-fullscreen', True)
        self.geometry("800x480+0+0")
        self.title("Set Start Time")
        
        def set_pop_fullscreen():
            self.attributes('-fullscreen', True)
            
        self.after(400, set_pop_fullscreen)
        
        # Make the popup related to the root window, helps with window stacking
        self.transient(parent)
        self.grab_set()
        
        self.hour_str = tk.StringVar(self, "12")
        self.minute_str = tk.StringVar(self, "00")
        self.am_pm = tk.StringVar(self, "AM")
        
        self.input_mode = "hour"  # Start with 'hour' as the default input mode
        
        self.setup_ui()
        
        # To keep track of the dialog result
        self.result = None
        
        # Override the destroy method
        self.protocol("WM_DELETE_WINDOW", self.custom_destroy)  # Handle window close button

    def setup_ui(self):
        display_size = 40
        button_size = 40
        ctr_butt_width = 6
        num_butt_width = 2
        num_butt_height = 1
        
        self.time_display = tk.Frame(self)
        self.time_display.pack(side=tk.TOP, pady=2)
        
        buttons = tk.Frame(self)
        buttons.pack(side=tk.TOP, pady=5)
        
        num_buttons = tk.Frame(buttons)
        num_buttons.pack(side=tk.LEFT, pady=5)
        
        control_buttons = tk.Frame(buttons)
        control_buttons.pack(side=tk.LEFT, pady=5, padx=40)
        
        # Label for hour input
        self.hour_label = tk.Label(self.time_display, textvariable=self.hour_str, font=("Avenir", display_size), bg="lightgrey")
        self.hour_label.grid(row=0, column=0)
        self.hour_label.bind("<Button-1>", lambda e: self.set_input_mode("hour"))  # Bind click event
        
        colon_label = tk.Label(self.time_display, text=":", font=("Avenir", display_size))
        colon_label.grid(row=0, column=1)
        
        # Label for minute input
        self.minute_label = tk.Label(self.time_display, textvariable=self.minute_str, font=("Avenir", display_size))
        self.minute_label.grid(row=0, column=2)
        self.minute_label.bind("<Button-1>", lambda e: self.set_input_mode("minute"))  # Bind click event
        
        # AM/PM toggle button
        am_pm_label = tk.Button(self.time_display, textvariable=self.am_pm, command=self.toggle_am_pm, font=("Avenir", display_size))
        am_pm_label.grid(row=0, column=3)
        
        # Numeric buttons
        for i in range(1, 10):
            btn = tk.Button(num_buttons, text=str(i), command=lambda n=i: self.append_digit(n), font=("Avenir", button_size), width=num_butt_width, height=num_butt_height)
            btn.grid(row=(i-1)//3, column=(i-1)%3, pady=2, padx=2)
            
        btn_zero = tk.Button(num_buttons, text="0", command=lambda: self.append_digit(0), font=("Avenir", button_size), width=num_butt_width, height=num_butt_height)
        btn_zero.grid(row=3, column=1, pady=2, padx=2)
        
        # Control buttons
        btn_cancel = tk.Button(control_buttons, text="Cancel", command=self.on_cancel, font=("Avenir", button_size), width=ctr_butt_width)
        btn_cancel.grid(row=2, column=0, padx=2)
        
        btn_clear = tk.Button(control_buttons, text="Clear", command=self.clear_input, font=("Avenir", button_size), width=ctr_butt_width)
        btn_clear.grid(row=1, column=0, padx=2)
        
        set_button = tk.Button(control_buttons, text="Set", command=self.on_set, font=("Avenir", button_size), width=ctr_butt_width)
        set_button.grid(row=0, column=0, padx=2)
        
        self.update_highlight()
        self.focus_set()
    
    def custom_destroy(self):
        global keypad_context
        keypad_context = "main"  # Reset context to main when dialog is closed
        self.destroy()
        
    def on_cancel(self):
        global keypad_context
        keypad_context = "main"  # Reset context to main when cancel is clicked
        self.destroy()
        
    def toggle_am_pm(self):
        self.am_pm.set("PM" if self.am_pm.get() == "AM" else "AM")
        
    def set_input_mode(self, mode):
        self.input_mode = mode
        self.update_highlight()
        
    def clear_input(self):
        if self.input_mode == "hour":
            self.hour_str.set("12")
        else:
            self.minute_str.set("00")
            
    def append_digit(self, digit):
        if self.input_mode == "hour":
            current = self.hour_str.get()
            # Update logic to allow changing both digits
            new_value = (current + str(digit))[-2:]  # Keep only the last two characters
            new_value_int = int(new_value)
            if new_value_int == 0:
                new_value_int = 12  # Handle special case for 0 hour
            elif new_value_int > 12:
                new_value_int = digit  # Reset to the last digit entered if over 12
            self.hour_str.set(f"{new_value_int:02}")
        else:  # minute mode
            current = self.minute_str.get()
            # Similar update logic for minutes
            new_value = (current + str(digit))[-2:]  # Keep only the last two characters
            new_value_int = int(new_value)
            if new_value_int >= 60:
                new_value_int = digit  # Reset to the last digit entered if over 59
            self.minute_str.set(f"{new_value_int:02}")
                
    def on_set(self):
        global keypad_context
        hour = self.hour_str.get().zfill(2)
        minute = self.minute_str.get().zfill(2)
        self.result = f"{hour}:{minute} {self.am_pm.get()}"
        keypad_context = "main"  # Reset context to main when time is set
        self.destroy()
    
    def update_highlight(self):
        default_bg_color = "lightgray"  # or any color that fits your theme
        highlight_color = "yellow"
        
        if self.input_mode == "hour":
            self.hour_label.config(bg=highlight_color)
            self.minute_label.config(bg=default_bg_color)
        else:
            self.hour_label.config(bg=default_bg_color)
            self.minute_label.config(bg=highlight_color)

def get_ntp_time():
    global custom_message_box
    client = ntplib.NTPClient()
    try:
        response = client.request('pool.ntp.org')
        ntp_time = datetime.fromtimestamp(response.tx_time)
        return ntp_time.replace(tzinfo=None)  # Remove timezone information for comparison
    except Exception as e:
        if custom_message_box is not None:
            custom_message_box.close()
        custom_message_box = CustomMessageBox(root, f"Failed to get NTP time: {e}")
        return None
    
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return "Error: " + str(e)
    
def is_debounced(min_interval=0.3):
    global last_button_press_time
    current_time = time.time()
    if (current_time - last_button_press_time) >= min_interval:
        last_button_press_time = current_time
        return True
    return False
    
def debounce(wait):
    """ Decorator that prevents a function from being called more than once every wait period. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                try:
                    debounced._timer.cancel()
                except AttributeError:
                    pass
                debounced._timer = threading.Timer(wait, fn, args=args, kwargs=kwargs)
                debounced._timer.start()
            return call_it
        return debounced
    return decorator
    
def set_race_time():
    global original_start_time, countdown_time, start_time_label, dialog, custom_message_box
    dialog = TouchTimeDialog(root)
    root.wait_window(dialog)  # Wait for the dialog to close
    if dialog is not None:  # Check if dialog is not None to avoid AttributeError
        time_input = dialog.result  # Temporarily store the result
    else:
        time_input = None  # Ensure time_input has a defined value even if dialog is None
    
    dialog = None  # Clear the dialog variable after closing
    
    if time_input:
        try:
            parsed_time = parse_time_input(time_input)
            if parsed_time:
                original_start_time = parsed_time
                ntp_now = get_ntp_time()
                if ntp_now is None:
                    if custom_message_box is not None:
                        custom_message_box.close()
                    custom_message_box = CustomMessageBox(root, "Could not synchronize with NTP time.")
                    return
                if original_start_time <= ntp_now:
                    if custom_message_box is not None:
                        custom_message_box.close()
                    custom_message_box = CustomMessageBox(root, "The specified time is in the past. Please enter a future time.")
                    return
                
                duration = (original_start_time - ntp_now).total_seconds()
                countdown_time[0] = duration
                start_countdown()
                start_time_label.config(text=f"Start Time: {original_start_time.strftime('%H:%M:%S')}")
                #messagebox.showinfo("Success", "Race start time set successfully.")
        except ValueError as e:
            if custom_message_box is not None:
                custom_message_box.close()
            custom_message_box = CustomMessageBox(root, str(e))

            
def start_countdown():
    global countdown_stop_event, countdown_thread, countdown_time
    countdown_stop_event.set()  # Signal any existing thread to stop
    
    if countdown_thread and countdown_thread.is_alive():
        countdown_thread.join(timeout=1)  # Wait for up to 1 second for the thread to stop
        if countdown_thread.is_alive():
            # Log or handle the scenario where the thread didn't stop as expected
            print("Warning: Countdown thread did not stop as expected.")
            
    countdown_stop_event.clear()  # Reset the event for the new countdown
    countdown_thread = Thread(target=update_countdown, daemon=True)
    countdown_thread.start()
    
def update_countdown():
    global countdown_time, countdown_stop_event
    end_time = datetime.now() + timedelta(seconds=countdown_time[0])
    while not countdown_stop_event.is_set() and datetime.now() < end_time:
        now = datetime.now()
        remaining = (end_time - now).total_seconds()
        countdown_time[0] = remaining
        mins, secs = divmod(int(remaining), 60)
        if mins < 10:
            countdown_label.config(text=f"{mins}:{secs:02d}")  # Removes leading zero for minutes less than 10
        else:
            countdown_label.config(text=f"{mins:02d}:{secs:02d}")
        time.sleep(1)
    if not countdown_stop_event.is_set():
        countdown_label.config(text="00:00")
        
def adjust_race_time(minutes):
    global original_start_time, countdown_time, start_time_label, last_button_press_time, custom_message_box
    
    # Use is_debounced directly to check if the function call should proceed
    if not is_debounced(0.3):  # Adjust the debounce interval as needed
        # Optionally, inform the user or log that the action is debounced
        print("Action debounced, please wait.")
        return

    if original_start_time is None:
        if custom_message_box is not None:
            custom_message_box.close()
        custom_message_box = CustomMessageBox(root, "Please set the race start time first.")
        return

    ntp_now = get_ntp_time()
    if ntp_now is None:
        if custom_message_box is not None:
            custom_message_box.close()
        custom_message_box = CustomMessageBox(root, "Could not synchronize with NTP time.")
        return

    # Calculate the new adjusted time
    adjusted_time = original_start_time + timedelta(minutes=minutes)
    
    # Perform checks and set the new original_start_time as needed
    if adjusted_time <= ntp_now:
        messagebox.showinfo("Info", "Adjusting to nearest future minute.")
        adjusted_time = ntp_now + timedelta(minutes=(1 if minutes > 0 else -1))
        
    original_start_time = adjusted_time
    
    # Recalculate the countdown and update UI
    duration = (original_start_time - ntp_now).total_seconds()
    countdown_time[0] = duration
    start_countdown()
    start_time_label.config(text=f"Start Time: {original_start_time.strftime('%H:%M:%S')}")
        
def parse_time_input(time_input):
    global custom_message_box
    try:
        ntp_now = get_ntp_time()
        if ntp_now is None:
            # Optionally, inform the user that the system will use the local time instead of NTP time
            if custom_message_box is not None:
                custom_message_box.close()
            custom_message_box = CustomMessageBox(root, "Using system's local time due to NTP time fetch failure.")
            ntp_now = datetime.now()  # Use system's local time as a fallback
            
        time_pattern = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?")
        match = time_pattern.match(time_input)
        if not match:
            raise ValueError("Invalid time format. Please use HH:MM or HH:MM AM/PM format.")
            
        hour, minute, period = match.groups()
        hour, minute = int(hour), int(minute)
        if period:  # Adjust for AM/PM
            if "PM" in period.upper() and hour < 12:
                hour += 12
            elif "AM" in period.upper() and hour == 12:
                hour = 0
                
        # Adjust for the next day if the time is past
        adjusted_time = ntp_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if adjusted_time < ntp_now:
            adjusted_time += timedelta(days=1)
            
        return adjusted_time
    except ValueError as e:
        if custom_message_box is not None:
            custom_message_box.close()
        custom_message_box = CustomMessageBox(root, str(e))
        return None

# GUI Setup
root = tk.Tk()
root.title("Countdown Clock")
root.geometry("800x480")
root.configure(bg='white')

def set_fullscreen():
    root.attributes('-fullscreen', True)
    
root.after(400, set_fullscreen)

# To toggle full-screen off (e.g., by pressing a key)
def toggle_fullscreen(event=None):
    root.attributes('-fullscreen', False)

# Bind the toggle function to a key, for example, F11
root.bind('<F11>', toggle_fullscreen)

info_frame = tk.Frame(root)
info_frame.pack(pady=10)

ip_address = get_ip_address()
instruct_label = tk.Label(info_frame, text="Use 'VNC Viewer' to Screen Share", font=("Avenir", 14))
ip_label = tk.Label(info_frame, text=f"IP Address: {ip_address}", font=("Avenir", 14))
instruct_label.pack()
ip_label.pack()

start_time_label = tk.Label(info_frame, text="Start Time: Not set", font=("Avenir", 14))
start_time_label.pack(pady=2)

timer_frame = tk.Frame(root, bg=green)
timer_frame.pack(pady=10)

countdown_label = tk.Label(timer_frame, bg=green, text="00:00", font=("Avenir", 50))
countdown_label.pack(pady=10, padx=20)

buttons_frame = tk.Frame(root)
buttons_frame.pack(pady=10)

button_font_size = 40
ctr_butt_pady = 20

set_time_button = tk.Button(buttons_frame, text="Set Start Time", command=set_race_time, font=("Avenir", button_font_size))
set_time_button.grid(row=0,column=0, padx=5, columnspan=4)

back_five_minutes_button = tk.Button(buttons_frame, text="◀◀ 5", command=lambda: adjust_race_time(-5), font=("Avenir", button_font_size))
back_five_minutes_button.grid(row=1,column=0, padx=5, pady=ctr_butt_pady)

back_minute_button = tk.Button(buttons_frame, text="◀ 1", command=lambda: adjust_race_time(-1), font=("Avenir", button_font_size))
back_minute_button.grid(row=1,column=1, padx=5, pady=ctr_butt_pady)

next_minute_button = tk.Button(buttons_frame, text="1 ▶", command=lambda: adjust_race_time(1), font=("Avenir", button_font_size))
next_minute_button.grid(row=1,column=2, padx=5, pady=ctr_butt_pady)

next_five_minutes_button = tk.Button(buttons_frame, text="5 ▶▶", command=lambda: adjust_race_time(5), font=("Avenir", button_font_size))
next_five_minutes_button.grid(row=1,column=3, padx=5, pady=ctr_butt_pady)

root.mainloop()

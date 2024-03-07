#!/usr/bin/env python3

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

# Initialize global variables
green = "#00FF00"
original_start_time = None
countdown_time = [0]  # Stores the countdown time in seconds
countdown_stop_event = Event()
countdown_thread = None
start_time_label = None
last_button_press_time = 0

class TouchTimeDialog(tk.Toplevel):
	def __init__(self, parent):
		super().__init__(parent)
		self.title("Set Race Start Time")
		
		self.hour_str = tk.StringVar(self, "12")
		self.minute_str = tk.StringVar(self, "00")
		self.am_pm = tk.StringVar(self, "AM")
		
		self.input_mode = "hour"  # Can be 'hour' or 'minute'
		
		self.setup_ui()
		
		# To keep track of the dialog result
		self.result = None
		
	def setup_ui(self):
		display_size = 40
		button_size = 40
		
		self.time_display = tk.Frame(self)
		self.time_display.pack(side=tk.TOP, pady=5)
		
		num_buttons = tk.Frame(self)
		num_buttons.pack(side=tk.TOP, pady=5)
		
		control_buttons = tk.Frame(self)
		control_buttons.pack(side=tk.TOP, pady=5)
		
		self.hour_label = tk.Label(self.time_display, textvariable=self.hour_str, font=("Avenir", display_size), bg="lightgrey")  # Initial highlight
		self.hour_label.grid(row=0, column=0)
		
		colon_label = tk.Label(self.time_display, text=":", font=("Avenir", display_size))
		colon_label.grid(row=0, column=1)
		
		self.minute_label = tk.Label(self.time_display, textvariable=self.minute_str, font=("Avenir", display_size))
		self.minute_label.grid(row=0, column=2)
		
		am_pm_label = tk.Button(self.time_display, textvariable=self.am_pm, command=self.toggle_am_pm, font=("Avenir", display_size))
		am_pm_label.grid(row=0, column=3)
		
		# Numeric buttons
		for i in range(1, 10):
			btn = tk.Button(num_buttons, text=str(i), command=lambda n=i: self.append_digit(n), font=("Avenir", button_size))
			btn.grid(row=(i-1)//3, column=(i-1)%3, pady=2, padx=2)
			
		btn_zero = tk.Button(num_buttons, text="0", command=lambda: self.append_digit(0), font=("Avenir", button_size))
		btn_zero.grid(row=3, column=1, pady=2, padx=2)
		
		# Control buttons
		btn_hour = tk.Button(control_buttons, text="Hour", command=lambda: self.set_input_mode("hour"), font=("Avenir", button_size))
		btn_hour.grid(row=0, column=0, padx=2)
		
		btn_minute = tk.Button(control_buttons, text="Minute", command=lambda: self.set_input_mode("minute"), font=("Avenir", button_size))
		btn_minute.grid(row=0, column=1, padx=2)
		
		btn_clear = tk.Button(control_buttons, text="Clear", command=self.clear_input, font=("Avenir", button_size))
		btn_clear.grid(row=0, column=2, padx=2)
		
		set_button = tk.Button(self, text="Set", command=self.on_set, font=("Avenir", button_size))
		set_button.pack(side=tk.BOTTOM, pady=10)
		
		self.update_highlight()
		
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
		hour = self.hour_str.get().zfill(2)
		minute = self.minute_str.get().zfill(2)
		self.result = f"{hour}:{minute} {self.am_pm.get()}"
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
	client = ntplib.NTPClient()
	try:
		response = client.request('pool.ntp.org')
		ntp_time = datetime.fromtimestamp(response.tx_time)
		return ntp_time.replace(tzinfo=None)  # Remove timezone information for comparison
	except Exception as e:
		messagebox.showerror("Error", f"Failed to get NTP time: {e}")
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
	global original_start_time, countdown_time, start_time_label
	dialog = TouchTimeDialog(root)
	root.wait_window(dialog)  # Wait for the dialog to close
	
	time_input = dialog.result  # Get the result from the dialog
	if time_input:
		try:
			parsed_time = parse_time_input(time_input)
			if parsed_time:
				original_start_time = parsed_time
				ntp_now = get_ntp_time()
				if ntp_now is None:
					messagebox.showerror("Error", "Could not synchronize with NTP time.")
					return
				if original_start_time <= ntp_now:
					messagebox.showinfo("Info", "The specified time is in the past. Please enter a future time.")
					return
				
				duration = (original_start_time - ntp_now).total_seconds()
				countdown_time[0] = duration
				start_countdown()
				start_time_label.config(text=f"Start Time: {original_start_time.strftime('%H:%M:%S')}")
				#messagebox.showinfo("Success", "Race start time set successfully.")
		except ValueError as e:
			messagebox.showerror("Error", str(e))
			
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
		countdown_label.config(text=f"{mins:02d}:{secs:02d}")
		time.sleep(1)
	if not countdown_stop_event.is_set():
		countdown_label.config(text="00:00")
			
def adjust_race_time(minutes):
	global original_start_time, countdown_time, start_time_label, last_button_press_time
	
	# Use is_debounced directly to check if the function call should proceed
	if not is_debounced(0.3):  # Adjust the debounce interval as needed
		# Optionally, inform the user or log that the action is debounced
		print("Action debounced, please wait.")
		return

	if original_start_time is None:
		messagebox.showinfo("Info", "Please set the race start time first.")
		return

	ntp_now = get_ntp_time()
	if ntp_now is None:
		messagebox.showerror("Error", "Could not synchronize with NTP time.")
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
	try:
		ntp_now = get_ntp_time()
		if ntp_now is None:
			# Optionally, inform the user that the system will use the local time instead of NTP time
			messagebox.showinfo("Info", "Using system's local time due to NTP time fetch failure.")
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
		messagebox.showerror("Error", str(e))
		return None

# GUI Setup
root = tk.Tk()
root.title("Countdown Clock")
root.geometry("800x480")

info_frame = tk.Frame(root)
info_frame.pack(pady=10)

ip_address = get_ip_address()
instruct_label = tk.Label(info_frame, text="Use 'VNC Viewer' to Screen Share", font=("Avenir", 14))
ip_label = tk.Label(info_frame, text=f"IP Address: {ip_address}", font=("Avenir", 16))
instruct_label.pack()
ip_label.pack(pady=20)

start_time_label = tk.Label(info_frame, text="Start Time: Not set", font=("Avenir", 16))
start_time_label.pack(pady=10)

timer_frame = tk.Frame(root, bg=green)
timer_frame.pack(pady=10)

countdown_label = tk.Label(timer_frame, bg=green, text="00:00", font=("Avenir", 48))
countdown_label.pack(pady=10, padx=20)

buttons_frame = tk.Frame(root)
buttons_frame.pack(pady=10)

set_time_button = tk.Button(buttons_frame, text="Set Race Time", command=set_race_time, font=("Avenir", 16))
set_time_button.grid(row=0,column=0, padx=5, columnspan=4)

back_five_minutes_button = tk.Button(buttons_frame, text="◀◀ 5 Minutes", command=lambda: adjust_race_time(-5), font=("Avenir", 16))
back_five_minutes_button.grid(row=1,column=0, padx=5)

back_minute_button = tk.Button(buttons_frame, text="◀ 1 Minute", command=lambda: adjust_race_time(-1), font=("Avenir", 16))
back_minute_button.grid(row=1,column=1, padx=5)

next_minute_button = tk.Button(buttons_frame, text="1 Minute ▶", command=lambda: adjust_race_time(1), font=("Avenir", 16))
next_minute_button.grid(row=1,column=2, padx=5)

next_five_minutes_button = tk.Button(buttons_frame, text="5 Minutes ▶▶", command=lambda: adjust_race_time(5), font=("Avenir", 16))
next_five_minutes_button.grid(row=1,column=3, padx=5)

root.mainloop()

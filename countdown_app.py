import tkinter as tk
from tkinter import simpledialog, messagebox
from threading import Thread, Event
import re
import socket
import ntplib
from datetime import datetime, timedelta

# Initialize global variables
green = "#00FF00"
original_start_time = None
countdown_time = [0]  # Stores the countdown time in seconds
countdown_stop_event = Event()
countdown_thread = None

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

def start_countdown():
    global countdown_thread, countdown_stop_event, original_start_time, countdown_time
    if original_start_time is None:
        messagebox.showinfo("Error", "Set the race time first.")
        return

    ntp_now = get_ntp_time()
    if ntp_now is None:
        messagebox.showerror("Error", "Could not synchronize with NTP time.")
        return

    duration = (original_start_time - ntp_now).total_seconds()
    if duration < 0:
        messagebox.showinfo("Error", "The specified time is in the past.")
        return

    countdown_time[0] = duration
    countdown_stop_event.clear()

    if countdown_thread is not None and countdown_thread.is_alive():
        countdown_stop_event.set()
        countdown_thread.join()

    countdown_stop_event.clear()
    countdown_thread = Thread(target=update_countdown, daemon=True)
    countdown_thread.start()

def update_countdown():
    global countdown_time
    while countdown_time[0] > 0 and not countdown_stop_event.is_set():
        mins, secs = divmod(int(countdown_time[0]), 60)
        countdown_label.config(text=f"{mins:02d}:{secs:02d}")
        time.sleep(1)
        countdown_time[0] -= 1
    if not countdown_stop_event.is_set():
        countdown_label.config(text="00:00")

def set_race_time():
    global original_start_time
    time_input = simpledialog.askstring("Input", "Enter race start time (HH:MM or HH:MM AM/PM):", parent=root)
    if time_input:
        try:
            original_start_time = parse_time_input(time_input)
            messagebox.showinfo("Success", f"Race start time set to {original_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

def adjust_race_time(minutes):
    global original_start_time
    if original_start_time:
        original_start_time += timedelta(minutes=minutes)
        start_countdown()
    else:
        messagebox.showinfo("Error", "Set the race time first.")

def parse_time_input(time_input):
    try:
        ntp_now = get_ntp_time()
        if ntp_now is None:
            raise Exception("NTP time fetch failed.")
        
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

timer_frame = tk.Frame(root, bg=green)
timer_frame.pack(pady=10)

countdown_label = tk.Label(timer_frame, bg=green, text="00:00", font=("Avenir", 48))
countdown_label.pack(pady=10, padx=20)

buttons_frame = tk.Frame(root)
buttons_frame.pack(pady=10)

set_time_button = tk.Button(buttons_frame, text="Set Race Time", command=set_race_time, font=("Avenir", 16))
set_time_button.pack(side=tk.LEFT, padx=5)

next_minute_button = tk.Button(buttons_frame, text="Next Minute", command=lambda: adjust_race_time(1), font=("Avenir", 16))
next_minute_button.pack(side=tk.LEFT, padx=5)

next_five_minutes_button = tk.Button(buttons_frame, text="Next 5 Minutes", command=lambda: adjust_race_time(5), font=("Avenir", 16))
next_five_minutes_button.pack(side=tk.LEFT, padx=5)

root.mainloop()


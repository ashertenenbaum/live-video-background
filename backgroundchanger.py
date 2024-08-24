import cv2
import os
import ctypes
import time
import tkinter as tk
from PIL import Image, ImageGrab
from threading import Thread
import win32gui

class BackgroundChanger:
    def __init__(self, root):
        self.root = root
        self.root.title("live camera background - asherskc")
        self.root.geometry("400x200")

        self.running = False
        self.camera_index = 0

        self.downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)

        self.original_bg_path = os.path.join(self.downloads_folder, "original_bg.bmp")
        self.temp_img_path = os.path.join(self.downloads_folder, "temp_bg.bmp")

        self.capture_thread = None

        self.save_original_background()

        start_button = tk.Button(root, text="Start", command=self.start_capture, width=20)
        start_button.pack(pady=10)

        stop_button = tk.Button(root, text="Stop", command=self.stop_capture, width=20)
        stop_button.pack(pady=10)

        camera_label = tk.Label(root, text="Select Camera:")
        camera_label.pack()

        self.camera_var = tk.StringVar(root)
        self.camera_dropdown = tk.OptionMenu(root, self.camera_var, *self.get_camera_list())
        self.camera_dropdown.config(width=20)
        self.camera_var.trace("w", self.change_camera)
        self.camera_dropdown.pack(pady=5)

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_camera_list(self):
        index = 0
        camera_list = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                camera_list.append(f"Camera {index}")
            cap.release()
            index += 1
        if not camera_list:
            camera_list.append("No camera available")
        return camera_list

    def save_original_background(self):
        SPI_GETDESKWALLPAPER = 0x0073
        buffer = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 512, buffer, 0)
        original_bg = buffer.value

        if os.path.exists(original_bg):
            original_image = Image.open(original_bg)
            original_image.save(self.original_bg_path)
        else:
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)
            blank_image = Image.new("RGB", (screen_width, screen_height), (0, 0, 0))
            blank_image.save(self.original_bg_path)

    def set_background(self, image_path):
        SPI_SETDESKWALLPAPER = 0x0014
        bmp_image_path = image_path.replace(".bmp", "") + ".bmp"
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, bmp_image_path, 3)

    def is_desktop_covered(self):
        desktop_hwnd = win32gui.FindWindow("Progman", None)
        desktop_rect = win32gui.GetWindowRect(desktop_hwnd)
        active_hwnd = win32gui.GetForegroundWindow()
        if active_hwnd == desktop_hwnd:
            return False
        active_rect = win32gui.GetWindowRect(active_hwnd)
        overlap_width = min(desktop_rect[2], active_rect[2]) - max(desktop_rect[0], active_rect[0])
        overlap_height = min(desktop_rect[3], active_rect[3]) - max(desktop_rect[1], active_rect[1])
        overlap_area = overlap_width * overlap_height
        desktop_area = (desktop_rect[2] - desktop_rect[0]) * (desktop_rect[3] - desktop_rect[1])
        return overlap_area > 0.5 * desktop_area

    def capture_background(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Could not open camera with index {self.camera_index}.")
            return

        while self.running:
            if not self.is_desktop_covered():
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture image.")
                    break

                cv2.imwrite(self.temp_img_path, frame)
                self.set_background(self.temp_img_path)

            time.sleep(1/60)

        cap.release()
        self.cleanup()

    def start_capture(self):
        if not self.running:
            self.running = True
            self.capture_thread = Thread(target=self.capture_background)
            self.capture_thread.start()

    def stop_capture(self):
        if self.running:
            self.running = False
            if self.capture_thread is not None:
                self.capture_thread.join()
            self.restore_original_background()

    def restore_original_background(self):
        self.set_background(self.original_bg_path)
        print("Original background restored.")

    def cleanup(self):
        if os.path.exists(self.temp_img_path):
            os.remove(self.temp_img_path)
            print("Temporary image deleted.")

    def change_camera(self, *args):
        try:
            self.camera_index = int(self.camera_var.get().split(" ")[-1])
            print(f"Camera index changed to {self.camera_index}.")
        except ValueError:
            print("Invalid camera index. Please select a valid camera.")

    def on_close(self):
        self.stop_capture()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundChanger(root)
    root.mainloop()

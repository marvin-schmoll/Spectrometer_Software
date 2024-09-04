import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import seabreeze.spectrometers as sb
import numpy as np
import threading
import queue
import time
import h5py
import os

class SpectrometerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Spectrometer Feed")
        
        # Set the custom icon for the window
        self.root.iconbitmap("spec.ico")
        
        # Initialize spectrometer
        try:
            self.devices = sb.list_devices()
            if not self.devices:
                raise ValueError("No Ocean Optics spectrometer found")
            self.spectrometer = sb.Spectrometer(self.devices[0])
            self.spectrometer.integration_time_micros(100000)  # Set integration time in microseconds
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize spectrometer: {e}")
            self.root.destroy()
            return

        # Background spectrum and subtraction toggle
        self.request_background = False
        self.background_spectrum = None
        self.subtract_background = tk.BooleanVar(value=False)
        
        # Data acquisition toggle
        self.acquiring = False
        self.acquired_spectra = []
        self.reference_lines = []  # Store reference lines

        # Set up the plot
        self.wavelengths = self.spectrometer.wavelengths()
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], 'k-', label="Live Spectrum", zorder=10)
        self.ax.set_xlim(self.wavelengths[0], self.wavelengths[-1])
        self.ax.set_ylim(0, 5000)  # Adjust the range according to expected intensity values
        self.ax.grid()
        self.ax.set_xlabel("Wavelength [nm]")
        self.ax.set_ylabel("Intensity")
        self.ax.legend(loc="upper right")

        # Set up the tkinter canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Integration time input
        control_frame = ttk.Frame(root, padding="10 10 10 10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        integration_frame = ttk.Frame(control_frame)
        integration_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.integration_label = ttk.Label(integration_frame, text="Integration Time (ms):")
        self.integration_label.pack(side=tk.LEFT, padx=5)
        
        self.integration_time_var = tk.StringVar(value="100")
        self.integration_entry = ttk.Entry(integration_frame, textvariable=self.integration_time_var, width=10)
        self.integration_entry.pack(side=tk.LEFT, padx=5)
        self.integration_entry.bind("<Return>", self.set_integration_time)

        # Filepath entry and acquisition controls
        filepath_frame = ttk.Frame(control_frame)
        filepath_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.filepath_label = ttk.Label(filepath_frame, text="Save Filepath:")
        self.filepath_label.pack(side=tk.LEFT, padx=5)
        
        self.filepath_var = tk.StringVar(value="spectra.h5")
        self.filepath_entry = ttk.Entry(filepath_frame, textvariable=self.filepath_var, width=40)
        self.filepath_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.browse_button = ttk.Button(filepath_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        acquisition_frame = ttk.Frame(control_frame)
        acquisition_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.acquire_button = ttk.Button(acquisition_frame, text="Start acquire", command=self.toggle_acquisition)
        self.acquire_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.acquiring_label = ttk.Label(acquisition_frame, text="", foreground="red")
        self.acquiring_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Buttons for various controls
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.bg_button = ttk.Button(button_frame, text="Take Background Spectrum", command=self.take_background)
        self.bg_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.toggle_button = ttk.Checkbutton(button_frame, text="Subtract Background", variable=self.subtract_background)
        self.toggle_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.autoscale_button = ttk.Button(button_frame, text="Autoscale Y-Axis", command=self.autoscale_y_axis)
        self.autoscale_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Add buttons for "Take Reference" and "Clear References"
        self.reference_button = ttk.Button(button_frame, text="Take Reference", command=self.take_reference)
        self.reference_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_button = ttk.Button(button_frame, text="Clear References", command=self.clear_references)
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Start the update loop
        self.data_queue = queue.Queue()
        self.running_event = threading.Event()
        self.running_event.set()
        self.update_thread = threading.Thread(target=self.spectrum_update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        self.update_plot()

    def take_background(self):
        # Puts in a request for taking a background spectrum
        self.request_background = True

    def autoscale_y_axis(self):
        # Autoscale y-axis to the current spectrum values
        intensities = self.line.get_ydata()
        if intensities.size > 0:
            self.ax.set_ylim(np.min(intensities), np.max(intensities))
            self.canvas.draw()
            print("Y-axis autoscaled to current spectrum values.")
        else:
            messagebox.showinfo("Autoscale", "No data available to autoscale Y-axis.")

    def take_reference(self):
        # Cache the current spectrum and display it as a new line on the graph
        intensities = self.line.get_ydata()
        if intensities.size > 0:
            reference_line, = self.ax.plot(self.wavelengths, intensities, lw=0.5,
                                           label=f"Reference {len(self.reference_lines) + 1}")
            self.reference_lines.append(reference_line)
            self.ax.legend(loc="upper right")
            self.canvas.draw()
            print(f"Reference {len(self.reference_lines)} taken and displayed.")
        else:
            messagebox.showinfo("Take Reference", "No data available to take as reference.")

    def clear_references(self):
        # Remove all reference lines from the graph
        for line in self.reference_lines:
            line.remove()
        self.reference_lines.clear()
        self.ax.legend(loc="upper right")
        self.canvas.draw()
        print("All reference lines cleared.")

    def update_plot(self):
        while not self.data_queue.empty():
            wavelengths, intensities = self.data_queue.get()
            
            if self.request_background:
                self.background_spectrum = intensities
                print("Background spectrum taken and cached.")
                self.request_background = False
            
            # Subtract background if enabled
            if self.subtract_background.get() and self.background_spectrum is not None:
                intensities = intensities - self.background_spectrum
            
            self.line.set_data(wavelengths, intensities)
            self.ax.relim()
            self.ax.autoscale_view(True, True, True)
            self.canvas.draw()

            # Save spectrum if acquiring
            if self.acquiring:
                self.acquired_spectra.append(intensities)

        # Schedule the next update
        if self.running_event.is_set():
            self.root.after(100, self.update_plot)

    def spectrum_update_loop(self):
        while self.running_event.is_set():
            try:
                # Read spectrum
                spectrum = self.spectrometer.spectrum()
                wavelengths = spectrum[0]
                intensities = spectrum[1]

                # Send data to the main thread
                self.data_queue.put((wavelengths, intensities))

                time.sleep(0.1)
            except sb.SeaBreezeError as e:
                print(f"Spectrometer error: {e}")
                messagebox.showerror("Spectrometer Error", f"Spectrometer error occurred: {e}")
                self.running_event.clear()
            except Exception as e:
                print(f"Error in spectrum update loop: {e}")
                messagebox.showerror("Error", f"An error occurred in the spectrum update loop: {e}")
                self.running_event.clear()

    def set_integration_time(self, event):
        try:
            new_time_ms = int(self.integration_time_var.get())
            if new_time_ms <= 0:
                raise ValueError("Integration time must be greater than 0 ms.")
            self.spectrometer.integration_time_micros(new_time_ms * 1000)  # Convert ms to microseconds
            print(f"Integration time set to {new_time_ms} ms")
        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Invalid integration time value: {e}")

    def toggle_acquisition(self):
        if self.acquiring:
            self.acquiring = False
            self.acquire_button.config(text="Start acquire")
            self.acquiring_label.config(text="")
            self.save_spectra()
        else:
            self.acquiring = True
            self.acquire_button.config(text="Stop acquire")
            self.acquiring_label.config(text="Acquiring...")
            self.acquired_spectra = []  # Reset acquired spectra list

    def save_spectra(self):
        # Save the acquired spectra to an HDF5 file
        file_path = self.filepath_var.get()
        if not file_path:
            messagebox.showerror("Save Error", "File path is empty. Please provide a valid file path.")
            return
        try:
            with h5py.File(file_path, "w") as f:
                f.create_dataset("wavelengths", data=self.wavelengths)
                f.create_dataset("spectra", data=np.array(self.acquired_spectra))
            print(f"Data saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save data: {e}")

    def browse_file(self):
        # Open a file dialog to select a file path
        file_path = filedialog.asksaveasfilename(defaultextension=".h5", filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")])
        if file_path:
            self.filepath_var.set(file_path)

    def close(self):
        print('Closing...')
        try:
            self.running_event.clear()
            self.update_thread.join()
            self.spectrometer.close()
            print('Program closed and spectrometer disconnected.')
        except Exception as e:
            print(f"Error during close: {e}")
        finally:
            self.root.destroy()

# Main function
if __name__ == "__main__":
    root = tk.Tk()
    app = SpectrometerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()

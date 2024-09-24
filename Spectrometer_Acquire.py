import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import seabreeze.spectrometers as sb
import avaspec_driver._avs_py as avs
import numpy as np
import threading
import queue
import time
import h5py
import os
import Stage_Interface
 
class SpectrometerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Spectrometer Feed")
        
        # Set the custom icon for the window
        self.root.iconbitmap("spec.ico")
        
        # Initialize Ocean Optics spectrometer
        try:
            self.devices = sb.list_devices()
            if not self.devices:
                raise ValueError("No Ocean Optics spectrometer found.")
            self.spectrometer = sb.Spectrometer(self.devices[0])
            self.spectrometer.integration_time_micros(100000)  # Set integration time in microseconds
            self.spec_type = "OCEAN_OPTICS"
            
        except Exception:
            # Initialize Aventes spectrometer
            try:
                avs.AVS_Init()
                self.devices = avs.AVS_GetList()
                self.active_spec_handle = avs.AVS_Activate(self.devices[0])
                avs.set_measure_params(self.active_spec_handle, 100, 1) # Set integration time in ms and averages
                avs.AVS_Measure(self.active_spec_handle)
                self.spec_type = "AVANTES"
                
            except Exception:
                q_string = "No Ocean Optics or Avantes spectrometers could be detected.\nProceed in Demo mode?"
                answer = messagebox.askquestion(title="No spectrometer found", message=q_string)
                if answer == "yes":
                    self.spec_type = "DEMO"
                else:
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
        
        # Stage for scans
        self.stage = None

        # Set up the plot
        if self.spec_type == "OCEAN_OPTICS":
            self.wavelengths = self.spectrometer.wavelengths()
        if self.spec_type == "AVANTES":
            self.wavelengths = avs.AVS_GetLambda(self.active_spec_handle)
        if self.spec_type == "DEMO":
            self.wavelengths = np.arange(1000)
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], 'k-', label="Live Spectrum", lw=0.8, zorder=10)  # Higher zorder for live spectrum
        self.ax.set_xlim(self.wavelengths[0], self.wavelengths[-1])
        self.ax.set_ylim(0, 5000)  # Adjust the range according to expected intensity values
        self.ax.grid()
        self.ax.set_xlabel("Wavelength [nm]")
        self.ax.set_ylabel("Intensity")
        self.legend_visible = True  # Track legend visibility
        self.legend = self.ax.legend(loc="upper left")  # Store the legend object

        # Set up the tkinter canvas
        plot_frame = ttk.Frame(root, padding="0 0 0 0")
        plot_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add the toolbar for zooming/panning
        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame)
        self.toolbar.pack(fill=tk.X)
        self.toolbar.update()

        # Create the menu bar
        self.create_menu_bar()

        # Integration time input
        control_frame = ttk.Frame(root, padding="10 10 10 10")
        control_frame.pack(fill=tk.X)

        integration_frame = ttk.Frame(control_frame)
        integration_frame.pack(fill=tk.X, pady=5)
        
        self.integration_label = ttk.Label(integration_frame, text="Integration Time (ms):")
        self.integration_label.pack(side=tk.LEFT, padx=5)
        
        self.integration_time_var = tk.StringVar(value="100")
        self.integration_entry = ttk.Entry(integration_frame, textvariable=self.integration_time_var, width=10)
        self.integration_entry.pack(side=tk.LEFT, padx=5)
        self.integration_entry.bind("<Return>", self.set_integration_time)

        # Filepath entry
        self.filepath_frame = ttk.Frame(control_frame)
        self.filepath_frame.pack(fill=tk.X, pady=5)
        
        self.filepath_label = ttk.Label(self.filepath_frame, text="Save Filepath:")
        self.filepath_label.pack(side=tk.LEFT, padx=5)
        
        self.filepath_var = tk.StringVar(value="spectra.h5")
        self.filepath_entry = ttk.Entry(self.filepath_frame, textvariable=self.filepath_var, width=40)
        self.filepath_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.browse_button = ttk.Button(self.filepath_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        # Frog scan parameters (initially invisible)
        frog_frame = ttk.Frame(control_frame)
        frog_frame.pack(fill=tk.X, pady=0)
        
        self.scan_frame = ttk.Frame(frog_frame)
        self.scan_frame.pack(fill=tk.X, pady=10)
        self.scan_frame.pack_forget()
        
        self.scan_start_label = ttk.Label(self.scan_frame, text="Start position:")
        self.scan_start_label.pack(side=tk.LEFT, padx=5)
        
        self.scan_start_var = tk.StringVar(value="10")
        self.scan_start_entry = ttk.Entry(self.scan_frame, textvariable=self.scan_start_var, width=10)
        self.scan_start_entry.pack(side=tk.LEFT, padx=2)   
        
        self.scan_stop_label = ttk.Label(self.scan_frame, text="Stop position:")
        self.scan_stop_label.pack(side=tk.LEFT, padx=[20,5])
        
        self.scan_stop_var = tk.StringVar(value="10")
        self.scan_stop_entry = ttk.Entry(self.scan_frame, textvariable=self.scan_stop_var, width=10)
        self.scan_stop_entry.pack(side=tk.LEFT, padx=2)
        
        self.scan_step_label = ttk.Label(self.scan_frame, text="Step size:")
        self.scan_step_label.pack(side=tk.LEFT, padx=[20,5])
        
        self.scan_step_var = tk.StringVar(value="10")
        self.scan_step_entry = ttk.Entry(self.scan_frame, textvariable=self.scan_step_var, width=10)
        self.scan_step_entry.pack(side=tk.LEFT, padx=2)      
        
        # Acquisition control
        acquisition_frame = ttk.Frame(control_frame)
        acquisition_frame.pack(fill=tk.X, pady=5)
        
        self.acquire_button = ttk.Button(acquisition_frame, text="Start acquire", command=self.toggle_acquisition)
        self.acquire_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.acquiring_label = ttk.Label(acquisition_frame, text="", foreground="red")
        self.acquiring_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Buttons for various controls
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
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

    def create_menu_bar(self):
        # Create a menu bar
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # Create 'View' menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="View", menu=view_menu)

        # Add 'Show Legend' option
        self.show_legend_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Legend", variable=self.show_legend_var, command=self.toggle_legend)
        
        # Add 'Show Toolbar' option
        self.show_toolbar_var = tk.BooleanVar(value=True)  # Toolbar visible by default
        view_menu.add_checkbutton(label="Show Toolbar", variable=self.show_toolbar_var, command=self.toggle_toolbar)
        
        # Create 'Tools' menu
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Tools", menu=tools_menu)
        
        # Add 'FROG interface' option
        tools_menu.add_command(label="Switch to FROG interface", command=self.frog_interface)
        
        # Add 'Stage interface' option
        tools_menu.add_command(label="Show stage interface", command=self.stage_interface)

    def toggle_legend(self):
        # Show or hide the legend based on the menu option
        self.legend_visible = self.show_legend_var.get()
        if self.legend_visible:
            self.legend = self.ax.legend(loc="upper left")
        else:
            if self.legend:
                self.legend.remove()
                self.legend = None
        self.canvas.draw()
        print(f"Legend visibility set to {self.legend_visible}")
    
    def toggle_toolbar(self):
        if self.show_toolbar_var.get():
            # Show the toolbar
            self.toolbar.pack(fill=tk.X)
            self.toolbar.update()
        else:
            # Hide the toolbar
            self.toolbar.pack_forget()
        print(f"Toolbar visibility set to {self.show_toolbar_var.get()}")

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
            reference_line, = self.ax.plot(self.wavelengths, intensities,
                                           label=f"Reference {len(self.reference_lines) + 1}", 
                                           lw=0.5, zorder=1)
            self.reference_lines.append(reference_line)
            if self.legend_visible:
                self.legend = self.ax.legend(loc="upper right")
            self.canvas.draw()
            print(f"Reference {len(self.reference_lines)} taken and displayed.")
        else:
            messagebox.showinfo("Take Reference", "No data available to take as reference.")

    def clear_references(self):
        # Remove all reference lines from the graph
        for line in self.reference_lines:
            line.remove()
        self.reference_lines.clear()
        if self.legend_visible:
            self.legend = self.ax.legend(loc="upper right")
        else:
            if self.legend:
                self.legend.remove()
                self.legend = None
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
                if self.spec_type == "OCEAN_OPTICS": # Read spectrum of Ocean Optics
                    spectrum = self.spectrometer.spectrum()
                    wavelengths = spectrum[0]
                    intensities = spectrum[1]
                
                if self.spec_type == "AVANTES": # Read spectrum of Avaspec
                    spectrum = avs.get_spectrum(self.active_spec_handle)
                    wavelengths = self.wavelengths
                    intensities = spectrum[1]
                
                if self.spec_type == "DEMO": # Output noise
                    wavelengths = self.wavelengths
                    intensities = np.random.rand(1000)

                # Send data to the main thread
                self.data_queue.put((wavelengths, intensities))

                time.sleep(0.1) # TODO: Can this be faster?
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
                raise ValueError("Integration time must be positive")
            if self.spec_type == "OCEAN_OPTICS":
                self.spectrometer.integration_time_micros(new_time_ms * 1000)  # Convert ms to microseconds
            if self.spec_type == "AVANTES":
                avs.AVS_StopMeasure(self.active_spec_handle)
                avs.set_measure_params(self.active_spec_handle, new_time_ms, 1)
                avs.AVS_Measure(self.active_spec_handle)
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
        '''Open a file dialog to select a file path'''
        file_path = filedialog.asksaveasfilename(defaultextension=".h5", filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")])
        if file_path:
            self.filepath_var.set(file_path)
            
    def frog_interface(self):
        if self.acquiring:
            self.toggle_acquisition()
        self.filepath_var.set('frog_scan.h5')
        self.scan_frame.pack(fill=tk.X)
        self.stage_interface()
    
    def stage_interface(self):
        if self.stage is None:
            Stage_Interface.StageControllerApp(self, self.stage)

    def close(self):
        print('Closing...')
        try:
            self.running_event.clear()
            self.update_thread.join()
            if self.spec_type == "OCEAN OPTICS":
                self.spectrometer.close()
            if self.spec_type == "AVANTES":
                avs.AVS_Deactivate(self.active_spec_handle)
                avs.AVS_Done()
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

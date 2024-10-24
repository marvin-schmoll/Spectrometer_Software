import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
from stage_driver import esp300
import threading
import time

# Main Application GUI
class StageControllerApp():
    def __init__(self, parent=None, stage=None, motor=None):
        if parent is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel()
        self.root.title("Stage Controller")
        
        self.parent = parent  # Calling class if applicable
        self.stage = stage  # Placeholder for the Stage object
        self.motor_number = motor  # Placeholder for the Stage object
        self.update_thread = None  # Thread for updating position
        self.running = False  # Control flag for thread

        # Create frames for better layout control
        com_frame = tk.Frame(self.root)
        motor_frame = tk.Frame(self.root)
        connect_frame = tk.Frame(self.root)
        home_frame = tk.Frame(self.root)
        move_frame = tk.Frame(self.root)
        errorcode_frame = tk.Frame(self.root)
        
        # COM Port Selection Dropdown (label on the left)
        self.com_label = tk.Label(com_frame, text="Select COM Port:")
        self.com_label.pack(side="left", padx=5)
        
        self.com_ports = self.get_com_ports()
        self.com_port_var = tk.StringVar(self.root)
        self.com_port_dropdown = ttk.Combobox(com_frame, textvariable=self.com_port_var, values=self.com_ports, state="readonly")
        self.com_port_dropdown.pack(side="left", padx=5)
        
        com_frame.pack(pady=5)
        
        # Motor Number Spinbox (label on the left)
        self.motor_label = tk.Label(motor_frame, text="Select Motor Number:")
        self.motor_label.pack(side="left", padx=5)
        
        self.motor_var = tk.IntVar(self.root, value=2)
        self.motor_spinbox = tk.Spinbox(motor_frame, from_=1, to=3, textvariable=self.motor_var, state="readonly", width=5)
        self.motor_spinbox.pack(side="left", padx=5)
        
        motor_frame.pack(pady=5)
        
        # Connect and Disconnect Buttons (side-by-side)
        self.connect_button = tk.Button(connect_frame, text="Connect", command=self.connect_stage)
        self.connect_button.pack(side="left", padx=5)
        
        self.disconnect_button = tk.Button(connect_frame, text="Disconnect", state="disabled", command=self.disconnect_stage)
        self.disconnect_button.pack(side="left", padx=5)
        
        connect_frame.pack(pady=5)
         
        # Position display label
        self.position_label = tk.Label(self.root, text="Current Position: N/A", fg="blue")
        self.position_label.pack(pady=5)
        
             
        # Home Button (single row)
        self.home_button = tk.Button(home_frame, text="Home", state="disabled", command=self.home_stage)
        self.home_button.pack()
        
        home_frame.pack(pady=5)
        
        # Move to Position (label on the left and move action bound to 'Enter')
        self.move_label = tk.Label(move_frame, text="Move to Position:")
        self.move_label.pack(side="left", padx=5)
        
        self.position_entry = tk.Entry(move_frame)
        self.position_entry.pack(side="left", padx=5)
        self.position_entry.bind("<Return>", lambda event: self.move_stage())
        
        move_frame.pack(pady=5)
        
        # Move Button
        self.move_button = tk.Button(self.root, text="Move to Position", state="disabled", command=self.move_stage)
        self.move_button.pack(pady=5)
        
        #show last errorcode
        self.errorcode_button = tk.Button(errorcode_frame, text="Show last errorcode",state="disabled",command=self.errors)
        self.errorcode_button.pack(side="left", padx=5)
        
        self.errorcode_label = tk.Label(errorcode_frame, text="None", fg="blue")
        self.errorcode_label.pack(side="left", padx=5)
        
        errorcode_frame.pack(pady=5)
      
        
        # Status label to display feedback
        self.status_label = tk.Label(self.root, text="", fg="blue")
        self.status_label.pack(pady=5)
        
        # Alter interface if a stage is already connected
        if self.stage is not None:
            self.running = True
            self.update_thread = threading.Thread(target=self.update_position_thread)
            self.update_thread.start()
            self.status_label.config(text="Already connected to a stage", fg="blue")
            self.com_port_dropdown.config(state="disabled")
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="normal")
            self.home_button.config(state="normal")
            self.move_button.config(state="normal")
            self.errorcode_button.config(state="normal")
            self.motor_spinbox.config(state="disabled")
        
        # Show window
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()
    
    def get_com_ports(self):
        """Get available COM ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect_stage(self):
        """Connect to the stage."""
        selected_port = self.com_port_var.get()
        self.motor_number = self.motor_var.get()
        
        if not selected_port:
            messagebox.showinfo("Connection failed", "Please select a COM port")
            return
        
        try:
            self.stage = esp300.ESP300Controller(selected_port, create_lock=True)
            self.stage.turn_motor_on(self.motor_number)
            if self.parent:
                self.parent.stage = self.stage
                self.parent.motor_number = self.motor_number
            self.status_label.config(text=f"Connected to {selected_port}", fg="green")
            self.com_port_dropdown.config(state="disabled")
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="normal")
            self.home_button.config(state="normal")
            self.move_button.config(state="normal")
            self.errorcode_button.config(state="normal")
            self.motor_spinbox.config(state="disabled")
            
            # Start position update thread
            self.running = True
            self.update_thread = threading.Thread(target=self.update_position_thread)
            self.update_thread.start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {selected_port}.\n{str(e)}")
    
    def disconnect_stage(self):
        """Disconnect from the stage."""
        if self.stage:
            # Stop the update thread
            self.running = False
            if self.update_thread:
                self.update_thread.join()

            self.stage.close()
            self.stage = None
            self.motor_number = None
            if self.parent:
                self.parent.stage = None
                self.parent.motor_number = None
            self.com_port_dropdown.config(state="enabled")
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.home_button.config(state="disabled")
            self.move_button.config(state="disabled")
            self.status_label.config(text="Disconnected from stage", fg="red")
            self.position_label.config(text="Current Position: N/A", fg="blue")  # Reset position display
            self.errorcode_button.config(state="disabled")
            self.motor_spinbox.config(state="normal")
    
    def update_position_thread(self):
        """Background thread to update the position every 0.5 seconds."""
        while self.running:
            if self.stage:
                try:
                    position = self.stage.get_position(self.motor_number)
                    # Schedule the position update in the main thread
                    self.root.after(0, self.update_position_label, position)
                except Exception:
                    self.root.after(0, self.update_position_label, None)
            time.sleep(0.5)
    
    def update_position_label(self, position):
        """Update the position label in the GUI thread."""
        if position is not None:
            self.position_label.config(text="Current Position: "+position, fg="blue")
        else:
            self.position_label.config(text="Error reading position", fg="red")
    
    def home_stage(self):
        """Send the stage to home position.""" 
        if self.stage:
            self.status_label.config(text=f"Homing motor {self.motor_number}...", fg="blue")
            try:
                self.stage.search_for_home(self.motor_number)
                self.status_label.config(text=f"Motor {self.motor_number} homed", fg="green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to home motor {self.motor_number}.\n{str(e)}")
    
    def move_stage(self):
        """Move the stage to the specified position."""
        if self.stage:
            try:
                position = float(self.position_entry.get())
                self.status_label.config(text=f"Moving motor {self.motor_number} to position {position}...", fg="blue")
                self.stage.move_absolute(self.motor_number, position)
                self.status_label.config(text=f"Motor {self.motor_number} moved to {position}", fg="green")
            except ValueError:
                messagebox.showerror("Error", "Invalid position. Please enter a valid number.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move motor {self.motor_number}.\n{str(e)}")

    def errors(self):
        error = self.stage.get_errors()
        if error[0] == '0':
            self.errorcode_label.config(text='No error detected :)', fg='green')
        else:
            self.errorcode_label.config(text=error[2], fg='red')
    
    def close(self):
        """Cleanup and close the application."""
        print('Closing stage UI')
        self.running = False  # Stop the update thread
        if self.update_thread:
            self.update_thread.join()
        if self.parent is None:
            if self.stage:
                self.stage.close()
        else:
            self.parent.stage_interface_open = False
        self.root.destroy()


if __name__ == "__main__":
    app = StageControllerApp()

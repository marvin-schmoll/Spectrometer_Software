import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

# Simulated Stage class
class Stage:
    def __init__(self, port, motor_num):
        self.port = port
        self.motor_num = motor_num
        self.connected = True
        print(f"Connected to stage on {self.port} (Motor {self.motor_num})")
    
    def disconnect(self):
        self.connected = False
        print(f"Disconnected from stage (Motor {self.motor_num})")
    
    def home(self):
        if self.connected:
            print(f"Homing stage (Motor {self.motor_num})...")
    
    def move_to(self, position):
        if self.connected:
            print(f"Moving stage (Motor {self.motor_num}) to position {position}")

# Main Application GUI
class StageControllerApp():
    def __init__(self, root):
        self.root = root
        self.root.title("Stage Controller")
        #self.geometry("400x250")
        
        self.stage = None  # Placeholder for the Stage object
        
        # Create frames for better layout control
        com_frame = tk.Frame(root)
        motor_frame = tk.Frame(root)
        connect_frame = tk.Frame(root)
        home_frame = tk.Frame(root)
        move_frame = tk.Frame(root)
        
        # COM Port Selection Dropdown (label on the left)
        self.com_label = tk.Label(com_frame, text="Select COM Port:")
        self.com_label.pack(side="left", padx=5)
        
        self.com_ports = self.get_com_ports()
        self.com_port_var = tk.StringVar(root)
        self.com_port_dropdown = ttk.Combobox(com_frame, textvariable=self.com_port_var, values=self.com_ports, state="readonly")
        self.com_port_dropdown.pack(side="left", padx=5)
        
        com_frame.pack(pady=5)
        
        # Motor Number Spinbox (label on the left)
        self.motor_label = tk.Label(motor_frame, text="Select Motor Number:")
        self.motor_label.pack(side="left", padx=5)
        
        self.motor_var = tk.IntVar(root, value=2)
        self.motor_spinbox = tk.Spinbox(motor_frame, from_=1, to=3, textvariable=self.motor_var, state="readonly", width=5)
        self.motor_spinbox.pack(side="left", padx=5)
        
        motor_frame.pack(pady=5)
        
        # Connect and Disconnect Buttons (side-by-side)
        self.connect_button = tk.Button(connect_frame, text="Connect", command=self.connect_stage)
        self.connect_button.pack(side="left", padx=5)
        
        self.disconnect_button = tk.Button(connect_frame, text="Disconnect", state="disabled", command=self.disconnect_stage)
        self.disconnect_button.pack(side="left", padx=5)
        
        connect_frame.pack(pady=5)
        
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
        self.move_button = tk.Button(root, text="Move to Position", state="disabled", command=self.move_stage)
        self.move_button.pack(pady=5)
    
    def get_com_ports(self):
        """Get available COM ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect_stage(self):
        """Connect to the stage."""
        selected_port = self.com_port_var.get()
        motor_number = self.motor_var.get()
        
        if not selected_port:
            messagebox.showwarning("Warning", "Please select a COM port")
            return
        
        self.stage = Stage(selected_port, motor_number)  # Create the Stage object with motor number
        self.connect_button.config(state="disabled")
        self.disconnect_button.config(state="normal")
        self.home_button.config(state="normal")
        self.move_button.config(state="normal")
    
    def disconnect_stage(self):
        """Disconnect from the stage."""
        if self.stage:
            self.stage.disconnect()
            self.stage = None
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.home_button.config(state="disabled")
            self.move_button.config(state="disabled")
    
    def home_stage(self):
        """Send the stage to home position."""
        if self.stage:
            self.stage.home()
    
    def move_stage(self):
        """Move the stage to the specified position."""
        if self.stage:
            try:
                position = float(self.position_entry.get())
                self.stage.move_to(position)
            except ValueError:
                messagebox.showerror("Error", "Invalid position. Please enter a valid number.")
    
    def close(self):
        print('Closing stage UI')
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StageControllerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()

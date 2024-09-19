# -*- coding: utf-8 -*-

import serial


class ESP300Controller:
    '''A Python interface to the Newport ESP300 Motion Controller using RS-232 communication.'''
    
    def __init__(self, port='COM27', baudrate=19200, timeout=1):
        """
        Initializes the connection to the ESP300 motion controller.
        
        Parameters
        ----------
        port : str
            Serial port to which the controller is connected.
        baudrate : int
            Communication baud rate (default: 19200).
        timeout : int
            Communication timeout in seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.bytesize=serial.EIGHTBITS
        self.parity=serial.PARITY_NONE
        self.stopbits=serial.STOPBITS_ONE
        self.timeout = timeout
        self.serial = serial.Serial(port, baudrate, bytesize=self.bytesize,
                                    parity=self.parity, stopbits=self.stopbits, 
                                    timeout=timeout)
        

    def send_command(self, command):
        """
        Sends a command to the ESP300 controller.
        
        Parameters
        ----------
        command : str
            The command string to be sent to the controller.
        """
        full_command = f"{command}\r"
        self.serial.write(full_command.encode())

    def read_response(self):
        """
        Reads the response from the controller.
        
        Returns
        -------
        str
            The response from the controller.
        """
        return self.serial.readline().decode().strip()
    
    
    def read_errors(self):
        """
        Reads the first entry from the error buffer.
        
        Command: TB?
        
        Returns
        -------
        arr of str
            error code, timestamp, error message
        """
        self.send_command("TB?")
        return self.read_response().split(',')
    
    
    def set_homing_mode(self, axis, mode=4):
        """
        Sets the default homing mode for the specified axis.

        Command: OM
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        mode : int
            Mode for home search:
            0: find zero position count
            1: find home and index signal
            2: find home signal
            3: find positive limit signal
            4: find negative limit signal
            5: find positive limit and index signals
            6: find negative limit and index signals
        """
        self.send_command(f"{axis}OM{mode}")

    def get_homing_mode(self, axis):
        """
        Gets the current default homing mode for the specified axis.

        Command: OM?

        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).

        Returns
        -------
        int
            The current homing mode of the axis:
            0: find zero position count
            1: find home and index signal
            2: find home signal
            3: find positive limit signal
            4: find negative limit signal
            5: find positive limit and index signals
            6: find negative limit and index signals
        """
        self.send_command(f"{axis}OM?")
        return self.read_response()
    
    def search_for_home(self, axis, mode=None):
        """
        Searches for home on the specified axis.

        Command: OR
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        mode : None or int
            Mode for home search:
            None: Use default mode (standard).
            0: find zero position count
            1: find home and index signal
            2: find home signal
            3: find positive limit signal
            4: find negative limit signal
            5: find positive limit and index signals
            6: find negative limit and index signals
        """
        if mode is None: self.send_command(f"{axis}OR")
        else:            self.send_command(f"{axis}OR{mode}")
        
        
    def abort_motion(self):
        """
        Stops motion on all axes immediately.

        Command: AB
        """
        self.send_command("AB")
    
    def move_absolute(self, axis, position):
        """
        Moves the specified axis to an absolute position.

        Command: PA
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        position : float
            Desired absolute position in predefined units.
        """
        self.send_command(f"{axis}PA{position}")

    def get_position(self, axis):
        """
        Retrieves the current position of the specified axis.

        Command: TP

        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).

        Returns
        -------
        str
            The current position of the axis.
        """
        self.send_command(f"{axis}TP")
        return self.read_response()

    def stop_motion(self, axis):
        """
        Stops motion on the specified axis.

        Command: ST
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        """
        self.send_command(f"{axis}ST")

    def wait_for_stop(self, axis):
        """
        Waits for the specified axis to stop.

        Command: WS
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        """
        self.send_command(f"{axis}WS")


    def set_velocity(self, axis, velocity):
        """
        Sets the velocity for the specified axis.

        Command: VA
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        velocity : float
            Desired velocity in predefined units/second.
        """
        self.send_command(f"{axis}VA{velocity}")

    def get_velocity(self, axis):
        """
        Retrieves the current velocity of the specified axis.

        Command: TV
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        
        Returns
        -------
        str
            The current velocity of the axis.
        """
        self.send_command(f"{axis}TV")
        return self.read_response()
    
    def set_acceleration(self, axis, acceleration):
        """
        Sets the acceleration for the specified axis.

        Command: AC
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        acceleration : float
            Acceleration value in predefined units/second².
        """
        self.send_command(f"{axis}AC{acceleration}")

    def get_acceleration(self, axis):
        """
        Gets the current acceleration for the specified axis.

        Command: AC?

        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).

        Returns
        -------
        str
            The current acceleration of the axis.
        """
        self.send_command(f"{axis}AC?")
        return self.read_response()


    def reset_controller(self):
        """
        Resets the controller.

        Command: RS
        """
        self.send_command("RS")

    
    def close(self):
        """
        Closes the serial connection to the controller.
        """
        self.serial.close()


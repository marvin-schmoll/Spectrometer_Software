# -*- coding: utf-8 -*-

import serial
import threading


class ESP300Controller:
    '''A Python interface to the Newport ESP300 Motion Controller using RS-232 communication.'''
    
    def __init__(self, port='COM27', baudrate=19200, timeout=1, create_lock=False):
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
        create_lock : bool
            If True a threading.Lock is created that is acquired before every 
            serial communication with the stage and released afterwards.
            This helps thread safety when it is commanded by multiple threads.
            Default is False.
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
        if create_lock:
            self.lock = threading.Lock()
        else:
            self.lock = None
        

    def send_command(self, command):
        """
        Sends a command to the ESP300 controller.
        
        Parameters
        ----------
        command : str
            The command string to be sent to the controller.
        """
        if self.lock is not None: self.lock.acquire()
        full_command = f"{command}\r"
        self.serial.write(full_command.encode())
        if self.lock is not None: self.lock.release()

    def read_response(self, command):
        """
        Sends a command to the controller.
        Reads its response and returns it as a string.
        
        Parameters
        ----------
        command : str
            The command string to be sent to the controller.
        
        Returns
        -------
        str
            The response from the controller.
        """
        full_command = f"{command}\r"
        if self.lock is not None: self.lock.acquire()
        self.serial.write(full_command.encode())
        reply = self.serial.readline().decode().strip()
        if self.lock is not None: self.lock.release()
        return reply
    
    
    def get_id(self, axis):
        """
        Reads the stage model and serial number.
        
        Command: ID?
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        
        Returns
        -------
        arr of str
            stage model, serial number
        """
        return self.read_response(f"{axis}ID?").split(',')
    
    def get_errors(self):
        """
        Reads the first entry from the error buffer.
        
        Command: TB?
        
        Returns
        -------
        arr of str
            error code, timestamp, error message
        """
        return self.read_response("TB?").split(',')


    def get_motor_on(self, axis):
        """
        Checks if specified motor is turned on.

        Command: MO?
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
            
        Returns
        -------
        bool
            True if specified motor is on.
        """
        return bool(int(self.read_response(f"{axis}MO?")))

    def turn_motor_on(self, axis):
        """
        Turns on the specified motor.

        Command: MO
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        """
        self.send_command(f"{axis}MO")
    
    def turn_motor_off(self, axis):
        """
        Turns off the specified motor.

        Command: MF
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        """
        self.send_command(f"{axis}MF")
        
    
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
        return self.read_response(f"{axis}OM?")
    
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
        return self.read_response(f"{axis}TP")

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
                
    def get_motion_status(self, axis):
        """
        Retrieves the motion status of the specified axis.

        Command: MD?
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        
        Returns
        -------
        bool
            Whether the axis is still moving.
        
        Notes
        -----
        The output is deliberately inverted from what the stage provides 
        and what its manual specifies. This is so that True corresponds to 
        moving and False corresponds to movement done.
        """
        return not bool(int(self.read_response(f"{axis}MD?")))
    

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
        Retrieves the set velocity of the specified axis.

        Command: VA?
        
        Parameters
        ----------
        axis : int
            Axis number (1 to MAX AXES).
        
        Returns
        -------
        str
            The current velocity of the axis.
        """
        return self.read_response(f"{axis}VA?")

    def get_velocity_current(self, axis):
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
        return self.read_response(f"{axis}TV")
    
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
        return self.read_response(f"{axis}AC?")


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

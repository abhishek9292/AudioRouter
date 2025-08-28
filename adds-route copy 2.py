import pyaudio
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from collections import deque
p = pyaudio.PyAudio()
class AudioRouter:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out1 = None
        self.stream_out2 = None
        self.is_running = False
        self.audio_thread = None
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        
        # Audio level monitoring
        self.input_levels = deque(maxlen=50)
        self.output1_levels = deque(maxlen=50)
        self.output2_levels = deque(maxlen=50)
        
        # Initialize GUI
        self.setup_gui()
        self.refresh_devices()
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Audio Router - Audio Forwarder")
        self.root.geometry("700x700")
        self.root.resizable(True, True)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Audio Router", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input device selection
        ttk.Label(main_frame, text="Input Device (VB-Cable Output):").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.input_var = tk.StringVar()
        self.input_combo = ttk.Combobox(main_frame, textvariable=self.input_var,
                                       width=50, state="readonly")
        self.input_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Output device 1 (Headphones)
        output1_frame = ttk.Frame(main_frame)
        output1_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        output1_frame.columnconfigure(1, weight=1)
        
        self.output1_enabled = tk.BooleanVar(value=True)
        self.output1_check = ttk.Checkbutton(output1_frame, text="Output 1 (Headphones):", 
                                           variable=self.output1_enabled,
                                           command=self.toggle_output1)
        self.output1_check.grid(row=0, column=0, sticky=tk.W)
        
        self.output1_var = tk.StringVar()
        self.output1_combo = ttk.Combobox(output1_frame, textvariable=self.output1_var,
                                         width=45, state="readonly")
        self.output1_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # Output device 2 (Recording/Other Apps)
        output2_frame = ttk.Frame(main_frame)
        output2_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        output2_frame.columnconfigure(1, weight=1)
        
        self.output2_enabled = tk.BooleanVar(value=True)
        self.output2_check = ttk.Checkbutton(output2_frame, text="Output 2 (Recording Device):", 
                                           variable=self.output2_enabled,
                                           command=self.toggle_output2)
        self.output2_check.grid(row=0, column=0, sticky=tk.W)
        
        self.output2_var = tk.StringVar()
        self.output2_combo = ttk.Combobox(output2_frame, textvariable=self.output2_var,
                                         width=45, state="readonly")
        self.output2_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # Refresh devices button
        refresh_btn = ttk.Button(main_frame, text="Refresh Devices", 
                               command=self.refresh_devices)
        refresh_btn.grid(row=4, column=2, sticky=tk.E, pady=10)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.apply_btn = ttk.Button(control_frame, text="Start Audio Routing", 
                                   command=self.toggle_routing)
        self.apply_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Stopped", 
                                     foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Audio level indicators frame
        indicator_frame = ttk.LabelFrame(main_frame, text="Audio Level Indicators", 
                                       padding="10")
        indicator_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), 
                           pady=20, padx=5)
        
        # Input level indicator
        self.input_level_frame = ttk.Frame(indicator_frame)
        self.input_level_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.input_level_frame.columnconfigure(2, weight=1)
        
        ttk.Label(self.input_level_frame, text="Input Level:").grid(
            row=0, column=0, sticky=tk.W)
        self.input_level_var = tk.StringVar(value="0%")
        self.input_level_label = ttk.Label(self.input_level_frame, textvariable=self.input_level_var)
        self.input_level_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.input_progress = ttk.Progressbar(self.input_level_frame, length=250, mode='determinate')
        self.input_progress.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=10)
        
        self.input_status_var = tk.StringVar(value="Inactive")
        self.input_status_label = ttk.Label(self.input_level_frame, textvariable=self.input_status_var, 
                                      foreground="red")
        self.input_status_label.grid(row=0, column=3, padx=10)
        
        # Output 1 level indicator
        self.level1_frame = ttk.Frame(indicator_frame)
        self.level1_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.level1_frame.columnconfigure(2, weight=1)
        
        ttk.Label(self.level1_frame, text="Output 1 Level:").grid(
            row=0, column=0, sticky=tk.W)
        self.level1_var = tk.StringVar(value="0%")
        self.level1_label = ttk.Label(self.level1_frame, textvariable=self.level1_var)
        self.level1_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.progress1 = ttk.Progressbar(self.level1_frame, length=250, mode='determinate')
        self.progress1.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=10)
        
        self.status1_var = tk.StringVar(value="Inactive")
        self.status1_label = ttk.Label(self.level1_frame, textvariable=self.status1_var, 
                                      foreground="red")
        self.status1_label.grid(row=0, column=3, padx=10)
        
        # Output 2 level indicator
        self.level2_frame = ttk.Frame(indicator_frame)
        self.level2_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.level2_frame.columnconfigure(2, weight=1)
        
        ttk.Label(self.level2_frame, text="Output 2 Level:").grid(
            row=0, column=0, sticky=tk.W)
        self.level2_var = tk.StringVar(value="0%")
        self.level2_label = ttk.Label(self.level2_frame, textvariable=self.level2_var)
        self.level2_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.progress2 = ttk.Progressbar(self.level2_frame, length=250, mode='determinate')
        self.progress2.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=10)
        
        self.status2_var = tk.StringVar(value="Inactive")
        self.status2_label = ttk.Label(self.level2_frame, textvariable=self.status2_var, 
                                      foreground="red")
        self.status2_label.grid(row=0, column=3, padx=10)
        
        # Configure indicator frame grid
        indicator_frame.columnconfigure(0, weight=1)
        
        # Info text
        info_text = """
Setup for Route Communication:
1. In Calling App: Set Speaker to "VB-Cable Input" and Microphone to your headset mic
2. In this app: Set Input to "VB-Cable Output" (captures Meet's audio)
3. Set Output 1 to your headphones (you hear the audio)  
4. Set Output 2 to another VB-Cable or recording device
5. Your headset mic connects directly to Call App (no feedback loops)

This way: Calling App → VB-Cable → This App → Your Headphones + Recording Device
Your Mic → Calling App (direct connection, no interference)

Note: Install VB-Cable first. You may need 2 VB-Cables for setups.
        """
        
        info_label = ttk.Label(main_frame, text=info_text.strip(), 
                              justify=tk.LEFT, foreground="gray")
        info_label.grid(row=7, column=0, columnspan=3, pady=20, sticky=tk.W)
        
        # Start level update timer
        self.update_levels()
        
    def toggle_output1(self):
        """Toggle output 1 availability"""
        if self.output1_enabled.get():
            self.output1_combo.config(state="readonly")
        else:
            self.output1_combo.config(state="disabled")
            # If routing is active, restart to apply changes
            if self.is_running:
                self.restart_routing()
    
    def toggle_output2(self):
        """Toggle output 2 availability"""
        if self.output2_enabled.get():
            self.output2_combo.config(state="readonly")
        else:
            self.output2_combo.config(state="disabled")
            # If routing is active, restart to apply changes
            if self.is_running:
                self.restart_routing()
    
    def restart_routing(self):
        """Restart audio routing with current settings"""
        if self.is_running:
            self.stop_routing()
            # Small delay to ensure clean shutdown
            self.root.after(100, self.start_routing)
    def is_device_active(self,index ):
        try:
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            input_device_index=index)
            stream.close()
            return True
        except Exception as e:
            return False
        
    def is_output_device_active(self, index):
        """Check if an output device is active and available"""
        try:
            # Try to open a stream to the output device
            stream = p.open(format=pyaudio.paInt16,
                           channels=2,
                           rate=44100,
                           output=True,
                           output_device_index=index,
                           frames_per_buffer=1024)
            stream.close()
            return True
        except Exception as e:
            return False
    

    def refresh_devices(self):
        """Refresh the list of available audio devices"""
        try:
            # Clear existing items
            self.input_combo['values'] = ()
            self.output1_combo['values'] = ()
            self.output2_combo['values'] = ()
            
            input_devices = []
            output_devices = []
            
            # Get device info
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                device_name = f"{i}: {device_info['name']} ({device_info['maxInputChannels']}in/{device_info['maxOutputChannels']}out)"
                
                if device_info['maxInputChannels'] > 0:
                    if(self.is_device_active(i)):
                        input_devices.append(device_name)
                if device_info['maxOutputChannels'] > 0:
                    if(self.is_output_device_active(i)):
                        output_devices.append(device_name)
            
           
           
            # Update comboboxes
            self.input_combo['values'] = input_devices
            self.output1_combo['values'] = output_devices
            self.output2_combo['values'] = output_devices
            
            # Set default selections if available
            if input_devices:
                self.input_combo.set(input_devices[0])
            if output_devices:
                self.output1_combo.set(output_devices[0])
                if len(output_devices) > 1:
                    self.output2_combo.set(output_devices[1])
                else:
                    self.output2_combo.set(output_devices[0])
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh devices: {str(e)}")
    
    def get_device_index(self, device_string):
        """Extract device index from the device string"""
        if device_string:
            return int(device_string.split(':')[0])
        return None
    
    def calculate_audio_level(self, data):
        """Calculate RMS audio level as percentage"""
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            if len(audio_data) == 0:
                return 0
            
            # Calculate RMS
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Convert to percentage (normalize to reasonable range)
            level = min(100, (rms / 3000) * 100)  # Adjust divisor as needed
            return level
        except:
            return 0
    
    def audio_callback(self):
        """Main audio processing loop"""
        try:
            while self.is_running:
                if self.stream_in:
                    # Read audio data from input
                    try:
                        data = self.stream_in.read(self.chunk, exception_on_overflow=False)
                        
                        # Calculate input audio level
                        input_level = self.calculate_audio_level(data)
                        self.input_levels.append(input_level)
                        
                        # Calculate output audio levels (same as input for now)
                        self.output1_levels.append(input_level)
                        self.output2_levels.append(input_level)
                        
                        # Write to outputs based on checkbox status
                        if self.output1_enabled.get() and self.stream_out1 and self.stream_out1.get_write_available() >= self.chunk:
                            self.stream_out1.write(data, exception_on_underflow=False)
                        
                        if self.output2_enabled.get() and self.stream_out2 and self.stream_out2.get_write_available() >= self.chunk:
                            self.stream_out2.write(data, exception_on_underflow=False)
                            
                    except Exception as e:
                        print(f"Audio processing error: {e}")
                        time.sleep(0.001)
                else:
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"Audio thread error: {e}")
            self.is_running = False
    
    def toggle_routing(self):
        """Start or stop audio routing"""
        if not self.is_running:
            self.start_routing()
        else:
            self.stop_routing()
    
    def start_routing(self):
        """Start audio routing"""
        try:
            # Get device indices
            input_idx = self.get_device_index(self.input_var.get())
            
            if input_idx is None:
                messagebox.showerror("Error", "Please select an input device")
                return
            
            # Check if at least one output is enabled
            if not self.output1_enabled.get() and not self.output2_enabled.get():
                messagebox.showerror("Error", "Please enable at least one output")
                return
            
            # Validate enabled outputs have selected devices
            if self.output1_enabled.get() and self.get_device_index(self.output1_var.get()) is None:
                messagebox.showerror("Error", "Please select Output 1 device or disable it")
                return
                
            if self.output2_enabled.get() and self.get_device_index(self.output2_var.get()) is None:
                messagebox.showerror("Error", "Please select Output 2 device or disable it")
                return
            
            # Close existing streams
            self.close_streams()
            
            # Open input stream
            self.stream_in = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=input_idx,
                frames_per_buffer=self.chunk
            )
            
            # Open output streams only if enabled
            if self.output1_enabled.get():
                output1_idx = self.get_device_index(self.output1_var.get())
                self.stream_out1 = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    output=True,
                    output_device_index=output1_idx,
                    frames_per_buffer=self.chunk
                )
            
            if self.output2_enabled.get():
                output2_idx = self.get_device_index(self.output2_var.get())
                self.stream_out2 = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    output=True,
                    output_device_index=output2_idx,
                    frames_per_buffer=self.chunk
                )
            
            # Start audio processing
            self.is_running = True
            self.audio_thread = threading.Thread(target=self.audio_callback)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            # Update UI
            self.apply_btn.config(text="Stop Audio Routing")
            self.status_label.config(text="Status: Running", foreground="green")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start audio routing: {str(e)}")
            self.stop_routing()
    
    def stop_routing(self):
        """Stop audio routing"""
        self.is_running = False
        
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1)
        
        self.close_streams()
        
        # Update UI
        self.apply_btn.config(text="Start Audio Routing")
        self.status_label.config(text="Status: Stopped", foreground="red")
        
        # Clear levels
        self.input_levels.clear()
        self.output1_levels.clear()
        self.output2_levels.clear()
    
    def close_streams(self):
        """Close all audio streams"""
        for stream in [self.stream_in, self.stream_out1, self.stream_out2]:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
        
        self.stream_in = None
        self.stream_out1 = None
        self.stream_out2 = None
    
    def update_levels(self):
        """Update audio level indicators"""
        try:
            # Update input level and status
            if self.is_running and self.stream_in:
                if self.input_levels:
                    avg_input_level = sum(self.input_levels) / len(self.input_levels)
                    self.input_level_var.set(f"{avg_input_level:.0f}%")
                    self.input_progress['value'] = avg_input_level
                else:
                    self.input_level_var.set("0%")
                    self.input_progress['value'] = 0
                self.input_status_var.set("Active")
                self.input_status_label.config(foreground="green")
            else:
                self.input_level_var.set("--")
                self.input_progress['value'] = 0
                self.input_status_var.set("Inactive")
                self.input_status_label.config(foreground="red")
            
            # Update output 1 level and status
            if self.output1_enabled.get() and self.is_running and self.stream_out1:
                if self.output1_levels:
                    avg_level1 = sum(self.output1_levels) / len(self.output1_levels)
                    self.level1_var.set(f"{avg_level1:.0f}%")
                    self.progress1['value'] = avg_level1
                else:
                    self.level1_var.set("0%")
                    self.progress1['value'] = 0
                self.status1_var.set("Active")
                self.status1_label.config(foreground="green")
            else:
                self.level1_var.set("--")
                self.progress1['value'] = 0
                if not self.output1_enabled.get():
                    self.status1_var.set("Disabled")
                    self.status1_label.config(foreground="gray")
                else:
                    self.status1_var.set("Inactive")
                    self.status1_label.config(foreground="red")
            
            # Update output 2 level and status
            if self.output2_enabled.get() and self.is_running and self.stream_out2:
                if self.output2_levels:
                    avg_level2 = sum(self.output2_levels) / len(self.output2_levels)
                    self.level2_var.set(f"{avg_level2:.0f}%")
                    self.progress2['value'] = avg_level2
                else:
                    self.level2_var.set("0%")
                    self.progress2['value'] = 0
                self.status2_var.set("Active")
                self.status2_label.config(foreground="green")
            else:
                self.level2_var.set("--")
                self.progress2['value'] = 0
                if not self.output2_enabled.get():
                    self.status2_var.set("Disabled")
                    self.status2_label.config(foreground="gray")
                else:
                    self.status2_var.set("Inactive")
                    self.status2_label.config(foreground="red")
                
        except:
            pass
        
        # Schedule next update
        self.root.after(50, self.update_levels)
    
    def on_closing(self):
        """Handle window close event"""
        self.stop_routing()
        try:
            self.p.terminate()
        except:
            pass
        self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = AudioRouter()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        input("Press Enter to exit...")
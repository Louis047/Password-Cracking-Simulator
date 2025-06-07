import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from start_pcs import PCSLauncher
from common.logger import get_logger

class ModernPCSGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Password Cracking Simulator - Control Panel")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize launcher
        self.launcher = PCSLauncher()
        self.logger = get_logger("GUI")
        
        # GUI state
        self.is_running = False
        self.monitoring_thread = None
        self.stop_monitoring = False
        
        self.setup_styles()
        self.create_widgets()
        self.center_window()
        
    def setup_styles(self):
        """Setup modern dark theme styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles for dark theme
        style.configure('Title.TLabel', 
                       background='#2b2b2b', 
                       foreground='#ffffff', 
                       font=('Arial', 16, 'bold'))
        
        style.configure('Subtitle.TLabel', 
                       background='#2b2b2b', 
                       foreground='#cccccc', 
                       font=('Arial', 10))
        
        style.configure('Modern.TButton',
                       background='#0078d4',
                       foreground='white',
                       font=('Arial', 10, 'bold'),
                       borderwidth=0)
        
        style.map('Modern.TButton',
                 background=[('active', '#106ebe'),
                           ('pressed', '#005a9e')])
        
        style.configure('Success.TButton',
                       background='#107c10',
                       foreground='white')
        
        style.configure('Danger.TButton',
                       background='#d13438',
                       foreground='white')
        
        style.configure('Modern.TFrame',
                       background='#2b2b2b',
                       borderwidth=1,
                       relief='solid')
        
        style.configure('Card.TFrame',
                       background='#3c3c3c',
                       borderwidth=1,
                       relief='solid')
    
    def create_widgets(self):
        """Create and layout GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Modern.TFrame')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="🔐 Password Cracking Simulator", 
                               style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Control Panel
        self.create_control_panel(main_frame)
        
        # Status Panel
        self.create_status_panel(main_frame)
        
        # Custom Password Panel
        self.create_password_panel(main_frame)
        
        # Results Panel
        self.create_results_panel(main_frame)
        
        # Log Panel
        self.create_log_panel(main_frame)
    
    def create_control_panel(self, parent):
        """Create system control panel"""
        control_frame = ttk.LabelFrame(parent, text="System Control", 
                                     style='Card.TFrame')
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Start/Stop buttons
        button_frame = ttk.Frame(control_frame, style='Modern.TFrame')
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 Start System", 
                                   command=self.start_system, 
                                   style='Success.TButton')
        self.start_btn.pack(side='left', padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="🛑 Stop System", 
                                  command=self.stop_system, 
                                  style='Danger.TButton', 
                                  state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 10))
        
        # Worker scaling
        worker_frame = ttk.Frame(control_frame, style='Modern.TFrame')
        worker_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Label(worker_frame, text="Workers:", 
                 style='Subtitle.TLabel').pack(side='left')
        
        self.worker_var = tk.StringVar(value="2")
        worker_spinbox = ttk.Spinbox(worker_frame, from_=1, to=10, 
                                   textvariable=self.worker_var, 
                                   width=5, command=self.scale_workers)
        worker_spinbox.pack(side='left', padx=(5, 10))
        
        ttk.Button(worker_frame, text="Apply", 
                  command=self.scale_workers, 
                  style='Modern.TButton').pack(side='left')
    
    def create_status_panel(self, parent):
        """Create system status panel"""
        status_frame = ttk.LabelFrame(parent, text="System Status", 
                                    style='Card.TFrame')
        status_frame.pack(fill='x', pady=(0, 10))
        
        # Status labels
        self.status_labels = {}
        status_items = [
            ("Workers", "workers"),
            ("Pending Tasks", "pending"),
            ("Active Tasks", "active"),
            ("Completed", "completed")
        ]
        
        status_grid = ttk.Frame(status_frame, style='Modern.TFrame')
        status_grid.pack(fill='x', padx=10, pady=10)
        
        for i, (label, key) in enumerate(status_items):
            col = i % 4
            
            item_frame = ttk.Frame(status_grid, style='Modern.TFrame')
            item_frame.grid(row=0, column=col, padx=10, sticky='ew')
            
            ttk.Label(item_frame, text=label, 
                     style='Subtitle.TLabel').pack()
            
            self.status_labels[key] = ttk.Label(item_frame, text="0", 
                                              style='Title.TLabel')
            self.status_labels[key].pack()
        
        # Configure grid weights
        for i in range(4):
            status_grid.columnconfigure(i, weight=1)
    
    def create_password_panel(self, parent):
        """Create custom password input panel"""
        password_frame = ttk.LabelFrame(parent, text="Custom Password Cracking", 
                                      style='Card.TFrame')
        password_frame.pack(fill='x', pady=(0, 10))
        
        input_frame = ttk.Frame(password_frame, style='Modern.TFrame')
        input_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(input_frame, text="Password:", 
                 style='Subtitle.TLabel').pack(side='left')
        
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(input_frame, textvariable=self.password_var, 
                                 width=30, show="*")
        password_entry.pack(side='left', padx=(5, 10), fill='x', expand=True)
        
        ttk.Button(input_frame, text="🔍 Crack Password", 
                  command=self.add_custom_password, 
                  style='Modern.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(input_frame, text="🗑️ Clear Results", 
                  command=self.clear_results, 
                  style='Modern.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(input_frame, text="🔄 Reset Tasks", 
                  command=self.reset_tasks, 
                  style='Modern.TButton').pack(side='left')
    
    def create_results_panel(self, parent):
        """Create results display panel"""
        results_frame = ttk.LabelFrame(parent, text="Cracked Passwords", 
                                     style='Card.TFrame')
        results_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(
            results_frame, 
            height=8, 
            bg='#1e1e1e', 
            fg='#00ff00', 
            font=('Consolas', 10),
            insertbackground='white'
        )
        self.results_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def create_log_panel(self, parent):
        """Create log display panel"""
        log_frame = ttk.LabelFrame(parent, text="System Logs", 
                                 style='Card.TFrame')
        log_frame.pack(fill='both', expand=True)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=6, 
            bg='#1e1e1e', 
            fg='#cccccc', 
            font=('Consolas', 9),
            insertbackground='white'
        )
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
    
    def start_system(self):
        """Start the PCS system"""
        try:
            self.log_message("🚀 Starting Password Cracking Simulator...")
            
            # Start master
            if self.launcher.start_master():
                self.log_message("✅ Master node started successfully")
                
                # Start workers
                worker_count = int(self.worker_var.get())
                for i in range(1, worker_count + 1):
                    if self.launcher.start_worker(i):
                        self.log_message(f"✅ Worker {i} started successfully")
                    else:
                        self.log_message(f"❌ Failed to start Worker {i}")
                
                self.is_running = True
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                
                # Start monitoring
                self.start_monitoring()
                
                self.log_message("🎮 System is now running!")
            else:
                self.log_message("❌ Failed to start master node")
                messagebox.showerror("Error", "Failed to start master node")
        
        except Exception as e:
            self.log_message(f"❌ Error starting system: {e}")
            messagebox.showerror("Error", f"Failed to start system: {e}")
    
    def stop_system(self):
        """Stop the PCS system"""
        try:
            self.log_message("🛑 Stopping system...")
            
            self.stop_monitoring = True
            self.launcher.stop_all()
            
            self.is_running = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            
            # Reset status
            for key in self.status_labels:
                self.status_labels[key].config(text="0")
            
            self.log_message("🏁 System stopped successfully")
        
        except Exception as e:
            self.log_message(f"❌ Error stopping system: {e}")
            messagebox.showerror("Error", f"Failed to stop system: {e}")
    
    def scale_workers(self):
        """Scale worker count"""
        if not self.is_running:
            return
        
        try:
            target_count = int(self.worker_var.get())
            current_count = self.launcher.scale_workers(target_count)
            self.log_message(f"🔧 Scaled workers to {current_count}")
        
        except Exception as e:
            self.log_message(f"❌ Error scaling workers: {e}")
            messagebox.showerror("Error", f"Failed to scale workers: {e}")
    
    def add_custom_password(self):
        """Add custom password for cracking"""
        password = self.password_var.get().strip()
        if not password:
            messagebox.showwarning("Warning", "Please enter a password")
            return
        
        if not self.is_running:
            messagebox.showwarning("Warning", "System must be running to add passwords")
            return
        
        try:
            result = self.launcher.add_custom_password(password)
            if result.get('status') == 'success':
                self.log_message(f"🔍 Added custom password for cracking")
                self.password_var.set("")  # Clear input
            else:
                self.log_message(f"❌ Failed to add password: {result.get('reason')}")
                messagebox.showerror("Error", f"Failed to add password: {result.get('reason')}")
        
        except Exception as e:
            self.log_message(f"❌ Error adding password: {e}")
            messagebox.showerror("Error", f"Failed to add password: {e}")
    
    def clear_results(self):
        """Clear all results"""
        if not self.is_running:
            messagebox.showwarning("Warning", "System must be running to clear results")
            return
        
        try:
            result = self.launcher.clear_results()
            if result.get('status') == 'success':
                self.results_text.delete(1.0, tk.END)
                self.log_message("🗑️ Results cleared")
            else:
                messagebox.showerror("Error", f"Failed to clear results: {result.get('reason')}")
        
        except Exception as e:
            self.log_message(f"❌ Error clearing results: {e}")
            messagebox.showerror("Error", f"Failed to clear results: {e}")
    
    def reset_tasks(self):
        """Reset to default tasks"""
        if not self.is_running:
            messagebox.showwarning("Warning", "System must be running to reset tasks")
            return
        
        try:
            result = self.launcher.reset_tasks()
            if result.get('status') == 'success':
                self.log_message("🔄 Tasks reset to default")
            else:
                messagebox.showerror("Error", f"Failed to reset tasks: {result.get('reason')}")
        
        except Exception as e:
            self.log_message(f"❌ Error resetting tasks: {e}")
            messagebox.showerror("Error", f"Failed to reset tasks: {e}")
    
    def start_monitoring(self):
        """Start system monitoring thread"""
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()
    
    def monitor_system(self):
        """Monitor system status and update GUI"""
        while not self.stop_monitoring and self.is_running:
            try:
                # Get status
                status = self.launcher.get_status()
                if status:
                    self.root.after(0, self.update_status, status)
                
                # Get results
                results = self.launcher.get_results()
                if results:
                    self.root.after(0, self.update_results, results)
                
                time.sleep(2)  # Update every 2 seconds
            
            except Exception as e:
                self.root.after(0, self.log_message, f"⚠️ Monitoring error: {e}")
                time.sleep(5)  # Wait longer on error
    
    def update_status(self, status):
        """Update status display"""
        try:
            self.status_labels['workers'].config(text=str(status.get('active_workers', 0)))
            self.status_labels['pending'].config(text=str(status.get('pending_tasks', 0)))
            self.status_labels['active'].config(text=str(status.get('active_tasks', 0)))
            self.status_labels['completed'].config(text=str(status.get('completed_results', 0)))
        except Exception as e:
            self.log_message(f"❌ Error updating status: {e}")
    
    def update_results(self, results):
        """Update results display"""
        try:
            current_text = self.results_text.get(1.0, tk.END)
            new_results = []
            
            for task_id, password in results.get('results', []):
                result_line = f"Task {task_id}: '{password}'\n"
                if result_line not in current_text:
                    new_results.append(result_line)
            
            if new_results:
                self.results_text.insert(tk.END, ''.join(new_results))
                self.results_text.see(tk.END)
        
        except Exception as e:
            self.log_message(f"❌ Error updating results: {e}")
    
    def log_message(self, message):
        """Add message to log display"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {message}\n"
            
            self.log_text.insert(tk.END, log_line)
            self.log_text.see(tk.END)
            
            # Keep log size manageable
            lines = self.log_text.get(1.0, tk.END).split('\n')
            if len(lines) > 100:
                self.log_text.delete(1.0, f"{len(lines)-50}.0")
        
        except Exception as e:
            print(f"Error logging message: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_running:
            if messagebox.askokcancel("Quit", "System is running. Stop and quit?"):
                self.stop_system()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("🎮 Password Cracking Simulator GUI Ready")
        self.log_message("💡 Click 'Start System' to begin")
        self.root.mainloop()

if __name__ == "__main__":
    app = ModernPCSGUI()
    app.run()
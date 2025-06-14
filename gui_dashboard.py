import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import sys
import os
import hashlib
import requests
from datetime import datetime
import json

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from start_pcs import PCSLauncher
from common.logger import get_logger
from common.config import MASTER_URL

class CommercialPCSGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Password Cracking Simulator - Commercial Edition")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0d1117')
        self.root.resizable(True, True)
        
        # Initialize launcher
        self.launcher = PCSLauncher()
        self.logger = get_logger("CommercialGUI")
        
        # GUI state
        self.current_mode = None
        self.is_running = False
        self.monitoring_thread = None
        self.stop_monitoring = False
        self.worker_results = {}  # Track individual worker performance
        self.crack_start_time = None
        
        # Demo mode data
        self.demo_passwords = []
        self.demo_hashes = []
        self.load_demo_data()
        
        self.setup_modern_styles()
        self.create_main_interface()
        self.center_window()
        
    def load_demo_data(self):
        """Load demo passwords and hashes from files"""
        try:
            # Load sample passwords for demo
            with open('data/password.txt', 'r') as f:
                self.demo_passwords = [line.strip() for line in f.readlines()[:20]]  # First 20 passwords
            
            # Load corresponding hashes
            with open('data/hashes.txt', 'r') as f:
                self.demo_hashes = [line.strip() for line in f.readlines()]
            
            # If hashes don't exist, create them
            if len(self.demo_hashes) < len(self.demo_passwords):
                self.create_demo_hashes()
                
        except FileNotFoundError:
            self.create_demo_data()
    
    def create_demo_data(self):
        """Create demo data files if they don't exist"""
        # Create sample passwords
        sample_passwords = [
            "password123", "admin", "123456", "qwerty", "letmein",
            "welcome", "password", "12345", "abc123", "test",
            "user", "guest", "login", "pass", "secret",
            "demo", "sample", "crack", "hash", "security"
        ]
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Write passwords
        with open('data/password.txt', 'w') as f:
            for pwd in sample_passwords:
                f.write(f"{pwd}\n")
        
        self.demo_passwords = sample_passwords
        self.create_demo_hashes()
    
    def create_demo_hashes(self):
        """Create corresponding hashes for demo passwords"""
        hashes = []
        for pwd in self.demo_passwords:
            hash_val = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
            hashes.append(hash_val)
        
        with open('data/hashes.txt', 'w') as f:
            for hash_val in hashes:
                f.write(f"{hash_val}\n")
        
        self.demo_hashes = hashes
    
    def setup_modern_styles(self):
        """Setup ultra-modern dark theme with effects"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern color palette
        colors = {
            'bg_primary': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'accent_blue': '#58a6ff',
            'accent_green': '#3fb950',
            'accent_red': '#f85149',
            'accent_orange': '#d29922',
            'text_primary': '#f0f6fc',
            'text_secondary': '#8b949e',
            'border': '#30363d'
        }
        
        # Configure modern styles
        style.configure('Modern.TFrame', background=colors['bg_secondary'], borderwidth=1, relief='solid')
        style.configure('Card.TFrame', background=colors['bg_tertiary'], borderwidth=1, relief='solid')
        style.configure('Gradient.TFrame', background=colors['bg_primary'])
        
        # Modern buttons with hover effects
        style.configure('Primary.TButton', 
                       background=colors['accent_blue'], foreground='white',
                       font=('Segoe UI', 11, 'bold'), borderwidth=0, focuscolor='none')
        style.map('Primary.TButton', 
                 background=[('active', '#1f6feb'), ('pressed', '#0969da')])
        
        style.configure('Success.TButton',
                       background=colors['accent_green'], foreground='white',
                       font=('Segoe UI', 11, 'bold'), borderwidth=0, focuscolor='none')
        style.map('Success.TButton',
                 background=[('active', '#2ea043'), ('pressed', '#238636')])
        
        style.configure('Danger.TButton',
                       background=colors['accent_red'], foreground='white',
                       font=('Segoe UI', 11, 'bold'), borderwidth=0, focuscolor='none')
        style.map('Danger.TButton',
                 background=[('active', '#da3633'), ('pressed', '#b62324')])
        
        style.configure('Warning.TButton',
                       background=colors['accent_orange'], foreground='white',
                       font=('Segoe UI', 11, 'bold'), borderwidth=0, focuscolor='none')
        
        # Modern labels
        style.configure('Title.TLabel', background=colors['bg_primary'], 
                       foreground=colors['text_primary'], font=('Segoe UI', 24, 'bold'))
        style.configure('Subtitle.TLabel', background=colors['bg_secondary'], 
                       foreground=colors['text_secondary'], font=('Segoe UI', 12))
        style.configure('Header.TLabel', background=colors['bg_tertiary'], 
                       foreground=colors['text_primary'], font=('Segoe UI', 14, 'bold'))
        style.configure('Metric.TLabel', background=colors['bg_tertiary'], 
                       foreground=colors['accent_blue'], font=('Segoe UI', 18, 'bold'))
        
        # Modern notebook
        style.configure('Modern.TNotebook', background=colors['bg_secondary'], borderwidth=0)
        style.configure('Modern.TNotebook.Tab', background=colors['bg_tertiary'], 
                       foreground=colors['text_secondary'], padding=[20, 10],
                       font=('Segoe UI', 11, 'bold'))
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', colors['accent_blue'])],
                 foreground=[('selected', 'white')])
    
    def create_main_interface(self):
        """Create the main interface with mode selection"""
        # Main container with gradient effect
        main_container = tk.Frame(self.root, bg='#0d1117')
        main_container.pack(fill='both', expand=True)
        
        # Header with logo and title
        self.create_header(main_container)
        
        # Mode selection or main interface
        self.content_frame = tk.Frame(main_container, bg='#0d1117')
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.show_mode_selection()
    
    def create_header(self, parent):
        """Create modern header with branding"""
        header_frame = tk.Frame(parent, bg='#161b22', height=80)
        header_frame.pack(fill='x', padx=20, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        # Logo and title
        title_frame = tk.Frame(header_frame, bg='#161b22')
        title_frame.pack(expand=True, fill='both')
        
        # Main title with icon
        title_label = tk.Label(title_frame, text="🔐 Password Cracking Simulator", 
                              bg='#161b22', fg='#f0f6fc', 
                              font=('Segoe UI', 24, 'bold'))
        title_label.pack(side='left', padx=20, pady=20)
        
        # Version and status
        version_label = tk.Label(title_frame, text="Commercial Edition v2.0", 
                                bg='#161b22', fg='#58a6ff', 
                                font=('Segoe UI', 12))
        version_label.pack(side='right', padx=20, pady=20)
    
    def show_mode_selection(self):
        """Show mode selection interface"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Mode selection container
        selection_frame = tk.Frame(self.content_frame, bg='#0d1117')
        selection_frame.pack(expand=True, fill='both')
        
        # Title
        mode_title = tk.Label(selection_frame, text="Choose Operation Mode", 
                             bg='#0d1117', fg='#f0f6fc', 
                             font=('Segoe UI', 20, 'bold'))
        mode_title.pack(pady=(50, 30))
        
        # Mode cards container
        cards_frame = tk.Frame(selection_frame, bg='#0d1117')
        cards_frame.pack(expand=True, fill='both', padx=100, pady=50)
        
        # Demo Mode Card
        self.create_mode_card(cards_frame, "Demo Mode", 
                             "🎮 Showcase password cracking with sample data",
                             ["• 5 Worker nodes by default", 
                              "• Pre-loaded sample passwords", 
                              "• Real-time performance comparison",
                              "• Educational demonstration"],
                             self.start_demo_mode, 'left')
        
        # Normal Mode Card
        self.create_mode_card(cards_frame, "Normal Mode", 
                             "⚙️ Custom password cracking with user input",
                             ["• Configurable worker count", 
                              "• Custom password input", 
                              "• Detailed performance analytics",
                              "• Production-ready interface"],
                             self.start_normal_mode, 'right')
    
    def create_mode_card(self, parent, title, description, features, command, side):
        """Create a modern mode selection card"""
        card_frame = tk.Frame(parent, bg='#21262d', relief='solid', borderwidth=1)
        card_frame.pack(side=side, fill='both', expand=True, padx=20)
        
        # Card content
        content_frame = tk.Frame(card_frame, bg='#21262d')
        content_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Title
        title_label = tk.Label(content_frame, text=title, 
                              bg='#21262d', fg='#f0f6fc', 
                              font=('Segoe UI', 18, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = tk.Label(content_frame, text=description, 
                             bg='#21262d', fg='#8b949e', 
                             font=('Segoe UI', 12), wraplength=300)
        desc_label.pack(pady=(0, 20))
        
        # Features
        for feature in features:
            feature_label = tk.Label(content_frame, text=feature, 
                                    bg='#21262d', fg='#58a6ff', 
                                    font=('Segoe UI', 10), anchor='w')
            feature_label.pack(fill='x', pady=2)
        
        # Select button
        select_btn = tk.Button(content_frame, text=f"Select {title}", 
                              command=command, bg='#58a6ff', fg='white',
                              font=('Segoe UI', 12, 'bold'), borderwidth=0,
                              cursor='hand2', activebackground='#1f6feb')
        select_btn.pack(pady=(30, 0), fill='x')
        
        # Hover effects
        def on_enter(e):
            card_frame.config(bg='#30363d')
            content_frame.config(bg='#30363d')
            for child in content_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg='#30363d')
        
        def on_leave(e):
            card_frame.config(bg='#21262d')
            content_frame.config(bg='#21262d')
            for child in content_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg='#21262d')
        
        card_frame.bind('<Enter>', on_enter)
        card_frame.bind('<Leave>', on_leave)
        content_frame.bind('<Enter>', on_enter)
        content_frame.bind('<Leave>', on_leave)
    
    def start_demo_mode(self):
        """Start demo mode interface"""
        self.current_mode = 'demo'
        self.create_demo_interface()
    
    def start_normal_mode(self):
        """Start normal mode interface"""
        self.current_mode = 'normal'
        self.create_normal_interface()
    
    def create_demo_interface(self):
        """Create demo mode interface"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Back button
        back_btn = tk.Button(self.content_frame, text="← Back to Mode Selection", 
                            command=self.show_mode_selection, bg='#21262d', fg='#f0f6fc',
                            font=('Segoe UI', 10), borderwidth=0, cursor='hand2')
        back_btn.pack(anchor='nw', pady=(0, 10))
        
        # Demo mode title
        demo_title = tk.Label(self.content_frame, text="🎮 Demo Mode - Password Cracking Showcase", 
                             bg='#0d1117', fg='#3fb950', 
                             font=('Segoe UI', 18, 'bold'))
        demo_title.pack(pady=(0, 20))
        
        # Control panel
        control_frame = tk.Frame(self.content_frame, bg='#161b22', relief='solid', borderwidth=1)
        control_frame.pack(fill='x', pady=(0, 10))
        
        control_inner = tk.Frame(control_frame, bg='#161b22')
        control_inner.pack(fill='x', padx=20, pady=15)
        
        # Demo controls
        tk.Label(control_inner, text="Demo Configuration:", 
                bg='#161b22', fg='#f0f6fc', font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        tk.Label(control_inner, text="Workers: 5 (Fixed)", 
                bg='#161b22', fg='#8b949e', font=('Segoe UI', 10)).pack(side='left', padx=(20, 0))
        
        tk.Label(control_inner, text=f"Sample Passwords: {len(self.demo_passwords)}", 
                bg='#161b22', fg='#8b949e', font=('Segoe UI', 10)).pack(side='left', padx=(20, 0))
        
        # Start demo button
        self.demo_start_btn = tk.Button(control_inner, text="🚀 Start Demo", 
                                       command=self.start_demo_cracking, bg='#3fb950', fg='white',
                                       font=('Segoe UI', 11, 'bold'), borderwidth=0, cursor='hand2')
        self.demo_start_btn.pack(side='right')
        
        # Create monitoring interface
        self.create_monitoring_interface()
    
    def create_normal_interface(self):
        """Create normal mode interface"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Back button
        back_btn = tk.Button(self.content_frame, text="← Back to Mode Selection", 
                            command=self.show_mode_selection, bg='#21262d', fg='#f0f6fc',
                            font=('Segoe UI', 10), borderwidth=0, cursor='hand2')
        back_btn.pack(anchor='nw', pady=(0, 10))
        
        # Normal mode title
        normal_title = tk.Label(self.content_frame, text="⚙️ Normal Mode - Custom Password Cracking", 
                               bg='#0d1117', fg='#58a6ff', 
                               font=('Segoe UI', 18, 'bold'))
        normal_title.pack(pady=(0, 20))
        
        # Configuration panel
        config_frame = tk.Frame(self.content_frame, bg='#161b22', relief='solid', borderwidth=1)
        config_frame.pack(fill='x', pady=(0, 10))
        
        config_inner = tk.Frame(config_frame, bg='#161b22')
        config_inner.pack(fill='x', padx=20, pady=15)
        
        # Worker configuration
        tk.Label(config_inner, text="Worker Count:", 
                bg='#161b22', fg='#f0f6fc', font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        self.worker_var = tk.StringVar(value="3")
        worker_spinbox = tk.Spinbox(config_inner, from_=1, to=10, 
                                   textvariable=self.worker_var, width=5,
                                   bg='#21262d', fg='#f0f6fc', font=('Segoe UI', 10))
        worker_spinbox.pack(side='left', padx=(10, 20))
        
        # Password input
        tk.Label(config_inner, text="Password to Crack:", 
                bg='#161b22', fg='#f0f6fc', font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(config_inner, textvariable=self.password_var, 
                                 width=20, show="*", bg='#21262d', fg='#f0f6fc',
                                 font=('Segoe UI', 10), insertbackground='white')
        password_entry.pack(side='left', padx=(10, 20))
        
        # Start button
        self.normal_start_btn = tk.Button(config_inner, text="🔍 Start Cracking", 
                                         command=self.start_normal_cracking, bg='#58a6ff', fg='white',
                                         font=('Segoe UI', 11, 'bold'), borderwidth=0, cursor='hand2')
        self.normal_start_btn.pack(side='right')
        
        # Create monitoring interface
        self.create_monitoring_interface()
    
    def create_monitoring_interface(self):
        """Create the monitoring interface for both modes"""
        # Main monitoring container
        monitor_frame = tk.Frame(self.content_frame, bg='#0d1117')
        monitor_frame.pack(fill='both', expand=True)
        
        # Top metrics row
        metrics_frame = tk.Frame(monitor_frame, bg='#0d1117')
        metrics_frame.pack(fill='x', pady=(0, 10))
        
        # Create metric cards
        self.create_metric_card(metrics_frame, "Active Workers", "0", "👥", 'left')
        self.create_metric_card(metrics_frame, "Tasks Completed", "0", "✅", 'left')
        self.create_metric_card(metrics_frame, "Passwords Cracked", "0", "🔓", 'left')
        self.create_metric_card(metrics_frame, "Elapsed Time", "00:00", "⏱️", 'left')
        
        # Main content area with tabs
        notebook = ttk.Notebook(monitor_frame, style='Modern.TNotebook')
        notebook.pack(fill='both', expand=True)
        
        # Worker Performance Tab
        worker_frame = tk.Frame(notebook, bg='#161b22')
        notebook.add(worker_frame, text="Worker Performance")
        self.create_worker_performance_tab(worker_frame)
        
        # Results Tab
        results_frame = tk.Frame(notebook, bg='#161b22')
        notebook.add(results_frame, text="Cracking Results")
        self.create_results_tab(results_frame)
        
        # System Logs Tab
        logs_frame = tk.Frame(notebook, bg='#161b22')
        notebook.add(logs_frame, text="System Logs")
        self.create_logs_tab(logs_frame)
    
    def create_metric_card(self, parent, title, value, icon, side):
        """Create a metric display card"""
        card = tk.Frame(parent, bg='#21262d', relief='solid', borderwidth=1)
        card.pack(side=side, fill='x', expand=True, padx=5)
        
        content = tk.Frame(card, bg='#21262d')
        content.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Icon and title
        header = tk.Frame(content, bg='#21262d')
        header.pack(fill='x')
        
        tk.Label(header, text=icon, bg='#21262d', fg='#58a6ff', 
                font=('Segoe UI', 16)).pack(side='left')
        tk.Label(header, text=title, bg='#21262d', fg='#8b949e', 
                font=('Segoe UI', 10)).pack(side='left', padx=(5, 0))
        
        # Value
        value_label = tk.Label(content, text=value, bg='#21262d', fg='#f0f6fc', 
                              font=('Segoe UI', 18, 'bold'))
        value_label.pack(anchor='w')
        
        # Store reference for updates
        setattr(self, f"{title.lower().replace(' ', '_')}_metric", value_label)
    
    def create_worker_performance_tab(self, parent):
        """Create worker performance monitoring tab"""
        # Worker stats table
        columns = ('Worker ID', 'Status', 'Tasks', 'Cracked', 'Success Rate', 'Avg Time', 'Last Seen')
        
        table_frame = tk.Frame(parent, bg='#161b22')
        table_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create treeview with modern styling
        self.worker_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.worker_tree.heading(col, text=col)
            self.worker_tree.column(col, width=120, anchor='center')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.worker_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.worker_tree.xview)
        self.worker_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack table and scrollbars
        self.worker_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    
    def create_results_tab(self, parent):
        """Create results display tab"""
        results_container = tk.Frame(parent, bg='#161b22')
        results_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Results header
        header_frame = tk.Frame(results_container, bg='#161b22')
        header_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(header_frame, text="🎯 Cracked Passwords", 
                bg='#161b22', fg='#3fb950', font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        # Clear button
        clear_btn = tk.Button(header_frame, text="🗑️ Clear Results", 
                             command=self.clear_results, bg='#f85149', fg='white',
                             font=('Segoe UI', 10, 'bold'), borderwidth=0, cursor='hand2')
        clear_btn.pack(side='right')
        
        # Results display
        self.results_text = tk.Text(results_container, 
                                   bg='#0d1117', fg='#3fb950', 
                                   font=('Consolas', 11),
                                   insertbackground='white',
                                   selectbackground='#58a6ff',
                                   wrap='word')
        
        results_scroll = tk.Scrollbar(results_container, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        results_scroll.pack(side='right', fill='y')
    
    def create_logs_tab(self, parent):
        """Create system logs tab"""
        logs_container = tk.Frame(parent, bg='#161b22')
        logs_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Logs header
        header_frame = tk.Frame(logs_container, bg='#161b22')
        header_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(header_frame, text="📋 System Logs", 
                bg='#161b22', fg='#58a6ff', font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        # Clear logs button
        clear_logs_btn = tk.Button(header_frame, text="🗑️ Clear Logs", 
                                  command=self.clear_logs, bg='#f85149', fg='white',
                                  font=('Segoe UI', 10, 'bold'), borderwidth=0, cursor='hand2')
        clear_logs_btn.pack(side='right')
        
        # Logs display
        self.logs_text = tk.Text(logs_container, 
                                bg='#0d1117', fg='#8b949e', 
                                font=('Consolas', 10),
                                insertbackground='white',
                                selectbackground='#58a6ff',
                                wrap='word')
        
        logs_scroll = tk.Scrollbar(logs_container, command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=logs_scroll.set)
        
        self.logs_text.pack(side='left', fill='both', expand=True)
        logs_scroll.pack(side='right', fill='y')
    
    def start_demo_cracking(self):
        """Start demo mode password cracking"""
        try:
            # Show loading indicator
            loading = self.create_loading_indicator(self.content_frame, "Starting Demo Mode...")
            self.log_message("🎮 Starting Demo Mode...")
            self.crack_start_time = time.time()
            
            # Set worker count to 5 for demo
            self.launcher.target_workers = 5
            
            def start_process():
                try:
                    # Start the system
                    if self.launcher.start_master():
                        self.root.after(0, lambda: self.log_message("✅ Master node started successfully"))
                        
                        # Start 5 workers for demo
                        self.launcher.start_workers(5)
                        self.root.after(0, lambda: self.log_message("✅ 5 Worker nodes started for demo"))
                        
                        # Load demo tasks
                        self.load_demo_tasks()
                        
                        self.is_running = True
                        self.root.after(0, lambda: self.demo_start_btn.config(text="🛑 Stop Demo", command=self.stop_system, bg='#f85149'))
                        
                        # Start monitoring
                        self.start_monitoring()
                        
                        self.root.after(0, lambda: self.log_message("🎮 Demo mode is now running!"))
                    else:
                        self.root.after(0, lambda: self.log_message("❌ Failed to start master node"))
                        self.root.after(0, lambda: messagebox.showerror("Error", "Failed to start master node"))
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"❌ Error starting demo: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to start demo: {e}"))
                finally:
                    # Remove loading indicator
                    self.root.after(0, loading.destroy)
            
            # Run in separate thread
            threading.Thread(target=start_process, daemon=True).start()
        
        except Exception as e:
            self.log_message(f"❌ Error starting demo: {e}")
            messagebox.showerror("Error", f"Failed to start demo: {e}")
    
    def start_normal_cracking(self):
        """Start normal mode password cracking"""
        try:
            password = self.password_var.get().strip()
            if not password:
                messagebox.showwarning("Warning", "Please enter a password to crack")
                return
            
            worker_count = int(self.worker_var.get())
            
            self.log_message(f"⚙️ Starting Normal Mode with {worker_count} workers...")
            self.crack_start_time = time.time()
            
            # Set worker count
            self.launcher.target_workers = worker_count
            
            # Start the system
            if self.launcher.start_master():
                self.log_message("✅ Master node started successfully")
                
                # Start workers
                self.launcher.start_workers(worker_count)
                self.log_message(f"✅ {worker_count} Worker nodes started")
                
                # Create custom task
                def create_custom_task(self, password):
                    """Create a custom task for the given password asynchronously"""
                    def send_task():
                        try:
                            # Generate hash for the password
                            target_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
                            
                            # Create candidate list (include the password and common passwords)
                            candidates = self.demo_passwords.copy()
                            if password not in candidates:
                                candidates.append(password)
                            
                            # Shuffle to make it more realistic
                            import random
                            random.shuffle(candidates)
                            
                            task = {
                                'task_id': 'custom_task_1',
                                'target_hash': target_hash,
                                'candidates': candidates,
                                'original_password': password
                            }
                            
                            # Send task to master
                            response = requests.post(f"{MASTER_URL}/load_custom_task", 
                                                   json={'task': task}, timeout=15)  # Increased timeout
                            
                            if response.status_code == 200:
                                self.root.after(0, lambda: self.log_message(f"📋 Created custom task for password cracking"))
                            else:
                                self.root.after(0, lambda: self.log_message("❌ Failed to create custom task"))
                        
                        except Exception as e:
                            self.root.after(0, lambda: self.log_message(f"❌ Error creating custom task: {e}"))
                    
                    # Run in separate thread
                    threading.Thread(target=send_task, daemon=True).start()
                
                self.is_running = True
                self.normal_start_btn.config(text="🛑 Stop Cracking", command=self.stop_system, bg='#f85149')
                
                # Start monitoring
                self.start_monitoring()
                
                self.log_message(f"⚙️ Normal mode is now running! Cracking password: {'*' * len(password)}")
            else:
                self.log_message("❌ Failed to start master node")
                messagebox.showerror("Error", "Failed to start master node")
        
        except Exception as e:
            self.log_message(f"❌ Error starting normal mode: {e}")
            messagebox.showerror("Error", f"Failed to start normal mode: {e}")
    
    def load_demo_tasks(self):
        """Load demo tasks into the master asynchronously"""
        def send_tasks():
            try:
                # Create tasks for demo passwords
                demo_tasks = []
                for i, (password, hash_val) in enumerate(zip(self.demo_passwords[:5], self.demo_hashes[:5])):
                    task = {
                        'task_id': f'demo_task_{i+1}',
                        'target_hash': hash_val,
                        'candidates': self.demo_passwords,  # Use all passwords as candidates
                        'original_password': password  # For demo tracking
                    }
                    demo_tasks.append(task)
                
                # Send tasks to master
                response = requests.post(f"{MASTER_URL}/load_demo_tasks", 
                                       json={'tasks': demo_tasks}, timeout=15)  # Increased timeout
                
                if response.status_code == 200:
                    self.root.after(0, lambda: self.log_message(f"📋 Loaded {len(demo_tasks)} demo tasks"))
                else:
                    self.root.after(0, lambda: self.log_message("❌ Failed to load demo tasks"))
            
            except Exception as e:
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda msg=error_msg: self.log_message(f"❌ Error loading demo tasks: {msg}"))
        
        # Run in separate thread
        threading.Thread(target=send_tasks, daemon=True).start()
    
    def create_custom_task(self, password):
        """Create a custom task for the given password"""
        try:
            # Generate hash for the password
            target_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            # Create candidate list (include the password and common passwords)
            candidates = self.demo_passwords.copy()
            if password not in candidates:
                candidates.append(password)
            
            # Shuffle to make it more realistic
            import random
            random.shuffle(candidates)
            
            task = {
                'task_id': 'custom_task_1',
                'target_hash': target_hash,
                'candidates': candidates,
                'original_password': password
            }
            
            # Send task to master
            response = requests.post(f"{MASTER_URL}/load_custom_task", 
                                   json={'task': task}, timeout=10)
            
            if response.status_code == 200:
                self.log_message(f"📋 Created custom task for password cracking")
            else:
                self.log_message("❌ Failed to create custom task")
        
        except Exception as e:
            self.log_message(f"❌ Error creating custom task: {e}")
    
    def start_monitoring(self):
        """Start system monitoring"""
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()
    
    def monitor_system(self):
        """Enhanced monitoring with detailed worker tracking"""
        update_interval = 2  # Update every 2 seconds instead of 1
        metrics_counter = 0
        worker_counter = 0
        results_counter = 0
        
        while not self.stop_monitoring and self.is_running:
            try:
                current_time = time.time()
                
                # Update metrics every 2 seconds
                if metrics_counter <= 0:
                    self.update_metrics()
                    metrics_counter = 2
                
                # Update worker performance every 3 seconds
                if worker_counter <= 0:
                    self.update_worker_performance()
                    worker_counter = 3
                
                # Check for results every 1 second
                if results_counter <= 0:
                    self.check_results()
                    results_counter = 1
                
                # Decrement counters
                metrics_counter -= 1
                worker_counter -= 1
                results_counter -= 1
                
                time.sleep(1)
            
            except Exception as e:
                self.root.after(0, self.log_message, f"⚠️ Monitoring error: {e}")
                time.sleep(5)
    
    def update_metrics(self):
        """Update top-level metrics asynchronously"""
        def fetch_metrics():
            try:
                # Get system status
                response = requests.get(f"{MASTER_URL}/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    
                    # Update metric cards using after method for thread safety
                    self.root.after(0, lambda: self.active_workers_metric.config(
                                   text=str(status.get('active_workers', 0))))
                    self.root.after(0, lambda: self.tasks_completed_metric.config(
                                   text=str(status.get('completed_tasks', 0))))
                    self.root.after(0, lambda: self.passwords_cracked_metric.config(
                                   text=str(status.get('passwords_cracked', 0))))
                    
                    # Update elapsed time
                    if self.crack_start_time:
                        elapsed = time.time() - self.crack_start_time
                        elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
                        self.root.after(0, lambda: self.elapsed_time_metric.config(text=elapsed_str))
            
            except Exception as e:
                self.root.after(0, self.log_message, f"Metrics update error: {e}")
        
        # Run in separate thread
        threading.Thread(target=fetch_metrics, daemon=True).start()
    
    def update_worker_performance(self):
        """Update worker performance table asynchronously"""
        def fetch_worker_data():
            try:
                response = requests.get(f"{MASTER_URL}/worker_stats", timeout=5)
                if response.status_code == 200:
                    workers_data = response.json()
                    if not isinstance(workers_data, dict) or 'workers' not in workers_data:
                        self.log_message("❌ Invalid worker stats format")
                        return
                    # Update worker tree in UI thread
                    self.root.after(0, lambda: self.refresh_worker_tree(workers_data))
            except requests.exceptions.RequestException as e:
                # Only log connection errors if system is running
                if self.is_running:
                    self.log_message(f"❌ Worker stats update error: {e}")
            except Exception as e:
                self.log_message(f"❌ Error fetching worker stats: {e}")
        
        # Run in separate thread
        threading.Thread(target=fetch_worker_data, daemon=True).start()
    
    def refresh_worker_tree(self, workers_data):
        """Refresh the worker performance tree"""
        try:
            # Clear existing items
            for item in self.worker_tree.get_children():
                self.worker_tree.delete(item)
            
            # Add current worker data
            workers = workers_data.get('workers', [])
            if not isinstance(workers, list):
                self.log_message("❌ Invalid worker data format")
                return
            
            for worker in workers:
                try:
                    # Extract worker data with safe defaults
                    worker_id = str(worker.get('worker_id', 'unknown'))
                    worker_id_short = worker_id[-12:] if len(worker_id) > 12 else worker_id
                    status = str(worker.get('status', 'unknown'))
                    tasks = int(worker.get('tasks_completed', 0))
                    cracked = int(worker.get('passwords_cracked', 0))
                    success_rate = f"{(cracked/max(tasks,1)*100):.1f}%" if tasks > 0 else "0%"
                    avg_time = f"{float(worker.get('avg_processing_time', 0)):.2f}s"
                    last_seen = time.strftime("%H:%M:%S", time.localtime(float(worker.get('last_heartbeat', time.time()))))
                    
                    # Color coding based on performance
                    tags = ()
                    if status == 'active' and cracked > 0:
                        tags = ('high_performer',)
                    elif status == 'active':
                        tags = ('active',)
                    else:
                        tags = ('inactive',)
                    
                    self.worker_tree.insert('', 'end', 
                        values=(worker_id_short, status, tasks, cracked, success_rate, avg_time, last_seen),
                        tags=tags)
                except Exception as e:
                    self.log_message(f"❌ Error processing worker data: {e}")
                    continue
            
            # Configure tag colors
            self.worker_tree.tag_configure('high_performer', foreground='#3fb950')
            self.worker_tree.tag_configure('active', foreground='#58a6ff')
            self.worker_tree.tag_configure('inactive', foreground='#f85149')
        
        except Exception as e:
            self.log_message(f"❌ Error updating worker tree: {e}")
    
    def check_results(self):
        """Check for new cracking results asynchronously"""
        def fetch_results():
            try:
                response = requests.get(f"{MASTER_URL}/results", timeout=5)
                if response.status_code == 200:
                    results_data = response.json()
                    
                    # Process new results
                    for result in results_data.get('results', []):
                        if len(result) >= 4:
                            task_id, password, worker_id, proc_time = result
                            worker_short = worker_id[-8:] if worker_id else "unknown"
                            
                            result_text = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Task {task_id}: Password '{password}' cracked by Worker {worker_short} in {proc_time:.2f}s\n"
                            
                            # Add to results display in UI thread
                            self.root.after(0, lambda t=result_text: self.add_result(t))
                            
                            # Log the result
                            self.root.after(0, lambda t=result_text: self.log_message(
                                           f"🎯 Password '{password}' cracked by Worker {worker_short} in {proc_time:.2f}s"))
            except Exception as e:
                pass  # Silently handle connection errors
        
        # Run in separate thread
        threading.Thread(target=fetch_results, daemon=True).start()
    
    def add_result(self, result_text):
        """Add result to results display"""
        try:
            current_text = self.results_text.get(1.0, tk.END)
            if result_text not in current_text:
                self.results_text.insert(tk.END, result_text)
                self.results_text.see(tk.END)
        except Exception as e:
            pass
    
    def stop_system(self):
        """Stop the PCS system"""
        try:
            self.log_message("🛑 Stopping system...")
            
            self.stop_monitoring = True
            self.launcher.stop_all()
            
            self.is_running = False
            
            # Reset buttons based on mode
            if self.current_mode == 'demo':
                self.demo_start_btn.config(text="🚀 Start Demo", command=self.start_demo_cracking, bg='#3fb950')
            elif self.current_mode == 'normal':
                self.normal_start_btn.config(text="🔍 Start Cracking", command=self.start_normal_cracking, bg='#58a6ff')
            
            self.log_message("✅ System stopped successfully")
        
        except Exception as e:
            self.log_message(f"❌ Error stopping system: {e}")
    
    def clear_results(self):
        """Clear results display"""
        self.results_text.delete(1.0, tk.END)
        self.log_message("🗑️ Results cleared")
    
    def clear_logs(self):
        """Clear logs display"""
        self.logs_text.delete(1.0, tk.END)
    
    def log_message(self, message):
        """Add message to logs"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            self.logs_text.insert(tk.END, log_entry)
            self.logs_text.see(tk.END)
            
            # Also log to console
            self.logger.info(message)
        except Exception as e:
            pass
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_running:
            if messagebox.askokcancel("Quit", "System is running. Stop and quit?"):
                self.stop_system()
                time.sleep(2)  # Give time for cleanup
                self.root.destroy()
        else:
            self.root.destroy()

    def create_loading_indicator(self, parent, text="Loading..."):
        """Create a loading indicator overlay"""
        overlay = tk.Frame(parent, bg='#0d1117', bd=0)
        overlay.place(relx=0.5, rely=0.5, anchor='center')
        
        # Spinner animation using Unicode characters
        spinner_label = tk.Label(overlay, text="⣾", font=('Segoe UI', 24), bg='#0d1117', fg='#58a6ff')
        spinner_label.pack(pady=(0, 10))
        
        # Loading text
        loading_label = tk.Label(overlay, text=text, font=('Segoe UI', 12), bg='#0d1117', fg='#8b949e')
        loading_label.pack()
        
        # Animate spinner
        spinner_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        spinner_idx = 0
        
        def update_spinner():
            nonlocal spinner_idx
            if overlay.winfo_exists():
                spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                spinner_label.config(text=spinner_chars[spinner_idx])
                overlay.after(100, update_spinner)
        
        update_spinner()
        return overlay

    def run(self):
        """Start the GUI application"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"GUI Error: {e}")

if __name__ == "__main__":
    app = CommercialPCSGUI()
    app.run()
import os
import subprocess
import threading
import json
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Setup modern theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "graphify_gui_config.json"

class GraphifyGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Graphify Studio")
        self.geometry("950x650")
        self.minsize(800, 500)

        # State
        self.projects = self.load_config()
        self.current_project_id = None
        self.process = None
        self.antigravity_installed = False
        self.hooks_installed = False
        self.active_cmd = None # None, 'build', 'clean', 'watch'

        # --- Grid Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar (Projects List) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Graphify Studio 🕸️", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.projects_scrollable_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.projects_scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.add_project_btn = ctk.CTkButton(self.sidebar_frame, text="+ Add Project", fg_color="#3498db", hover_color="#2980b9", command=self.add_project)
        self.add_project_btn.grid(row=2, column=0, padx=20, pady=20)

        # --- Main View ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Welcome Screen
        self.welcome_label = ctk.CTkLabel(self.main_frame, text="Select or Add a Project to start mapping.", font=ctk.CTkFont(size=24), text_color="gray")
        self.welcome_label.grid(row=0, column=0, pady=250)

        # Project Details View
        self.details_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_frame.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.project_title = ctk.CTkLabel(self.header_frame, text="Project Name", font=ctk.CTkFont(size=28, weight="bold"))
        self.project_title.grid(row=0, column=0, sticky="w")
        
        # Clickable Path
        self.project_path_label = ctk.CTkLabel(self.details_frame, text="Path: ...", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray", cursor="hand2")
        self.project_path_label.grid(row=0, column=0, sticky="sw", padx=15, pady=(45, 0))
        self.project_path_label.bind("<Button-1>", lambda e: self.open_project_folder())

        # --- Tabview ---
        self.tabview = ctk.CTkTabview(self.details_frame, fg_color="#1e1e1e")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_build = self.tabview.add("🚀 Build & Monitor")
        self.tab_settings = self.tabview.add("⚙️ Project Settings")

        # --- Build Tab ---
        self.tab_build.grid_columnconfigure(0, weight=1)
        self.tab_build.grid_rowconfigure(2, weight=1)

        self.actions_frame = ctk.CTkFrame(self.tab_build, fg_color="transparent")
        self.actions_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_build = ctk.CTkButton(self.actions_frame, text="Build Graph", height=35, width=120, fg_color="#2ecc71", hover_color="#27ae60", command=self.build_graph)
        self.btn_build.pack(side="left", padx=5)

        self.btn_clean = ctk.CTkButton(self.actions_frame, text="Clean Build", height=35, width=120, fg_color="#3498db", hover_color="#2980b9", command=self.clean_build)
        self.btn_clean.pack(side="left", padx=5)

        self.btn_watch = ctk.CTkButton(self.actions_frame, text="Enable Watch", height=35, width=120, fg_color="#f39c12", hover_color="#d35400", command=self.watch_graph)
        self.btn_watch.pack(side="left", padx=5)

        self.btn_open = ctk.CTkButton(self.actions_frame, text="Open HTML", height=35, width=120, fg_color="#9b59b6", hover_color="#8e44ad", command=self.open_html)
        self.btn_open.pack(side="left", padx=5)

        # Console Header with Clear button
        self.console_header = ctk.CTkFrame(self.tab_build, fg_color="transparent")
        self.console_header.grid(row=1, column=0, sticky="ew", padx=10)
        ctk.CTkLabel(self.console_header, text="Console Output:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.btn_clear_console = ctk.CTkButton(self.console_header, text="Clear", width=60, height=20, fg_color="transparent", border_width=1, command=lambda: self.console_textbox.delete("1.0", "end"))
        self.btn_clear_console.pack(side="right")

        self.console_textbox = ctk.CTkTextbox(self.tab_build, font=ctk.CTkFont(family="Consolas", size=13), border_width=1, fg_color="#121212")
        self.console_textbox.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))

        # --- Settings Tab ---
        self.tab_settings.grid_columnconfigure(0, weight=1)

        # API & Mode
        self.api_frame = ctk.CTkLabel(self.tab_settings, text="Extraction Configuration", font=ctk.CTkFont(weight="bold"))
        self.api_frame.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        self.api_settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="#2b2b2b")
        self.api_settings_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        ctk.CTkLabel(self.api_settings_frame, text="Mode:").pack(side="left", padx=(15, 5), pady=10)
        self.mode_switch = ctk.CTkSegmentedButton(self.api_settings_frame, values=["Normal (Local)", "Deep (AI)"], command=self.update_api_visibility)
        self.mode_switch.set("Normal (Local)")
        self.mode_switch.pack(side="left", padx=10)

        ctk.CTkLabel(self.api_settings_frame, text="API Key:").pack(side="left", padx=(20, 5), pady=10)
        self.api_key_entry = ctk.CTkEntry(self.api_settings_frame, placeholder_text="GEMINI_API_KEY...", width=200, show="*")
        self.api_key_entry.pack(side="left", padx=10)
        self.api_key_entry.configure(state="disabled", fg_color="#1a1a1a")
        
        self.btn_show_key = ctk.CTkButton(self.api_settings_frame, text="👁", width=30, height=30, fg_color="transparent", command=self.toggle_api_visibility)
        self.btn_show_key.pack(side="left", padx=2)

        # Integrations
        ctk.CTkLabel(self.tab_settings, text="Project Integrations", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=15, pady=(20, 5))
        self.integ_frame = ctk.CTkFrame(self.tab_settings, fg_color="#2b2b2b")
        self.integ_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        
        ctk.CTkLabel(self.integ_frame, text="Antigravity:").grid(row=0, column=0, padx=15, pady=15)
        self.btn_integ_antigravity = ctk.CTkButton(self.integ_frame, text="Checking...", width=150, command=self.toggle_antigravity)
        self.btn_integ_antigravity.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(self.integ_frame, text="Git Hooks:").grid(row=0, column=2, padx=(40, 15), pady=15)
        self.btn_integ_hooks = ctk.CTkButton(self.integ_frame, text="Checking...", width=150, command=self.toggle_hooks)
        self.btn_integ_hooks.grid(row=0, column=3, padx=5)

        # Ignore
        self.ignore_label_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.ignore_label_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(20, 5))
        ctk.CTkLabel(self.ignore_label_frame, text=".graphifyignore Settings", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.btn_save_ignore = ctk.CTkButton(self.ignore_label_frame, text="Save Ignore", width=100, height=24, command=self.save_ignore_settings)
        self.btn_save_ignore.pack(side="right")

        self.ignore_textbox = ctk.CTkTextbox(self.tab_settings, height=120, border_width=1, fg_color="#121212")
        self.ignore_textbox.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Remove Project (Safety Zone)
        self.remove_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.remove_frame.grid(row=6, column=0, sticky="ew", padx=15, pady=(20, 10))
        ctk.CTkLabel(self.remove_frame, text="Danger Zone", text_color="#e74c3c", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.btn_remove = ctk.CTkButton(self.remove_frame, text="Remove Project from Studio", fg_color="transparent", border_width=1, border_color="#e74c3c", text_color="#e74c3c", hover_color="#c0392b", command=self.remove_project)
        self.btn_remove.pack(side="right")

        self.refresh_project_list()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.projects, f, indent=4)

    def refresh_project_list(self):
        # Clear existing buttons
        for widget in self.projects_scrollable_frame.winfo_children():
            widget.destroy()

        # Add project buttons
        for pid, data in self.projects.items():
            # Check if this project is watching for the indicator
            is_watching = self.is_watch_running_externally(data['path'])
            indicator = " 🔴" if is_watching else ""
            
            btn = ctk.CTkButton(self.projects_scrollable_frame, text=f"{data['name']}{indicator}", 
                                fg_color="#3498db" if self.current_project_id == pid else "transparent",
                                hover_color="#34495e", anchor="w", 
                                command=lambda p=pid: self.select_project(p))
            btn.pack(fill="x", pady=2)

    def add_project(self):
        folder_path = filedialog.askdirectory(title="Select Project Folder")
        if folder_path:
            name = os.path.basename(folder_path)
            pid = str(hash(folder_path))
            self.projects[pid] = {
                "name": name,
                "path": folder_path
            }
            self.save_config()
            self.refresh_project_list()
            self.select_project(pid)

    def select_project(self, pid):
        self.current_project_id = pid
        data = self.projects[pid]
        
        self.welcome_label.grid_remove()
        self.details_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_project_list() # To update the selected color

        self.project_title.configure(text=data['name'])
        self.project_path_label.configure(text=f"Path: {data['path']}")

        # Load ignore file
        ignore_path = os.path.join(data['path'], ".graphifyignore")
        self.ignore_textbox.delete("1.0", "end")
        if os.path.exists(ignore_path):
            with open(ignore_path, 'r') as f:
                self.ignore_textbox.insert("1.0", f.read())
        
        self.refresh_integration_status()

    def open_project_folder(self):
        if not self.current_project_id: return
        path = self.projects[self.current_project_id]['path']
        os.startfile(path)

    def toggle_api_visibility(self):
        if self.api_key_entry.cget("show") == "*":
            self.api_key_entry.configure(show="")
            self.btn_show_key.configure(text="🔒")
        else:
            self.api_key_entry.configure(show="*")
            self.btn_show_key.configure(text="👁")

    def refresh_integration_status(self):
        if not self.current_project_id: return
        data = self.projects[self.current_project_id]
        path = data['path']
        
        # Check Antigravity (rules/graphify.md is the main marker for Antigravity)
        rule_path = os.path.join(path, ".agent", "rules", "graphify.md")
        self.antigravity_installed = os.path.exists(rule_path)
        if self.antigravity_installed:
            self.btn_integ_antigravity.configure(text="Uninstall Antigravity", fg_color="#e74c3c", hover_color="#c0392b")
        else:
            self.btn_integ_antigravity.configure(text="Install Antigravity", fg_color="#3498db", hover_color="#2980b9")
            
        # Check Hooks
        try:
            res = subprocess.run(["graphify", "hook", "status"], cwd=path, capture_output=True, text=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            output = res.stdout.lower()
            self.hooks_installed = "post-commit: installed" in output or "post-checkout: installed" in output
        except:
            self.hooks_installed = False
            
        if self.hooks_installed:
            self.btn_integ_hooks.configure(text="Uninstall Hooks", fg_color="#e74c3c", hover_color="#c0392b")
        else:
            self.btn_integ_hooks.configure(text="Install Hooks", fg_color="#3498db", hover_color="#2980b9")

        # --- Check for existing Watch process ---
        # Reset local tracking first so it doesn't "stick" when switching projects
        if self.process is None:
            self.active_cmd = None
            
            if self.is_watch_running_externally(path):
                self.btn_watch.configure(text="Stop Watch", fg_color="#e74c3c", hover_color="#c0392b")
                self.btn_build.configure(state="disabled")
                self.btn_clean.configure(state="disabled")
                self.active_cmd = 'watch'
            else:
                self.btn_watch.configure(text="Enable Watch", fg_color="#f39c12", hover_color="#d35400")
                self.btn_build.configure(state="normal")
                self.btn_clean.configure(state="normal")

    def is_watch_running_externally(self, project_path):
        """Check if a graphify watch process is already running for this path."""
        try:
            if os.name == 'nt':
                # Stricter check: look for 'graphify' and 'watch' but IGNORE the 'wmic' search process itself
                cmd = 'wmic process where "CommandLine like \'%graphify%\' and CommandLine like \'%watch%\' and not CommandLine like \'%wmic%\'" get CommandLine,ProcessId'
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=0x08000000)
                output = res.stdout.lower()
                
                # Check if we have any actual lines after the header
                lines = [l.strip() for l in output.splitlines() if l.strip()]
                # If we only have the header "CommandLine ProcessId", it's length 1
                return len(lines) > 1
            return False
        except:
            return False

    def toggle_antigravity(self):
        if self.antigravity_installed:
            self.uninstall_antigravity()
        else:
            self.install_antigravity()

    def toggle_hooks(self):
        if self.hooks_installed:
            self.uninstall_hooks()
        else:
            self.install_hooks()

    def update_api_visibility(self, mode):
        if mode == "Deep (AI)":
            self.api_key_entry.configure(state="normal", fg_color="#34495e")
        else:
            self.api_key_entry.configure(state="disabled", fg_color="#2b2b2b")

    def save_ignore_settings(self):
        if not self.current_project_id: return
        data = self.projects[self.current_project_id]
        ignore_path = os.path.join(data['path'], ".graphifyignore")
        content = self.ignore_textbox.get("1.0", "end-1c")
        try:
            with open(ignore_path, 'w') as f:
                f.write(content)
            self.append_console(f"✅ Saved .graphifyignore for {data['name']}\n")
            
            # UX Feedback
            original_text = self.btn_save_ignore.cget("text")
            self.btn_save_ignore.configure(text="✅ Saved!", fg_color="#2ecc71")
            self.after(2000, lambda: self.btn_save_ignore.configure(text=original_text, fg_color=("#3a7ebf", "#1f538d"))) # default colors
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ignore file: {e}")

    def remove_project(self):
        if self.current_project_id:
            del self.projects[self.current_project_id]
            self.save_config()
            self.current_project_id = None
            self.details_frame.grid_remove()
            self.welcome_label.grid(row=1, column=0, pady=250)
            self.refresh_project_list()

    def append_console(self, text):
        self.console_textbox.insert("end", text)
        self.console_textbox.see("end")

    def run_command(self, cmd_args, cmd_type):
        if self.process and self.process.poll() is None:
            return

        data = self.projects[self.current_project_id]
        cwd = data['path']
        self.active_cmd = cmd_type
        
        self.console_textbox.delete("1.0", "end")
        self.append_console(f"🚀 Running: {' '.join(cmd_args)}\n{'-'*50}\n")
        
        # UI State: Disable other buttons, transform current one
        self.btn_build.configure(state="disabled")
        self.btn_clean.configure(state="disabled")
        self.btn_watch.configure(state="disabled")
        
        if cmd_type == 'build':
            self.btn_build.configure(state="normal", text="Stop Build", fg_color="#e74c3c", hover_color="#c0392b")
        elif cmd_type == 'clean':
            self.btn_clean.configure(state="normal", text="Stop Clean", fg_color="#e74c3c", hover_color="#c0392b")
        elif cmd_type == 'watch':
            self.btn_watch.configure(state="normal", text="Stop Watch", fg_color="#e74c3c", hover_color="#c0392b")

        # Inject API key if provided
        env = os.environ.copy()
        api_key = self.api_key_entry.get().strip()
        if api_key and self.mode_switch.get() == "Deep (AI)":
            env["GEMINI_API_KEY"] = api_key
            env["GOOGLE_API_KEY"] = api_key
            self.append_console("🔑 API Key injected into environment.\n")

        # Set GRAPHIFY_FORCE=1 so ignoring files actually removes them from the graph
        env["GRAPHIFY_FORCE"] = "1"

        def target():
            try:
                self.process = subprocess.Popen(
                    cmd_args, 
                    cwd=cwd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    shell=True,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                for line in self.process.stdout:
                    self.console_textbox.after(0, self.append_console, line)
                
                self.process.wait()
                
                if self.process.returncode == 0:
                    status = "✅ Process finished successfully."
                elif self.process.returncode < 0 or self.process.returncode == 1 or self.process.returncode == 130:
                    status = "⏹ Process stopped."
                else:
                    status = f"❌ Process failed with exit code {self.process.returncode}."

                self.console_textbox.after(0, self.append_console, f"\n{'-'*50}\n{status}\n")
                self.after(500, self.refresh_integration_status)
                
            except Exception as e:
                self.console_textbox.after(0, self.append_console, f"❌ Error: {e}\n")
            finally:
                self.active_cmd = None
                self.btn_build.configure(state="normal", text="Build Graph", fg_color="#2ecc71", hover_color="#27ae60")
                self.btn_clean.configure(state="normal", text="Clean Build", fg_color="#3498db", hover_color="#2980b9")
                self.btn_watch.configure(state="normal", text="Enable Watch", fg_color="#f39c12", hover_color="#d35400")

        threading.Thread(target=target, daemon=True).start()

    def stop_process(self):
        if self.process and self.process.poll() is None:
            self.append_console("\n⏹ Stopping process...\n")
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.process.terminate()
        elif self.active_cmd == 'watch':
            # Handle stopping an externally running watch process
            self.append_console("\n⏹ Stopping external watch process...\n")
            if os.name == 'nt':
                # Force kill any python process running graphify watch
                cmd = f'wmic process where "CommandLine like \'%graphify%watch%\'" call terminate'
                subprocess.run(cmd, capture_output=True, shell=True, creationflags=0x08000000)
            
            # Reset UI
            self.active_cmd = None
            self.btn_build.configure(state="normal", text="Build Graph", fg_color="#2ecc71", hover_color="#27ae60")
            self.btn_clean.configure(state="normal", text="Clean Build", fg_color="#3498db", hover_color="#2980b9")
            self.btn_watch.configure(state="normal", text="Enable Watch", fg_color="#f39c12", hover_color="#d35400")

    def install_antigravity(self):
        if not self.current_project_id: return
        self.tabview.set("🚀 Build & Monitor")
        self.run_command(["graphify", "antigravity", "install"], "build")

    def uninstall_antigravity(self):
        if not self.current_project_id: return
        self.tabview.set("🚀 Build & Monitor")
        self.run_command(["graphify", "antigravity", "uninstall"], "build")

    def install_hooks(self):
        if not self.current_project_id: return
        self.tabview.set("🚀 Build & Monitor")
        self.run_command(["graphify", "hook", "install"], "build")

    def uninstall_hooks(self):
        if not self.current_project_id: return
        self.tabview.set("🚀 Build & Monitor")
        self.run_command(["graphify", "hook", "uninstall"], "build")

    def clean_build(self):
        if not self.current_project_id: return
        if self.active_cmd == 'clean':
            self.stop_process()
            return

        data = self.projects[self.current_project_id]
        cwd = data['path']
        out_dir = os.path.join(cwd, "graphify-out")
        if os.path.exists(out_dir):
            import shutil
            try:
                shutil.rmtree(out_dir)
                self.console_textbox.delete("1.0", "end")
                self.append_console(f"🧹 Cleaned existing graphify-out directory.\n")
            except Exception as e:
                self.console_textbox.delete("1.0", "end")
                self.append_console(f"❌ Failed to clean directory: {e}\n")
        self.build_graph()

    def build_graph(self):
        if not self.current_project_id: return
        if self.active_cmd == 'build':
            self.stop_process()
            return

        mode = self.mode_switch.get()
        if mode == "Normal (Local)":
            self.run_command(["graphify", "update", ".", "--force"], "build")
        else:
            self.run_command(["graphify", "extract", "."], "build")

    def watch_graph(self):
        if not self.current_project_id: return
        if self.active_cmd == 'watch':
            self.stop_process()
            return
        self.run_command(["graphify", "watch", "."], "watch")

    def open_html(self):
        if not self.current_project_id: return
        data = self.projects[self.current_project_id]
        html_path = os.path.join(data['path'], "graphify-out", "graph.html")
        if os.path.exists(html_path):
            webbrowser.open(f"file:///{html_path}")
        else:
            messagebox.showerror("Error", "graph.html not found. Please build the graph first.")

def ensure_graphify_installed():
    """Ensure the graphify CLI is installed."""
    try:
        # Check if graphify is available (use --help since --version is not supported)
        subprocess.run(["graphify", "--help"], capture_output=True, check=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("🚀 Graphify CLI not found. Installing via pip...")
        try:
            # Install graphifyy (correct package name)
            subprocess.run(["pip", "install", "graphifyy"], check=True, shell=True)
            print("✅ Graphify installed successfully!")
        except Exception as e:
            print(f"❌ Failed to auto-install Graphify: {e}")
            messagebox.showwarning("Warning", f"Graphify CLI is missing and auto-install failed. Please run 'pip install graphifyy' manually.\n\nError: {e}")

if __name__ == "__main__":
    ensure_graphify_installed()
    app = GraphifyGUI()
    app.mainloop()

import sys
import os
import subprocess
import shutil
import json
import threading
import concurrent.futures
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from plyfile import PlyData, PlyElement

# ==========================================
# FILE PATHS & CONFIG
# ==========================================
# 1. gsbox.exe Pfad (PyInstaller kompatibel)
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

GSBOX_PATH = os.path.join(BUNDLE_DIR, "gsbox.exe")

# 2. Config-Verzeichnis im User-Home-Ordner erzwingen (Garantiert Schreibrechte!)
USER_HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(USER_HOME, ".3DGS_Batchprocessor")
os.makedirs(CONFIG_DIR, exist_ok=True) # Erstellt den Ordner, falls er nicht existiert
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    'min_x': "-5.0", 'max_x': "5.0",
    'min_y': "-5.0", 'max_y': "5.0",
    'min_z': "-5.0", 'max_z': "5.0",
    'trans_x': "", 'trans_y': "", 'trans_z': "",
    'rot_x': "", 'rot_y': "", 'rot_z': "",
    'scale': "1.0",
    'format': "spz",
    'filename_prefix': "animation"
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass
    return config

def parse_float(val_str, default=0.0):
    val_str = str(val_str).strip().replace(',', '.')
    if not val_str:
        return default
    try:
        return float(val_str)
    except ValueError:
        return default

def crop_ply(input_file, output_file, bounds):
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    plydata = PlyData.read(input_file)
    v_data = plydata['vertex'].data

    mask = (v_data['x'] >= min_x) & (v_data['x'] <= max_x) & \
           (v_data['y'] >= min_y) & (v_data['y'] <= max_y) & \
           (v_data['z'] >= min_z) & (v_data['z'] <= max_z)
           
    filtered_data = v_data[mask]
    new_vertex = PlyElement.describe(filtered_data, 'vertex')
    PlyData([new_vertex], text=False).write(output_file)


class App:
    def __init__(self, root, input_files):
        self.root = root
        self.root.title("4DGS Batch Processor (Apple SHARP -> SPZ/PLY)")
        self.input_files = input_files
        self.config = load_config()
        
        self.format_var = tk.StringVar(value=self.config.get('format', 'spz'))
        self.entries = {}
        
        self.processed_count = 0
        self.total_count = 0
        self.lock = threading.Lock()
        
        # Einstellungen speichern, wenn das Fenster über das 'X' geschlossen wird
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.build_ui()
        self.update_file_count() # Setzt den anfänglichen Status der Buttons

    def save_current_config(self):
        """Speichert alle aktuellen Eingaben in die JSON-Datei"""
        try:
            current_config = {key: ent.get() for key, ent in self.entries.items()}
            current_config['format'] = self.format_var.get()
            with open(CONFIG_FILE, 'w') as f:
                json.dump(current_config, f)
        except Exception as e:
            self.log_msg(f"Failed to save settings: {e}")

    def on_close(self):
        self.save_current_config()
        self.root.destroy()

    def build_ui(self):
        style = ttk.Style()
        style.configure("LargeBold.TButton", font=("Segoe UI", 11, "bold"))

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === HEADER (Info & Browse Button) ===
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        
        self.lbl_file_count = ttk.Label(top_frame, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_file_count.pack(side=tk.LEFT, pady=5)
        
        self.btn_browse = ttk.Button(top_frame, text="📁 Browse Folder...", command=self.browse_folder)
        self.btn_browse.pack(side=tk.RIGHT)

        # === TRANSFORMATION ===
        lf_trans = ttk.LabelFrame(main_frame, text=" 1. Transformation (Optional, empty = 0) ", padding=10)
        lf_trans.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)

        trans_labels =['trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z', 'scale']
        for i, key in enumerate(trans_labels):
            ttk.Label(lf_trans, text=key.replace('_', ' ').title() + ":").grid(row=i//3, column=(i%3)*2, padx=5, pady=2, sticky="e")
            ent = ttk.Entry(lf_trans, width=10)
            ent.insert(0, str(self.config.get(key, "")))
            ent.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=2)
            self.entries[key] = ent

        # === CROPBOX ===
        lf_crop = ttk.LabelFrame(main_frame, text=" 2. Cropbox (Applied after transformation) ", padding=10)
        lf_crop.grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)
        
        crop_labels =['min_x', 'max_x', 'min_y', 'max_y', 'min_z', 'max_z']
        for i, key in enumerate(crop_labels):
            ttk.Label(lf_crop, text=key.replace('_', ' ').title() + ":").grid(row=i//2, column=(i%2)*2, padx=5, pady=2, sticky="e")
            ent = ttk.Entry(lf_crop, width=10)
            ent.insert(0, str(self.config.get(key, "")))
            ent.grid(row=i//2, column=(i%2)*2+1, padx=5, pady=2)
            self.entries[key] = ent

        # === OUTPUT SETTINGS ===
        lf_format = ttk.LabelFrame(main_frame, text=" 3. Output Settings ", padding=10)
        lf_format.grid(row=3, column=0, columnspan=4, sticky="ew", pady=5)
        
        ttk.Label(lf_format, text="Filename Prefix:").pack(side=tk.LEFT, padx=(5, 5))
        ent_prefix = ttk.Entry(lf_format, width=15)
        ent_prefix.insert(0, str(self.config.get('filename_prefix', 'animation')))
        ent_prefix.pack(side=tk.LEFT, padx=(0, 20))
        self.entries['filename_prefix'] = ent_prefix

        ttk.Radiobutton(lf_format, text="SPZ (Max compression)", variable=self.format_var, value="spz").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(lf_format, text="PLY (Uncompressed)", variable=self.format_var, value="ply").pack(side=tk.LEFT, padx=10)

        # === BUTTONS ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=15, sticky="ew")

        self.btn_start = ttk.Button(button_frame, text="Process All Files (Whole Stack)", style="LargeBold.TButton", command=lambda: self.start_processing(test_mode=False))
        self.btn_start.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10), ipady=8)

        self.btn_test = ttk.Button(button_frame, text="Create Testfile (1st)", command=lambda: self.start_processing(test_mode=True))
        self.btn_test.pack(side=tk.RIGHT, fill=tk.Y)

        # === LOGGING ===
        self.log = tk.Text(main_frame, height=8, width=60, state=tk.DISABLED, bg="#f0f0f0")
        self.log.grid(row=5, column=0, columnspan=4)

    def browse_folder(self):
        """Erlaubt dem User einen Ordner direkt aus der GUI zu wählen"""
        folder = filedialog.askdirectory(parent=self.root, title="Select folder containing .ply files")
        if folder:
            files =[]
            for f in os.listdir(folder):
                if f.lower().endswith('.ply'):
                    files.append(os.path.join(folder, f))
            files.sort()
            self.input_files = files
            self.update_file_count()

    def update_file_count(self):
        """Aktualisiert das UI basierend auf der Anzahl der geladenen Dateien"""
        count = len(self.input_files)
        if count > 0:
            self.lbl_file_count.config(text=f"{count} .ply file(s) loaded. Ready to process.", foreground="green")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_test.config(state=tk.NORMAL)
        else:
            self.lbl_file_count.config(text="No .ply files loaded. Please browse for a folder.", foreground="red")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_test.config(state=tk.DISABLED)

    def log_msg(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def set_gui_state(self, state):
        self.btn_start.config(state=state)
        self.btn_test.config(state=state)
        self.btn_browse.config(state=state)

    def start_processing(self, test_mode=False):
        if not os.path.exists(GSBOX_PATH):
            messagebox.showerror("Error", f"gsbox.exe not found!\nExpected at: {GSBOX_PATH}")
            return

        # Einstellungen sofort speichern
        self.save_current_config()
        self.set_gui_state(tk.DISABLED)

        # Werte auslesen
        user_min_x = parse_float(self.entries['min_x'].get(), -5.0)
        user_max_x = parse_float(self.entries['max_x'].get(), 5.0)
        user_min_y = parse_float(self.entries['min_y'].get(), -5.0)
        user_max_y = parse_float(self.entries['max_y'].get(), 5.0)
        user_min_z = parse_float(self.entries['min_z'].get(), -5.0)
        user_max_z = parse_float(self.entries['max_z'].get(), 5.0)

        bounds = (-user_max_x, -user_min_x, -user_max_y, -user_min_y, user_min_z, user_max_z)

        tx = -parse_float(self.entries['trans_x'].get(), 0.0) 
        ty = -parse_float(self.entries['trans_y'].get(), 0.0) 
        tz = parse_float(self.entries['trans_z'].get(), 0.0)
        rx = parse_float(self.entries['rot_x'].get(), 0.0)
        ry = parse_float(self.entries['rot_y'].get(), 0.0)
        rz = parse_float(self.entries['rot_z'].get(), 0.0)
        scale = parse_float(self.entries['scale'].get(), 1.0)
        
        fmt = self.format_var.get()
        prefix = self.entries['filename_prefix'].get().strip() or "animation"
        needs_transform = any([tx != 0, ty != 0, tz != 0, rx != 0, ry != 0, rz != 0, scale != 1.0])

        work_dir = os.path.dirname(self.input_files[0])
        out_dir = os.path.join(work_dir, f"output_{fmt}")
        temp_dir = os.path.join(work_dir, "temp_processing")
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        files_to_run = [self.input_files[0]] if test_mode else self.input_files
        self.total_count = len(files_to_run)
        self.processed_count = 0

        self.log_msg(f"--- Starting Processing ({self.total_count} files) ---")
        self.log_msg(f"Using multithreading. Output folder: {out_dir}\n")

        thread = threading.Thread(target=self.process_batch, args=(
            files_to_run, bounds, tx, ty, tz, rx, ry, rz, scale, 
            needs_transform, fmt, prefix, temp_dir, out_dir, test_mode
        ), daemon=True)
        thread.start()

    def process_batch(self, files_to_run, bounds, tx, ty, tz, rx, ry, rz, scale, needs_transform, fmt, prefix, temp_dir, out_dir, test_mode):
        max_workers = max(1, os.cpu_count() // 2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures =[]
            for filepath in files_to_run:
                file_index = self.input_files.index(filepath) + 1
                futures.append(executor.submit(
                    self.process_single_file, filepath, file_index, bounds, 
                    tx, ty, tz, rx, ry, rz, scale, needs_transform, 
                    fmt, prefix, temp_dir, out_dir, test_mode
                ))

            for future in concurrent.futures.as_completed(futures):
                try: future.result() 
                except Exception as e: self.log_msg(f"Thread error: {e}")

        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try: os.remove(os.path.join(temp_dir, f))
                except: pass
            try: os.rmdir(temp_dir)
            except: pass

        if test_mode: self.log_msg(f"\n✅ TEST DONE! Check the output folder.")
        else: self.log_msg("\n✅ DONE! All files successfully processed.")
            
        self.root.after(0, lambda: self.set_gui_state(tk.NORMAL))

    def process_single_file(self, filepath, file_index, bounds, tx, ty, tz, rx, ry, rz, scale, needs_transform, fmt, prefix, temp_dir, out_dir, test_mode):
        filename = os.path.basename(filepath)
        name_no_ext = f"{prefix}_{file_index:04d}"
        out_filename = f"{name_no_ext}_TEST.{fmt}" if test_mode else f"{name_no_ext}.{fmt}"
        
        thread_id = threading.get_ident()
        temp_trans_file = os.path.join(temp_dir, f"trans_{thread_id}_{filename}")
        temp_crop_file = os.path.join(temp_dir, f"crop_{thread_id}_{filename}")
        final_out_file = os.path.join(out_dir, out_filename)

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            if needs_transform:
                cmd_args =[GSBOX_PATH, "ply2ply", "-i", filepath, "-o", temp_trans_file]
                if tx != 0: cmd_args.extend(["-tx", str(tx)])
                if ty != 0: cmd_args.extend(["-ty", str(ty)])
                if tz != 0: cmd_args.extend(["-tz", str(tz)])
                if rx != 0: cmd_args.extend(["-rx", str(rx)])
                if ry != 0: cmd_args.extend(["-ry", str(ry)])
                if rz != 0: cmd_args.extend(["-rz", str(rz)])
                if scale != 1.0: cmd_args.extend(["-s", str(scale)])
                
                subprocess.run(cmd_args, startupinfo=startupinfo, check=True)
                crop_input = temp_trans_file
            else:
                crop_input = filepath

            crop_ply(crop_input, temp_crop_file, bounds)

            if fmt == "spz":
                cmd_args =[GSBOX_PATH, "ply2spz", "-i", temp_crop_file, "-o", final_out_file]
                subprocess.run(cmd_args, startupinfo=startupinfo, check=True)
            else:
                shutil.move(temp_crop_file, final_out_file)

        except Exception as e:
            self.log_msg(f"Error on {filename}: {e}")
            return
            
        finally:
            if os.path.exists(temp_trans_file): os.remove(temp_trans_file)
            if os.path.exists(temp_crop_file): os.remove(temp_crop_file)

        with self.lock:
            self.processed_count += 1
            self.log_msg(f"[{self.processed_count}/{self.total_count}] Finished {filename} -> {out_filename}")


if __name__ == "__main__":
    try:
        files_to_process =[]
        
        # Wurde das Programm per SendTo/DragDrop gestartet?
        valid_args = [a for a in sys.argv[1:] if os.path.exists(a)]
        if valid_args:
            first_arg = valid_args[0]
            target_dir = first_arg if os.path.isdir(first_arg) else os.path.dirname(first_arg)
            if os.path.exists(target_dir):
                for f in os.listdir(target_dir):
                    if f.lower().endswith('.ply'):
                        files_to_process.append(os.path.join(target_dir, f))
        
        files_to_process.sort()

        # GUI ganz normal und sicher starten (keine unsichtbaren Fenster-Tricks mehr!)
        root = tk.Tk()
        app = App(root, files_to_process)
        root.mainloop()
        
    except Exception as e:
        # Falls irgendetwas beim Start abstürzt (was bei noconsole unsichtbar wäre),
        # schreiben wir einen Crash-Log auf den Desktop!
        crash_log = os.path.join(os.path.expanduser("~"), "Desktop", "4DGS_CrashLog.txt")
        with open(crash_log, "w") as f:
            f.write(traceback.format_exc())
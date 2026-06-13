import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import fitz  # PyMuPDF
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

class PDFProcessor:
    def __init__(self, parcel_sheets, blackout_sheets, manual_duplex, output_dir, processed_dir, log_callback):
        self.parcel_sheets = parcel_sheets
        self.blackout_sheets = blackout_sheets
        self.manual_duplex = manual_duplex
        self.output_dir = output_dir
        self.processed_dir = processed_dir
        self.log = log_callback

    def process(self, input_pdf):
        self.log(f"Processing: {os.path.basename(input_pdf)}")
        try:
            doc = fitz.open(input_pdf)
        except Exception as e:
            self.log(f"Error opening {input_pdf}: {e}")
            return False

        if len(doc) == 0:
            self.log("PDF is empty. Skipping.")
            return False

        # Prepare dimensions based on first page
        src_rect = doc[0].rect
        out_width = src_rect.width * 2
        out_height = src_rect.height

        P = self.parcel_sheets * 4
        
        # Prepare mapped pages
        new_pages = []
        src_idx = 0
        total_src = len(doc)

        while src_idx < total_src:
            parcel_content = []
            for i in range(1, P + 1):
                if i <= P // 2:
                    sheet_idx = (i + 1) // 2
                else:
                    sheet_idx = (P - i + 2) // 2
                
                if sheet_idx in self.blackout_sheets:
                    parcel_content.append(None)
                else:
                    if src_idx < total_src:
                        parcel_content.append(src_idx)
                        src_idx += 1
                    else:
                        parcel_content.append(None)
            new_pages.extend(parcel_content)

        out_doc_front = fitz.open()
        out_doc_back = fitz.open() if self.manual_duplex else out_doc_front

        chunks = len(new_pages) // P
        
        for c in range(chunks):
            chunk = new_pages[c*P : (c+1)*P]
            for k in range(1, self.parcel_sheets + 1):
                if k in self.blackout_sheets:
                    continue  # Skip rendering this physical sheet entirely

                # Front side
                front_left = chunk[P - 2*k + 1]
                front_right = chunk[2*k - 2]
                
                # Back side
                back_left = chunk[2*k - 1]
                back_right = chunk[P - 2*k]

                # Render Front
                page_front = out_doc_front.new_page(width=out_width, height=out_height)
                if front_left is not None:
                    page_front.show_pdf_page(fitz.Rect(0, 0, src_rect.width, src_rect.height), doc, front_left)
                if front_right is not None:
                    page_front.show_pdf_page(fitz.Rect(src_rect.width, 0, out_width, src_rect.height), doc, front_right)

                # Render Back
                page_back = out_doc_back.new_page(width=out_width, height=out_height)
                if back_left is not None:
                    page_back.show_pdf_page(fitz.Rect(0, 0, src_rect.width, src_rect.height), doc, back_left)
                if back_right is not None:
                    page_back.show_pdf_page(fitz.Rect(src_rect.width, 0, out_width, src_rect.height), doc, back_right)

        base_name = os.path.splitext(os.path.basename(input_pdf))[0]
        try:
            if self.manual_duplex:
                front_path = os.path.join(self.output_dir, f"{base_name}_Front_Sides.pdf")
                back_path = os.path.join(self.output_dir, f"{base_name}_Back_Sides.pdf")
                out_doc_front.save(front_path)
                out_doc_back.save(back_path)
                self.log(f"Saved manual duplex outputs:\n  {front_path}\n  {back_path}")
            else:
                out_path = os.path.join(self.output_dir, f"{base_name}_Booklet.pdf")
                out_doc_front.save(out_path)
                self.log(f"Saved auto duplex output:\n  {out_path}")
            
            doc.close()
            out_doc_front.close()
            if self.manual_duplex:
                out_doc_back.close()
            
            # Move to processed
            shutil.move(input_pdf, os.path.join(self.processed_dir, os.path.basename(input_pdf)))
            return True
        except Exception as e:
            self.log(f"Failed to save output for {base_name}: {e}")
            return False

class PDFHandler(FileSystemEventHandler):
    def __init__(self, processor_factory, log_callback):
        self.processor_factory = processor_factory
        self.log = log_callback
        self.processing = set()

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.schedule_process(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.schedule_process(event.src_path)

    def schedule_process(self, path):
        if path in self.processing:
            return
        self.processing.add(path)
        threading.Thread(target=self._wait_and_process, args=(path,), daemon=True).start()

    def _wait_and_process(self, path):
        # Wait for file to finish writing (e.g. from Print to PDF)
        stable_count = 0
        last_size = -1
        while stable_count < 3:
            time.sleep(1)
            if not os.path.exists(path):
                self.processing.discard(path)
                return
            try:
                current_size = os.path.getsize(path)
                if current_size == last_size and current_size > 0:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_size = current_size
            except Exception:
                stable_count = 0
                
        # Try to rename it to itself to ensure it's not locked
        try:
            os.rename(path, path)
        except OSError:
            self.log(f"File locked, waiting: {os.path.basename(path)}")
            time.sleep(2)
            self.processing.discard(path)
            self.schedule_process(path)
            return

        processor = self.processor_factory()
        processor.process(path)
        self.processing.discard(path)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coptic Print - Bookbinding PDF Formatter")
        self.geometry("600x500")
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_dir = os.path.join(self.base_dir, "Input")
        self.output_dir = os.path.join(self.base_dir, "Output")
        self.processed_dir = os.path.join(self.base_dir, "Processed")
        
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

        self.observer = None
        
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Parcel Config
        ttk.Label(frame, text="Sheets per Parcel:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.var_sheets = tk.IntVar(value=3)
        ttk.Spinbox(frame, from_=1, to=20, textvariable=self.var_sheets, width=5).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Blackout Sheets (comma-separated e.g., '2,4'):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.var_blackout = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.var_blackout, width=20).grid(row=1, column=1, sticky=tk.W, pady=5)

        # Print Mode
        ttk.Label(frame, text="Print Mode:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.var_mode = tk.StringVar(value="auto")
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Auto Duplex (Single PDF)", variable=self.var_mode, value="auto").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Manual Single-Sided (Split Front/Back)", variable=self.var_mode, value="manual").pack(side=tk.LEFT, padx=5)

        # Controls
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.btn_start = ttk.Button(ctrl_frame, text="Start Watching Input Folder", command=self.start_watching)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(ctrl_frame, text="Stop Watching", command=self.stop_watching, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # Log
        ttk.Label(frame, text="Log:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.log_area = scrolledtext.ScrolledText(frame, width=70, height=15, state='disabled')
        self.log_area.grid(row=5, column=0, columnspan=2, sticky=(tk.N, tk.E, tk.W, tk.S))
        
        self.log(f"Ready. Input folder: {self.input_dir}")

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def get_processor(self):
        sheets = self.var_sheets.get()
        blackout_str = self.var_blackout.get()
        blackout = []
        if blackout_str.strip():
            try:
                blackout = [int(x.strip()) for x in blackout_str.split(',')]
            except Exception:
                self.log("Warning: Invalid blackout sheets format. Ignoring blackout.")
                
        manual = self.var_mode.get() == "manual"
        return PDFProcessor(sheets, blackout, manual, self.output_dir, self.processed_dir, self.log)

    def start_watching(self):
        if self.observer is not None:
            return
            
        handler = PDFHandler(self.get_processor, self.log)
        self.observer = Observer()
        self.observer.schedule(handler, self.input_dir, recursive=False)
        self.observer.start()
        
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log("Started watching Input folder for new PDFs...")

        # Check existing files
        for f in os.listdir(self.input_dir):
            if f.lower().endswith('.pdf'):
                path = os.path.join(self.input_dir, f)
                handler.schedule_process(path)

    def stop_watching(self):
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log("Stopped watching.")

if __name__ == "__main__":
    app = App()
    app.mainloop()

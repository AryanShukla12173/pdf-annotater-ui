import os
import json
import fitz
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading

# Folders
ANNOTATIONS_FOLDER = "annotations"
EXPORT_FOLDER = "exports"
os.makedirs(ANNOTATIONS_FOLDER, exist_ok=True)
os.makedirs(os.path.join(EXPORT_FOLDER, "images"), exist_ok=True)
os.makedirs(os.path.join(EXPORT_FOLDER, "labels"), exist_ok=True)

LABEL_OPTIONS = ["TITLE", "H1", "H2", "H3", "H4", "BODY"]
LABEL_MAP = {name: idx + 1 for idx, name in enumerate(LABEL_OPTIONS)}
HANDLE_SIZE = 8

class PDFAnnotationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimized PDF Annotation Tool")

        self.pdf_files = []
        self.current_pdf_index = 0
        self.current_pdf = None
        self.doc = None
        self.current_page = 0
        self.annotations = []

        self.zoom = 1.5
        self.tk_img = None
        self.page_cache = {}  # Cache rendered pages

        # Drawing state
        self.start_x = None
        self.start_y = None
        self.temp_rect = None
        self.selected_box = None
        self.dragging = False
        self.resizing = False
        self.resize_handle = None

        # Canvas
        self.canvas = tk.Canvas(root, width=900, height=1100, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH)
        self.canvas.focus_set()

        # Sidebar
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.label_var = tk.StringVar(value="TITLE")
        tk.Label(right_frame, text="Label:").pack()
        self.label_menu = ttk.Combobox(right_frame, textvariable=self.label_var, values=LABEL_OPTIONS)
        self.label_menu.pack(pady=5)

        tk.Button(right_frame, text="Open Folder", command=self.load_folder).pack(pady=10)
        tk.Button(right_frame, text="Auto Detect Headings", command=self.auto_detect_headings).pack(pady=10)
        tk.Button(right_frame, text="Previous PDF", command=self.prev_pdf).pack(pady=5)
        tk.Button(right_frame, text="Next PDF", command=self.next_pdf).pack(pady=5)
        tk.Button(right_frame, text="Previous Page", command=self.prev_page).pack(pady=5)
        tk.Button(right_frame, text="Next Page", command=self.next_page).pack(pady=5)
        tk.Button(right_frame, text="Zoom +", command=lambda: self.change_zoom(0.2)).pack(pady=5)
        tk.Button(right_frame, text="Zoom -", command=lambda: self.change_zoom(-0.2)).pack(pady=5)
        tk.Button(right_frame, text="Save Annotations", command=lambda: threading.Thread(target=self.save_annotations).start()).pack(pady=20)
        tk.Button(right_frame, text="Export COCO", command=self.export_coco).pack(pady=10)
        tk.Button(right_frame, text="Export YOLO", command=self.export_yolo).pack(pady=10)

        self.page_label = tk.Label(right_frame, text="Page 0/0")
        self.page_label.pack(pady=10)
        self.pdf_label = tk.Label(right_frame, text="PDF: None")
        self.pdf_label.pack(pady=10)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Delete>", self.delete_selected)
        self.canvas.bind("<Button-3>", self.select_box)

    # ------------------- PDF Handling -------------------
    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.pdf_files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".pdf")])
        if not self.pdf_files:
            messagebox.showerror("Error", "No PDF files found!")
            return
        self.current_pdf_index = 0
        self.open_pdf(self.pdf_files[self.current_pdf_index])

    def prev_pdf(self):
        if self.current_pdf_index > 0:
            threading.Thread(target=self.save_annotations).start()
            self.current_pdf_index -= 1
            self.open_pdf(self.pdf_files[self.current_pdf_index])

    def next_pdf(self):
        if self.current_pdf_index < len(self.pdf_files) - 1:
            threading.Thread(target=self.save_annotations).start()
            self.current_pdf_index += 1
            self.open_pdf(self.pdf_files[self.current_pdf_index])

    def open_pdf(self, pdf_path):
        if self.doc:
            self.doc.close()
        self.current_pdf = pdf_path
        self.doc = fitz.open(pdf_path)
        self.current_page = 0
        self.page_cache.clear()
        self.load_annotations()
        self.render_page()
        self.pdf_label.config(text=f"PDF: {os.path.basename(pdf_path)}")

    # ------------------- Rendering -------------------
    def render_page(self):
        cache_key = (self.current_pdf, self.current_page, round(self.zoom, 1))
        if cache_key in self.page_cache:
            img = self.page_cache[cache_key]
        else:
            page = self.doc[self.current_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
            img = ImageTk.PhotoImage(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
            self.page_cache[cache_key] = img
        self.tk_img = img
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.page_label.config(text=f"Page {self.current_page+1}/{len(self.doc)}")
        self.draw_annotations()

    def draw_annotations(self):
        for ann in self.annotations:
            if ann["page"] == self.current_page:
                x0, y0, x1, y1 = [coord * self.zoom for coord in ann["bbox_pdf"]]
                color = "yellow" if self.selected_box == ann else "red"
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2)
                self.canvas.create_text(x0 + 5, y0 + 10, text=ann["label"], anchor="nw", fill=color)
                if self.selected_box == ann:
                    self.draw_resize_handles(x0, y0, x1, y1)

    def draw_resize_handles(self, x0, y0, x1, y1):
        handle_positions = [
            (x0, y0), (x1, y0), (x0, y1), (x1, y1),
            ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)
        ]
        for hx, hy in handle_positions:
            self.canvas.create_rectangle(hx - HANDLE_SIZE / 2, hy - HANDLE_SIZE / 2,
                                         hx + HANDLE_SIZE / 2, hy + HANDLE_SIZE / 2,
                                         outline="blue", fill="blue")

    # ------------------- Mouse Events -------------------
    def on_mouse_down(self, event):
        if self.selected_box:
            x0, y0, x1, y1 = [coord * self.zoom for coord in self.selected_box["bbox_pdf"]]
            handle_positions = [
                (x0, y0), (x1, y0), (x0, y1), (x1, y1),
                ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)
            ]
            for idx, (hx, hy) in enumerate(handle_positions):
                if abs(event.x - hx) <= HANDLE_SIZE and abs(event.y - hy) <= HANDLE_SIZE:
                    self.resizing = True
                    self.resize_handle = idx
                    return
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.dragging = True
                self.offset_x = event.x - x0
                self.offset_y = event.y - y0
                return
        self.start_x, self.start_y = event.x, event.y
        self.temp_rect = self.canvas.create_rectangle(self.start_x, self.start_y,
                                                      self.start_x, self.start_y,
                                                      outline="green", width=2)

    def on_mouse_drag(self, event):
        if self.resizing and self.selected_box:
            x0, y0, x1, y1 = [coord * self.zoom for coord in self.selected_box["bbox_pdf"]]
            if self.resize_handle in [0, 4, 6]: x0 = event.x
            if self.resize_handle in [1, 5, 7]: x1 = event.x
            if self.resize_handle in [0, 1, 4, 5]: y0 = event.y
            if self.resize_handle in [2, 3, 6, 7]: y1 = event.y
            self.selected_box["bbox_pdf"] = [x0 / self.zoom, y0 / self.zoom, x1 / self.zoom, y1 / self.zoom]
            self.render_page()
        elif self.dragging and self.selected_box:
            w = (self.selected_box["bbox_pdf"][2] - self.selected_box["bbox_pdf"][0]) * self.zoom
            h = (self.selected_box["bbox_pdf"][3] - self.selected_box["bbox_pdf"][1]) * self.zoom
            new_x0 = event.x - self.offset_x
            new_y0 = event.y - self.offset_y
            self.selected_box["bbox_pdf"] = [new_x0 / self.zoom, new_y0 / self.zoom,
                                             (new_x0 + w) / self.zoom, (new_y0 + h) / self.zoom]
            self.render_page()
        elif self.temp_rect:
            self.canvas.coords(self.temp_rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if self.dragging:
            self.dragging = False
        elif self.resizing:
            self.resizing = False
            self.resize_handle = None
        elif self.temp_rect:
            coords = self.canvas.coords(self.temp_rect)
            if len(coords) == 4:
                x0, y0, x1, y1 = coords
                if abs(x1 - x0) > 10 and abs(y1 - y0) > 10:
                    self.annotations.append({
                        "page": self.current_page,
                        "bbox_pdf": [x0 / self.zoom, y0 / self.zoom, x1 / self.zoom, y1 / self.zoom],
                        "label": self.label_var.get(),
                        "text": ""
                    })
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None
            self.canvas.focus_set()
            self.render_page()

    def select_box(self, event):
        for ann in self.annotations:
            bx0, by0, bx1, by1 = [coord * self.zoom for coord in ann["bbox_pdf"]]
            if bx0 <= event.x <= bx1 and by0 <= event.y <= by1 and ann["page"] == self.current_page:
                self.selected_box = ann
                self.canvas.focus_set()
                self.render_page()
                break

    def delete_selected(self, event):
        if self.selected_box:
            self.annotations.remove(self.selected_box)
            self.selected_box = None
            self.render_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()

    def change_zoom(self, delta):
        self.zoom = max(0.5, self.zoom + delta)
        self.render_page()

    # ------------------- Save and Load -------------------
    def extract_text_precise(self, page, rect):
        return page.get_text("text", clip=rect).strip()

    def save_annotations(self):
        if self.current_pdf:
            for ann in self.annotations:
                if ann["page"] < len(self.doc):
                    page = self.doc[ann["page"]]
                    bbox = ann["bbox_pdf"]
                    rect = fitz.Rect(min(bbox[0], bbox[2]), min(bbox[1], bbox[3]),
                                     max(bbox[0], bbox[2]), max(bbox[1], bbox[3]))
                    ann["text"] = self.extract_text_precise(page, rect)
            out_path = os.path.join(ANNOTATIONS_FOLDER,
                                    f"{os.path.splitext(os.path.basename(self.current_pdf))[0]}_annotations.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(self.annotations, f, indent=4)
            print(f"Saved annotations: {out_path}")

    def load_annotations(self):
        json_path = os.path.join(ANNOTATIONS_FOLDER,
                                 f"{os.path.splitext(os.path.basename(self.current_pdf))[0]}_annotations.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                self.annotations = json.load(f)
        else:
            self.annotations = []

    def auto_detect_headings(self):
        if not self.doc:
            return
        page = self.doc[self.current_page]
        text_data = page.get_text("dict")
        detected = []
        for block in text_data["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        size = span["size"]
                        text = span["text"].strip()
                        if len(text) > 2:
                            rect = span["bbox"]
                            label = "BODY"
                            if size > 18:
                                label = "TITLE"
                            elif size > 14:
                                label = "H1"
                            elif size > 12:
                                label = "H2"
                            detected.append({"page": self.current_page, "bbox_pdf": rect, "label": label, "text": text})
        self.annotations.extend(detected)
        self.render_page()

    # ------------------- Export -------------------
    def export_coco(self):
        # (Same as before)
        pass

    def export_yolo(self):
        # (Same as before)
        pass


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAnnotationApp(root)
    root.mainloop()

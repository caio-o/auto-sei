import os
import re
import time
import threading
import subprocess
import sys
import tkinter as tk
from tkinter import (
    filedialog,
    messagebox,
    StringVar,
    Toplevel,
    Label,
    Button,
    Entry,
    simpledialog,
)
from tkinter import ttk

import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab, Image, ImageTk
from pynput import keyboard

from process_store import (
    load_process_data,
    save_process_data,
    list_saved_processes,
    delete_process_data,
    load_app_config,
    save_app_config,
)
from word_template_utils import extract_placeholders_from_docx, render_template_to_docx
from excel_utils import export_process_to_excel, build_excel_row_text


OCR_LANG = "por+eng"
HOTKEY_CAPTURE = "<f8>"
HOTKEY_QUIT = "<f9>"

SELECTION_RECT_OUTER = "#00E5FF"
SELECTION_RECT_INNER = "#FFFFFF"
SELECTION_TEXT = "#FFD400"
SELECTION_BG_ALPHA = 0.52

capture_lock = threading.Lock()

FIELD_LABELS = {
    "numero_titulo": "Nº título",
    "data_emissao": "Data de emissão",
    "titular": "Titular",
    "cpf_titular": "CPF titular",
    "conjuge": "Cônjuge",
    "cpf_conjuge": "CPF cônjuge",
    "pa": "PA",
    "lote": "Lote",
    "municipio": "Município",
    "extrato": "Extrato",
    "memoria": "Memória",
    "gru": "GRU",
    "observacao": "Observação",
    "numero_processo": "Número do processo",
    "data_atual": "Data atual",
}

FIELD_ORDER = [
    "numero_titulo",
    "data_emissao",
    "titular",
    "cpf_titular",
    "conjuge",
    "cpf_conjuge",
    "pa",
    "lote",
    "municipio",
    "extrato",
    "memoria",
    "gru",
    "observacao",
]

CAPTURE_KEYS = [
    "numero_titulo",
    "data_emissao",
    "titular",
    "cpf_titular",
    "conjuge",
    "cpf_conjuge",
    "pa",
    "lote",
    "municipio",
]

MANUAL_ONLY_KEYS = ["extrato", "memoria", "gru", "observacao", "requerimento"]


def get_field_label(key: str) -> str:
    return FIELD_LABELS.get(str(key or ""), str(key or ""))


def normalize_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "ﬁ": "fi",
        "ﬂ": "fl",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)

    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    prev_blank = False

    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
            continue
        cleaned.append(line)
        prev_blank = False

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = text.replace(" N0 ", " N° ")
    text = text.replace(" No ", " N° ")
    text = text.replace("|", "I")

    return text.strip()


def merge_broken_single_lines(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    if len(lines) <= 3:
        return " ".join(lines).strip()
    return text.strip()


def upscale_for_small_text(img_bgr: np.ndarray, scale: float = 3.0) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    return cv2.resize(
        img_bgr,
        (max(1, int(w * scale)), max(1, int(h * scale))),
        interpolation=cv2.INTER_CUBIC,
    )


def preprocess_variants(img_bgr: np.ndarray):
    up = upscale_for_small_text(img_bgr, scale=3.0)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

    blur = cv2.bilateralFilter(gray, 9, 75, 75)

    kernel_sharp = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(blur, -1, kernel_sharp)

    th_adapt = cv2.adaptiveThreshold(
        sharp,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    _, th_otsu = cv2.threshold(
        sharp,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    return [gray, sharp, th_adapt, th_otsu]


def ocr_with_confidence(img_any: np.ndarray, psm: int):
    if len(img_any.shape) == 2:
        img_rgb = cv2.cvtColor(img_any, cv2.COLOR_GRAY2RGB)
    else:
        img_rgb = cv2.cvtColor(img_any, cv2.COLOR_BGR2RGB)

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        img_rgb,
        lang=OCR_LANG,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    words = []
    confs = []

    for txt, conf in zip(data["text"], data["conf"]):
        txt = txt.strip()
        try:
            conf = float(conf)
        except Exception:
            conf = -1

        if txt:
            words.append(txt)
        if conf >= 0:
            confs.append(conf)

    text = " ".join(words).strip()
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return text, avg_conf


def best_ocr_from_image(img_bgr: np.ndarray):
    variants = preprocess_variants(img_bgr)
    psms = [6, 7, 11, 12]

    best_text = ""
    best_conf = 0.0
    best_score = -9999.0

    for variant in variants:
        for psm in psms:
            text, conf = ocr_with_confidence(variant, psm)
            clean = normalize_text(text)
            score = conf + min(len(clean) * 0.03, 15)

            if score > best_score:
                best_text = clean
                best_conf = conf
                best_score = score

    return best_text, best_conf


def do_ocr_from_pil(pil_img: Image.Image):
    img = np.array(pil_img)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    text, conf = best_ocr_from_image(img_bgr)
    text = normalize_text(text)
    return text, conf


def sanitize_text_for_path(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[\\:*?"<>|]', "_", text)
    text = re.sub(r"\s+", " ", text)
    return text


def preserve_process_format_for_filename(text: str) -> str:
    text = sanitize_text_for_path(text)
    return text.replace("/", "∕")

def create_default_process_data(process_number: str) -> dict:
    from datetime import datetime

    return {
        "numero_processo": process_number,
        "data_atual": datetime.now().strftime("%d/%m/%Y"),

        # OCR
        "numero_titulo": "",
        "data_emissao": "",
        "titular": "",
        "cpf_titular": "",
        "conjuge": "",
        "cpf_conjuge": "",
        "pa": "",
        "lote": "",
        "municipio": "",

        # MANUAIS
        "extrato": "",
        "memoria": "",
        "gru": "",
        "observacao": "",
        "requerimento": "",
    }

def ensure_all_default_keys(data: dict, process_number: str = "") -> dict:
    base = create_default_process_data(process_number or str((data or {}).get("numero_processo", "") or ""))
    merged = dict(base)
    if isinstance(data, dict):
        merged.update(data)
    for key in FIELD_ORDER:
        merged.setdefault(key, "")
    return merged


class ScreenSelector:
    def __init__(self, parent):
        self.parent = parent
        self.overlay = Toplevel(self.parent)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", SELECTION_BG_ALPHA)
        self.overlay.configure(bg="black")
        self.overlay.config(cursor="tcross")

        self.start_x = None
        self.start_y = None
        self.rect_outer = None
        self.rect_inner = None
        self.dim_text = None
        self.bbox = None

        self.canvas = tk.Canvas(self.overlay, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.overlay.bind("<Escape>", self.cancel)

        self.canvas.create_rectangle(
            18,
            18,
            520,
            74,
            fill="#111111",
            outline=SELECTION_TEXT,
            width=2,
        )

        self.canvas.create_text(
            30,
            30,
            anchor="nw",
            text="Arrasta pra selecionar | Esc cancela",
            fill=SELECTION_TEXT,
            font=("Arial", 16, "bold"),
        )

    def on_press(self, event):
        self.start_x = self.overlay.winfo_pointerx()
        self.start_y = self.overlay.winfo_pointery()

        self.rect_outer = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline=SELECTION_RECT_OUTER,
            width=4,
        )

        self.rect_inner = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline=SELECTION_RECT_INNER,
            width=2,
            dash=(6, 4),
        )

        self.dim_text = self.canvas.create_text(
            self.start_x + 12,
            self.start_y - 12,
            anchor="sw",
            text="0 x 0",
            fill=SELECTION_RECT_OUTER,
            font=("Arial", 14, "bold"),
        )

    def on_drag(self, event):
        cur_x = self.overlay.winfo_pointerx()
        cur_y = self.overlay.winfo_pointery()

        self.canvas.coords(self.rect_outer, self.start_x, self.start_y, cur_x, cur_y)
        self.canvas.coords(self.rect_inner, self.start_x, self.start_y, cur_x, cur_y)

        width = abs(cur_x - self.start_x)
        height = abs(cur_y - self.start_y)

        label_x = min(self.start_x, cur_x) + 10
        label_y = min(self.start_y, cur_y) - 8
        if label_y < 20:
            label_y = min(self.start_y, cur_y) + 20

        self.canvas.coords(self.dim_text, label_x, label_y)
        self.canvas.itemconfig(self.dim_text, text=f"{width} x {height}")

    def on_release(self, event):
        end_x = self.overlay.winfo_pointerx()
        end_y = self.overlay.winfo_pointery()

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        if abs(x2 - x1) >= 5 and abs(y2 - y1) >= 5:
            self.bbox = (x1, y1, x2, y2)

        self.overlay.destroy()

    def cancel(self, event=None):
        self.bbox = None
        self.overlay.destroy()

    def get_bbox(self):
        self.parent.wait_window(self.overlay)
        return self.bbox


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR + Modelo Word")
        self.root.geometry("1220x700")

        self.process_number = ""
        self.template_path = ""
        self.fields = []
        self.data = {}
        self.current_selected_field = StringVar(value="")
        self.current_selected_key = ""
        self.nome_usuario_salvar = ""
        self.ocr_busy = False
        self.hotkeys = None

        # AUTO COLAR MANUAL
        self.auto_manual_paste_var = tk.BooleanVar(value=False)
        self.last_clipboard_text = ""
        self.clipboard_popup_open = False

        self.config = load_app_config()
        self.build_ui()
        self.load_config_into_app()
        self.initialize_process()

        try:
            self.hotkeys = keyboard.GlobalHotKeys({
                HOTKEY_CAPTURE: lambda: threading.Thread(
                    target=self.capture_and_fill,
                    daemon=True,
                ).start(),
                HOTKEY_QUIT: self.quit_program,
            })
            self.hotkeys.start()
            self.set_status("Atalhos ativos: F8 captura | F9 sai")
        except Exception as e:
            self.set_status(f"Atalhos não iniciaram: {e}")

        self.schedule_clipboard_watch()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=10)

        row1 = tk.Frame(top)
        row1.pack(fill="x", pady=(0, 4))
        row2 = tk.Frame(top)
        row2.pack(fill="x")

        Button(row1, text="Selecionar modelo Word", command=self.select_template, width=22).pack(side="left", padx=4)
        Button(row1, text="Novo processo", command=self.open_new_process_flow, width=14).pack(side="left", padx=4)
        Button(row1, text="Histórico", command=self.open_history_window, width=12).pack(side="left", padx=4)
        self.btn_capture = Button(row1, text="Capturar (F8)", command=lambda: threading.Thread(target=self.capture_and_fill, daemon=True).start(), width=16)
        self.btn_capture.pack(side="left", padx=4)
        Button(row1, text="Salvar dados", command=self.save_data, width=14).pack(side="left", padx=4)
        Button(row1, text="Gerar Word", command=self.generate_word, width=14).pack(side="left", padx=4)

        Button(row2, text="Gerar Excel", command=self.generate_excel, width=14).pack(side="left", padx=4)
        Button(row2, text="Copiar Nº Título", command=self.copy_numero_titulo, width=18).pack(side="left", padx=4)
        Button(row2, text="Copiar texto Excel", command=self.copy_excel_text, width=18).pack(side="left", padx=4)
        Button(row2, text="Boot", command=self.open_boot_window, width=12).pack(side="left", padx=4)
        tk.Checkbutton(
            row2,
            text="Auto colar manual",
            variable=self.auto_manual_paste_var,
            command=self.toggle_auto_manual_paste,
        ).pack(side="left", padx=8)
        Button(row2, text="Abrir Renomeador", command=self.run_rename_app, width=18).pack(side="left", padx=4)

        info = tk.Frame(self.root)
        info.pack(fill="x", padx=12, pady=(0, 8))

        self.lbl_process = Label(info, text="Processo atual: -", anchor="w", font=("Arial", 10, "bold"))
        self.lbl_process.pack(fill="x")

        self.lbl_model = Label(info, text="Modelo: não selecionado", anchor="w")
        self.lbl_model.pack(fill="x")

        self.lbl_name = Label(info, text="Nome para salvar: não definido", anchor="w")
        self.lbl_name.pack(fill="x")

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.status_var = StringVar(value="Pronto.")
        self.lbl_status = Label(status_frame, textvariable=self.status_var, anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True)

        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=220)
        self.progress.pack(side="right", padx=4)

        body = tk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(body)
        left.pack(side="left", fill="y")

        Label(left, text="Campos de captura / OCR", font=("Arial", 12, "bold")).pack(anchor="w")
        self.capture_listbox = tk.Listbox(left, width=34, height=12, exportselection=False)
        self.capture_listbox.pack(fill="y", pady=(6, 10))
        self.capture_listbox.bind("<<ListboxSelect>>", lambda event: self.on_select_field("capture"))

        Label(left, text="Campos manuais", font=("Arial", 12, "bold")).pack(anchor="w")
        self.manual_listbox = tk.Listbox(left, width=34, height=10, exportselection=False)
        self.manual_listbox.pack(fill="y", pady=(6, 0))
        self.manual_listbox.bind("<<ListboxSelect>>", lambda event: self.on_select_field("manual"))

        center = tk.Frame(body)
        center.pack(side="left", fill="both", expand=True, padx=12)

        Label(center, text="Campo selecionado", font=("Arial", 11, "bold")).pack(anchor="w")
        self.entry_field = Entry(center, textvariable=self.current_selected_field, font=("Arial", 12), state="readonly", width=40)
        self.entry_field.pack(fill="x", pady=(0, 8))

        Label(center, text="Valor", font=("Arial", 11, "bold")).pack(anchor="w")
        self.text_value = tk.Text(center, height=10, font=("Consolas", 11))
        self.text_value.pack(fill="x", pady=(0, 8))

        btn_row = tk.Frame(center)
        btn_row.pack(fill="x", pady=(0, 10))
        Button(btn_row, text="Atualizar valor", command=self.update_current_value, width=18).pack(side="left", padx=4)
        Button(btn_row, text="Limpar valor", command=self.clear_current_value, width=18).pack(side="left", padx=4)

        Label(center, text="Todos os valores", font=("Arial", 11, "bold")).pack(anchor="w")
        self.text_all = tk.Text(center, height=22, font=("Consolas", 10))
        self.text_all.pack(fill="both", expand=True)

    def get_ordered_keys(self):
        keys = []
        seen = set()

        for key in FIELD_ORDER:
            if key not in seen:
                keys.append(key)
                seen.add(key)

        for key in (self.fields or []):
            if key not in seen:
                keys.append(key)
                seen.add(key)

        for key in sorted((self.data or {}).keys()):
            if key not in seen and key not in ("numero_processo", "data_atual"):
                keys.append(key)
                seen.add(key)

        return keys

    def get_capture_keys(self):
        return [key for key in CAPTURE_KEYS if key in self.get_ordered_keys() or key in FIELD_ORDER]

    def get_manual_keys(self):
        keys = []
        seen = set()
        for key in MANUAL_ONLY_KEYS:
            if key in self.get_ordered_keys() and key not in seen:
                keys.append(key)
                seen.add(key)
        return keys

    def clear_field_selection(self):
        try:
            self.capture_listbox.selection_clear(0, tk.END)
        except Exception:
            pass
        try:
            self.manual_listbox.selection_clear(0, tk.END)
        except Exception:
            pass

    def get_selected_list_name(self):
        try:
            if self.capture_listbox.curselection():
                return "capture"
        except Exception:
            pass
        try:
            if self.manual_listbox.curselection():
                return "manual"
        except Exception:
            pass
        return ""


    def select_field_by_key(self, key: str):
        key = str(key or "").strip()
        if not key:
            return

        capture_keys = self.get_capture_keys()
        manual_keys = self.get_manual_keys()

        self.clear_field_selection()

        if key in capture_keys:
            idx = capture_keys.index(key)
            self.capture_listbox.selection_set(idx)
            self.capture_listbox.activate(idx)
            self.capture_listbox.see(idx)
        elif key in manual_keys:
            idx = manual_keys.index(key)
            self.manual_listbox.selection_set(idx)
            self.manual_listbox.activate(idx)
            self.manual_listbox.see(idx)
        else:
            return

        self.current_selected_key = key
        self.current_selected_field.set(get_field_label(key))
        self.text_value.delete("1.0", tk.END)
        self.text_value.insert("1.0", str(self.data.get(key, "") or ""))


    def load_config_into_app(self):
        model_path = self.config.get("modelo_word_path", "").strip()
        saved_name = self.config.get("nome_usuario_salvar", "").strip()
        boot_cfg = self.config.get("boot_config", {}) if isinstance(self.config.get("boot_config", {}), dict) else {}
        if "boot_script_path" not in self.config:
            self.config["boot_script_path"] = str(boot_cfg.get("script_path", "") or "")
        if "boot_macro" not in self.config:
            self.config["boot_macro"] = str(boot_cfg.get("macro", "") or "")

        self.nome_usuario_salvar = saved_name
        self.update_name_label()

        if model_path and os.path.exists(model_path):
            try:
                self.apply_template_path(model_path, save_config=False)
                self.set_status("Modelo salvo carregado.")
            except Exception:
                self.template_path = ""
                self.fields = []
                self.lbl_model.config(text="Modelo salvo inválido. Selecione um novo.")
                self.set_status("Modelo salvo ficou inválido.")
        else:
            self.lbl_model.config(text="Modelo: não selecionado")

    def initialize_process(self):
        ultimo = self.config.get("ultimo_processo", "").strip()
        if ultimo:
            dados = load_process_data(ultimo)
            if dados:
                self.load_process_into_ui(ultimo, dados)
                self.set_status("Último processo carregado.")
                return

        self.open_new_process_flow()

    def set_status(self, text: str):
        self.status_var.set(text)

    def start_busy(self, message: str):
        self.ocr_busy = True
        self.progress.start(10)
        self.btn_capture.config(state="disabled")
        self.set_status(message)

    def stop_busy(self, message: str):
        self.ocr_busy = False
        self.progress.stop()
        self.btn_capture.config(state="normal")
        self.set_status(message)

    def update_name_label(self):
        if self.nome_usuario_salvar.strip():
            self.lbl_name.config(text=f"Nome para salvar: {self.nome_usuario_salvar}")
        else:
            self.lbl_name.config(text="Nome para salvar: não definido")

    def ensure_save_name(self) -> bool:
        if not getattr(self, "nome_usuario_salvar", "").strip():
            nome = simpledialog.askstring(
                "Nome para salvar",
                "Digite o nome da pessoa para usar no nome do arquivo:",
            )
            if not nome or not nome.strip():
                messagebox.showwarning("Aviso", "Nome não informado.")
                return False

            self.nome_usuario_salvar = nome.strip()
            self.config["nome_usuario_salvar"] = self.nome_usuario_salvar
            save_app_config(self.config)
            self.update_name_label()

        return True

    def apply_template_path(self, path: str, save_config: bool = True):
        fields = extract_placeholders_from_docx(path)
        if not fields:
            raise ValueError("Nenhuma chave {campo} encontrada no modelo.")

        self.template_path = path
        self.fields = fields

        for key in fields:
            self.data.setdefault(key, "")

        self.reload_field_list()
        self.refresh_all_values()
        self.lbl_model.config(text=f"Modelo: {path}")

        if save_config:
            self.config["modelo_word_path"] = path
            save_app_config(self.config)



    def toggle_auto_manual_paste(self):
        ativo = bool(self.auto_manual_paste_var.get())
        if ativo:
            try:
                self.last_clipboard_text = str(self.root.clipboard_get() or "").strip()
            except Exception:
                self.last_clipboard_text = ""
            self.set_status("Auto colar manual ativado.")
            self.schedule_clipboard_watch()
        else:
            self.set_status("Auto colar manual desativado.")

    def schedule_clipboard_watch(self):
        self.root.after(800, self.check_clipboard_for_manual_paste)

    def check_clipboard_for_manual_paste(self):
        if not self.auto_manual_paste_var.get():
            return

        if self.clipboard_popup_open:
            self.schedule_clipboard_watch()
            return

        try:
            texto = self.root.clipboard_get()
        except Exception:
            self.schedule_clipboard_watch()
            return

        texto = str(texto or "").strip()

        if not texto:
            self.schedule_clipboard_watch()
            return

        if texto != self.last_clipboard_text:
            self.last_clipboard_text = texto
            if len(texto) > 3:
                self.open_manual_paste_selector(texto)

        self.schedule_clipboard_watch()

    def open_manual_paste_selector(self, texto: str):
        manual_keys = self.get_manual_keys()
        if not manual_keys:
            return

        self.clipboard_popup_open = True
        result = {"ok": False, "field": ""}

        win = tk.Toplevel(self.root)
        win.title("Colar em campo manual")
        win.geometry("620x340")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        selected_label = StringVar(value=get_field_label(manual_keys[0]))

        Label(
            win,
            text="Texto copiado detectado. Escolhe o campo manual:",
            font=("Arial", 11, "bold"),
        ).pack(padx=10, pady=(10, 6), anchor="w")

        preview = tk.Text(win, height=8, font=("Consolas", 10), wrap="word")
        preview.pack(fill="both", padx=10, pady=(0, 10))
        preview.insert("1.0", texto[:2000])
        preview.config(state="disabled")

        frame = tk.Frame(win)
        frame.pack(pady=(0, 10))

        labels = [get_field_label(k) for k in manual_keys]
        tk.OptionMenu(frame, selected_label, *labels).pack()

        tk.Checkbutton(
            win,
            text="Auto colar manual ativo",
            variable=self.auto_manual_paste_var,
            command=self.toggle_auto_manual_paste,
        ).pack(anchor="w", padx=10)

        def confirmar():
            label = selected_label.get().strip()
            for k in manual_keys:
                if get_field_label(k) == label:
                    result["field"] = k
                    result["ok"] = True
                    break
            win.destroy()

        def cancelar():
            win.destroy()

        btns = tk.Frame(win)
        btns.pack(pady=10)
        Button(btns, text="Cancelar", command=cancelar, width=12).pack(side="left", padx=6)
        Button(btns, text="Colar", command=confirmar, width=12).pack(side="left", padx=6)

        win.protocol("WM_DELETE_WINDOW", cancelar)
        self.root.wait_window(win)

        self.clipboard_popup_open = False

        if result["ok"] and result["field"]:
            self.apply_manual_clipboard_text(result["field"], texto)

    def apply_manual_clipboard_text(self, field: str, texto: str):
        self.data[field] = texto
        self.select_field_by_key(field)
        self.text_value.delete("1.0", tk.END)
        self.text_value.insert("1.0", texto)
        self.refresh_all_values()
        self.save_data()
        self.set_status(f"Colado em '{get_field_label(field)}'")

    def select_template(self):
        path = filedialog.askopenfilename(
            title="Selecionar modelo Word",
            filetypes=[("Arquivos Word", "*.docx")],
        )
        if not path:
            return

        try:
            self.apply_template_path(path, save_config=True)
            self.set_status("Modelo selecionado e salvo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler modelo Word:\n{e}")

    def ask_process_number_dialog(self) -> str:
        result = {"process": None}

        dialog = tk.Toplevel(self.root)
        dialog.title("Novo processo")
        dialog.attributes("-topmost", True)
        dialog.geometry("430x170")
        dialog.resizable(False, False)
        dialog.grab_set()

        Label(dialog, text="Número do processo", font=("Arial", 14, "bold")).pack(pady=(18, 8))

        entry_var = StringVar()
        entry = Entry(dialog, textvariable=entry_var, font=("Arial", 14), justify="center", width=30)
        entry.pack(pady=(0, 14))
        entry.focus_set()

        info_var = StringVar(value="")

        def confirm(event=None):
            value = entry_var.get().strip()
            if not value:
                info_var.set("Digita um número de processo válido.")
                return
            result["process"] = value
            dialog.destroy()

        Label(dialog, textvariable=info_var, fg="red").pack()
        Button(dialog, text="Confirmar", command=confirm, width=18).pack(pady=8)
        dialog.bind("<Return>", confirm)

        self.root.wait_window(dialog)
        return result["process"] or ""

    def open_new_process_flow(self):
        process_number = self.ask_process_number_dialog()
        if not process_number:
            if not self.process_number:
                self.root.destroy()
            return

        existing = load_process_data(process_number)
        if existing:
            self.load_process_into_ui(process_number, existing)
            self.set_status("Processo existente carregado.")
        else:
            data = create_default_process_data(process_number)
            if self.fields:
                for key in self.fields:
                    data.setdefault(key, "")
            save_process_data(process_number, data)
            self.load_process_into_ui(process_number, data)
            self.set_status("Novo processo criado.")

    def load_process_into_ui(self, process_number: str, data: dict):
        self.process_number = process_number
        self.data = ensure_all_default_keys(
            data if isinstance(data, dict) else {},
            process_number,
        )

        if self.fields:
            for key in self.fields:
                self.data.setdefault(key, "")

        self.reload_field_list()
        self.lbl_process.config(text=f"Processo atual: {self.process_number}")
        self.refresh_all_values()
        self.select_field_by_key("observacao")

        self.config["ultimo_processo"] = self.process_number
        save_app_config(self.config)



    def open_history_window(self):
        self.save_data()
        processes = list_saved_processes()

        win = tk.Toplevel(self.root)
        win.title("Histórico de processos")
        win.geometry("760x500")
        win.grab_set()

        Label(win, text="Processos salvos", font=("Arial", 12, "bold")).pack(pady=(10, 6))

        tree = ttk.Treeview(
            win,
            columns=("processo", "titular", "observacao"),
            show="headings",
            height=16,
            selectmode="extended",
        )
        tree.heading("processo", text="Processo")
        tree.heading("titular", text="Titular")
        tree.heading("observacao", text="Observação")
        tree.column("processo", width=180, anchor="w")
        tree.column("titular", width=220, anchor="w")
        tree.column("observacao", width=320, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=6)

        process_lookup = {}
        for item in processes:
            data = load_process_data(item) or {}
            processo = str(data.get("numero_processo", item) or item)
            titular = str(data.get("titular", "") or "")
            observacao = str(data.get("observacao", "") or "")
            iid = tree.insert("", tk.END, values=(processo, titular, observacao))
            process_lookup[iid] = processo

        if not processes:
            tree.insert("", tk.END, values=("(nenhum processo salvo)", "", ""))

        def open_selected(event=None):
            sel = tree.selection()
            if not sel:
                return

            iid = sel[0]
            value = process_lookup.get(iid, "")
            if not value:
                return

            data = load_process_data(value)
            if not data:
                messagebox.showerror("Erro", "Não foi possível carregar esse processo.")
                return

            self.load_process_into_ui(value, data)
            self.select_field_by_key("observacao")
            self.set_status("Processo carregado pelo histórico.")
            win.destroy()

        def delete_selected_history():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleciona pelo menos um processo.")
                return

            processos_sel = [process_lookup.get(iid, "") for iid in sel if process_lookup.get(iid, "")]
            if not processos_sel:
                return

            if not messagebox.askyesno(
                "Confirmar exclusão",
                "Apagar os históricos selecionados e os dados desses processos?"
            ):
                return

            removidos = 0
            for processo in processos_sel:
                if delete_process_data(processo):
                    removidos += 1

            for iid in sel:
                if tree.exists(iid):
                    tree.delete(iid)
                process_lookup.pop(iid, None)

            if self.process_number in processos_sel:
                self.process_number = ""
                self.data = ensure_all_default_keys({}, "")
                self.current_selected_key = ""
                self.current_selected_field.set("")
                self.lbl_process.config(text="Processo atual: -")
                self.text_value.delete("1.0", tk.END)
                self.reload_field_list()
                self.refresh_all_values()

            self.set_status(f"{removidos} processo(s) apagado(s).")
            messagebox.showinfo("Sucesso", f"{removidos} processo(s) apagado(s).")

        btns = tk.Frame(win)
        btns.pack(pady=(0, 10))
        Button(btns, text="Abrir processo", command=open_selected, width=18).pack(side="left", padx=6)
        Button(btns, text="Apagar selecionados", command=delete_selected_history, width=18).pack(side="left", padx=6)

        tree.bind("<Double-Button-1>", open_selected)

    def reload_field_list(self):
        self.capture_listbox.delete(0, tk.END)
        self.manual_listbox.delete(0, tk.END)

        for key in self.get_capture_keys():
            self.capture_listbox.insert(tk.END, get_field_label(key))

        for key in self.get_manual_keys():
            self.manual_listbox.insert(tk.END, get_field_label(key))

    def on_select_field(self, source=None, event=None):
        selected = self.get_selected_field(source=source)
        if not selected:
            return
        self.current_selected_key = selected
        self.current_selected_field.set(get_field_label(selected))
        self.text_value.delete("1.0", tk.END)
        self.text_value.insert("1.0", self.data.get(selected, ""))

    def get_selected_field(self, source=None):
        source = source or self.get_selected_list_name()

        if source == "capture":
            sel = self.capture_listbox.curselection()
            if not sel:
                return ""
            keys = self.get_capture_keys()
            idx = sel[0]
            if idx < 0 or idx >= len(keys):
                return ""
            return keys[idx]

        if source == "manual":
            sel = self.manual_listbox.curselection()
            if not sel:
                return ""
            keys = self.get_manual_keys()
            idx = sel[0]
            if idx < 0 or idx >= len(keys):
                return ""
            return keys[idx]

        return ""

    def set_field_value_safe(self, key: str, value: str):
        key = str(key or "").strip()
        if not key:
            return False

        valid_keys = set(self.get_ordered_keys()) | {"numero_processo", "data_atual"}
        if key not in valid_keys:
            return False

        self.data[key] = "" if value is None else str(value)
        return True

    def update_current_value(self):
        field = str(getattr(self, "current_selected_key", "") or "").strip()
        if not field:
            messagebox.showwarning("Aviso", "Seleciona uma chave primeiro.")
            return

        value = self.text_value.get("1.0", tk.END).strip()
        self.data[field] = value
        self.refresh_all_values()
        self.save_data()
        self.set_status(f"Campo '{get_field_label(field)}' atualizado manualmente.")

    def clear_current_value(self):
        field = str(getattr(self, "current_selected_key", "") or "").strip()
        if not field:
            return

        self.text_value.delete("1.0", tk.END)
        self.data[field] = ""
        self.refresh_all_values()
        self.save_data()
        self.set_status(f"Campo '{get_field_label(field)}' limpo.")


    def sync_current_editor_to_data(self):
        field = str(getattr(self, "current_selected_key", "") or "").strip()
        if not field:
            return

        try:
            value = self.text_value.get("1.0", tk.END).strip()
        except Exception:
            return

        self.data[field] = value

    def refresh_all_values(self):
        self.text_all.delete("1.0", tk.END)

        if not isinstance(self.data, dict):
            self.data = {}

        for k in self.get_ordered_keys():
            self.text_all.insert(tk.END, f"{get_field_label(k)}: {self.data.get(k, '')}\n")

    def save_data(self):
        self.sync_current_editor_to_data()

        if not isinstance(self.data, dict):
            self.data = {}

        if self.process_number:
            self.data["numero_processo"] = self.process_number

        save_process_data(self.process_number, self.data)

        self.config["ultimo_processo"] = self.process_number
        self.config["nome_usuario_salvar"] = self.nome_usuario_salvar
        if self.template_path:
            self.config["modelo_word_path"] = self.template_path
        save_app_config(self.config)

        self.set_status("Dados salvos.")

    def confirm_capture_with_key(self, cropped_img: Image.Image):
        result = {"approved": False, "selected_key": ""}

        win = tk.Toplevel(self.root)
        win.title("Confirmar captura")
        win.attributes("-topmost", True)
        win.grab_set()

        preview_img = cropped_img.copy()
        preview_img.thumbnail((700, 420))
        tk_img = ImageTk.PhotoImage(preview_img)

        Label(
            win,
            text="Confirma a captura e escolhe a chave",
            font=("Arial", 11, "bold"),
        ).pack(padx=10, pady=(10, 6))

        lbl_img = Label(win, image=tk_img)
        lbl_img.image = tk_img
        lbl_img.pack(padx=10, pady=(0, 10))

        available_keys = [key for key in self.get_capture_keys() if key not in MANUAL_ONLY_KEYS]
        if not available_keys:
            available_keys = [key for key in self.get_ordered_keys() if key not in MANUAL_ONLY_KEYS]
        if not available_keys:
            available_keys = [""]

        display_to_key = {get_field_label(key): key for key in available_keys if key}
        menu_labels = list(display_to_key.keys()) or [""]
        current_key = str(getattr(self, "current_selected_key", "") or "").strip()
        current_label = get_field_label(current_key) if current_key in display_to_key.values() else menu_labels[0]
        selected_key_var = StringVar(value=current_label)

        frame_keys = tk.Frame(win)
        frame_keys.pack(padx=10, pady=(0, 10), fill="x")

        Label(frame_keys, text="Chave:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8))

        key_menu = tk.OptionMenu(frame_keys, selected_key_var, *menu_labels)
        key_menu.config(width=24)
        key_menu.grid(row=0, column=1, sticky="w")

        def approve(event=None):
            result["approved"] = True
            result["selected_key"] = display_to_key.get(selected_key_var.get().strip(), "")
            win.destroy()

        def cancel(event=None):
            result["approved"] = False
            win.destroy()

        btns = tk.Frame(win)
        btns.pack(pady=(0, 12))
        Button(btns, text="Confirmar", command=approve, width=14).pack(side="left", padx=6)
        Button(btns, text="Cancelar", command=cancel, width=14).pack(side="left", padx=6)

        win.bind("<Return>", approve)
        win.bind("<Escape>", cancel)

        self.root.wait_window(win)
        return result["approved"], result["selected_key"]

    def capture_and_fill(self):
        if self.ocr_busy:
            self.root.after(0, lambda: self.set_status("OCR ainda está rodando. Espera terminar pra capturar de novo."))
            return

        if not self.template_path:
            self.root.after(0, lambda: messagebox.showwarning("Aviso", "Seleciona um modelo Word primeiro."))
            return

        if not capture_lock.acquire(blocking=False):
            self.root.after(0, lambda: self.set_status("Já existe uma captura em andamento."))
            return

        try:
            time.sleep(0.25)

            selector = ScreenSelector(self.root)
            bbox = selector.get_bbox()

            if not bbox:
                capture_lock.release()
                self.root.after(0, lambda: self.set_status("Captura cancelada."))
                return

            cropped = ImageGrab.grab(bbox=bbox)

            approved, selected_key = self.confirm_capture_with_key(cropped)
            if not approved or not selected_key:
                capture_lock.release()
                self.root.after(0, lambda: self.set_status("Captura cancelada."))
                return

            self.root.after(0, lambda: self.start_busy(f"Rodando OCR para '{selected_key}'..."))

            def worker():
                try:
                    text, conf = do_ocr_from_pil(cropped)
                    value = merge_broken_single_lines(text)
                    def apply_result():
                        ok = self.set_field_value_safe(selected_key, value)
                        if not ok:
                            self.stop_busy("Erro: campo inválido para OCR.")
                            messagebox.showerror("Erro", f"Campo inválido: {selected_key}")
                            return

                        self.current_selected_key = selected_key
                        self.current_selected_field.set(get_field_label(selected_key))
                        self.select_field_by_key(selected_key)
                        self.text_value.delete("1.0", tk.END)
                        self.text_value.insert("1.0", value)
                        self.refresh_all_values()
                        self.save_data()
                        self.stop_busy(
                            f"OCR concluído em '{get_field_label(selected_key)}' | conf={conf:.1f} | pode capturar de novo."
                        )
                    self.root.after(0, apply_result)


                except Exception as e:
                    self.root.after(0, lambda: self.stop_busy(f"Erro no OCR: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("Erro OCR", str(e)))
                finally:
                    capture_lock.release()

            threading.Thread(target=worker, daemon=True).start()

        except Exception as e:
            if capture_lock.locked():
                capture_lock.release()
            self.root.after(0, lambda: self.stop_busy(f"Erro ao iniciar captura: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))

    def generate_word(self):
        if not self.template_path:
            messagebox.showwarning("Aviso", "Seleciona um modelo Word primeiro.")
            return

        if not self.ensure_save_name():
            return

        try:
            self.data["numero_processo"] = self.process_number

            if not self.data.get("data_atual"):
                from datetime import datetime
                self.data["data_atual"] = datetime.now().strftime("%d/%m/%Y")

            pasta_base = os.path.dirname(os.path.abspath(__file__))
            pasta_destino = os.path.join(pasta_base, "saida_word")
            os.makedirs(pasta_destino, exist_ok=True)

            nome_base = sanitize_text_for_path(self.nome_usuario_salvar)
            numero_proc = preserve_process_format_for_filename(
                str(self.data.get("numero_processo", self.process_number))
            )
            nome_arquivo = f"{nome_base}-{numero_proc}.docx"

            output_path = os.path.join(pasta_destino, nome_arquivo)

            render_template_to_docx(self.template_path, output_path, self.data)

            self.save_data()

            try:
                os.startfile(output_path)
            except Exception:
                pass

            messagebox.showinfo("Sucesso", f"Word gerado com sucesso:\n{output_path}")
            self.set_status(f"Word gerado em: {output_path}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar Word:\n{e}")
            self.set_status(f"Falha ao gerar Word: {e}")
    def generate_excel(self):
        if not self.process_number:
            messagebox.showwarning("Aviso", "Nenhum processo selecionado.")
            return

        try:
            self.data["numero_processo"] = self.process_number

            pasta_base = os.path.dirname(os.path.abspath(__file__))
            pasta_destino = os.path.join(pasta_base, "saida_excel")
            os.makedirs(pasta_destino, exist_ok=True)

            output_path = os.path.join(pasta_destino, "relatoria.xlsx")

            export_process_to_excel(output_path, self.data)

            self.save_data()
            messagebox.showinfo("Sucesso", f"Relatoria atualizada com sucesso:\n{output_path}")
            self.set_status(f"Relatoria atualizada em: {output_path}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar Excel:\n{e}")
            self.set_status(f"Falha ao gerar Excel: {e}")
    def copy_numero_titulo(self):
        self.sync_current_editor_to_data()
        valor = str(self.data.get("numero_titulo", "") or "").strip()
        if not valor:
            messagebox.showwarning("Aviso", "Número de título vazio.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(valor)
            self.root.update()
            self.set_status("Número de título copiado.")
            messagebox.showinfo("Sucesso", "Número de título copiado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao copiar número de título:\n{e}")

    def copy_excel_text(self):
        self.sync_current_editor_to_data()
        if not self.process_number:
            messagebox.showwarning("Aviso", "Nenhum processo selecionado.")
            return

        try:
            self.sync_current_editor_to_data()
            self.data["numero_processo"] = self.process_number
            texto = build_excel_row_text(self.data)
            self.root.clipboard_clear()
            self.root.clipboard_append(texto)
            self.root.update()
            self.save_data()
            self.set_status("Linha copiada para colar no Excel ou Google Sheets.")
            messagebox.showinfo("Sucesso", "Texto copiado. Agora é só colar no Excel ou Google Sheets.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao copiar texto para Excel:\n{e}")

    def open_boot_window(self):
        result = {"action": "cancel"}

        win = tk.Toplevel(self.root)
        win.title("Configuração de boot")
        win.geometry("640x220")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        script_var = StringVar(value=str(self.config.get("boot_script_path", "") or ""))
        macro_var = StringVar(value=str(self.config.get("boot_macro", "") or ""))

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        Label(frame, text="Script .py do boot", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        Entry(frame, textvariable=script_var, width=56).grid(row=1, column=0, sticky="we", padx=(0, 8), pady=(4, 10))

        def browse_script():
            path = filedialog.askopenfilename(
                title="Selecionar script de boot",
                filetypes=[("Arquivos Python", "*.py")],
            )
            if path:
                script_var.set(path)

        Button(frame, text="Selecionar .py", command=browse_script, width=16).grid(row=1, column=1, sticky="e")

        Label(frame, text="Macro / argumento (opcional)", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w")
        Entry(frame, textvariable=macro_var, width=56).grid(row=3, column=0, columnspan=2, sticky="we", pady=(4, 10))

        status_var = StringVar(value="Escolhe o script e clica em Rodar.")
        Label(frame, textvariable=status_var, anchor="w").grid(row=4, column=0, columnspan=2, sticky="we", pady=(0, 10))

        frame.columnconfigure(0, weight=1)

        def close_cancel():
            result["action"] = "cancel"
            win.destroy()

        def run_boot():
            script_path = str(script_var.get() or "").strip()
            macro = str(macro_var.get() or "").strip()

            if not script_path:
                messagebox.showwarning("Aviso", "Seleciona um script .py.")
                return

            if not os.path.exists(script_path):
                messagebox.showerror("Erro", f"Script não encontrado:\n{script_path}")
                return

            self.config["boot_script_path"] = script_path
            self.config["boot_macro"] = macro
            self.config["boot_config"] = {"script_path": script_path, "macro": macro}
            save_app_config(self.config)

            result["action"] = "run"
            result["script_path"] = script_path
            result["macro"] = macro
            win.destroy()

        btns = tk.Frame(frame)
        btns.grid(row=5, column=0, columnspan=2, pady=(4, 0))
        Button(btns, text="Cancelar", command=close_cancel, width=16).pack(side="left", padx=6)
        Button(btns, text="Rodar", command=run_boot, width=16).pack(side="left", padx=6)

        self.root.wait_window(win)

        if result.get("action") != "run":
            return

        script_path = result["script_path"]
        macro = result["macro"]

        cmd = [sys.executable, script_path]
        if macro:
            cmd.append(macro)

        try:
            self.start_busy("Executando boot...")
            self.root.update_idletasks()
            completed = subprocess.run(cmd, cwd=os.path.dirname(script_path) or None, capture_output=True, text=True)
            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()

            if completed.returncode == 0:
                msg = "Boot finalizado com sucesso."
                if stdout:
                    msg += f"\n\nSaída:\n{stdout[:2000]}"
                messagebox.showinfo("Boot", msg)
                self.set_status("Boot finalizado com sucesso.")
            else:
                msg = f"Boot finalizou com erro (código {completed.returncode})."
                if stderr:
                    msg += f"\n\nErro:\n{stderr[:2000]}"
                elif stdout:
                    msg += f"\n\nSaída:\n{stdout[:2000]}"
                messagebox.showerror("Boot", msg)
                self.set_status("Boot finalizou com erro.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao executar boot:\n{e}")
            self.set_status(f"Falha ao executar boot: {e}")
        finally:
            self.stop_busy("Pronto.")

    def run_rename_app(self):
        try:
            pasta_base = os.path.dirname(os.path.abspath(__file__))
            arquivo_renomeador = os.path.join(pasta_base, "renomear_arquivos.py")

            if not os.path.exists(arquivo_renomeador):
                messagebox.showerror("Erro", f"Arquivo não encontrado:\n{arquivo_renomeador}")
                return

            subprocess.Popen([sys.executable, arquivo_renomeador], cwd=pasta_base)
            self.set_status("Renomeador aberto.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir renomeador:\n{e}")

    def quit_program(self):
        try:
            if self.hotkeys:
                self.hotkeys.stop()
        except Exception:
            pass
        self.root.destroy()

    def on_close(self):
        self.save_data()
        self.quit_program()


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
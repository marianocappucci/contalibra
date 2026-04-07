import os
from fpdf import FPDF

PDF_DIR = os.path.join(os.path.dirname(__file__), "remitos_pdf")
PRESUPUESTOS_PDF_DIR = os.path.join(os.path.dirname(__file__), "presupuestos_pdf")

# Configuración de empresa — editar a gusto
EMPRESA_NOMBRE = "compulibra - soluciones informáticas"
EMPRESA_DIRECCION = "Malvinas 214, Suipacha, Buenos Aires"
EMPRESA_CUIT = "CUIT: 20-28993360-4"
EMPRESA_TELEFONO = "Tel: (2324) 500263"
EMPRESA_EMAIL = "marianocappucci@gmail.com"


class RemitoPDF(FPDF):
    def __init__(self, remito):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.remito = remito
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        remito = self.remito
        # Empresa (izquierda)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, EMPRESA_NOMBRE, ln=True)
        self.set_font("Helvetica", "", 9)
        for line in [EMPRESA_DIRECCION, EMPRESA_CUIT, EMPRESA_TELEFONO, EMPRESA_EMAIL]:
            self.cell(0, 5, line, ln=True)

        # Caja REMITO (derecha) — reposicionamos
        self.set_xy(130, 15)
        self.set_font("Helvetica", "B", 18)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.cell(65, 12, "REMITO", border=1, align="C", fill=True, ln=True)
        self.set_text_color(0, 0, 0)

        self.set_xy(130, 27)
        self.set_font("Helvetica", "", 10)
        self.cell(65, 7, f"N\u00b0 {remito['number']}", border=1, align="C", ln=True)
        self.set_xy(130, 34)
        self.cell(65, 7, f"Fecha: {remito['date']}", border=1, align="C", ln=True)

        self.ln(8)
        self.set_line_width(0.5)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Documento no válido como factura", align="L")
        self.set_text_color(0, 0, 0)


class PresupuestoPDF(FPDF):
    def __init__(self, presupuesto):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.presupuesto = presupuesto
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        presupuesto = self.presupuesto
        # Empresa (izquierda)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, EMPRESA_NOMBRE, ln=True)
        self.set_font("Helvetica", "", 9)
        for line in [EMPRESA_DIRECCION, EMPRESA_CUIT, EMPRESA_TELEFONO, EMPRESA_EMAIL]:
            self.cell(0, 5, line, ln=True)

        # Caja PRESUPUESTO (derecha)
        self.set_xy(130, 15)
        self.set_font("Helvetica", "B", 18)
        self.set_fill_color(25, 60, 100)
        self.set_text_color(255, 255, 255)
        self.cell(65, 12, "PRESUPUESTO", border=1, align="C", fill=True, ln=True)
        self.set_text_color(0, 0, 0)

        self.set_xy(130, 27)
        self.set_font("Helvetica", "", 10)
        self.cell(65, 7, f"N\u00b0 {presupuesto['number']}", border=1, align="C", ln=True)
        self.set_xy(130, 34)
        self.cell(65, 7, f"Fecha: {presupuesto['date']}", border=1, align="C", ln=True)
        self.set_xy(130, 41)
        self.cell(65, 7, f"Válido: {presupuesto['valid_until']}", border=1, align="C", ln=True)

        self.ln(5)
        self.set_line_width(0.5)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Presupuesto válido hasta: {self.presupuesto['valid_until']}", align="L")
        self.set_text_color(0, 0, 0)


def _section_title(pdf, text):
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 6, f"  {text}", border=0, ln=True, fill=True)
    pdf.ln(1)


def _client_block(pdf, remito):
    _section_title(pdf, "DATOS DEL CLIENTE")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_draw_color(180, 180, 180)
    start_y = pdf.get_y()
    pdf.rect(15, start_y, 180, 28)

    fields = [
        ("Cliente", remito["client_name"]),
        ("Domicilio", remito.get("client_address") or "-"),
        ("CUIT / DNI", remito.get("client_cuit") or "-"),
        ("Email", remito.get("client_email") or "-"),
        ("Teléfono", remito.get("client_phone") or "-"),
    ]
    col_w = 90
    x_left = 18
    y = start_y + 3
    for i, (label, value) in enumerate(fields):
        col = i % 2
        row = i // 2
        x = x_left + col * col_w
        yl = start_y + 3 + row * 7
        pdf.set_xy(x, yl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(28, 6, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w - 30, 6, str(value)[:40], ln=False)

    pdf.set_y(start_y + 30)
    pdf.ln(3)


def _items_table(pdf, items):
    _section_title(pdf, "DETALLE")

    headers = ["Descripción", "Cant.", "Precio Unit.", "Subtotal"]
    col_widths = [95, 20, 32, 33]

    # Encabezado tabla
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        align = "L" if h == "Descripción" else "R"
        pdf.cell(w, 7, f" {h}" if align == "L" else h, border=1, align=align, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Filas
    pdf.set_font("Helvetica", "", 9)
    for i, item in enumerate(items):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        desc = str(item["description"])[:55]
        qty = f"{item['qty']:g}"
        unit = f"$ {item['unit_price']:,.2f}"
        sub = f"$ {item['subtotal']:,.2f}"
        pdf.cell(col_widths[0], 6, f" {desc}", border="LRB", align="L", fill=fill)
        pdf.cell(col_widths[1], 6, qty, border="LRB", align="R", fill=fill)
        pdf.cell(col_widths[2], 6, unit, border="LRB", align="R", fill=fill)
        pdf.cell(col_widths[3], 6, sub, border="LRB", align="R", fill=fill)
        pdf.ln()

    pdf.ln(2)


def _totals_block(pdf, remito):
    col_value = 33  # igual que columna "Subtotal" de la tabla (x=162 a x=195)
    col_label = 180 - col_value
    x_start = 15

    def row(label, value, bold=False):
        pdf.set_xy(x_start, pdf.get_y())
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        pdf.cell(col_label, 7, label, align="R")
        pdf.cell(col_value, 7, value, border=1, align="R")
        pdf.ln()

    tax_pct = int(remito["tax_rate"] * 100)
    row("Subtotal:", f"$ {remito['subtotal']:,.2f}")
    row(f"IVA {tax_pct}%:", f"$ {remito['tax_amount']:,.2f}")
    pdf.set_font("Helvetica", "B", 11)
    row("TOTAL:", f"$ {remito['total']:,.2f}", bold=True)
    pdf.ln(3)


def _observations_block(pdf, observations):
    if not observations:
        return
    _section_title(pdf, "OBSERVACIONES")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, observations)
    pdf.ln(2)


def generate_pdf(remito, output_dir=None):
    os.makedirs(output_dir or PDF_DIR, exist_ok=True)
    safe_number = remito["number"].replace("/", "-")
    filename = f"remito_{safe_number}_{remito['date']}.pdf"
    filepath = os.path.join(output_dir or PDF_DIR, filename)

    pdf = RemitoPDF(remito)
    pdf.add_page()

    _client_block(pdf, remito)
    _items_table(pdf, remito["items"])
    _totals_block(pdf, remito)
    _observations_block(pdf, remito.get("observations", ""))

    pdf.output(filepath)
    return os.path.abspath(filepath)


def generate_pdf_presupuesto(presupuesto, output_dir=None):
    os.makedirs(output_dir or PRESUPUESTOS_PDF_DIR, exist_ok=True)
    safe_number = presupuesto["number"].replace("/", "-")
    filename = f"presupuesto_{safe_number}_{presupuesto['date']}.pdf"
    filepath = os.path.join(output_dir or PRESUPUESTOS_PDF_DIR, filename)

    pdf = PresupuestoPDF(presupuesto)
    pdf.add_page()

    _client_block(pdf, presupuesto)
    _items_table(pdf, presupuesto["items"])
    _totals_block(pdf, presupuesto)
    _observations_block(pdf, presupuesto.get("observations", ""))

    pdf.output(filepath)
    return os.path.abspath(filepath)

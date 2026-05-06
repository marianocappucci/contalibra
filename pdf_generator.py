import os
from fpdf import FPDF
import config_manager

PDF_DIR              = os.path.join(os.path.dirname(__file__), "remitos_pdf")
PRESUPUESTOS_PDF_DIR = os.path.join(os.path.dirname(__file__), "presupuestos_pdf")


def _empresa():
    cfg = config_manager.load()
    return {
        "nombre":    cfg.get("empresa_nombre",    ""),
        "direccion": cfg.get("empresa_direccion", ""),
        "cuit":      cfg.get("empresa_cuit",      ""),
        "telefono":  cfg.get("empresa_telefono",  ""),
        "email":     cfg.get("empresa_email",     ""),
        "logo_path": cfg.get("logo_path",         ""),
    }


def _draw_header_empresa(pdf, empresa, y_start=15, right_box_x=130):
    """Dibuja logo (o razón social si no hay logo) + datos de empresa."""
    logo_path = empresa.get("logo_path", "")
    y = y_start

    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=15, y=y, h=20)
        y += 22
    else:
        pdf.set_xy(15, y)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(right_box_x - 20, 7, empresa["nombre"], ln=True)
        y = pdf.get_y()

    pdf.set_xy(15, y)
    pdf.set_font("Helvetica", "", 9)
    for line in filter(None, [empresa["direccion"], empresa["cuit"],
                               empresa["telefono"],  empresa["email"]]):
        pdf.set_x(15)
        pdf.cell(right_box_x - 20, 5, line, ln=True)

    return pdf.get_y()


class RemitoPDF(FPDF):
    def __init__(self, remito):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.remito = remito
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        remito  = self.remito
        empresa = _empresa()

        # Caja REMITO — siempre en la esquina superior derecha
        self.set_xy(130, 15)
        self.set_font("Helvetica", "B", 18)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.cell(65, 12, "REMITO", border=1, align="C", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.set_xy(130, 27)
        self.set_font("Helvetica", "", 10)
        self.cell(65, 7, f"N° {remito['number']}", border=1, align="C", ln=True)
        self.set_xy(130, 34)
        self.cell(65, 7, f"Fecha: {remito['date']}", border=1, align="C", ln=True)

        # Columna izquierda: logo + empresa
        y_after = _draw_header_empresa(self, empresa)

        y_sep = max(y_after + 2, 44)
        self.set_line_width(0.5)
        self.line(15, y_sep, 195, y_sep)
        self.set_y(y_sep + 3)

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
        empresa     = _empresa()

        # Caja PRESUPUESTO — esquina superior derecha
        self.set_xy(130, 15)
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(25, 60, 100)
        self.set_text_color(255, 255, 255)
        self.cell(65, 12, "PRESUPUESTO", border=1, align="C", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.set_xy(130, 27)
        self.set_font("Helvetica", "", 10)
        self.cell(65, 7, f"N° {presupuesto['number']}", border=1, align="C", ln=True)
        self.set_xy(130, 34)
        self.cell(65, 7, f"Fecha: {presupuesto['date']}", border=1, align="C", ln=True)
        self.set_xy(130, 41)
        self.cell(65, 7, f"Válido: {presupuesto['valid_until']}", border=1, align="C", ln=True)

        # Columna izquierda: logo + empresa
        y_after = _draw_header_empresa(self, empresa)

        y_sep = max(y_after + 2, 50)
        self.set_line_width(0.5)
        self.line(15, y_sep, 195, y_sep)
        self.set_y(y_sep + 3)

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


def _client_block(pdf, doc):
    _section_title(pdf, "DATOS DEL CLIENTE")
    pdf.set_draw_color(180, 180, 180)
    start_y = pdf.get_y()

    # Columna izquierda: Cliente, Domicilio, CUIT/DNI
    left_fields = [
        ("Cliente",    doc["client_name"]),
        ("Domicilio",  doc.get("client_address") or "-"),
        ("CUIT / DNI", doc.get("client_cuit")    or "-"),
    ]
    # Columna derecha: Email, Teléfono
    right_fields = [
        ("Email",     doc.get("client_email") or "-"),
        ("Teléfono",  doc.get("client_phone") or "-"),
    ]

    field_h = 7
    box_h   = max(len(left_fields), len(right_fields)) * field_h
    mid_x   = 105  # punto medio: 15 + 90

    pdf.rect(15, start_y, 180, box_h)
    pdf.set_line_width(0.3)
    pdf.line(mid_x, start_y, mid_x, start_y + box_h)
    pdf.set_line_width(0.5)

    label_w = 28
    for i, (label, value) in enumerate(left_fields):
        y = start_y + 3 + i * field_h
        pdf.set_xy(18, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, 6, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(mid_x - 18 - label_w - 2, 6, str(value)[:38], ln=False)

    for i, (label, value) in enumerate(right_fields):
        y = start_y + 3 + i * field_h
        pdf.set_xy(mid_x + 3, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, 6, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(195 - mid_x - label_w - 6, 6, str(value)[:38], ln=False)

    pdf.set_y(start_y + box_h + 3)
    pdf.ln(3)


def _items_table(pdf, items):
    _section_title(pdf, "DETALLE")

    headers    = ["Descripción", "Cant.", "Precio Unit.", "Subtotal"]
    col_widths = [95, 20, 32, 33]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        align = "L" if h == "Descripción" else "R"
        pdf.cell(w, 7, f" {h}" if align == "L" else h, border=1, align=align, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "", 9)
    for i, item in enumerate(items):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_widths[0], 6, f" {str(item['description'])[:55]}", border="LRB", align="L", fill=fill)
        pdf.cell(col_widths[1], 6, f"{item['qty']:g}",                   border="LRB", align="R", fill=fill)
        pdf.cell(col_widths[2], 6, f"$ {item['unit_price']:,.2f}",        border="LRB", align="R", fill=fill)
        pdf.cell(col_widths[3], 6, f"$ {item['subtotal']:,.2f}",          border="LRB", align="R", fill=fill)
        pdf.ln()

    pdf.ln(2)


def _totals_block(pdf, doc):
    col_value = 33
    col_label = 180 - col_value

    def row(label, value, bold=False):
        pdf.set_xy(15, pdf.get_y())
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        pdf.cell(col_label, 7, label, align="R")
        pdf.cell(col_value, 7, value, border=1, align="R")
        pdf.ln()

    tax_pct = int(doc["tax_rate"] * 100)
    row("Subtotal:", f"$ {doc['subtotal']:,.2f}")
    row(f"IVA {tax_pct}%:", f"$ {doc['tax_amount']:,.2f}")
    pdf.set_font("Helvetica", "B", 11)
    row("TOTAL:", f"$ {doc['total']:,.2f}", bold=True)
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
    filepath = os.path.join(output_dir or PDF_DIR,
                            f"remito_{safe_number}_{remito['date']}.pdf")
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
    filepath = os.path.join(output_dir or PRESUPUESTOS_PDF_DIR,
                            f"presupuesto_{safe_number}_{presupuesto['date']}.pdf")
    pdf = PresupuestoPDF(presupuesto)
    pdf.add_page()
    _client_block(pdf, presupuesto)
    _items_table(pdf, presupuesto["items"])
    _totals_block(pdf, presupuesto)
    _observations_block(pdf, presupuesto.get("observations", ""))
    pdf.output(filepath)
    return os.path.abspath(filepath)

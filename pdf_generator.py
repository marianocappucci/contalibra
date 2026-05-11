import os
from fpdf import FPDF
import config_manager

PDF_DIR              = os.path.join(os.path.dirname(__file__), "remitos_pdf")
PRESUPUESTOS_PDF_DIR = os.path.join(os.path.dirname(__file__), "presupuestos_pdf")
FACTURAS_PDF_DIR     = os.path.join(os.path.dirname(__file__), "facturas_pdf")

_TIPO_LABELS    = {1: "FACTURA A",      6: "FACTURA B",      11: "FACTURA C",
                   3: "NOTA CREDITO A", 8: "NOTA CREDITO B", 13: "NOTA CREDITO C",
                   2: "NOTA DEBITO A",  7: "NOTA DEBITO B",  12: "NOTA DEBITO C"}
_CONCEPTO_LABELS = {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}
_IVA_LABELS     = {1: "Responsable Inscripto", 6: "Monotributista", 4: "IVA Exento",
                   5: "Consumidor Final", 3: "No Alcanzado"}


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

    left_fields = [
        ("Cliente",    doc["client_name"]),
        ("Domicilio",  doc.get("client_address") or "-"),
        ("CUIT / DNI", doc.get("client_cuit")    or "-"),
    ]
    right_fields = [
        ("Email",     doc.get("client_email") or "-"),
        ("Teléfono",  doc.get("client_phone") or "-"),
    ]

    PAD     = 3   # mm — igual arriba y abajo
    field_h = 7   # espacio entre filas
    cell_h  = 6   # alto del texto
    max_rows = max(len(left_fields), len(right_fields))
    # box_h: PAD arriba + filas + PAD abajo (cell_h < field_h, la diferencia es el gap entre filas)
    box_h = PAD + (max_rows - 1) * field_h + cell_h + PAD

    mid_x   = 105  # 15 + 90 — divide el área en dos mitades iguales
    label_w = 28   # ancho reservado para la etiqueta en negrita

    # Ancho exacto de valores: desde el fin del label hasta el borde interior de cada columna
    left_val_w  = mid_x - (15 + PAD + label_w) - PAD       # hasta mid_x con margen
    right_val_w = (195 - PAD) - (mid_x + PAD + label_w)    # hasta borde derecho con margen

    pdf.rect(15, start_y, 180, box_h)
    pdf.set_line_width(0.3)
    pdf.line(mid_x, start_y, mid_x, start_y + box_h)
    pdf.set_line_width(0.5)

    for i, (label, value) in enumerate(left_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(15 + PAD, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(left_val_w, cell_h, str(value), ln=False)

    for i, (label, value) in enumerate(right_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(mid_x + PAD, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(right_val_w, cell_h, str(value), ln=False)

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


class FacturaPDF(FPDF):
    def __init__(self, factura):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.factura = factura
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        factura = self.factura
        empresa = _empresa()
        tipo_label = _TIPO_LABELS.get(factura["tipo"], "DOCUMENTO")

        self.set_xy(130, 15)
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(25, 60, 100)
        self.set_text_color(255, 255, 255)
        self.cell(65, 12, tipo_label, border=1, align="C", fill=True, ln=True)
        self.set_text_color(0, 0, 0)

        pv  = str(factura["punto_venta"]).zfill(4)
        num = str(factura["numero"]).zfill(8)
        self.set_xy(130, 27)
        self.set_font("Helvetica", "", 10)
        self.cell(65, 7, f"N° {pv}-{num}", border=1, align="C", ln=True)
        self.set_xy(130, 34)
        self.cell(65, 7, f"Fecha: {factura.get('fecha', '')}", border=1, align="C", ln=True)
        self.set_xy(130, 41)
        self.cell(65, 7, _CONCEPTO_LABELS.get(factura.get("concepto", 1), "Productos"),
                  border=1, align="C", ln=True)

        y_after = _draw_header_empresa(self, empresa)

        y_sep = max(y_after + 2, 50)
        self.set_line_width(0.5)
        self.line(15, y_sep, 195, y_sep)
        self.set_y(y_sep + 3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Comprobante emitido por Contalibra - ARCA", align="L")
        self.set_text_color(0, 0, 0)


def _factura_client_block(pdf, factura):
    _section_title(pdf, "DATOS DEL RECEPTOR")
    pdf.set_draw_color(180, 180, 180)
    start_y = pdf.get_y()

    iva_text = _IVA_LABELS.get(factura.get("cliente_iva_cond") or 0, "")

    left_fields = [
        ("Razón social", factura.get("cliente_razon") or "-"),
        ("CUIT",         factura.get("cliente_cuit")   or "-"),
        ("Domicilio",    factura.get("cliente_domicilio") or "-"),
    ]
    right_fields = [
        ("Cond. IVA", iva_text or "-"),
    ]

    PAD     = 3
    field_h = 7
    cell_h  = 6
    max_rows = max(len(left_fields), len(right_fields))
    box_h   = PAD + (max_rows - 1) * field_h + cell_h + PAD
    mid_x   = 105
    label_w = 28
    left_val_w  = mid_x - (15 + PAD + label_w) - PAD
    right_val_w = (195 - PAD) - (mid_x + PAD + label_w)

    pdf.rect(15, start_y, 180, box_h)
    pdf.set_line_width(0.3)
    pdf.line(mid_x, start_y, mid_x, start_y + box_h)
    pdf.set_line_width(0.5)

    for i, (label, value) in enumerate(left_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(15 + PAD, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(left_val_w, cell_h, str(value)[:45], ln=False)

    for i, (label, value) in enumerate(right_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(mid_x + PAD, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(right_val_w, cell_h, str(value)[:30], ln=False)

    pdf.set_y(start_y + box_h + 3)
    pdf.ln(3)


def _factura_totals_block(pdf, factura):
    col_value = 33
    col_label = 180 - col_value

    def row(label, value, bold=False):
        pdf.set_xy(15, pdf.get_y())
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        pdf.cell(col_label, 7, label, align="R")
        pdf.cell(col_value, 7, value, border=1, align="R")
        pdf.ln()

    sub  = factura.get("subtotal", 0)
    iva  = factura.get("iva_amount", 0)
    tot  = factura.get("total", 0)
    tipo = factura.get("tipo", 0)
    if iva > 0 and tipo != 11:
        pct = round(iva / sub * 100) if sub > 0 else 21
        row("Subtotal:", f"$ {sub:,.2f}")
        row(f"IVA {pct:.0f}%:", f"$ {iva:,.2f}")
    pdf.set_font("Helvetica", "B", 11)
    row("TOTAL:", f"$ {tot:,.2f}", bold=True)
    pdf.ln(3)


def _cae_block(pdf, factura):
    _section_title(pdf, "COMPROBANTE ELECTRONICO - ARCA")
    cae     = factura.get("cae")  or ""
    cae_vto = factura.get("cae_vto") or ""
    if cae_vto and len(cae_vto) == 8:
        cae_vto = f"{cae_vto[6:8]}/{cae_vto[4:6]}/{cae_vto[0:4]}"

    pdf.set_font("Helvetica", "", 9)
    if cae:
        pdf.set_x(15)
        pdf.cell(35, 6, "CAE N°:", ln=False)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, cae, ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(15)
        pdf.cell(35, 6, "Venc. CAE:", ln=False)
        pdf.cell(0, 6, cae_vto, ln=True)
    else:
        pdf.set_text_color(180, 0, 0)
        pdf.set_x(15)
        pdf.cell(0, 6, "Pendiente de autorización ARCA", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def generate_pdf_factura(factura, output_dir=None):
    os.makedirs(output_dir or FACTURAS_PDF_DIR, exist_ok=True)
    pv  = str(factura["punto_venta"]).zfill(4)
    num = str(factura["numero"]).zfill(8)
    filepath = os.path.join(output_dir or FACTURAS_PDF_DIR, f"factura_{pv}_{num}.pdf")
    pdf = FacturaPDF(factura)
    pdf.add_page()
    _factura_client_block(pdf, factura)
    _items_table(pdf, factura["items"])
    _factura_totals_block(pdf, factura)
    _cae_block(pdf, factura)
    _observations_block(pdf, factura.get("observaciones", ""))
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

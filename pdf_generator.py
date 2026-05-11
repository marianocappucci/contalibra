import os
import json
import base64
from fpdf import FPDF
import config_manager

PDF_DIR              = os.path.join(os.path.dirname(__file__), "remitos_pdf")
PRESUPUESTOS_PDF_DIR = os.path.join(os.path.dirname(__file__), "presupuestos_pdf")
FACTURAS_PDF_DIR     = os.path.join(os.path.dirname(__file__), "facturas_pdf")

_TIPO_LABELS    = {1: "FACTURA A",      6: "FACTURA B",      11: "FACTURA C",
                   3: "NOTA CREDITO A", 8: "NOTA CREDITO B", 13: "NOTA CREDITO C",
                   2: "NOTA DEBITO A",  7: "NOTA DEBITO B",  12: "NOTA DEBITO C"}
_CONCEPTO_LABELS = {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}
_IVA_LABELS      = {1: "Responsable Inscripto", 6: "Monotributista", 4: "IVA Exento",
                    5: "Consumidor Final", 3: "No Alcanzado"}

# ── QR support (optional) ─────────────────────────────────────────────────────
try:
    import qrcode as _qrlib
    _HAS_QR = True
except ImportError:
    _HAS_QR = False

# ── PIL support for RGBA → RGB logo flattening ────────────────────────────────
try:
    from PIL import Image as _PILImage
    import io as _io
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _prepare_logo(path: str):
    """
    Flatten RGBA PNG to RGB for embedding in PDF.
    If the logo is white-on-transparent (designed for dark backgrounds),
    invert it to dark-on-white so it's visible on the white page.
    """
    if not _HAS_PIL:
        return path
    try:
        img = _PILImage.open(path)
        if img.mode != "RGBA":
            return path
        _, _, _, alpha = img.split()
        # Sample opaque pixels to decide if the logo is white-on-transparent
        opaque = [(img.getpixel((x, y))[:3])
                  for x in range(0, img.size[0], 15)
                  for y in range(0, img.size[1], 15)
                  if img.getpixel((x, y))[3] > 128]
        is_white_logo = bool(opaque) and (
            sum(r + g + b for r, g, b in opaque) / (len(opaque) * 3) > 240
        )
        bg = _PILImage.new("RGB", img.size, (255, 255, 255))
        if is_white_logo:
            # Paste dark content (near-black) where the logo is visible
            dark = _PILImage.new("RGB", img.size, (30, 30, 30))
            bg.paste(dark, mask=alpha)
        else:
            bg.paste(img, mask=alpha)
        buf = _io.BytesIO()
        bg.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception:
        return path

# ── ARCA invoice constants ────────────────────────────────────────────────────
_TIPO_LETRA = {1:"A", 6:"B", 11:"C", 3:"A", 8:"B", 13:"C", 2:"A", 7:"B", 12:"C"}
_TIPO_COD   = {1:"001", 6:"006", 11:"011", 3:"003", 8:"008", 13:"013",
               2:"002", 7:"007", 12:"012"}
_TIPO_NOMBRE_DOC = {
    1:"FACTURA", 6:"FACTURA", 11:"FACTURA",
    3:"NOTA DE CREDITO", 8:"NOTA DE CREDITO", 13:"NOTA DE CREDITO",
    2:"NOTA DE DEBITO",  7:"NOTA DE DEBITO",  12:"NOTA DE DEBITO",
}
_IVA_EMISOR_LABEL = {
    "Monotributista":        "Responsable Monotributo",
    "Responsable Inscripto": "IVA Responsable Inscripto",
    "IVA Exento":            "IVA Exento",
}
_TIPOS_C = {11, 12, 13}


def _empresa():
    cfg = config_manager.load()
    return {
        "nombre":             cfg.get("empresa_nombre",            ""),
        "direccion":          cfg.get("empresa_direccion",         ""),
        "cuit":               cfg.get("empresa_cuit",              ""),
        "telefono":           cfg.get("empresa_telefono",          ""),
        "email":              cfg.get("empresa_email",             ""),
        "logo_path":          cfg.get("logo_path",                 ""),
        "iibb":               cfg.get("empresa_iibb",              ""),
        "iva_condition":      cfg.get("empresa_iva_condition",     "Monotributista"),
        "inicio_actividades": cfg.get("empresa_inicio_actividades",""),
    }


def _fmt_fecha(s: str) -> str:
    """YYYY-MM-DD → DD/MM/YYYY"""
    if not s or len(s) < 10:
        return s or ""
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"


def _afip_qr_url(factura: dict, empresa_cuit: str) -> str:
    cuit_rec = (factura.get("cliente_cuit") or "").replace("-", "").strip()
    tipo_doc = 80 if (len(cuit_rec) == 11 and cuit_rec.isdigit()) else 99
    nro_doc  = int(cuit_rec) if tipo_doc == 80 else 0
    cae_s    = (factura.get("cae") or "").strip()
    cae_int  = int(cae_s) if cae_s.isdigit() else 0
    cuit_e   = empresa_cuit.replace("-", "").strip()
    d = {
        "ver": 1,
        "fecha": factura.get("fecha", ""),
        "cuit": int(cuit_e) if cuit_e.isdigit() else 0,
        "ptoVta": int(factura.get("punto_venta", 1)),
        "tipoCmp": int(factura.get("tipo", 11)),
        "nroCmp": int(factura.get("numero", 1)),
        "importe": round(float(factura.get("total", 0)), 2),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": tipo_doc,
        "nroDocRec": nro_doc,
        "tipoCodAut": "E",
        "codAut": cae_int,
    }
    enc = base64.b64encode(json.dumps(d, separators=(",", ":")).encode()).decode()
    return f"https://www.afip.gob.ar/fe/qr/?p={enc}"


def _draw_qr(pdf, url: str, x: float, y: float, size: float):
    if not _HAS_QR:
        return
    try:
        qr = _qrlib.QRCode(version=None,
                            error_correction=_qrlib.constants.ERROR_CORRECT_M,
                            box_size=1, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        n    = len(matrix)
        cell = size / n
        pdf.set_fill_color(0, 0, 0)
        for ri, row in enumerate(matrix):
            for ci, dark in enumerate(row):
                if dark:
                    pdf.rect(x + ci * cell, y + ri * cell, cell, cell, style="F")
        pdf.set_fill_color(255, 255, 255)
    except Exception:
        pass


# ── Remito PDF ────────────────────────────────────────────────────────────────

def _draw_header_empresa(pdf, empresa, y_start=15, right_box_x=130):
    logo_path = empresa.get("logo_path", "")
    y = y_start
    if logo_path and os.path.exists(logo_path):
        pdf.image(_prepare_logo(logo_path), x=15, y=y, h=20)
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
        y_after = _draw_header_empresa(self, empresa)
        y_sep = max(y_after + 2, 44)
        self.set_line_width(0.5)
        self.line(15, y_sep, 195, y_sep)
        self.set_y(y_sep + 3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Documento no valido como factura", align="L")
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
        self.cell(65, 7, f"Valido: {presupuesto['valid_until']}", border=1, align="C", ln=True)
        y_after = _draw_header_empresa(self, empresa)
        y_sep = max(y_after + 2, 50)
        self.set_line_width(0.5)
        self.line(15, y_sep, 195, y_sep)
        self.set_y(y_sep + 3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Presupuesto valido hasta: {self.presupuesto['valid_until']}", align="L")
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
    left_fields  = [("Cliente",    doc["client_name"]),
                    ("Domicilio",  doc.get("client_address") or "-"),
                    ("CUIT / DNI", doc.get("client_cuit")    or "-")]
    right_fields = [("Email",    doc.get("client_email") or "-"),
                    ("Telefono", doc.get("client_phone") or "-")]
    PAD = 3; field_h = 7; cell_h = 6
    max_rows = max(len(left_fields), len(right_fields))
    box_h  = PAD + (max_rows - 1) * field_h + cell_h + PAD
    mid_x  = 105; label_w = 28
    left_val_w  = mid_x - (15 + PAD + label_w) - PAD
    right_val_w = (195 - PAD) - (mid_x + PAD + label_w)
    pdf.rect(15, start_y, 180, box_h)
    pdf.set_line_width(0.3)
    pdf.line(mid_x, start_y, mid_x, start_y + box_h)
    pdf.set_line_width(0.5)
    for i, (label, value) in enumerate(left_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(15 + PAD, y)
        pdf.set_font("Helvetica", "B", 9); pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9);  pdf.cell(left_val_w, cell_h, str(value), ln=False)
    for i, (label, value) in enumerate(right_fields):
        y = start_y + PAD + i * field_h
        pdf.set_xy(mid_x + PAD, y)
        pdf.set_font("Helvetica", "B", 9); pdf.cell(label_w, cell_h, f"{label}:", ln=False)
        pdf.set_font("Helvetica", "", 9);  pdf.cell(right_val_w, cell_h, str(value), ln=False)
    pdf.set_y(start_y + box_h + 3)
    pdf.ln(3)


def _items_table(pdf, items):
    _section_title(pdf, "DETALLE")
    headers    = ["Descripcion", "Cant.", "Precio Unit.", "Subtotal"]
    col_widths = [95, 20, 32, 33]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(50, 50, 50); pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        align = "L" if h == "Descripcion" else "R"
        pdf.cell(w, 7, f" {h}" if align == "L" else h, border=1, align=align, fill=True)
    pdf.ln(); pdf.set_text_color(0, 0, 0)
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
    col_value = 33; col_label = 180 - col_value
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


# ── Factura PDF — formato Compulibra ─────────────────────────────────────────

_TIPO_TITULO = {
    1: "FACTURA DE VENTA",    6: "FACTURA DE VENTA",    11: "FACTURA DE VENTA",
    3: "NOTA DE CREDITO",     8: "NOTA DE CREDITO",     13: "NOTA DE CREDITO",
    2: "NOTA DE DEBITO",      7: "NOTA DE DEBITO",      12: "NOTA DE DEBITO",
}


def _wrap_text(pdf, text, max_width):
    """Word-wrap text into lines fitting max_width mm (uses current font)."""
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if pdf.get_string_width(test) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


class FacturaPDF(FPDF):
    def __init__(self, factura):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.factura = factura
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=36)
        self.alias_nb_pages()

    def header(self):
        f   = self.factura
        emp = _empresa()
        tipo      = f.get("tipo", 11)
        letra     = _TIPO_LETRA.get(tipo, "C")
        cod       = _TIPO_COD.get(tipo, "011")
        doc_titulo = _TIPO_TITULO.get(tipo, "FACTURA DE VENTA")
        pv  = str(f.get("punto_venta", 1)).zfill(4)
        num = str(f.get("numero", 1)).zfill(8)

        y0 = 10
        lx, lw = 10, 80

        # ── Bloque izquierdo: logo + datos empresa ────────────────────────────
        lcy = y0
        logo = emp.get("logo_path", "")
        if logo and os.path.exists(logo):
            self.image(_prepare_logo(logo), x=lx, y=lcy, h=18)
            lcy += 20

        for bold_lbl, val in filter(lambda kv: kv[1], [
            ("Razon Social:", emp.get("nombre", "")),
            ("Domicilio:",    emp.get("direccion", "")),
            ("CUIT:",         emp.get("cuit", "")),
            ("Ing. Brutos:",  emp.get("iibb", "")),
            ("Inicio Act.:",  _fmt_fecha(emp["inicio_actividades"]) if emp.get("inicio_actividades") else ""),
        ]):
            self.set_xy(lx, lcy)
            self.set_font("Helvetica", "B", 8)
            self.cell(21, 4.5, bold_lbl, ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(lw - 21, 4.5, str(val)[:38], ln=True)
            lcy = self.get_y()

        # ── Centro: letra + COD + condición IVA (sin recuadro) ───────────────────
        bx, bw = 93, 24

        self.set_font("Helvetica", "B", 28)
        self.set_xy(bx, y0 + 2)
        self.cell(bw, 18, letra, align="C")

        self.set_font("Helvetica", "", 7)
        self.set_xy(bx, y0 + 22)
        self.cell(bw, 4.5, f"COD. {cod}", align="C")

        iva_cond_emp = emp.get("iva_condition", "Monotributista")
        iva_lbl_emp  = _IVA_EMISOR_LABEL.get(iva_cond_emp, iva_cond_emp)
        self.set_font("Helvetica", "", 6)
        self.set_xy(bx, y0 + 27)
        self.cell(bw, 4.5, iva_lbl_emp[:24], align="C")

        # ── Bloque derecho alineado al borde: título + número + campos ─────────
        rx, rw = 118, 82
        rcy = y0

        self.set_xy(rx, rcy)
        self.set_font("Helvetica", "B", 11)
        self.cell(rw, 7, doc_titulo, align="R", ln=True)
        rcy = self.get_y()

        self.set_xy(rx, rcy)
        self.set_font("Helvetica", "B", 8)
        self.cell(14, 5, "N\xb0:", ln=False)
        self.set_font("Helvetica", "B", 9)
        self.cell(rw - 14, 5, f"{letra}-{pv}-{num}", align="R", ln=True)
        rcy = self.get_y()

        for lbl, val in filter(lambda kv: kv[1], [
            ("Fecha:",        _fmt_fecha(f.get("fecha", ""))),
            ("CUIT:",         emp.get("cuit", "")),
            ("Ing. Brutos:",  emp.get("iibb", "")),
            ("Inicio Act.:",  _fmt_fecha(emp["inicio_actividades"]) if emp.get("inicio_actividades") else ""),
        ]):
            self.set_xy(rx, rcy)
            self.set_font("Helvetica", "B", 8)
            self.cell(22, 5, lbl, ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(rw - 22, 5, str(val), align="R", ln=True)
            rcy = self.get_y()

        # ── Línea separadora ──────────────────────────────────────────────────
        sep_y = max(lcy + 2, y0 + 36, rcy + 2)
        self.set_line_width(0.5)
        self.line(10, sep_y, 200, sep_y)
        self.set_line_width(0.3)
        cur_y = sep_y + 2

        # ── Período de servicio (concepto 2/3) ────────────────────────────────
        concepto = f.get("concepto", 1)
        if concepto in (2, 3):
            desde = _fmt_fecha(f.get("fch_serv_desde", ""))
            hasta = _fmt_fecha(f.get("fch_serv_hasta", ""))
            vto   = _fmt_fecha(f.get("fch_vto_pago",   ""))
            self.set_xy(10, cur_y)
            self.set_font("Helvetica", "B", 8)
            self.cell(30, 5, "Per. Facturado Desde:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(22, 5, desde, ln=False)
            self.set_font("Helvetica", "B", 8)
            self.cell(12, 5, "Hasta:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(22, 5, hasta, ln=False)
            self.set_font("Helvetica", "B", 8)
            self.cell(18, 5, "Vto. Pago:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, vto, ln=True)
            cur_y = self.get_y() + 1

        # ── Receptor ─────────────────────────────────────────────────────────
        iva_rec = _IVA_LABELS.get(f.get("cliente_iva_cond") or 0, "")
        razon   = str(f.get("cliente_razon", ""))

        self.set_xy(10, cur_y)
        self.set_font("Helvetica", "B", 8)
        self.cell(18, 5, "Sr.(es):", ln=False)
        self.set_font("Helvetica", "", 8)
        self.cell(87, 5, razon[:52], ln=False)
        if f.get("cliente_cuit"):
            self.set_font("Helvetica", "B", 8)
            self.cell(10, 5, "CUIT:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, str(f.get("cliente_cuit", "")), ln=False)
        self.ln()
        cur_y = self.get_y()

        self.set_xy(10, cur_y)
        if f.get("cliente_domicilio"):
            self.set_font("Helvetica", "B", 8)
            self.cell(18, 5, "Domicilio:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(87, 5, str(f.get("cliente_domicilio", ""))[:52], ln=False)
        if iva_rec:
            self.set_font("Helvetica", "B", 8)
            self.cell(20, 5, "Cond. IVA:", ln=False)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, iva_rec, ln=False)
        self.ln()
        cur_y = self.get_y()

        self.set_line_width(0.4)
        self.line(10, cur_y + 1, 200, cur_y + 1)
        self.set_line_width(0.3)
        self.set_y(cur_y + 4)

    def footer(self):
        f   = self.factura
        emp = _empresa()
        cae     = f.get("cae") or ""
        cae_vto = f.get("cae_vto") or ""
        if cae_vto and len(cae_vto) == 8:
            cae_vto = f"{cae_vto[6:8]}/{cae_vto[4:6]}/{cae_vto[0:4]}"

        fy = self.h - 34
        self.set_line_width(0.5)
        self.line(10, fy, 200, fy)
        fy += 2

        # QR (izquierda)
        if _HAS_QR and cae and emp.get("cuit"):
            try:
                _draw_qr(self, _afip_qr_url(f, emp["cuit"]), 11, fy, 23)
            except Exception:
                pass

        # CAE info (centro)
        cx, fy2 = 40, fy
        self.set_font("Helvetica", "B", 8)
        self.set_xy(cx, fy2)
        if cae:
            self.cell(90, 5, "Comprobante Autorizado por ARCA", ln=True)
            fy2 = self.get_y()
            self.set_font("Helvetica", "", 8)
            self.set_xy(cx, fy2)
            self.cell(90, 5, f"CAE N\xb0: {cae}", ln=True)
            fy2 = self.get_y()
            self.set_xy(cx, fy2)
            self.cell(90, 5, f"Fecha de Vto. de CAE: {cae_vto}", ln=True)
        else:
            self.set_text_color(180, 0, 0)
            self.cell(90, 5, "Pendiente de autorizacion ARCA", ln=True)
            self.set_text_color(0, 0, 0)

        # Página (derecha)
        self.set_font("Helvetica", "", 8)
        self.set_xy(130, fy)
        self.cell(70, 5, f"Pag. {self.page_no()}/{{nb}}", align="R")

        # Disclaimer
        self.set_font("Helvetica", "I", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, self.h - 8)
        self.cell(190, 4,
            "Esta Agencia no se responsabiliza por los datos ingresados en el detalle de la operacion",
            align="C")
        self.set_text_color(0, 0, 0)


def _factura_items_table(pdf, items):
    """Tabla de ítems — 6 columnas con descripciones multi-línea."""
    widths  = [12, 90, 18, 30, 15, 25]
    headers = ["Cod.", "Articulo", "Cantidad", "Precio Unit.", "% Dto.", "Importe"]
    aligns  = ["C",    "L",        "R",        "R",            "R",      "R"]
    LINE_H  = 5

    def draw_header():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_draw_color(150, 150, 150)
        pdf.set_line_width(0.3)
        for h, w, a in zip(headers, widths, aligns):
            pdf.cell(w, 6, h, border=1, align=a, fill=True)
        pdf.ln()

    draw_header()
    pdf.set_font("Helvetica", "", 8)

    for idx, item in enumerate(items):
        fill = idx % 2 == 0
        fc   = (248, 248, 248) if fill else (255, 255, 255)

        desc  = str(item.get("description", ""))
        qty   = item.get("qty", 1)
        price = item.get("unit_price", 0)
        sub   = item.get("subtotal", 0)

        desc_lines = _wrap_text(pdf, desc, widths[1] - 2)
        row_h = max(len(desc_lines), 1) * LINE_H + 2

        if pdf.get_y() + row_h > pdf.h - 36:
            pdf.add_page()
            draw_header()
            pdf.set_font("Helvetica", "", 8)

        pdf.set_fill_color(*fc)
        y_row = pdf.get_y()

        pdf.cell(widths[0], row_h, str(idx + 1),      border=1, align="C", fill=fill)
        desc_x = pdf.get_x()
        pdf.cell(widths[1], row_h, "",                 border=1, align="L", fill=fill)
        pdf.cell(widths[2], row_h, f"{qty:g}",         border=1, align="R", fill=fill)
        pdf.cell(widths[3], row_h, f"{price:,.2f}",    border=1, align="R", fill=fill)
        pdf.cell(widths[4], row_h, "0,00",             border=1, align="R", fill=fill)
        pdf.cell(widths[5], row_h, f"{sub:,.2f}",      border=1, align="R", fill=fill)

        for li, line in enumerate(desc_lines):
            pdf.set_xy(desc_x + 1, y_row + 1 + li * LINE_H)
            pdf.cell(widths[1] - 2, LINE_H, line, align="L")

        pdf.set_xy(10, y_row + row_h)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.ln(3)


def _factura_totals_block(pdf, factura):
    """Barra IVA + barra resumen (Factura A/B) o totales simples (Factura C)."""
    sub  = factura.get("subtotal", 0)
    iva  = factura.get("iva_amount", 0)
    tot  = factura.get("total", 0)
    tipo = factura.get("tipo", 11)

    pdf.set_draw_color(150, 150, 150)
    pdf.set_line_width(0.3)

    if iva > 0 and tipo not in _TIPOS_C:
        pct = round(iva / sub * 100) if sub > 0 else 21

        # Barra desglose IVA (4 columnas)
        iw = [48, 47, 47, 48]
        iva_hdrs = [f"Neto Grav. {pct:.0f}%", f"IVA {pct:.0f}%",
                    "Neto No Gravado", "Otros Tributos"]
        iva_vals = [f"$ {sub:,.2f}", f"$ {iva:,.2f}", "$ 0,00", "$ 0,00"]

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        for h, w in zip(iva_hdrs, iw):
            pdf.cell(w, 5, h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        pdf.set_fill_color(255, 255, 255)
        for v, w in zip(iva_vals, iw):
            pdf.cell(w, 5, v, border=1, align="R")
        pdf.ln()
        pdf.ln(2)

        # Barra resumen (3 columnas)
        sw = [63, 63, 64]
        s_hdrs = ["Bruto", "Impuestos", "Importe Total"]
        s_vals = [f"$ {sub:,.2f}", f"$ {iva:,.2f}", f"$ {tot:,.2f}"]

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        for h, w in zip(s_hdrs, sw):
            pdf.cell(w, 5, h, border=1, align="C", fill=True)
        pdf.ln()

        for i, (v, w) in enumerate(zip(s_vals, sw)):
            pdf.set_font("Helvetica", "B" if i == 2 else "", 9 if i == 2 else 8)
            if i == 2:
                pdf.set_fill_color(230, 242, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.cell(w, 6, v, border=1, align="R", fill=True)
        pdf.ln()

    else:
        # Totales simples para Factura C / sin IVA
        lw, vw = 150, 40

        def row(label, value, bold=False, h=6):
            pdf.set_x(10)
            pdf.set_font("Helvetica", "B" if bold else "", 10 if bold else 9)
            pdf.cell(lw, h, label, align="R")
            pdf.cell(vw, h, f"$ {value:,.2f}", border=1, align="R")
            pdf.ln()

        row("Subtotal:", sub)
        row("Importe Total:", tot, bold=True, h=7)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.ln(3)


def generate_pdf_factura(factura, output_dir=None):
    os.makedirs(output_dir or FACTURAS_PDF_DIR, exist_ok=True)
    pv  = str(factura["punto_venta"]).zfill(4)
    num = str(factura["numero"]).zfill(8)
    filepath = os.path.join(output_dir or FACTURAS_PDF_DIR, f"factura_{pv}_{num}.pdf")
    pdf = FacturaPDF(factura)
    pdf.add_page()
    _factura_items_table(pdf, factura["items"])
    if factura.get("observaciones"):
        _observations_block(pdf, factura["observaciones"])
    tipo     = factura.get("tipo", 11)
    iva      = factura.get("iva_amount", 0)
    totals_h = 28 if (iva > 0 and tipo not in _TIPOS_C) else 18
    target_y = pdf.h - 36 - totals_h
    cur_y    = pdf.get_y()
    if cur_y + totals_h > pdf.h - 36:
        pdf.add_page()
    elif cur_y < target_y:
        pdf.set_y(target_y)
    _factura_totals_block(pdf, factura)
    pdf.output(filepath)
    return os.path.abspath(filepath)

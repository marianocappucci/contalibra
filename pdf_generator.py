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
_TIPO_LETRA  = {1:"A", 6:"B", 11:"C", 3:"A", 8:"B", 13:"C", 2:"A", 7:"B", 12:"C"}
_TIPO_COD    = {1:"001", 6:"006", 11:"011", 3:"003", 8:"008", 13:"013",
                2:"002", 7:"007", 12:"012"}
_TIPO_NOMBRE_DOC = {
    1:"FACTURA",        6:"FACTURA",        11:"FACTURA",
    3:"NOTA DE CRÉDITO", 8:"NOTA DE CRÉDITO", 13:"NOTA DE CRÉDITO",
    2:"NOTA DE DÉBITO",  7:"NOTA DE DÉBITO",  12:"NOTA DE DÉBITO",
}
_IVA_EMISOR_LABEL = {
    "Monotributista":        "Responsable Monotributo",
    "Responsable Inscripto": "IVA Responsable Inscripto",
    "IVA Exento":            "IVA Exento",
}
_TIPOS_C = {11, 12, 13}

# ── Paleta de diseño ──────────────────────────────────────────────────────────
_TEAL     = (44, 122, 123)
_DARK     = (28, 28, 28)
_NOTES_BG = (224, 237, 244)
_BORDER   = (200, 200, 200)
_WHITE    = (255, 255, 255)
_MUTED    = (110, 110, 110)
_LX, _RX, _CW = 12, 198, 186

# ── QR y PIL ─────────────────────────────────────────────────────────────────
try:
    import qrcode as _qrlib
    _HAS_QR = True
except ImportError:
    _HAS_QR = False

try:
    from PIL import Image as _PILImage
    import io as _io
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _prepare_logo(path: str):
    if not _HAS_PIL:
        return path
    try:
        img = _PILImage.open(path)
        if img.mode != "RGBA":
            return path
        _, _, _, alpha = img.split()
        opaque = [(img.getpixel((x, y))[:3])
                  for x in range(0, img.size[0], 15)
                  for y in range(0, img.size[1], 15)
                  if img.getpixel((x, y))[3] > 128]
        is_white_logo = bool(opaque) and (
            sum(r + g + b for r, g, b in opaque) / (len(opaque) * 3) > 240
        )
        bg = _PILImage.new("RGB", img.size, (255, 255, 255))
        if is_white_logo:
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
        "ver": 1, "fecha": factura.get("fecha", ""),
        "cuit": int(cuit_e) if cuit_e.isdigit() else 0,
        "ptoVta": int(factura.get("punto_venta", 1)),
        "tipoCmp": int(factura.get("tipo", 11)),
        "nroCmp": int(factura.get("numero", 1)),
        "importe": round(float(factura.get("total", 0)), 2),
        "moneda": "PES", "ctz": 1,
        "tipoDocRec": tipo_doc, "nroDocRec": nro_doc,
        "tipoCodAut": "E", "codAut": cae_int,
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
        pdf.set_fill_color(*_WHITE)
    except Exception:
        pass


def _wrap_text(pdf, text: str, max_width: float) -> list:
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


# ── Bloque de cabecera común ──────────────────────────────────────────────────

def _draw_header_block(pdf, letra, titulo, codigo, info_fields, empresa):
    """
    Dibuja la sección superior: logo + nombre empresa (izq),
    caja oscura con letra + info box (der), línea separadora.
    Retorna la Y después del separador.
    """
    y0 = 12

    # Izquierda: logo (si existe) o nombre de empresa en texto
    logo_path = empresa.get("logo_path", "")
    has_logo  = bool(logo_path and os.path.exists(logo_path))
    if has_logo:
        pdf.image(_prepare_logo(logo_path), x=_LX, y=y0, h=16)
    else:
        pdf.set_xy(_LX, y0)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*_DARK)
        pdf.cell(100, 8, empresa.get("nombre", ""), ln=False)

        iva_cond = empresa.get("iva_condition", "")
        if iva_cond:
            pdf.set_xy(_LX, y0 + 9)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*_MUTED)
            pdf.cell(100, 5, iva_cond, ln=False)

    # Derecha: caja con letra + título + info sub-box
    rbx = 113
    rbw = _RX - rbx   # 85 mm
    box_s = 28

    pdf.set_fill_color(*_DARK)
    pdf.rect(rbx, y0, box_s, box_s, style="F")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_WHITE)
    pdf.set_xy(rbx, y0 + 4)
    pdf.cell(box_s, 20, letra, align="C", ln=False)

    pdf.set_text_color(*_DARK)
    tx2 = rbx + box_s + 4
    tw2 = rbw - box_s - 4
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(tx2, y0 + 4)
    pdf.cell(tw2, 6, titulo, ln=False)
    if codigo:
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_MUTED)
        pdf.set_xy(tx2, y0 + 11)
        pdf.cell(tw2, 5, f"Código {codigo} · Original", ln=False)

    # Sub-box de info (PV / N° / Fecha)
    info_y   = y0 + box_s + 3
    row_h    = 5.5
    info_h   = len(info_fields) * row_h + 4
    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.3)
    pdf.rect(rbx, info_y, rbw, info_h, style="D")

    for i, (lbl, val) in enumerate(info_fields):
        ry = info_y + 2 + i * row_h
        pdf.set_xy(rbx + 3, ry)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_MUTED)
        pdf.cell(36, row_h, lbl, ln=False)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_DARK)
        pdf.cell(rbw - 39, row_h, str(val or ""), ln=False)

    sep_y = info_y + info_h + 4
    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.5)
    pdf.line(_LX, sep_y, _RX, sep_y)
    pdf.set_text_color(*_DARK)
    return sep_y + 4


# ── Bloque EMISOR | CLIENTE ───────────────────────────────────────────────────

def _draw_emisor_cliente(pdf, empresa, client_fields):
    """
    Dos columnas: EMISOR (izq) y CLIENTE (der) con cabecera teal.
    client_fields: lista de (label, value).
    """
    y = pdf.get_y()
    col_w = (_CW - 4) // 2   # ~91 mm cada columna

    iva_cond_emp = empresa.get("iva_condition", "Monotributista")
    iva_lbl_emp  = _IVA_EMISOR_LABEL.get(iva_cond_emp, iva_cond_emp)
    emisor_fields = [
        ("Razón social",       empresa.get("nombre", "")),
        ("CUIT",               empresa.get("cuit", "")),
        ("Condición IVA",      iva_lbl_emp),
        ("Domicilio",          empresa.get("direccion", "")),
        ("Ingresos Brutos",    empresa.get("iibb", "")),
        ("Inicio actividades", _fmt_fecha(empresa.get("inicio_actividades", ""))),
    ]
    emisor_fields = [(l, v) for l, v in emisor_fields if v]

    label_h  = 7
    row_h    = 6
    pad      = 3
    max_rows = max(len(emisor_fields), len(client_fields), 1)
    box_h    = label_h + max_rows * row_h + pad

    def draw_col(bx, bw, title, fields):
        pdf.set_fill_color(*_TEAL)
        pdf.set_draw_color(*_BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(bx, y, bw, box_h, style="D")
        pdf.rect(bx, y, bw, label_h, style="F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_WHITE)
        pdf.set_xy(bx + pad, y + 1.5)
        pdf.cell(bw - 2 * pad, label_h - 3, title, ln=False)

        for i, (lbl, val) in enumerate(fields):
            fy = y + label_h + i * row_h
            lbl_w = bw * 0.42
            pdf.set_xy(bx + pad, fy)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*_MUTED)
            pdf.cell(lbl_w, row_h, lbl, ln=False)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*_DARK)
            pdf.cell(bw - lbl_w - 2 * pad, row_h, str(val or "")[:40], ln=False)

    draw_col(_LX,              col_w, "EMISOR",  emisor_fields)
    draw_col(_LX + col_w + 4,  col_w, "CLIENTE", client_fields)

    pdf.set_text_color(*_DARK)
    pdf.set_y(y + box_h + 5)


# ── Tabla de ítems ────────────────────────────────────────────────────────────

def _draw_items_table(pdf, items, show_iva_col=False):
    """Tabla de artículos con encabezado teal."""
    if show_iva_col:
        widths  = [82, 20, 33, 18, 33]
        headers = ["DESCRIPCIÓN", "CANTIDAD", "PRECIO UNITARIO", "IVA", "IMPORTE"]
        aligns  = ["L", "R", "R", "C", "R"]
    else:
        widths  = [100, 22, 33, 31]
        headers = ["DESCRIPCIÓN", "CANTIDAD", "PRECIO UNITARIO", "IMPORTE"]
        aligns  = ["L", "R", "R", "R"]

    LINE_H = 5

    def draw_header():
        pdf.set_x(_LX)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_fill_color(*_TEAL)
        pdf.set_text_color(*_WHITE)
        pdf.set_line_width(0)
        for h, w, a in zip(headers, widths, aligns):
            pdf.cell(w, 7, f"  {h}" if a == "L" else h,
                     border=0, align=a, fill=True)
        pdf.ln()
        pdf.set_text_color(*_DARK)

    draw_header()

    for idx, item in enumerate(items):
        fill = idx % 2 == 0
        if fill:
            pdf.set_fill_color(248, 249, 250)
        else:
            pdf.set_fill_color(*_WHITE)

        raw_desc = str(item.get("description", ""))
        # Split at newline into title + detail
        parts     = raw_desc.split("\n", 1)
        title_txt = parts[0].strip()
        detail_txt = parts[1].strip() if len(parts) > 1 else item.get("detalle", "")

        qty   = item.get("qty", 1)
        price = item.get("unit_price", 0)
        sub   = item.get("subtotal", 0)

        has_detail = bool(detail_txt)
        row_h = LINE_H + (LINE_H if has_detail else 0) + 3

        if pdf.get_y() + row_h > pdf.h - 50:
            pdf.add_page()
            draw_header()

        y_row = pdf.get_y()
        pdf.set_x(_LX)

        # Celda de descripción (fondo, sin texto)
        pdf.cell(widths[0], row_h, "", fill=fill, ln=False)

        # Columnas numéricas
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(widths[1], row_h, f"{qty:g}",        fill=fill, align="R", ln=False)
        pdf.cell(widths[2], row_h, f"$ {price:,.2f}", fill=fill, align="R", ln=False)
        if show_iva_col:
            iva_pct = item.get("iva_pct", 0)
            pdf.cell(widths[3], row_h, f"{iva_pct:.0f}%", fill=fill, align="C", ln=False)
        pdf.cell(widths[-1], row_h, f"$ {sub:,.2f}", fill=fill, align="R", ln=True)

        # Texto de descripción superpuesto
        pdf.set_xy(_LX + 2, y_row + 1.5)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(widths[0] - 4, LINE_H, title_txt[:70], ln=False)
        if has_detail:
            pdf.set_xy(_LX + 2, y_row + 1.5 + LINE_H)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*_MUTED)
            pdf.cell(widths[0] - 4, LINE_H, detail_txt[:80], ln=False)
            pdf.set_text_color(*_DARK)

        pdf.set_xy(_LX, y_row + row_h)

    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.3)
    pdf.line(_LX, pdf.get_y(), _RX, pdf.get_y())
    pdf.ln(4)


# ── Totales + Notas ───────────────────────────────────────────────────────────

def _draw_totals_and_notes(pdf, sub, iva_amount, otros, total, tax_pct,
                           observations=None):
    """
    Izquierda: caja de notas (azul claro).
    Derecha: filas Subtotal / IVA / Otros tributos / Total.
    """
    y        = pdf.get_y()
    notes_w  = 90
    totals_w = _CW - notes_w - 4
    row_h    = 7
    box_h    = row_h * 4
    notes_h  = max(box_h, 30)

    # Caja de notas
    pdf.set_fill_color(*_NOTES_BG)
    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.3)
    pdf.rect(_LX, y, notes_w, notes_h, style="FD")
    if observations:
        pdf.set_xy(_LX + 3, y + 3)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(notes_w - 6, 5, "Notas:", ln=False)
        pdf.set_xy(_LX + 3, y + 9)
        pdf.set_font("Helvetica", "", 7.5)
        # guardar posición y usar multi_cell con ancho limitado
        pdf.multi_cell(notes_w - 6, 4.5, str(observations)[:400])

    # Filas de totales
    tx = _LX + notes_w + 4
    rows_data = [
        ("Subtotal",              f"$ {sub:,.2f}",        False),
        (f"IVA {tax_pct:.0f}%",  f"$ {iva_amount:,.2f}", False),
        ("Otros tributos",        f"$ {otros:,.2f}",      False),
        ("Total",                 f"$ {total:,.2f}",      True),
    ]

    for i, (lbl, val, is_total) in enumerate(rows_data):
        ry = y + i * row_h
        if is_total:
            pdf.set_fill_color(*_DARK)
            pdf.set_draw_color(*_DARK)
            pdf.rect(tx, ry, totals_w, row_h, style="F")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_WHITE)
        else:
            pdf.set_draw_color(*_BORDER)
            pdf.set_line_width(0.3)
            pdf.rect(tx, ry, totals_w, row_h, style="D")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*_DARK)

        lbl_w = totals_w * 0.52
        pdf.set_xy(tx + 3, ry + 1.5)
        pdf.cell(lbl_w - 3, row_h - 3, lbl, ln=False)
        pdf.set_xy(tx + lbl_w, ry + 1.5)
        pdf.cell(totals_w - lbl_w - 3, row_h - 3, val, align="R", ln=False)

    pdf.set_text_color(*_DARK)
    pdf.set_y(y + notes_h + 5)


# ── Marca de agua para documentos no fiscales ─────────────────────────────────

def _draw_no_fiscal_notice(pdf, text="DOCUMENTO NO VÁLIDO COMO FACTURA"):
    y = pdf.get_y() + 3
    pdf.set_draw_color(180, 80, 0)
    pdf.set_line_width(0.5)
    pdf.rect(_LX, y, _CW, 8, style="D")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(180, 80, 0)
    pdf.set_xy(_LX, y + 1.5)
    pdf.cell(_CW, 5, text, align="C", ln=False)
    pdf.set_text_color(*_DARK)
    pdf.set_y(y + 12)


# ── Footer CAE (facturas) ─────────────────────────────────────────────────────

def _draw_factura_footer(pdf, factura, empresa):
    cae     = factura.get("cae") or ""
    cae_vto = factura.get("cae_vto") or ""
    if cae_vto and len(cae_vto) == 8:
        cae_vto = f"{cae_vto[6:8]}/{cae_vto[4:6]}/{cae_vto[0:4]}"

    fy = pdf.h - 36
    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.4)
    pdf.line(_LX, fy, _RX, fy)
    fy += 2

    qr_size = 26
    qr_x    = _RX - qr_size
    qr_y    = fy

    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.3)
    pdf.rect(qr_x, qr_y, qr_size, qr_size, style="D")

    if _HAS_QR and cae and empresa.get("cuit"):
        try:
            _draw_qr(pdf, _afip_qr_url(factura, empresa["cuit"]),
                     qr_x + 1, qr_y + 1, qr_size - 2)
        except Exception:
            pass
    else:
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*_MUTED)
        pdf.set_xy(qr_x, qr_y + 8)
        pdf.cell(qr_size, 4, "QR fiscal ARCA /", align="C")
        pdf.set_xy(qr_x, qr_y + 12)
        pdf.cell(qr_size, 4, "AFIP", align="C")
        pdf.set_text_color(*_DARK)

    # Info CAE
    cx = _LX
    cy = fy + 1
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_DARK)
    pdf.set_xy(cx, cy)
    if cae:
        pdf.cell(qr_x - cx - 3, 5, f"CAE/CAI: {cae}", ln=True)
        pdf.set_xy(cx, pdf.get_y())
        pdf.cell(qr_x - cx - 3, 5, f"Vencimiento CAE/CAI: {cae_vto}", ln=True)
    else:
        pdf.set_text_color(180, 0, 0)
        pdf.cell(qr_x - cx - 3, 5, "Pendiente de autorización ARCA", ln=True)
        pdf.set_text_color(*_DARK)
    pdf.set_xy(cx, pdf.get_y())
    pdf.cell(qr_x - cx - 3, 5,
             "Moneda: Pesos argentinos · Tipo de cambio: no aplica", ln=False)

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_MUTED)
    pdf.set_xy(_LX, pdf.h - 8)
    pdf.cell(_CW, 4, f"Pág. {pdf.page_no()}/{{nb}}", align="R")
    pdf.set_text_color(*_DARK)


# ── Clases PDF ────────────────────────────────────────────────────────────────

class FacturaPDF(FPDF):
    def __init__(self, factura):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.factura = factura
        self._emp    = None
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=38)
        self.alias_nb_pages()

    def header(self):
        f   = self.factura
        emp = self._emp or _empresa()
        tipo  = f.get("tipo", 11)
        letra = _TIPO_LETRA.get(tipo, "C")
        cod   = _TIPO_COD.get(tipo, "011")
        titulo = _TIPO_NOMBRE_DOC.get(tipo, "FACTURA")
        pv    = str(f.get("punto_venta", 1)).zfill(4)
        num   = str(f.get("numero", 1)).zfill(8)
        fecha = _fmt_fecha(f.get("fecha", ""))
        info_fields = [
            ("Punto de venta:",    pv),
            ("Comprobante N\xb0:", f"{letra}-{pv}-{num}"),
            ("Fecha de emisión:",  fecha),
        ]
        end_y = _draw_header_block(self, letra, titulo, cod, info_fields, emp)
        self.set_y(end_y)

    def footer(self):
        emp = self._emp or _empresa()
        _draw_factura_footer(self, self.factura, emp)


class RemitoPDF(FPDF):
    def __init__(self, remito):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.remito = remito
        self._emp   = None
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        r   = self.remito
        emp = self._emp or _empresa()
        info_fields = [
            ("N° Remito:", r["number"]),
            ("Fecha:",     _fmt_fecha(r["date"]) or r["date"]),
        ]
        end_y = _draw_header_block(self, "R", "REMITO", "", info_fields, emp)
        self.set_y(end_y)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED)
        self.cell(0, 5, "Documento no válido como factura", align="C")
        self.set_text_color(*_DARK)


class PresupuestoPDF(FPDF):
    def __init__(self, presupuesto):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.presupuesto = presupuesto
        self._emp        = None
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        p   = self.presupuesto
        emp = self._emp or _empresa()
        info_fields = [
            ("N° Presupuesto:", p["number"]),
            ("Fecha:",          _fmt_fecha(p["date"]) or p["date"]),
            ("Válido hasta:",   _fmt_fecha(p.get("valid_until", "")) or p.get("valid_until", "")),
        ]
        end_y = _draw_header_block(self, "P", "PRESUPUESTO", "", info_fields, emp)
        self.set_y(end_y)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED)
        self.cell(0, 5,
            f"Presupuesto válido hasta: {self.presupuesto.get('valid_until', '')}",
            align="C")
        self.set_text_color(*_DARK)


# ── Funciones de generación ───────────────────────────────────────────────────

def generate_pdf(remito, output_dir=None):
    os.makedirs(output_dir or PDF_DIR, exist_ok=True)
    safe_number = remito["number"].replace("/", "-")
    filepath = os.path.join(output_dir or PDF_DIR,
                            f"remito_{safe_number}_{remito['date']}.pdf")
    emp = _empresa()
    pdf = RemitoPDF(remito)
    pdf._emp = emp
    pdf.add_page()

    # EMISOR + CLIENTE
    client_fields = [
        ("Nombre",    remito.get("client_name", "")),
        ("CUIT/DNI",  remito.get("client_cuit", "")),
        ("Domicilio", remito.get("client_address", "")),
        ("Email",     remito.get("client_email", "")),
        ("Teléfono",  remito.get("client_phone", "")),
    ]
    client_fields = [(l, v) for l, v in client_fields if v]
    _draw_emisor_cliente(pdf, emp, client_fields)

    _draw_items_table(pdf, remito["items"], show_iva_col=False)

    sub = remito.get("subtotal", 0)
    tax = remito.get("tax_amount", 0)
    tot = remito.get("total", 0)
    pct = round(remito.get("tax_rate", 0) * 100)
    _draw_totals_and_notes(pdf, sub, tax, 0, tot, pct,
                           remito.get("observations", ""))

    _draw_no_fiscal_notice(pdf)
    pdf.output(filepath)
    return os.path.abspath(filepath)


def generate_pdf_presupuesto(presupuesto, output_dir=None):
    os.makedirs(output_dir or PRESUPUESTOS_PDF_DIR, exist_ok=True)
    safe_number = presupuesto["number"].replace("/", "-")
    filepath = os.path.join(output_dir or PRESUPUESTOS_PDF_DIR,
                            f"presupuesto_{safe_number}_{presupuesto['date']}.pdf")
    emp = _empresa()
    pdf = PresupuestoPDF(presupuesto)
    pdf._emp = emp
    pdf.add_page()

    # EMISOR + CLIENTE
    client_fields = [
        ("Nombre",    presupuesto.get("client_name", "")),
        ("CUIT/DNI",  presupuesto.get("client_cuit", "")),
        ("Domicilio", presupuesto.get("client_address", "")),
        ("Email",     presupuesto.get("client_email", "")),
        ("Teléfono",  presupuesto.get("client_phone", "")),
    ]
    client_fields = [(l, v) for l, v in client_fields if v]
    _draw_emisor_cliente(pdf, emp, client_fields)

    _draw_items_table(pdf, presupuesto["items"], show_iva_col=False)

    sub = presupuesto.get("subtotal", 0)
    tax = presupuesto.get("tax_amount", 0)
    tot = presupuesto.get("total", 0)
    pct = round(presupuesto.get("tax_rate", 0) * 100)
    _draw_totals_and_notes(pdf, sub, tax, 0, tot, pct,
                           presupuesto.get("observations", ""))

    _draw_no_fiscal_notice(
        pdf, "PARA PRESUPUESTO/PROFORMA: DOCUMENTO NO VÁLIDO COMO FACTURA")
    pdf.output(filepath)
    return os.path.abspath(filepath)


def generate_pdf_factura(factura, output_dir=None):
    os.makedirs(output_dir or FACTURAS_PDF_DIR, exist_ok=True)
    pv  = str(factura["punto_venta"]).zfill(4)
    num = str(factura["numero"]).zfill(8)
    filepath = os.path.join(output_dir or FACTURAS_PDF_DIR, f"factura_{pv}_{num}.pdf")

    emp = _empresa()
    pdf = FacturaPDF(factura)
    pdf._emp = emp
    pdf.add_page()

    # EMISOR + CLIENTE
    iva_rec = _IVA_LABELS.get(factura.get("cliente_iva_cond") or 0, "Consumidor Final")
    client_fields = [
        ("Nombre",          factura.get("cliente_razon", "")),
        ("CUIT/DNI",        factura.get("cliente_cuit", "")),
        ("Condición IVA",   iva_rec),
        ("Domicilio",       factura.get("cliente_domicilio", "")),
        ("Condición venta", factura.get("condicion_venta", "")),
    ]
    client_fields = [(l, v) for l, v in client_fields if v]
    _draw_emisor_cliente(pdf, emp, client_fields)

    # Período de servicio (concepto 2/3)
    concepto = factura.get("concepto", 1)
    if concepto in (2, 3):
        desde = _fmt_fecha(factura.get("fch_serv_desde", ""))
        hasta = _fmt_fecha(factura.get("fch_serv_hasta", ""))
        vto   = _fmt_fecha(factura.get("fch_vto_pago", ""))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_MUTED)
        pdf.set_x(_LX)
        txt = f"Per. facturado: {desde} al {hasta}"
        if vto:
            txt += f"  ·  Vto. pago: {vto}"
        pdf.cell(_CW, 5, txt, ln=True)
        pdf.set_text_color(*_DARK)
        pdf.ln(2)

    # Tabla de ítems (col IVA visible para Factura A/B)
    tipo     = factura.get("tipo", 11)
    show_iva = tipo not in _TIPOS_C
    _draw_items_table(pdf, factura["items"], show_iva_col=show_iva)

    # Totales
    sub  = factura.get("subtotal", 0)
    iva  = factura.get("iva_amount", 0)
    tot  = factura.get("total", 0)
    if sub > 0 and iva > 0:
        tax_pct = round(iva / sub * 100)
    elif tipo not in _TIPOS_C:
        tax_pct = 21
    else:
        tax_pct = 0

    totals_h = 40
    if pdf.get_y() + totals_h > pdf.h - 38:
        pdf.add_page()

    _draw_totals_and_notes(pdf, sub, iva, 0, tot, tax_pct,
                           factura.get("observaciones", ""))
    pdf.output(filepath)
    return os.path.abspath(filepath)

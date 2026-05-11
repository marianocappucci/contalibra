"""
Cliente WSPadron A4 de ARCA/AFIP.
Consulta datos de contribuyentes por CUIT usando credenciales WSAA.
"""

import ssl
import xml.etree.ElementTree as ET

import httpx

WSPADRON_URL = {
    "homologacion": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4",
    "produccion":   "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4",
}

_NS = "http://a4.soap.ws.server.puc.sr/"


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.set_ciphers("ALL:@SECLEVEL=0")
    return ctx


async def consultar_persona(
    cuit_empresa: str,
    cuit_consultar: str,
    token: str,
    sign: str,
    ambiente: str = "produccion",
) -> dict:
    """
    Consulta datos de un contribuyente en WSPadron A4.
    Devuelve dict con: nombre, domicilio, iva_condition, estado, cuit.
    Lanza RuntimeError con mensaje legible ante cualquier falla.
    """
    url  = WSPADRON_URL.get(ambiente, WSPADRON_URL["produccion"])
    cuit_e = cuit_empresa.replace("-", "").strip()
    cuit_c = cuit_consultar.replace("-", "").strip()

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<SOAP-ENV:Envelope '
        'xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:ns="{_NS}">'
        "<SOAP-ENV:Body>"
        "<ns:getPersona>"
        f"<token>{token}</token>"
        f"<sign>{sign}</sign>"
        f"<cuitRepresentada>{cuit_e}</cuitRepresentada>"
        f"<idPersona>{cuit_c}</idPersona>"
        "</ns:getPersona>"
        "</SOAP-ENV:Body>"
        "</SOAP-ENV:Envelope>"
    )

    async with httpx.AsyncClient(verify=_ssl_ctx(), timeout=15) as client:
        resp = await client.post(
            url,
            content=body.encode(),
            headers={
                "Content-Type": "text/xml; charset=UTF-8",
                "SOAPAction": '""',
            },
        )

    root = ET.fromstring(resp.text)

    # SOAP fault check
    fault = next((e.text for e in root.iter() if e.tag.endswith("faultstring")), None)
    if fault:
        if "no encontrado" in fault.lower() or "not found" in fault.lower() or "inexistente" in fault.lower():
            raise RuntimeError("CUIT no encontrado en el padrón de ARCA.")
        raise RuntimeError(f"WSPadron: {fault}")

    # Buscar getPersonaReturn
    ret = next((e for e in root.iter() if e.tag.endswith("getPersonaReturn")), None)
    if ret is None:
        raise RuntimeError("WSPadron: respuesta inesperada (sin getPersonaReturn)")

    def text(tag):
        el = next((e for e in ret.iter() if e.tag.endswith(tag)), None)
        return (el.text or "").strip() if el is not None else ""

    tipo_persona = text("tipoPersona")
    estado       = text("estadoClave")

    if tipo_persona == "JURIDICA":
        nombre = text("razonSocial") or text("nombre")
    else:
        apellido = text("apellido")
        nombre_p = text("nombre")
        nombre   = f"{apellido}, {nombre_p}".strip(", ") if apellido else nombre_p

    # Domicilio fiscal
    dom_el = next((e for e in ret.iter() if e.tag.endswith("domicilioFiscal")), None)
    domicilio = ""
    if dom_el is not None:
        calle     = next((e.text or "" for e in dom_el if e.tag.endswith("calle")),     "").strip()
        numero    = next((e.text or "" for e in dom_el if e.tag.endswith("numero")),    "").strip()
        localidad = next((e.text or "" for e in dom_el if e.tag.endswith("localidad")), "").strip()
        provincia = next((e.text or "" for e in dom_el if e.tag.endswith("descripcionProvincia")), "").strip()
        parts = [p for p in [f"{calle} {numero}".strip(), localidad, provincia] if p]
        domicilio = ", ".join(parts)

    # Condición IVA
    iva_condition = _detectar_iva(ret)

    return {
        "cuit":          cuit_c,
        "nombre":        nombre,
        "domicilio":     domicilio,
        "iva_condition": iva_condition,
        "estado":        estado,
    }


def _detectar_iva(ret: ET.Element) -> str:
    """Determina la condición IVA a partir del nodo getPersonaReturn."""
    # Monotributista: existe datosMonotributo con actividad activa
    mono = next((e for e in ret.iter() if e.tag.endswith("datosMonotributo")), None)
    if mono is not None:
        estado_mono = next((e.text for e in mono.iter() if e.tag.endswith("estado")), "") or ""
        if estado_mono.upper() in ("ACTIVO", ""):
            return "Monotributista"

    # Buscar en impuestos: idImpuesto 32 = IVA RI, 34 = IVA Exento, 33 = IVA No Responsable
    for imp in ret.iter():
        if not imp.tag.endswith("impuesto"):
            continue
        id_imp = next((e.text for e in imp if e.tag.endswith("idImpuesto")), "") or ""
        estado_imp = next((e.text for e in imp if e.tag.endswith("estado")), "") or ""
        if estado_imp.upper() != "ACTIVO":
            continue
        if id_imp == "32":
            return "Responsable Inscripto"
        if id_imp == "34":
            return "IVA Exento"
        if id_imp == "33":
            return "IVA No Responsable"

    return "Consumidor Final"

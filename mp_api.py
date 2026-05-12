import httpx

MP_API_BASE = "https://api.mercadopago.com"


async def obtener_pago(payment_id: str, access_token: str) -> dict:
    url = f"{MP_API_BASE}/v1/payments/{payment_id}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code == 404:
            raise ValueError(f"Pago {payment_id} no encontrado en MercadoPago.")
        r.raise_for_status()
        return r.json()


async def crear_orden_qr(
    user_id: str,
    pos_id: str,
    access_token: str,
    external_reference: str,
    titulo: str,
    items: list[dict],
    total: float,
) -> dict:
    """
    Crea una orden en el POS QR Dinámico de MP.
    Devuelve el dict de respuesta de MP (contiene 'in_store_order_id').
    Los ítems deben tener: title, quantity, unit_price.
    """
    url = f"{MP_API_BASE}/instore/qrs/merchant/stores/{{}}/pos/{pos_id}/orders"
    # MP usa: PUT /instore/qrs/merchant/stores/{store_id}/pos/{pos_id}/orders
    # pero con user_id como header o en la URL según versión de API.
    # La URL correcta para QR Dinámico V2:
    url = f"{MP_API_BASE}/instore/qrs/merchant/stores/default/pos/{pos_id}/orders"

    payload = {
        "external_reference": external_reference,
        "title": titulo,
        "description": titulo,
        "total_amount": round(total, 2),
        "items": [
            {
                "sku_number": str(it.get("producto_id") or idx),
                "category": "marketplace",
                "title": it["nombre"],
                "description": it.get("nombre", ""),
                "quantity": it["qty"],
                "unit_measure": "unit",
                "unit_price": round(it["precio"], 2),
                "total_amount": round(it["subtotal"], 2),
            }
            for idx, it in enumerate(items)
        ],
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.put(url, json=payload, headers=headers)
        if not r.is_success:
            raise RuntimeError(
                f"MP QR error {r.status_code}: {r.text[:300]}"
            )
        return r.json()


async def eliminar_orden_qr(pos_id: str, access_token: str) -> None:
    """Cancela la orden pendiente en el POS (deja el QR sin orden asignada)."""
    url = f"{MP_API_BASE}/instore/qrs/merchant/stores/default/pos/{pos_id}/orders"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.delete(url, headers=headers)


async def buscar_pago_por_referencia(
    external_reference: str, access_token: str
) -> dict | None:
    """
    Busca el último pago aprobado para una external_reference.
    Devuelve el dict del pago o None.
    """
    url = f"{MP_API_BASE}/v1/payments/search"
    params = {
        "external_reference": external_reference,
        "sort": "date_created",
        "criteria": "desc",
        "limit": 1,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None

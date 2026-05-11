import httpx

MP_API_BASE = "https://api.mercadopago.com"


async def obtener_pago(payment_id, access_token: str) -> dict:
    url = f"{MP_API_BASE}/v1/payments/{payment_id}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code == 404:
            raise ValueError(f"Pago {payment_id} no encontrado en MercadoPago.")
        r.raise_for_status()
        return r.json()

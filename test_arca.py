#!/usr/bin/env python3
"""
Script de prueba para conectar a ARCA y obtener CAE en homologación.
"""

import sys
from datetime import datetime, timedelta
import database as db

# Intentar importar pyafipws
try:
    from pyafipws.wsfev1 import WSFEv1
except ImportError as e:
    print(f"❌ Error al importar pyafipws: {e}")
    print("Instala con: pip install pyafipws")
    sys.exit(1)


def test_arca():
    """Prueba conexión a ARCA y obtiene CAE."""

    print("\n" + "="*70)
    print("TEST DE CONEXIÓN A ARCA - HOMOLOGACIÓN")
    print("="*70 + "\n")

    # Obtener configuración de ARCA
    config = db.obtener_arca_config("compulibra")

    if not config:
        print("❌ Error: No hay configuración ARCA cargada para 'compulibra'")
        print("   Ve a la app → Certificado ARCA → Cargar Certificado")
        return False

    print(f"✓ Configuración encontrada:")
    print(f"  - Empresa: {config['empresa']}")
    print(f"  - CUIT: {config['cuit']}")
    print(f"  - Punto de venta: {config['punto_venta']}")
    print(f"  - Ambiente: {config['ambiente']}")
    print(f"  - Certificado: {config['certificado_path']}")
    print()

    # Verificar que los archivos existan
    import os
    if not os.path.exists(config['clave_path']):
        print(f"❌ Error: Clave privada no encontrada en {config['clave_path']}")
        return False
    if not os.path.exists(config['certificado_path']):
        print(f"❌ Error: Certificado no encontrado en {config['certificado_path']}")
        return False

    print("✓ Archivos de certificado verificados\n")

    # Crear instancia de WSFEv1
    print("Conectando a ARCA...")
    try:
        wsfev1 = WSFEv1()

        # Configurar para homologación (se detecta automáticamente)
        # HOMO = True para homologación

        # Cargar certificado y clave
        wsfev1.Cuit = config['cuit']
        wsfev1.LoadCertificate(config['certificado_path'])
        wsfev1.LoadPrivateKey(config['clave_path'])

        print("✓ Certificado cargado\n")

        # Conectar a WSAA para obtener token
        print("Obteniendo token de WSAA...")
        wsfev1.Authenticate()

        if not wsfev1.Token or not wsfev1.Sign:
            print("❌ Error obteniendo token")
            print(f"   {wsfev1.ErrMsg}")
            return False

        print(f"✓ Token obtenido")
        print(f"  - Token: {wsfev1.Token[:50]}...")
        print(f"  - Sign: {wsfev1.Sign[:50]}...\n")

        # Obtener último número de comprobante
        print("Consultando último número de comprobante...")
        last_number = wsfev1.CompUltimoAutorizado(
            config['punto_venta'],
            1  # Tipo de comprobante: 1 = Factura A
        )

        if not last_number:
            print(f"❌ Error obteniendo último número")
            print(f"   {wsfev1.ErrMsg}")
            return False

        print(f"✓ Último número de factura A: {last_number}\n")

        # Preparar factura de prueba
        print("Preparando factura de prueba...")
        nuevo_numero = int(last_number) + 1
        fecha = datetime.now().strftime("%Y%m%d")

        # Datos de la factura
        factura = {
            "CantReg": 1,
            "PtoVta": config['punto_venta'],
            "CbteTipo": 1,  # Factura A
            "CbteNro": nuevo_numero,
            "CbteFecha": int(fecha),
            "ImpTotal": 100.00,
            "ImpTotConc": 0,
            "ImpNetUnifafip": 0,
            "ImpTaxVat": 21.00,
            "ImpTotOper": 100.00,
            "ImpOpEx": 0,
            "FchVencPago": int(fecha),
            "FchCbte": int(fecha),
            "CUITEmisor": config['cuit'],
            "CUIT": "20000000001",  # CUIT de cliente de prueba
            "IVA": 21,
            "Concepto": 1,
            "DocTipo": 80,  # CUIT
            "DocNro": 20000000001,
        }

        print(f"✓ Factura preparada:")
        print(f"  - Tipo: A")
        print(f"  - Número: {nuevo_numero}")
        print(f"  - Fecha: {fecha}")
        print(f"  - Total: $100.00\n")

        # Solicitar CAE
        print("Solicitando CAE a WSFEV1...")

        # Crear solicitud de factura
        wsfev1.CrearFactura(
            tipo_cbte=factura['CbteTipo'],
            punto_vta=factura['PtoVta'],
            cbte_nro=factura['CbteNro'],
            imp_total=factura['ImpTotal'],
            imp_neto=factura['ImpTotOper'] - factura['ImpTaxVat'],
            imp_iva=factura['ImpTaxVat'],
            imp_otros_tributos=0,
            fecha_cbte=factura['FchCbte'],
            fecha_venc_pago=factura['FchVencPago'],
            tipo_doc=factura['DocTipo'],
            nro_doc=factura['DocNro'],
            concepto=factura['Concepto'],
            tipo_expo=0
        )

        # Agregar IVA
        wsfev1.AgregarIVA(
            alicuota=21.00,
            base_imponible=factura['ImpTotOper'] - factura['ImpTaxVat']
        )

        # Autorizar (FECAESolicitar)
        cae = wsfev1.CAESolicitar()

        if not cae:
            print(f"❌ Error obteniendo CAE")
            print(f"   Error: {wsfev1.ErrMsg}")
            print(f"   Código: {wsfev1.ErrCode}")
            if hasattr(wsfev1, 'Errores') and wsfev1.Errores:
                for error in wsfev1.Errores:
                    print(f"   - {error}")
            return False

        vto_cae = wsfev1.VtoCAE if hasattr(wsfev1, 'VtoCAE') else "Sin info"
        print(f"✅ CAE OBTENIDO: {cae}")
        print(f"✓ Vencimiento: {vto_cae}\n")

        print("="*70)
        print("✅ TEST EXITOSO - CONEXIÓN A ARCA VERIFICADA")
        print("="*70)
        print(f"\nAhora estás listo para integrar facturación en la app.\n")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import os
    # Asegurarse de estar en el directorio correcto
    os.chdir(os.path.dirname(__file__))

    # Inicializar BD
    db.init_db()

    # Ejecutar test
    éxito = test_arca()
    sys.exit(0 if éxito else 1)

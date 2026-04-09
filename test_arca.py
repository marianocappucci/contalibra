#!/usr/bin/env python3
"""
Script de prueba para conectar a ARCA y obtener CAE en homologación.
"""

import sys
import os
from datetime import datetime
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
    if not os.path.exists(config['clave_path']):
        print(f"❌ Error: Clave privada no encontrada en {config['clave_path']}")
        return False
    if not os.path.exists(config['certificado_path']):
        print(f"❌ Error: Certificado no encontrado en {config['certificado_path']}")
        return False

    print("✓ Archivos de certificado verificados\n")

    # Crear instancia de WSFEv1
    print("Creando instancia de WSFEv1...")
    try:
        wsfev1 = WSFEv1()

        # Configurar CUIT
        wsfev1.Cuit = config['cuit']

        # Conectar (homologación por defecto en pyafipws)
        print("Conectando a WSAA (homologación)...")
        wsfev1.Conectar(
            cache="",
            wsdl=None,
            proxy="",
            wrapper=None,
            cacert=None,
            timeout=30,
            soap_server=None
        )

        # Cargar certificado y clave
        print("Cargando certificado...")
        wsfev1.SetCertificate(config['certificado_path'])
        wsfev1.SetPrivateKey(config['clave_path'])

        print("✓ Certificado cargado\n")

        # Autenticar
        print("Obteniendo token de WSAA...")
        ta = wsfev1.Autenticar()

        if not ta:
            print(f"❌ Error en autenticación")
            print(f"   Error: {wsfev1.ErrMsg}")
            print(f"   Código: {wsfev1.ErrCode}")
            return False

        print(f"✓ Token obtenido")
        print(f"  - Token: {wsfev1.Token[:50]}..." if wsfev1.Token else "  - Token: No disponible")
        print()

        # Obtener último número de comprobante
        print("Consultando último número de comprobante...")
        last_number = wsfev1.CompUltimoAutorizado(
            config['punto_venta'],
            1  # Tipo de comprobante: 1 = Factura A
        )

        if not last_number:
            print(f"❌ Error obteniendo último número")
            print(f"   Error: {wsfev1.ErrMsg}")
            return False

        print(f"✓ Último número de factura A: {last_number}\n")

        # Preparar factura de prueba
        print("Preparando factura de prueba...")
        nuevo_numero = int(last_number) + 1
        fecha = datetime.now().strftime("%Y%m%d")

        print(f"✓ Factura preparada:")
        print(f"  - Tipo: A (responsable inscripto)")
        print(f"  - Número: {nuevo_numero}")
        print(f"  - Punto de venta: {config['punto_venta']}")
        print(f"  - Fecha: {fecha}")
        print(f"  - Total: $100.00\n")

        # Crear factura
        print("Creando factura...")
        wsfev1.CrearFactura(
            tipo_cbte=1,  # Factura A
            punto_vta=config['punto_venta'],
            cbte_nro=nuevo_numero,
            imp_total=100.00,
            imp_neto=82.64,
            imp_iva=17.36,
            imp_otros_tributos=0,
            fecha_cbte=int(fecha),
            fecha_venc_pago=int(fecha),
            tipo_doc=80,  # CUIT
            nro_doc=20000000001,  # Cliente de prueba
            concepto=1,  # Productos
            tipo_expo=0
        )

        # Agregar IVA (21%)
        print("Agregando IVA...")
        wsfev1.AgregarIVA(
            alicuota=21.0,
            base_imponible=82.64
        )

        # Solicitar CAE
        print("Solicitando CAE a WSFEV1...\n")
        cae = wsfev1.CAESolicitar()

        if not cae:
            print(f"❌ Error obteniendo CAE")
            print(f"   Error: {wsfev1.ErrMsg}")
            print(f"   Código: {wsfev1.ErrCode}")
            if hasattr(wsfev1, 'Errores') and wsfev1.Errores:
                print(f"   Detalles:")
                for error in wsfev1.Errores:
                    print(f"     - {error}")
            return False

        vto_cae = wsfev1.VtoCAE if hasattr(wsfev1, 'VtoCAE') else "Sin info"

        print("="*70)
        print("✅ CAE OBTENIDO EXITOSAMENTE")
        print("="*70)
        print(f"CAE: {cae}")
        print(f"Vencimiento: {vto_cae}")
        print()
        print("✓ Conexión a ARCA verificada correctamente")
        print("✓ Certificado funciona correctamente")
        print()
        print("Ahora estás listo para integrar facturación en la app.\n")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Asegurarse de estar en el directorio correcto
    os.chdir(os.path.dirname(__file__))

    # Inicializar BD
    db.init_db()

    # Ejecutar test
    éxito = test_arca()
    sys.exit(0 if éxito else 1)

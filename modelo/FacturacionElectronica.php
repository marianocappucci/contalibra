<?php
/**
 * IMPORTANTE: Este es un stub/simulación de facturación electrónica.
 * Para usar AFIP u otro ente fiscal real se deben implementar los
 * webservices oficiales, certificados, CUIT, punto de venta, etc.
 */
class FacturacionElectronica extends BaseModel {

    public function enviarAFiscal($venta) {
        // Simula la respuesta de un webservice de AFIP
        // No es válido para producción, solo modo demo.
        $cae = 'SIM' . str_pad($venta['id'], 10, '0', STR_PAD_LEFT);
        $fecha_vto = date('Ymd', strtotime('+10 days'));

        $stmt = $this->db->prepare("UPDATE ventas SET estado='FACTURADA', cae=?, cae_vencimiento=? WHERE id=?");
        $stmt->execute([$cae, $fecha_vto, $venta['id']]);

        return [
            'resultado' => 'A',
            'cae' => $cae,
            'cae_vencimiento' => $fecha_vto
        ];
    }
}

import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './context/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Clientes } from './pages/Clientes'
import { ClienteForm } from './pages/ClienteForm'
import { ClienteDetalle } from './pages/ClienteDetalle'
import { Productos } from './pages/Productos'
import { ProductoForm } from './pages/ProductoForm'
import { ListasPrecio } from './pages/ListasPrecio'
import { ListaPrecioNueva } from './pages/ListaPrecioNueva'
import { ListaPrecioDetalle } from './pages/ListaPrecioDetalle'
import { Proveedores } from './pages/Proveedores'
import { ProveedorForm } from './pages/ProveedorForm'
import { ProveedorDetalle } from './pages/ProveedorDetalle'
import { Egresos } from './pages/Egresos'
import { EgresoNuevo } from './pages/EgresoNuevo'
import { EgresoDetalle } from './pages/EgresoDetalle'
import { Usuarios } from './pages/Usuarios'
import { UsuarioForm } from './pages/UsuarioForm'
import { Config } from './pages/Config'
import { Depositos } from './pages/Depositos'
import { DepositoForm } from './pages/DepositoForm'
import { DepositoDetalle } from './pages/DepositoDetalle'
import { DepositoTransferencia } from './pages/DepositoTransferencia'
import { Stock } from './pages/Stock'
import { CuentaCorriente } from './pages/CuentaCorriente'
import { CuentaCorrienteDetalle } from './pages/CuentaCorrienteDetalle'
import { Tesoreria } from './pages/Tesoreria'
import { TesoreriaCuentaForm } from './pages/TesoreriaCuentaForm'
import { TesoreriaDetalle } from './pages/TesoreriaDetalle'
import { Caja } from './pages/Caja'
import { CajaNueva } from './pages/CajaNueva'
import { Cajas } from './pages/Cajas'
import { CajaForm } from './pages/CajaForm'
import { Turnos } from './pages/Turnos'
import { TurnoAbrir } from './pages/TurnoAbrir'
import { TurnoDetalle } from './pages/TurnoDetalle'
import { TurnoCerrar } from './pages/TurnoCerrar'
import { Ventas } from './pages/Ventas'
import { VentaNueva } from './pages/VentaNueva'
import { VentaDetalle } from './pages/VentaDetalle'
import { Facturas } from './pages/Facturas'
import { FacturaNueva } from './pages/FacturaNueva'
import { FacturaDetalle } from './pages/FacturaDetalle'
import { Remitos } from './pages/Remitos'
import { RemitoNuevo } from './pages/RemitoNuevo'
import { RemitoDetalle } from './pages/RemitoDetalle'
import { Presupuestos } from './pages/Presupuestos'
import { PresupuestoForm } from './pages/PresupuestoForm'
import { PresupuestoDetalle } from './pages/PresupuestoDetalle'
import { MpBandeja } from './pages/MpBandeja'
import { LibrosIva } from './pages/LibrosIva'
import { Reportes } from './pages/Reportes'
import { CajaMedios } from './pages/CajaMedios'
import { Logs } from './pages/Logs'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">
        Cargando…
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clientes"
        element={
          <ProtectedRoute>
            <Clientes />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clientes/nuevo"
        element={
          <ProtectedRoute>
            <ClienteForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clientes/:id/editar"
        element={
          <ProtectedRoute>
            <ClienteForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clientes/:id"
        element={
          <ProtectedRoute>
            <ClienteDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/productos"
        element={
          <ProtectedRoute>
            <Productos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/productos/nuevo"
        element={
          <ProtectedRoute>
            <ProductoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/productos/:id/editar"
        element={
          <ProtectedRoute>
            <ProductoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listas-precio"
        element={
          <ProtectedRoute>
            <ListasPrecio />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listas-precio/nueva"
        element={
          <ProtectedRoute>
            <ListaPrecioNueva />
          </ProtectedRoute>
        }
      />
      <Route
        path="/listas-precio/:id"
        element={
          <ProtectedRoute>
            <ListaPrecioDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/proveedores"
        element={
          <ProtectedRoute>
            <Proveedores />
          </ProtectedRoute>
        }
      />
      <Route
        path="/proveedores/nuevo"
        element={
          <ProtectedRoute>
            <ProveedorForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/proveedores/:id/editar"
        element={
          <ProtectedRoute>
            <ProveedorForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/proveedores/:id"
        element={
          <ProtectedRoute>
            <ProveedorDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/egresos"
        element={
          <ProtectedRoute>
            <Egresos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/egresos/nuevo"
        element={
          <ProtectedRoute>
            <EgresoNuevo />
          </ProtectedRoute>
        }
      />
      <Route
        path="/egresos/:id"
        element={
          <ProtectedRoute>
            <EgresoDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios"
        element={
          <ProtectedRoute>
            <Usuarios />
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios/nuevo"
        element={
          <ProtectedRoute>
            <UsuarioForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios/:id/editar"
        element={
          <ProtectedRoute>
            <UsuarioForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/config"
        element={
          <ProtectedRoute>
            <Config />
          </ProtectedRoute>
        }
      />
      <Route
        path="/depositos"
        element={
          <ProtectedRoute>
            <Depositos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/depositos/nuevo"
        element={
          <ProtectedRoute>
            <DepositoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/depositos/transferencia"
        element={
          <ProtectedRoute>
            <DepositoTransferencia />
          </ProtectedRoute>
        }
      />
      <Route
        path="/depositos/:id/editar"
        element={
          <ProtectedRoute>
            <DepositoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/depositos/:id"
        element={
          <ProtectedRoute>
            <DepositoDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/stock"
        element={
          <ProtectedRoute>
            <Stock />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cuenta-corriente"
        element={
          <ProtectedRoute>
            <CuentaCorriente />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cuenta-corriente/:id"
        element={
          <ProtectedRoute>
            <CuentaCorrienteDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tesoreria"
        element={
          <ProtectedRoute>
            <Tesoreria />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tesoreria/nueva-cuenta"
        element={
          <ProtectedRoute>
            <TesoreriaCuentaForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tesoreria/:id/editar"
        element={
          <ProtectedRoute>
            <TesoreriaCuentaForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tesoreria/:id"
        element={
          <ProtectedRoute>
            <TesoreriaDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/caja"
        element={
          <ProtectedRoute>
            <Caja />
          </ProtectedRoute>
        }
      />
      <Route
        path="/caja/nuevo"
        element={
          <ProtectedRoute>
            <CajaNueva />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cajas"
        element={
          <ProtectedRoute>
            <Cajas />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cajas/nueva"
        element={
          <ProtectedRoute>
            <CajaForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cajas/:id/editar"
        element={
          <ProtectedRoute>
            <CajaForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/turnos"
        element={
          <ProtectedRoute>
            <Turnos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/turnos/abrir"
        element={
          <ProtectedRoute>
            <TurnoAbrir />
          </ProtectedRoute>
        }
      />
      <Route
        path="/turnos/:id/cerrar"
        element={
          <ProtectedRoute>
            <TurnoCerrar />
          </ProtectedRoute>
        }
      />
      <Route
        path="/turnos/:id"
        element={
          <ProtectedRoute>
            <TurnoDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ventas"
        element={
          <ProtectedRoute>
            <Ventas />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ventas/nueva"
        element={
          <ProtectedRoute>
            <VentaNueva />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ventas/:id"
        element={
          <ProtectedRoute>
            <VentaDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/facturas"
        element={
          <ProtectedRoute>
            <Facturas />
          </ProtectedRoute>
        }
      />
      <Route
        path="/facturas/nueva"
        element={
          <ProtectedRoute>
            <FacturaNueva />
          </ProtectedRoute>
        }
      />
      <Route
        path="/facturas/:id"
        element={
          <ProtectedRoute>
            <FacturaDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/remitos"
        element={
          <ProtectedRoute>
            <Remitos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/remitos/nuevo"
        element={
          <ProtectedRoute>
            <RemitoNuevo />
          </ProtectedRoute>
        }
      />
      <Route
        path="/remitos/:id"
        element={
          <ProtectedRoute>
            <RemitoDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/presupuestos"
        element={
          <ProtectedRoute>
            <Presupuestos />
          </ProtectedRoute>
        }
      />
      <Route
        path="/presupuestos/nuevo"
        element={
          <ProtectedRoute>
            <PresupuestoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/presupuestos/:id/editar"
        element={
          <ProtectedRoute>
            <PresupuestoForm />
          </ProtectedRoute>
        }
      />
      <Route
        path="/presupuestos/:id"
        element={
          <ProtectedRoute>
            <PresupuestoDetalle />
          </ProtectedRoute>
        }
      />
      <Route
        path="/mp-bandeja"
        element={
          <ProtectedRoute>
            <MpBandeja />
          </ProtectedRoute>
        }
      />
      <Route
        path="/libros-iva"
        element={
          <ProtectedRoute>
            <LibrosIva />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reportes"
        element={
          <ProtectedRoute>
            <Reportes />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reportes/caja-medios"
        element={
          <ProtectedRoute>
            <CajaMedios />
          </ProtectedRoute>
        }
      />
      <Route
        path="/logs"
        element={
          <ProtectedRoute>
            <Logs />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

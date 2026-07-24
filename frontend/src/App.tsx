import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './context/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Clientes } from './pages/Clientes'
import { Productos } from './pages/Productos'
import { ListasPrecio } from './pages/ListasPrecio'
import { Proveedores } from './pages/Proveedores'
import { Egresos } from './pages/Egresos'
import { Usuarios } from './pages/Usuarios'
import { Config } from './pages/Config'
import { Depositos } from './pages/Depositos'
import { Stock } from './pages/Stock'
import { CuentaCorriente } from './pages/CuentaCorriente'
import { Tesoreria } from './pages/Tesoreria'
import { Caja } from './pages/Caja'
import { Cajas } from './pages/Cajas'
import { Turnos } from './pages/Turnos'
import { Ventas } from './pages/Ventas'
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
        path="/productos"
        element={
          <ProtectedRoute>
            <Productos />
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
        path="/proveedores"
        element={
          <ProtectedRoute>
            <Proveedores />
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
        path="/usuarios"
        element={
          <ProtectedRoute>
            <Usuarios />
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
        path="/tesoreria"
        element={
          <ProtectedRoute>
            <Tesoreria />
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
        path="/cajas"
        element={
          <ProtectedRoute>
            <Cajas />
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
        path="/ventas"
        element={
          <ProtectedRoute>
            <Ventas />
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

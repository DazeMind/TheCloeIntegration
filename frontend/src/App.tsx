import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import EmitirBoleta from './pages/EmitirBoleta'
import Consulta from './pages/Consulta'
import Configuracion from './pages/Configuracion'
import Reportes from './pages/Reportes'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="emitir" element={<EmitirBoleta />} />
          <Route path="consulta" element={<Consulta />} />
          <Route path="configuracion" element={<Configuracion />} />
          <Route path="reportes" element={<Reportes />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

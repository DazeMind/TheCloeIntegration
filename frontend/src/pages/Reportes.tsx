import { useState, useEffect } from 'react'
import client from '../api/client'

export default function Reportes() {
  const [datos, setDatos] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    cargarReporte()
  }, [])

  const cargarReporte = async () => {
    try {
      const res = await client.get('/reportes/resumen/')
      setDatos(res.data)
    } catch (err) {
      // Fallback: intentar desde el endpoint de integraciones
      try {
        const [resumen, estado] = await Promise.all([
          client.get('/integraciones/reportes/'),
          client.get('/integraciones/estado-circuito/'),
        ])
        setDatos(resumen.data)
      } catch (err2) {
        setError('Error al cargar reportes')
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="text-gray-500">Cargando reportes...</div>
  if (error) return <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">{error}</div>
  if (!datos) return null

  const stats = [
    { label: 'Total Emisiones', value: datos.total_emisiones, icon: '📄', color: 'blue' },
    { label: 'Emitidos', value: datos.emitidos, icon: '✅', color: 'green' },
    { label: 'Rechazados', value: datos.rechazados, icon: '❌', color: 'red' },
    { label: 'Pendientes', value: datos.pendientes, icon: '⏳', color: 'yellow' },
    { label: 'Monto Total', value: `$${(datos.monto_total || 0).toLocaleString()}`, icon: '💰', color: 'purple' },
    { label: 'Estado Circuit Breaker', value: datos.estado_circuit_breaker || 'N/A', icon: '🔌', color: datos.estado_circuit_breaker === 'CLOSED' ? 'green' : 'red' },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Reportes</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">{stat.label}</span>
              <span className="text-2xl">{stat.icon}</span>
            </div>
            <p className={`text-3xl font-bold mt-3 text-${stat.color}-600`}>{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">Estado del Circuit Breaker</h3>
        <div className="bg-gray-50 p-4 rounded-lg">
          <p>Estado actual: <span className={`font-bold ${datos.estado_circuit_breaker === 'CLOSED' ? 'text-green-600' : 'text-red-600'}`}>{datos.estado_circuit_breaker}</span></p>
          {datos.fallas_acumuladas !== undefined && (
            <p>Fallas acumuladas: {datos.fallas_acumuladas}</p>
          )}
        </div>
      </div>
    </div>
  )
}

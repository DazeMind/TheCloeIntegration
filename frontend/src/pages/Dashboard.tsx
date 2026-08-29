import { useState, useEffect } from 'react'
import client from '../api/client'

interface Resumen {
  total_emisiones: number
  emitidos: number
  rechazados: number
  pendientes: number
  monto_total: number
  tasa_exito: number
  ultimos_7_dias: number
  ultimos_30_dias: number
}

export default function Dashboard() {
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/reportes/resumen/')
      .then((res) => {
        // Si la respuesta es un array (ViewSet list), tomar el primer elemento o buscar el resumen
        setResumen(res.data)
        setLoading(false)
      })
      .catch((err) => {
        setError('Error al cargar el resumen')
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="text-gray-500">Cargando...</div>
  if (error) return <div className="text-red-500">{error}</div>
  if (!resumen) return null

  const stats = [
    { label: 'Total Emisiones', value: resumen.total_emisiones, color: 'blue' },
    { label: 'Emitidos', value: resumen.emitidos, color: 'green' },
    { label: 'Rechazados', value: resumen.rechazados, color: 'red' },
    { label: 'Pendientes', value: resumen.pendientes, color: 'yellow' },
    { label: 'Monto Total', value: `$${resumen.monto_total.toLocaleString()}`, color: 'purple' },
    { label: 'Tasa Éxito', value: `${resumen.tasa_exito}%`, color: 'indigo' },
    { label: 'Últimos 7 días', value: resumen.ultimos_7_dias, color: 'teal' },
    { label: 'Últimos 30 días', value: resumen.ultimos_30_dias, color: 'orange' },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-bold mt-2 text-${stat.color}-600`}>{stat.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

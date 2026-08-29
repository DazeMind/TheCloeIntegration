import { useState } from 'react'
import client from '../api/client'

interface Documento {
  id: number
  id_venta: string
  folio: number | null
  tipo_documento: number
  estado: string
  respuesta_sii: any
  mensaje_error: string | null
  monto_total: number | null
  fecha_creacion: string
  fecha_actualizacion: string
}

export default function Consulta() {
  const [idVenta, setIdVenta] = useState('')
  const [documento, setDocumento] = useState<Documento | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const buscar = async () => {
    if (!idVenta.trim()) return
    setLoading(true)
    setError('')
    setDocumento(null)

    try {
      const res = await client.get(`/integraciones/consulta/${idVenta.trim()}/`)
      setDocumento(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se encontró el documento')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Consultar Documento</h2>
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={idVenta}
            onChange={(e) => setIdVenta(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && buscar()}
            className="flex-1 border rounded-lg px-4 py-2"
            placeholder="ID de venta (ej: V-2026-08-001)"
          />
          <button
            onClick={buscar}
            disabled={loading}
            className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">{error}</div>
      )}

      {documento && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">Resultado</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">ID Venta</p>
              <p className="font-medium">{documento.id_venta}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">Folio SII</p>
              <p className="font-medium">{documento.folio ?? 'N/A'}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">Estado</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                documento.estado === 'EMITIDO' ? 'bg-green-100 text-green-800' :
                documento.estado === 'RECHAZADO' ? 'bg-red-100 text-red-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {documento.estado}
              </span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">Monto Total</p>
              <p className="font-medium">${documento.monto_total?.toLocaleString() ?? 'N/A'}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg col-span-2">
              <p className="text-sm text-gray-500">Fecha de Creación</p>
              <p className="font-medium">{new Date(documento.fecha_creacion).toLocaleString('es-Cl')}</p>
            </div>
          </div>

          {documento.mensaje_error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">
              <strong>Error:</strong> {documento.mensaje_error}
            </div>
          )}

          {documento.respuesta_sii && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                Ver respuesta completa del SII
              </summary>
              <pre className="mt-2 bg-gray-100 p-4 rounded-lg text-xs overflow-auto">
                {JSON.stringify(documento.respuesta_sii, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

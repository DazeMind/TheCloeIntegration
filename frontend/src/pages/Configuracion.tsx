import { useState, useEffect } from 'react'
import client from '../api/client'

interface Credencial {
  id: number
  nombre: string
  api_key: string
  base_url: string
  activa: boolean
}

interface Config {
  id: number
  empresa: string
  timbrado: string
  prefijo_folio: string
  ambiente: string
  activa: boolean
}

export default function Configuracion() {
  const [credenciales, setCredenciales] = useState<Credencial[]>([])
  const [configuracion, setConfiguracion] = useState<Config | null>(null)
  const [nuevaCredencial, setNuevaCredencial] = useState({ nombre: '', api_key: '', base_url: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    try {
      const [credRes, confRes] = await Promise.all([
        client.get('/credenciales/'),
        client.get('/configuracion/'),
      ])
      setCredenciales(credRes.data)
      setConfiguracion(confRes.data?.[0] || null)
    } catch (err) {
      setError('Error al cargar configuración')
    } finally {
      setLoading(false)
    }
  }

  const agregarCredencial = async () => {
    try {
      await client.post('/credenciales/', nuevaCredencial)
      setNuevaCredencial({ nombre: '', api_key: '', base_url: '' })
      cargarDatos()
    } catch (err: any) {
      setError(err.response?.data || 'Error al agregar credencial')
    }
  }

  const toggleActiva = async (id: number, activa: boolean) => {
    try {
      await client.patch(`/credenciales/${id}/`, { activa: !activa })
      cargarDatos()
    } catch (err: any) {
      setError('Error al actualizar credencial')
    }
  }

  if (loading) return <div className="text-gray-500">Cargando...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Configuración</h2>
      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">{error}</div>}

      {/* Configuración de la integración */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-bold mb-4">Configuración de Integración</h3>
        {configuracion ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Empresa</p>
              <p className="font-medium">{configuracion.empresa}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Ambiente</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                configuracion.ambiente === 'produccion' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              }`}>
                {configuracion.ambiente}
              </span>
            </div>
            <div>
              <p className="text-sm text-gray-500">Timbrado</p>
              <p className="font-medium">{configuracion.timbrado || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Prefijo Folio</p>
              <p className="font-medium">{configuracion.prefijo_folio}</p>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">Sin configuración activa</p>
        )}
      </div>

      {/* Credenciales */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">Credenciales SimpleAPI</h3>
        <div className="space-y-3 mb-6">
          {credenciales.map((cred) => (
            <div key={cred.id} className="flex justify-between items-center bg-gray-50 p-4 rounded-lg">
              <div>
                <p className="font-medium">{cred.nombre}</p>
                <p className="text-sm text-gray-500">API: {cred.api_key.slice(0, 4)}...{cred.api_key.slice(-4)}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-sm px-2 py-1 rounded ${cred.activa ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                  {cred.activa ? 'Activa' : 'Inactiva'}
                </span>
                <button
                  onClick={() => toggleActiva(cred.id, cred.activa)}
                  className={`text-sm px-3 py-1 rounded ${cred.activa ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}
                >
                  {cred.activa ? 'Desactivar' : 'Activar'}
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="border-t pt-4">
          <h4 className="font-medium mb-3">Agregar nueva credencial</h4>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Nombre"
              value={nuevaCredencial.nombre}
              onChange={(e) => setNuevaCredencial({ ...nuevaCredencial, nombre: e.target.value })}
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="password"
              placeholder="API Key"
              value={nuevaCredencial.api_key}
              onChange={(e) => setNuevaCredencial({ ...nuevaCredencial, api_key: e.target.value })}
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="url"
              placeholder="Base URL"
              value={nuevaCredencial.base_url}
              onChange={(e) => setNuevaCredencial({ ...nuevaCredencial, base_url: e.target.value })}
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <button
              onClick={agregarCredencial}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
            >
              Guardar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

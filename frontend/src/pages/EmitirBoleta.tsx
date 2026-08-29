import { useState } from 'react'
import client from '../api/client'

interface Item {
  nombre_producto: string
  cantidad: number
  precio_unitario: number
}

interface Response {
  id_venta: string
  folio: number | null
  estado: string
  monto_total: number
  message: string
}

export default function EmitirBoleta() {
  const [idVenta, setIdVenta] = useState('')
  const [items, setItems] = useState<Item[]>([{ nombre_producto: '', cantidad: 1, precio_unitario: 0 }])
  const [resultado, setResultado] = useState<Response | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const agregarItem = () => {
    setItems([...items, { nombre_producto: '', cantidad: 1, precio_unitario: 0 }])
  }

  const actualizarItem = (index: number, campo: keyof Item, valor: string | number) => {
    const nuevos = [...items]
    nuevos[index] = { ...nuevos[index], [campo]: valor }
    setItems(nuevos)
  }

  const eliminarItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResultado(null)

    try {
      const res = await client.post('/integraciones/emitir-boleta/', {
        id_venta: idVenta,
        items: items.filter((item) => item.nombre_producto.trim() !== ''),
      })
      setResultado(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al emitir boleta')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Emitir Boleta Electrónica</h2>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">ID de Venta</label>
          <input
            type="text"
            value={idVenta}
            onChange={(e) => setIdVenta(e.target.value)}
            className="w-full border rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="Ej: V-2026-08-001"
            required
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium">Items</label>
            <button type="button" onClick={agregarItem} className="text-sm text-primary-600 hover:text-primary-800">
              + Agregar Item
            </button>
          </div>
          <div className="space-y-3">
            {items.map((item, index) => (
              <div key={index} className="flex gap-3 items-start">
                <input
                  type="text"
                  placeholder="Nombre del producto"
                  value={item.nombre_producto}
                  onChange={(e) => actualizarItem(index, 'nombre_producto', e.target.value)}
                  className="flex-1 border rounded-lg px-3 py-2 text-sm"
                  required
                />
                <input
                  type="number"
                  placeholder="Cantidad"
                  value={item.cantidad}
                  onChange={(e) => actualizarItem(index, 'cantidad', Number(e.target.value))}
                  className="w-24 border rounded-lg px-3 py-2 text-sm"
                  min={1}
                  required
                />
                <input
                  type="number"
                  placeholder="Precio unit."
                  value={item.precio_unitario}
                  onChange={(e) => actualizarItem(index, 'precio_unitario', Number(e.target.value))}
                  className="w-32 border rounded-lg px-3 py-2 text-sm"
                  min={0}
                  step="0.01"
                  required
                />
                <button type="button" onClick={() => eliminarItem(index)} className="text-red-500 hover:text-red-700 text-sm mt-6">
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary-600 text-white py-3 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Emitiendo...' : 'Emitir Boleta'}
        </button>
      </form>

      {error && (
        <div className="mt-6 bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">
          {error}
        </div>
      )}

      {resultado && (
        <div className="mt-6 bg-green-50 border border-green-200 text-green-700 rounded-lg p-6">
          <h3 className="font-bold text-lg mb-2">✅ {resultado.message}</h3>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <p className="text-sm text-gray-600">ID Venta</p>
              <p className="font-medium">{resultado.id_venta}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Folio SII</p>
              <p className="font-medium">{resultado.folio ?? 'Pendiente'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Estado</p>
              <p className="font-medium">{resultado.estado}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Monto Total</p>
              <p className="font-medium">${resultado.monto_total.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

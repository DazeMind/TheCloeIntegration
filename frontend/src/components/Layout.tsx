import { NavLink } from 'react-router-dom'

const navLinks = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/emitir', label: 'Emitir Boleta', icon: '📄' },
  { to: '/consulta', label: 'Consulta', icon: '🔍' },
  { to: '/reportes', label: 'Reportes', icon: '📈' },
  { to: '/configuracion', label: 'Configuración', icon: '⚙️' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6 border-b border-gray-700">
          <h1 className="text-xl font-bold">The Cloe</h1>
          <p className="text-sm text-gray-400">Integración Tributaria</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <span className="text-lg">{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-700">
          <p className="text-xs text-gray-500">SII / SimpleAPI</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  )
}

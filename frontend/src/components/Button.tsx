interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
}

export default function Button({ variant = 'primary', className = '', children, ...props }: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50'
  const variantStyles = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }

  return (
    <button className={`${baseStyles} ${variantStyles[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

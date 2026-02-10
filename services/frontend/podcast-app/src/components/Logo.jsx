import { useNavigate } from 'react-router-dom'

function Logo({ className = '', size = 'default' }) {
  const navigate = useNavigate()

  const sizes = {
    small: 'text-xl',
    default: 'text-2xl',
    large: 'text-3xl'
  }

  return (
    <button
      onClick={() => navigate('/podcast')}
      className={`font-bold text-primary-pink hover:text-pink-400 transition-colors ${sizes[size]} ${className}`}
      style={{
        background: 'linear-gradient(90deg, #FF3B9A 0%, #FF6BB5 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text'
      }}
    >
      NewsJuice
    </button>
  )
}

export default Logo

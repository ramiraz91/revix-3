import { cn } from '@/lib/utils';

// Configuración de calidades de pantalla
const CALIDAD_CONFIG = {
  genuine: {
    label: 'Genuine',
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-800',
    borderColor: 'border-amber-300',
    icon: '⭐',
  },
  refurbished_genuine: {
    label: 'Refurb',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-300',
    icon: '🔄',
  },
  soft_oled: {
    label: 'Soft OLED',
    bgColor: 'bg-emerald-100',
    textColor: 'text-emerald-800',
    borderColor: 'border-emerald-300',
    icon: '✨',
  },
  hard_oled: {
    label: 'Hard OLED',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
    borderColor: 'border-blue-300',
    icon: '💎',
  },
  service_pack: {
    label: 'Service Pack',
    bgColor: 'bg-teal-100',
    textColor: 'text-teal-800',
    borderColor: 'border-teal-300',
    icon: '🏭',
  },
  oled: {
    label: 'OLED',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-800',
    borderColor: 'border-purple-300',
    icon: '📱',
  },
  incell: {
    label: 'InCell',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-800',
    borderColor: 'border-orange-300',
    icon: '📟',
  },
  desconocido: {
    label: 'Sin clasificar',
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-600',
    borderColor: 'border-slate-300',
    icon: '❓',
  },
};

/**
 * Badge que muestra la calidad de una pantalla
 */
export function CalidadPantallaBadge({ 
  calidad, 
  showIcon = true, 
  size = 'sm',
  className = '' 
}) {
  if (!calidad) return null;
  
  const config = CALIDAD_CONFIG[calidad] || CALIDAD_CONFIG.desconocido;
  
  const sizeClasses = {
    xs: 'text-[10px] px-1.5 py-0.5',
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };
  
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        config.bgColor,
        config.textColor,
        config.borderColor,
        sizeClasses[size] || sizeClasses.sm,
        className
      )}
      data-testid={`calidad-badge-${calidad}`}
    >
      {showIcon && <span className="text-[0.9em]">{config.icon}</span>}
      {config.label}
    </span>
  );
}

/**
 * Lista de todas las calidades disponibles para selector
 */
export function getCalidadesDisponibles() {
  return Object.entries(CALIDAD_CONFIG).map(([key, config]) => ({
    value: key,
    label: config.label,
    icon: config.icon,
  }));
}

/**
 * Selector de calidad de pantalla
 */
export function CalidadPantallaSelector({ 
  value, 
  onChange, 
  disabled = false,
  className = '' 
}) {
  const calidades = getCalidadesDisponibles().filter(c => c.value !== 'desconocido');
  
  return (
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={cn(
        'rounded-md border border-input bg-background px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
      data-testid="calidad-pantalla-selector"
    >
      <option value="">Seleccionar calidad...</option>
      {calidades.map((c) => (
        <option key={c.value} value={c.value}>
          {c.icon} {c.label}
        </option>
      ))}
    </select>
  );
}

export { CALIDAD_CONFIG };
export default CalidadPantallaBadge;

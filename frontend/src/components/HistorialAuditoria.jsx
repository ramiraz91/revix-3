import React, { useState, useEffect } from 'react';
import { History, User, Clock, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { auditoriaAPI } from '../lib/api';

const HistorialAuditoria = ({ entidad, entidadId }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const cargarLogs = async () => {
      try {
        const res = await auditoriaAPI.porEntidad(entidad, entidadId);
        setLogs(res.data || []);
      } catch (error) {
        console.error('Error cargando historial de auditoría:', error);
      } finally {
        setLoading(false);
      }
    };

    if (entidadId) {
      cargarLogs();
    }
  }, [entidad, entidadId]);

  const getAccionColor = (accion) => {
    switch (accion) {
      case 'crear': return 'bg-green-500/20 text-green-400';
      case 'cambiar_estado': return 'bg-blue-500/20 text-blue-400';
      case 'actualizar': return 'bg-yellow-500/20 text-yellow-400';
      case 'eliminar': return 'bg-red-500/20 text-red-400';
      case 'autorizar': return 'bg-purple-500/20 text-purple-400';
      case 'rechazar': return 'bg-orange-500/20 text-orange-400';
      case 'subir_evidencia': return 'bg-cyan-500/20 text-cyan-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  const getAccionLabel = (accion) => {
    const labels = {
      'crear': 'Creación',
      'cambiar_estado': 'Cambio de estado',
      'actualizar': 'Actualización',
      'eliminar': 'Eliminación',
      'autorizar': 'Autorización',
      'rechazar': 'Rechazo',
      'subir_evidencia': 'Evidencia subida',
      'añadir_material': 'Material añadido',
      'aprobar_material': 'Material aprobado'
    };
    return labels[accion] || accion;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderCambios = (cambios) => {
    if (!cambios || Object.keys(cambios).length === 0) return null;

    return (
      <div className="mt-2 pl-4 border-l-2 border-slate-600 space-y-1">
        {Object.entries(cambios).map(([key, value]) => (
          <div key={key} className="text-xs">
            <span className="text-slate-500">{key}:</span>{' '}
            {typeof value === 'object' && value !== null ? (
              value.antes !== undefined ? (
                <span>
                  <span className="text-red-400 line-through">{String(value.antes)}</span>
                  {' → '}
                  <span className="text-green-400">{String(value.despues)}</span>
                </span>
              ) : (
                <span className="text-slate-300">{JSON.stringify(value)}</span>
              )
            ) : (
              <span className="text-slate-300">{String(value)}</span>
            )}
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="text-slate-400 text-sm flex items-center gap-2">
        <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
        Cargando historial...
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="text-slate-500 text-sm flex items-center gap-2">
        <History className="w-4 h-4" />
        Sin historial de auditoría
      </div>
    );
  }

  const visibleLogs = expanded ? logs : logs.slice(0, 3);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <History className="w-4 h-4" />
          Historial de Cambios
        </h4>
        {logs.length > 3 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-slate-400"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3 h-3 mr-1" />
                Ver menos
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3 mr-1" />
                Ver todos ({logs.length})
              </>
            )}
          </Button>
        )}
      </div>

      <div className="space-y-2">
        {visibleLogs.map((log) => (
          <div
            key={log.id}
            className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className={getAccionColor(log.accion)}>
                    {getAccionLabel(log.accion)}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {log.usuario_email || 'Sistema'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(log.created_at)}
                  </span>
                </div>
                {renderCambios(log.cambios)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HistorialAuditoria;

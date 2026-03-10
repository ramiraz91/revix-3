import React, { useState, useEffect } from 'react';
import { AlertTriangle, Clock, CheckCircle, RefreshCw, AlertCircle, XCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { alertasSLAAPI } from '../lib/api';
import { toast } from 'sonner';

const AlertasSLA = ({ onOrderClick }) => {
  const [alertas, setAlertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verificando, setVerificando] = useState(false);

  const cargarAlertas = async () => {
    try {
      const res = await alertasSLAAPI.listar({ resuelta: false });
      setAlertas(res.data || []);
    } catch (error) {
      console.error('Error cargando alertas SLA:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarAlertas();
  }, []);

  const verificarSLA = async () => {
    setVerificando(true);
    try {
      const res = await alertasSLAAPI.verificar();
      toast.success(`Verificación completada: ${res.data.alertas_generadas} nuevas alertas`);
      cargarAlertas();
    } catch (error) {
      toast.error('Error al verificar SLA');
    } finally {
      setVerificando(false);
    }
  };

  const resolverAlerta = async (alertaId) => {
    try {
      await alertasSLAAPI.resolver(alertaId);
      toast.success('Alerta resuelta');
      cargarAlertas();
    } catch (error) {
      toast.error('Error al resolver alerta');
    }
  };

  const getTipoColor = (tipo) => {
    switch (tipo) {
      case 'critico': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'vencido': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'proximo_vencer': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getTipoIcon = (tipo) => {
    switch (tipo) {
      case 'critico': return <XCircle className="w-4 h-4" />;
      case 'vencido': return <AlertCircle className="w-4 h-4" />;
      case 'proximo_vencer': return <Clock className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  const getTipoLabel = (tipo) => {
    switch (tipo) {
      case 'critico': return 'CRÍTICO';
      case 'vencido': return 'VENCIDO';
      case 'proximo_vencer': return 'Próximo a vencer';
      default: return tipo;
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Cargando alertas...
        </div>
      </div>
    );
  }

  if (alertas.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Sin alertas de SLA pendientes</span>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={verificarSLA}
            disabled={verificando}
            className="border-slate-600"
          >
            {verificando ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Verificar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          <h3 className="font-semibold text-white">Alertas SLA</h3>
          <Badge variant="destructive" className="ml-2">{alertas.length}</Badge>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={verificarSLA}
          disabled={verificando}
          className="border-slate-600"
        >
          {verificando ? (
            <RefreshCw className="w-4 h-4 animate-spin mr-2" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2" />
          )}
          Verificar
        </Button>
      </div>
      
      <div className="divide-y divide-slate-700/50 max-h-[300px] overflow-y-auto">
        {alertas.map((alerta) => (
          <div 
            key={alerta.id} 
            className="p-3 hover:bg-slate-700/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className={getTipoColor(alerta.tipo_alerta)}>
                    {getTipoIcon(alerta.tipo_alerta)}
                    <span className="ml-1">{getTipoLabel(alerta.tipo_alerta)}</span>
                  </Badge>
                </div>
                <button
                  onClick={() => onOrderClick && onOrderClick(alerta.orden_id)}
                  className="text-blue-400 hover:text-blue-300 font-medium text-sm"
                >
                  {alerta.numero_orden}
                </button>
                <p className="text-slate-400 text-xs mt-1">
                  {alerta.dias_en_proceso} días en proceso (SLA: {alerta.sla_objetivo} días)
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => resolverAlerta(alerta.id)}
                className="text-green-400 hover:text-green-300 hover:bg-green-500/10"
              >
                <CheckCircle className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AlertasSLA;

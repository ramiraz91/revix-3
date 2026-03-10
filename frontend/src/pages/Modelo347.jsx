import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { ArrowLeft, FileText, Download, Users, TrendingUp, TrendingDown } from 'lucide-react';

export default function Modelo347() {
  const navigate = useNavigate();
  const [año, setAño] = useState(new Date().getFullYear());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cargarDatos();
  }, [año]);

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/contabilidad/informes/modelo-347?año=${año}`);
      setData(res.data);
    } catch (error) {
      toast.error('Error cargando datos del modelo 347');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  const años = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    años.push(y);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="modelo347-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/contabilidad')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <FileText className="h-6 w-6 text-orange-600" />
              Modelo 347
            </h1>
            <p className="text-gray-500">Declaración anual de operaciones con terceros</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Select value={String(año)} onValueChange={(v) => setAño(parseInt(v))}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {años.map(y => (
                <SelectItem key={y} value={String(y)}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => toast.info('Exportación próximamente')}>
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
        </div>
      </div>

      {/* Info */}
      <Card className="bg-orange-50 border-orange-200">
        <CardContent className="pt-4">
          <p className="text-orange-800">
            <strong>Modelo 347:</strong> Declaración informativa de operaciones con terceros. 
            Deben declararse las operaciones que superen <strong>{formatCurrency(data?.limite_declaracion || 3005.06)}</strong> anuales 
            con un mismo cliente o proveedor.
          </p>
        </CardContent>
      </Card>

      {/* Resumen */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Terceros a Declarar</p>
                <p className="text-2xl font-bold">{data?.resumen?.num_terceros || 0}</p>
              </div>
              <Users className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Ventas</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(data?.resumen?.total_ventas)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Compras</p>
                <p className="text-2xl font-bold text-red-600">{formatCurrency(data?.resumen?.total_compras)}</p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Operaciones</p>
                <p className="text-2xl font-bold">{formatCurrency(data?.resumen?.total_operaciones)}</p>
              </div>
              <FileText className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Operaciones declarables */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Operaciones Declarables ({data?.operaciones_declarables?.length || 0})</span>
            <Badge variant="outline">
              {data?.operaciones_no_declarables || 0} operaciones bajo el límite
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium text-gray-600">NIF/CIF</th>
                  <th className="text-left p-3 font-medium text-gray-600">Nombre Fiscal</th>
                  <th className="text-right p-3 font-medium text-gray-600">Ventas</th>
                  <th className="text-right p-3 font-medium text-gray-600">Compras</th>
                  <th className="text-right p-3 font-medium text-gray-600">Total</th>
                  <th className="text-center p-3 font-medium text-gray-600">Facturas</th>
                </tr>
              </thead>
              <tbody>
                {data?.operaciones_declarables?.map((op, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="p-3 font-mono">{op.nif_cif}</td>
                    <td className="p-3 font-medium">{op.nombre_fiscal}</td>
                    <td className="p-3 text-right text-green-600">
                      {op.ventas > 0 ? formatCurrency(op.ventas) : '-'}
                    </td>
                    <td className="p-3 text-right text-red-600">
                      {op.compras > 0 ? formatCurrency(op.compras) : '-'}
                    </td>
                    <td className="p-3 text-right font-bold">{formatCurrency(op.total)}</td>
                    <td className="p-3 text-center">
                      <Badge variant="outline">{op.num_facturas}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!data?.operaciones_declarables || data.operaciones_declarables.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                No hay operaciones que superen el límite de {formatCurrency(data?.limite_declaracion || 3005.06)}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

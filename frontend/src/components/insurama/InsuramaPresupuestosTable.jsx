import { Eye, Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export function InsuramaPresupuestosTable({ presupuestos, loading, onVerDetalle }) {
  const getMarginBadge = (precio, reserveValue) => {
    if (!precio || !reserveValue || reserveValue <= 0) return null;
    const p = parseFloat(precio);
    const r = parseFloat(reserveValue);
    if (p <= 0 || r <= 0) return null;
    const pct = ((r - p) / r * 100).toFixed(0);
    if (p > r) {
      return <Badge variant="destructive" className="text-[10px]">Sobre máx.</Badge>;
    }
    if (pct <= 10) {
      return <Badge className="bg-amber-100 text-amber-700 text-[10px]">Margen {pct}%</Badge>;
    }
    return <Badge className="bg-green-100 text-green-700 text-[10px]">Margen {pct}%</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mis Presupuestos</CardTitle>
        <CardDescription>
          Últimos presupuestos enviados a Insurama
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : presupuestos.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            No hay presupuestos disponibles
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código Siniestro</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Dispositivo</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Mi Precio</TableHead>
                <TableHead>Máx. Siniestro</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {presupuestos.map((p) => (
                <TableRow key={p.id} data-testid={`presupuesto-row-${p.id}`}>
                  <TableCell className="font-mono font-medium">
                    {p.codigo_siniestro}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{p.cliente_nombre}</p>
                      {p.cliente_telefono && (
                        <p className="text-xs text-muted-foreground">{p.cliente_telefono}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p>{p.dispositivo}</p>
                      {p.product_name && (
                        <p className="text-xs text-muted-foreground">{p.product_name}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{p.estado}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <span className="font-bold text-green-600">
                        {p.precio ? `${p.precio}€` : '-'}
                      </span>
                      {getMarginBadge(p.precio, p.reserve_value)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <div className="flex flex-col gap-1">
                            {p.reserve_value ? (
                              <span className="font-semibold text-blue-600">
                                {parseFloat(p.reserve_value).toFixed(2)}€
                              </span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                            {p.claim_real_value && parseFloat(p.claim_real_value) > 0 && (
                              <span className="text-xs text-muted-foreground">
                                Real: {parseFloat(p.claim_real_value).toFixed(2)}€
                              </span>
                            )}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Valor máximo que la aseguradora paga por este siniestro</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => onVerDetalle(p.codigo_siniestro)}
                      data-testid={`ver-detalle-${p.codigo_siniestro}`}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Ver
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

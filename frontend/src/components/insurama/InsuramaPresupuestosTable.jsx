import { Eye, Loader2 } from 'lucide-react';
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

export function InsuramaPresupuestosTable({ presupuestos, loading, onVerDetalle }) {
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
                <TableHead>Precio</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {presupuestos.map((p) => (
                <TableRow key={p.id}>
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
                  <TableCell>{p.dispositivo}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{p.estado}</Badge>
                  </TableCell>
                  <TableCell>
                    {p.precio ? `${p.precio}€` : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => onVerDetalle(p.codigo_siniestro)}
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

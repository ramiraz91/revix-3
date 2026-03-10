import { FileImage, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';

export function OrdenFotosTab({ 
  fotos, 
  showImagePreview, 
  previewImage, 
  onOpenPreview, 
  onClosePreview 
}) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileImage className="w-5 h-5" />
            Fotos y Evidencias
          </CardTitle>
        </CardHeader>
        <CardContent>
          {fotos.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No hay fotos subidas
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {fotos.map((foto, index) => (
                <div 
                  key={index}
                  className="relative group cursor-pointer rounded-lg overflow-hidden border"
                  onClick={() => onOpenPreview(foto.src)}
                >
                  <img
                    src={foto.src}
                    alt={`Evidencia ${index + 1}`}
                    className="w-full h-32 object-cover transition-transform group-hover:scale-105"
                  />
                  <div className="absolute bottom-2 right-2">
                    <Badge variant={foto.tipo === 'tecnico' ? 'secondary' : 'default'} className="text-xs">
                      {foto.tipo === 'tecnico' ? 'Técnico' : 'Admin'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Image Preview Dialog */}
      <Dialog open={showImagePreview} onOpenChange={onClosePreview}>
        <DialogContent className="max-w-4xl p-0">
          <Button 
            variant="ghost" 
            size="icon" 
            className="absolute right-2 top-2 z-10 bg-black/50 hover:bg-black/70 text-white"
            onClick={() => onClosePreview(false)}
          >
            <X className="w-4 h-4" />
          </Button>
          {previewImage && (
            <img 
              src={previewImage} 
              alt="Preview" 
              className="w-full h-auto max-h-[80vh] object-contain"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

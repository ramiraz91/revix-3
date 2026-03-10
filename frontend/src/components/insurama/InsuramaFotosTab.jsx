import { Loader2, Image, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function InsuramaFotosTab({ fotos, loading }) {
  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {fotos.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            No hay fotos disponibles
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {fotos.map((foto, idx) => (
              <div key={idx} className="relative group">
                <div className="aspect-square rounded-lg bg-muted flex items-center justify-center overflow-hidden">
                  {foto.download_link ? (
                    <img 
                      src={foto.download_link} 
                      alt={foto.name || `Foto ${idx + 1}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Image className="w-12 h-12 text-muted-foreground" />
                  )}
                </div>
                <p className="text-xs text-center mt-1 truncate">{foto.name || `Documento ${idx + 1}`}</p>
                {foto.download_link && (
                  <a 
                    href={foto.download_link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Button size="icon" variant="secondary" className="w-8 h-8">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

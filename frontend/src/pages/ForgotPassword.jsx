import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle2, Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authAPI } from '@/lib/api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Introduce tu email');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authAPI.recuperarPassword(email.trim().toLowerCase());
      setSent(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 429) {
        setError(detail || 'Demasiadas solicitudes. Espera unos minutos.');
      } else {
        // La API siempre responde igual para no revelar si el email existe
        setSent(true);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <img 
            src="https://customer-assets.emergentagent.com/job_repair-sync/artifacts/htn5g20t_nexora_logo_transparent.png" 
            alt="NEXORA"
            className="h-16 mx-auto mb-4"
          />
        </div>

        <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur-xl">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-2xl">
              {sent ? 'Revisa tu email' : 'Recuperar contraseña'}
            </CardTitle>
            <CardDescription>
              {sent 
                ? 'Si el email está registrado, recibirás un enlace para restablecer tu contraseña.'
                : 'Introduce tu email y te enviaremos instrucciones para restablecer tu contraseña.'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sent ? (
              <div className="space-y-6">
                <div className="flex flex-col items-center gap-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-green-600" />
                  </div>
                  <p className="text-center text-muted-foreground text-sm">
                    El enlace de recuperación es válido durante <strong>1 hora</strong>. 
                    Revisa también la carpeta de spam si no lo encuentras.
                  </p>
                </div>
                <Link to="/crm/login">
                  <Button variant="outline" className="w-full" data-testid="back-to-login">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Volver al inicio de sesión
                  </Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="tu@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 h-11"
                      data-testid="forgot-password-email"
                      autoFocus
                    />
                  </div>
                </div>

                {error && (
                  <p className="text-sm text-red-600 bg-red-50 p-2 rounded" data-testid="forgot-password-error">
                    {error}
                  </p>
                )}

                <Button 
                  type="submit" 
                  className="w-full h-12 text-base bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-lg shadow-blue-500/25" 
                  disabled={loading}
                  data-testid="forgot-password-submit"
                >
                  {loading ? (
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <>
                      <Send className="w-5 h-5 mr-2" />
                      Enviar enlace de recuperación
                    </>
                  )}
                </Button>

                <div className="text-center pt-2">
                  <Link 
                    to="/crm/login" 
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
                  >
                    <ArrowLeft className="w-3 h-3" />
                    Volver al inicio de sesión
                  </Link>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
        
        <p className="text-center text-xs text-blue-200/60 mt-6">
          © {new Date().getFullYear()} NEXORA. Todos los derechos reservados.
        </p>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, LogIn, Sparkles, Shield, Zap, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';

export default function Login() {
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage('');
    try {
      await login(credentials.email, credentials.password);
      toast.success('¡Bienvenido!');
      navigate('/');
    } catch (error) {
      const detail = error.response?.data?.detail || 'Credenciales incorrectas';
      setErrorMessage(detail);
      // Si es error 429 (rate limit), mostrar toast más visible
      if (error.response?.status === 429) {
        toast.error(detail, { duration: 8000 });
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
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: '4s' }}></div>
      </div>

      <div className="w-full max-w-5xl grid lg:grid-cols-2 gap-8 items-center relative z-10">
        {/* Left side - Branding */}
        <div className="hidden lg:block text-white space-y-8 pr-8">
          <div>
            <img 
              src="https://customer-assets.emergentagent.com/job_repair-sync/artifacts/htn5g20t_nexora_logo_transparent.png" 
              alt="NEXORA"
              className="h-24 mb-6"
            />
            <h1 className="text-4xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-200">
              Gestión Inteligente para tu Negocio
            </h1>
            <p className="text-xl text-blue-200/80">
              La plataforma CRM/ERP más completa para servicios técnicos de telefonía móvil
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Automatización Total</h3>
                <p className="text-sm text-blue-200/70">Integración con Insurama, polling automático y notificaciones en tiempo real</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Asistente IA</h3>
                <p className="text-sm text-blue-200/70">Diagnósticos inteligentes y sugerencias de reparación con Gemini</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <Shield className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Control Total</h3>
                <p className="text-sm text-blue-200/70">Gestión de órdenes, inventario, clientes y logística en un solo lugar</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login form */}
        <div className="w-full max-w-md mx-auto lg:mx-0">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <img 
              src="https://customer-assets.emergentagent.com/job_repair-sync/artifacts/htn5g20t_nexora_logo_transparent.png" 
              alt="NEXORA"
              className="h-16 mx-auto mb-4"
            />
          </div>

          <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur-xl">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl">Bienvenido</CardTitle>
              <CardDescription>Accede a tu cuenta para continuar</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="tu@email.com"
                      value={credentials.email}
                      onChange={(e) => setCredentials(prev => ({ ...prev, email: e.target.value }))}
                      className="pl-10 h-11"
                      data-testid="login-email"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="password">Contraseña</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={credentials.password}
                      onChange={(e) => setCredentials(prev => ({ ...prev, password: e.target.value }))}
                      className="pl-10 h-11"
                      data-testid="login-password"
                    />
                  </div>
                </div>

                {errorMessage && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" data-testid="login-error-message">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                <Button 
                  type="submit" 
                  className="w-full h-12 text-base bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-lg shadow-blue-500/25" 
                  disabled={loading} 
                  data-testid="login-submit"
                >
                  {loading ? (
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <>
                      <LogIn className="w-5 h-5 mr-2" />
                      Iniciar Sesión
                    </>
                  )}
                </Button>

                <div className="text-center">
                  <Link 
                    to="/forgot-password" 
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    data-testid="forgot-password-link"
                  >
                    ¿Has olvidado tu contraseña?
                  </Link>
                </div>
              </form>

              {/* Features mini */}
              <div className="mt-6 pt-6 border-t grid grid-cols-3 gap-2 text-center">
                <div className="p-2">
                  <CheckCircle2 className="w-5 h-5 mx-auto text-green-500 mb-1" />
                  <p className="text-[10px] text-muted-foreground">Multi-usuario</p>
                </div>
                <div className="p-2">
                  <CheckCircle2 className="w-5 h-5 mx-auto text-green-500 mb-1" />
                  <p className="text-[10px] text-muted-foreground">Tiempo real</p>
                </div>
                <div className="p-2">
                  <CheckCircle2 className="w-5 h-5 mx-auto text-green-500 mb-1" />
                  <p className="text-[10px] text-muted-foreground">Seguro</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <p className="text-center text-xs text-blue-200/60 mt-6">
            © {new Date().getFullYear()} NEXORA. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </div>
  );
}

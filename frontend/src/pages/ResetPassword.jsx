import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Lock, ArrowLeft, CheckCircle2, AlertCircle, Eye, EyeOff, KeyRound } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authAPI } from '@/lib/api';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [tokenValid, setTokenValid] = useState(false);
  const [userEmail, setUserEmail] = useState('');

  // Verificar token al cargar
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setError('No se ha proporcionado un token de recuperación.');
        setVerifying(false);
        return;
      }
      try {
        const response = await authAPI.verificarTokenReset(token);
        if (response.data.valido) {
          setTokenValid(true);
          setUserEmail(response.data.email || '');
        } else {
          setError(response.data.motivo || 'Enlace inválido o caducado.');
        }
      } catch (err) {
        setError('No se pudo verificar el enlace. Puede que haya caducado.');
      } finally {
        setVerifying(false);
      }
    };
    verifyToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      await authAPI.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Error al restablecer la contraseña.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  // Estado de carga inicial
  if (verifying) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
        <div className="text-center text-white">
          <div className="animate-spin w-10 h-10 border-4 border-blue-400 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p>Verificando enlace...</p>
        </div>
      </div>
    );
  }

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
            {success ? (
              <>
                <CardTitle className="text-2xl text-green-700">¡Contraseña actualizada!</CardTitle>
                <CardDescription>Ya puedes acceder con tu nueva contraseña.</CardDescription>
              </>
            ) : !tokenValid ? (
              <>
                <CardTitle className="text-2xl text-red-700">Enlace no válido</CardTitle>
                <CardDescription>{error}</CardDescription>
              </>
            ) : (
              <>
                <CardTitle className="text-2xl">Nueva contraseña</CardTitle>
                <CardDescription>
                  {userEmail ? `Crea una nueva contraseña para ${userEmail}` : 'Introduce tu nueva contraseña.'}
                </CardDescription>
              </>
            )}
          </CardHeader>
          <CardContent>
            {success ? (
              <div className="space-y-6">
                <div className="flex flex-col items-center gap-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-green-600" />
                  </div>
                </div>
                <Button 
                  onClick={() => navigate('/crm/login')} 
                  className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
                  data-testid="go-to-login"
                >
                  Ir al inicio de sesión
                </Button>
              </div>
            ) : !tokenValid ? (
              <div className="space-y-6">
                <div className="flex flex-col items-center gap-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                    <AlertCircle className="w-8 h-8 text-red-600" />
                  </div>
                  <p className="text-center text-muted-foreground text-sm">
                    Puedes solicitar un nuevo enlace de recuperación.
                  </p>
                </div>
                <Link to="/forgot-password">
                  <Button variant="outline" className="w-full" data-testid="request-new-link">
                    Solicitar nuevo enlace
                  </Button>
                </Link>
                <Link to="/crm/login">
                  <Button variant="ghost" className="w-full" data-testid="back-to-login">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Volver al inicio de sesión
                  </Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Nueva contraseña</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10 pr-10 h-11"
                      data-testid="reset-password-new"
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">Mínimo 6 caracteres</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirmar contraseña</Label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="confirmPassword"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="pl-10 h-11"
                      data-testid="reset-password-confirm"
                    />
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" data-testid="reset-password-error">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <Button 
                  type="submit" 
                  className="w-full h-12 text-base bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-lg shadow-blue-500/25" 
                  disabled={loading}
                  data-testid="reset-password-submit"
                >
                  {loading ? (
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    'Guardar nueva contraseña'
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

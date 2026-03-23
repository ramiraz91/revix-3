import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '@/lib/api';

const AuthContext = createContext(null);

// Usuario master por defecto - Sin login requerido
const DEFAULT_MASTER_USER = {
  id: 'auto-master',
  email: 'master@revix.es',
  nombre: 'Admin',
  apellidos: 'Master',
  role: 'master',
  avatar_url: null
};

export function AuthProvider({ children }) {
  // Inicializar directamente con usuario master
  const [user, setUser] = useState(DEFAULT_MASTER_USER);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Asegurar que siempre haya un usuario master activo
    if (!user) {
      setUser(DEFAULT_MASTER_USER);
    }
  }, [user]);

  const login = async (email, password) => {
    // Login ya no es necesario, pero mantenemos la función por compatibilidad
    const res = await authAPI.login({ email, password });
    const { token, user: loggedUser } = res.data;
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(loggedUser));
    setUser(loggedUser);
    return loggedUser;
  };

  const logout = () => {
    // Logout no hace nada - siempre mantiene al usuario master
    // localStorage.removeItem('token');
    // localStorage.removeItem('user');
    // setUser(null);
  };

  const isAdmin = () => user?.role === 'admin' || user?.role === 'master';
  const isTecnico = () => user?.role === 'tecnico';
  const isMaster = () => user?.role === 'master';

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAdmin, isTecnico, isMaster }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

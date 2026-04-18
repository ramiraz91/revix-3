import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Logo Revix.es — composición tipográfica oficial.
 * "Revix" + punto azul #0055FF + "es"
 * Props:
 *  - size: "sm" | "md" | "lg"
 *  - variant: "light" (default, texto negro) | "dark" (texto blanco, para fondos oscuros)
 *  - asLink: si true, envuelve en <Link to="/"> (default true)
 */
const SIZES = {
  sm: 'text-xl',
  md: 'text-2xl',
  lg: 'text-4xl md:text-5xl',
};

export default function Logo({ size = 'md', variant = 'light', asLink = true, className = '' }) {
  const color = variant === 'dark' ? 'text-white' : 'text-[#111111]';
  const content = (
    <span
      className={`font-[800] tracking-tight inline-flex items-baseline ${SIZES[size]} ${color} ${className}`}
      data-testid="revix-logo"
    >
      Revix<span className="text-[#0055FF]">.</span>es
    </span>
  );

  if (!asLink) return content;

  return (
    <Link to="/" className="inline-flex items-baseline" aria-label="Ir al inicio de Revix.es">
      {content}
    </Link>
  );
}

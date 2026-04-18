import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

// ══════════════════════════════════════════════════════════════════════════════
// Design primitives — estilo Apple Care minimalista
// Usar estos componentes para máxima coherencia entre páginas.
// ══════════════════════════════════════════════════════════════════════════════

export function Container({ children, className = '', ...rest }) {
  return (
    <div className={`max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function Section({ children, className = '', id, tone = 'default' }) {
  const toneClasses = {
    default: 'bg-white',
    subtle: 'bg-[#F5F5F7]',
    dark: 'bg-[#111111] text-white',
  }[tone];
  return (
    <section id={id} className={`py-24 sm:py-32 ${toneClasses} ${className}`}>
      <Container>{children}</Container>
    </section>
  );
}

export function Eyebrow({ children, className = '' }) {
  return (
    <p
      className={`text-xs sm:text-sm font-semibold uppercase tracking-[0.18em] text-[#0055FF] ${className}`}
    >
      {children}
    </p>
  );
}

export function H1({ children, className = '' }) {
  return (
    <h1
      className={`font-[800] text-[#111111] tracking-[-0.04em] text-4xl sm:text-6xl md:text-7xl leading-[1.02] ${className}`}
    >
      {children}
    </h1>
  );
}

export function H2({ children, className = '' }) {
  return (
    <h2
      className={`font-[700] text-[#111111] tracking-[-0.035em] text-3xl sm:text-5xl leading-[1.05] ${className}`}
    >
      {children}
    </h2>
  );
}

export function H3({ children, className = '' }) {
  return (
    <h3
      className={`font-[700] text-[#111111] tracking-[-0.02em] text-xl sm:text-2xl ${className}`}
    >
      {children}
    </h3>
  );
}

export function Lead({ children, className = '' }) {
  return (
    <p className={`text-lg sm:text-xl text-[#6E6E73] leading-relaxed ${className}`}>{children}</p>
  );
}

export function Body({ children, className = '' }) {
  return <p className={`text-base text-[#3A3A3C] leading-relaxed ${className}`}>{children}</p>;
}

/* ---------- Botones ---------- */
function baseButtonClasses(variant) {
  const base =
    'inline-flex items-center justify-center gap-2 font-semibold rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0055FF] focus-visible:ring-offset-2';
  const size = 'px-7 py-3.5 text-sm sm:text-base';
  const variants = {
    primary: 'bg-[#0055FF] text-white hover:bg-[#0044CC] shadow-sm hover:shadow-md',
    secondary:
      'bg-[#F5F5F7] text-[#111111] hover:bg-[#E5E5EA] border border-transparent',
    ghost: 'bg-transparent text-[#0055FF] hover:underline underline-offset-4',
    dark: 'bg-[#111111] text-white hover:bg-[#2B2B2E]',
  };
  return `${base} ${size} ${variants[variant] || variants.primary}`;
}

export function CTAButton({ to, href, variant = 'primary', children, withArrow = false, testid, className = '', onClick, type }) {
  const cls = `${baseButtonClasses(variant)} ${className}`;
  const inner = (
    <>
      {children}
      {withArrow && <ArrowRight className="w-4 h-4" strokeWidth={2.5} />}
    </>
  );
  if (to) {
    return (
      <Link to={to} className={cls} data-testid={testid} onClick={onClick}>
        {inner}
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className={cls} data-testid={testid} onClick={onClick}>
        {inner}
      </a>
    );
  }
  return (
    <button type={type || 'button'} className={cls} data-testid={testid} onClick={onClick}>
      {inner}
    </button>
  );
}

/* ---------- Cards ---------- */
export function Card({ children, className = '', tone = 'default' }) {
  const tones = {
    default: 'bg-white border border-[#E5E5EA] hover:shadow-[0_8px_40px_rgba(0,0,0,0.06)]',
    subtle: 'bg-[#F5F5F7] border border-transparent hover:bg-[#EFEFF2]',
    dark: 'bg-[#111111] text-white border border-white/10 hover:border-white/20',
    brand: 'bg-[#0055FF] text-white border border-transparent hover:bg-[#0044CC]',
  };
  return (
    <div
      className={`rounded-3xl p-8 sm:p-10 transition-all duration-300 ${tones[tone]} ${className}`}
    >
      {children}
    </div>
  );
}

/* ---------- Motion helpers ---------- */
export function FadeUp({ children, delay = 0, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ---------- Page-level Hero ---------- */
export function PageHero({ eyebrow, title, subtitle, children, tone = 'default' }) {
  const bg = tone === 'subtle' ? 'bg-[#F5F5F7]' : 'bg-white';
  return (
    <section className={`pt-32 pb-20 sm:pt-40 sm:pb-28 ${bg}`}>
      <Container className="max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="space-y-6 text-center"
        >
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          <H1>{title}</H1>
          {subtitle && <Lead className="max-w-2xl mx-auto">{subtitle}</Lead>}
          {children && <div className="pt-4 flex flex-wrap items-center justify-center gap-3">{children}</div>}
        </motion.div>
      </Container>
    </section>
  );
}

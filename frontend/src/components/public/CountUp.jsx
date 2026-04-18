import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useMotionValue, useSpring, useTransform } from 'framer-motion';

/**
 * CountUp — contador animado que se dispara al entrar en viewport.
 * Props:
 *  - to: valor final numérico
 *  - decimals: número de decimales (default 0)
 *  - duration: duración en segundos (default 2)
 *  - prefix / suffix: texto opcional
 */
export default function CountUp({ to, decimals = 0, duration = 2, prefix = '', suffix = '', className = '' }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { duration: duration * 1000, bounce: 0 });
  const display = useTransform(spring, (v) =>
    `${prefix}${v.toFixed(decimals).replace('.', ',')}${suffix}`
  );
  const [text, setText] = useState(`${prefix}0${decimals ? ',' + '0'.repeat(decimals) : ''}${suffix}`);

  useEffect(() => {
    if (inView) mv.set(to);
  }, [inView, mv, to]);

  useEffect(() => {
    return display.on('change', (v) => setText(v));
  }, [display]);

  return (
    <span ref={ref} className={className}>
      {text}
    </span>
  );
}

/**
 * Performance hooks for optimized data fetching
 * Fase 4: Optimizaciones de Frontend
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';

/**
 * Hook para debounce de valores (búsquedas)
 * @param {any} value - Valor a debouncer
 * @param {number} delay - Delay en ms (default 300)
 */
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook para búsqueda con debounce
 * @param {Function} searchFn - Función de búsqueda async
 * @param {number} delay - Delay en ms
 */
export function useDebouncedSearch(searchFn, delay = 300) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const debouncedQuery = useDebounce(query, delay);
  
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      return;
    }
    
    let cancelled = false;
    
    const search = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await searchFn(debouncedQuery);
        if (!cancelled) {
          setResults(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    
    search();
    
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, searchFn]);
  
  return { query, setQuery, results, loading, error };
}

/**
 * Hook para paginación infinita
 * @param {Function} fetchFn - Función que recibe (page, pageSize) y retorna {data, total, pages}
 * @param {number} pageSize - Tamaño de página
 */
export function useInfiniteScroll(fetchFn, pageSize = 50) {
  const [data, setData] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  
  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    try {
      const result = await fetchFn(page, pageSize);
      setData(prev => [...prev, ...result.data]);
      setTotal(result.total);
      setHasMore(page < result.pages);
      setPage(p => p + 1);
    } catch (err) {
      console.error('Error loading more:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, page, pageSize, loading, hasMore]);
  
  const reset = useCallback(() => {
    setData([]);
    setPage(1);
    setHasMore(true);
    setTotal(0);
  }, []);
  
  return { data, loading, hasMore, total, loadMore, reset };
}

/**
 * Hook para memoización de filtros
 * Evita re-fetches innecesarios
 */
export function useMemoizedFilters(filters) {
  const prevFilters = useRef(filters);
  
  const memoized = useMemo(() => {
    const prevStr = JSON.stringify(prevFilters.current);
    const currStr = JSON.stringify(filters);
    
    if (prevStr !== currStr) {
      prevFilters.current = filters;
      return filters;
    }
    
    return prevFilters.current;
  }, [filters]);
  
  return memoized;
}

/**
 * Hook para cache simple en memoria
 */
export function useSimpleCache(key, fetchFn, ttlMs = 60000) {
  const cache = useRef({});
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const cached = cache.current[key];
    const now = Date.now();
    
    if (cached && (now - cached.timestamp) < ttlMs) {
      setData(cached.data);
      setLoading(false);
      return;
    }
    
    let cancelled = false;
    
    const fetch = async () => {
      setLoading(true);
      try {
        const result = await fetchFn();
        if (!cancelled) {
          cache.current[key] = { data: result, timestamp: now };
          setData(result);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    
    fetch();
    
    return () => {
      cancelled = true;
    };
  }, [key, fetchFn, ttlMs]);
  
  return { data, loading };
}

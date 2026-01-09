/**
 * Hook for responsive container sizing.
 *
 * Observes a container element and calculates the optimal size for
 * a square element that fits within it, respecting min/max constraints.
 */

import { useRef, useState, useEffect, useCallback } from 'react';

interface UseContainerSizeOptions {
  /** Padding to subtract from available dimensions (default: 12) */
  padding?: number;
  /** Maximum size for the element (default: 600) */
  maxSize?: number;
  /** Minimum size for the element (default: 300) */
  minSize?: number;
  /** Extra height to account for (e.g., controls) */
  heightOffset?: number;
}

interface UseContainerSizeResult {
  containerRef: React.RefObject<HTMLDivElement | null>;
  size: number;
}

export function useContainerSize(options: UseContainerSizeOptions = {}): UseContainerSizeResult {
  const {
    padding = 12,
    maxSize = 600,
    minSize = 300,
    heightOffset = 0,
  } = options;

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(minSize);

  const updateSize = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const availableWidth = rect.width - padding;
    const availableHeight = rect.height - padding - heightOffset;
    const availableSize = Math.min(availableWidth, availableHeight, maxSize);
    setSize(Math.max(minSize, Math.floor(availableSize)));
  }, [padding, maxSize, minSize, heightOffset]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(container);
    // Initial calculation with a small delay to ensure layout is complete
    requestAnimationFrame(updateSize);

    return () => resizeObserver.disconnect();
  }, [updateSize]);

  return { containerRef, size };
}

/**
 * Hook for dual grid layout sizing (comparison mode).
 */
export function useDualContainerSize(options: UseContainerSizeOptions = {}): UseContainerSizeResult {
  const {
    padding = 24,
    maxSize = 400,
    minSize = 200,
    heightOffset = 40,
  } = options;

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(minSize);

  const updateSize = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    // Each grid takes half the width minus gap
    const availableWidth = (rect.width - padding) / 2;
    const availableHeight = rect.height - heightOffset;
    const availableSize = Math.min(availableWidth, availableHeight, maxSize);
    setSize(Math.max(minSize, Math.floor(availableSize)));
  }, [padding, maxSize, minSize, heightOffset]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(container);
    requestAnimationFrame(updateSize);

    return () => resizeObserver.disconnect();
  }, [updateSize]);

  return { containerRef, size };
}

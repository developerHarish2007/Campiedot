import React, { useRef, useEffect, useState, useCallback } from 'react';

interface ScrollableDockProps {
  children: React.ReactNode;
  activeId?: string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  hintCaption?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function ScrollableDock({
  children,
  activeId,
  prefix,
  suffix,
  hintCaption,
  className = '',
  style
}: ScrollableDockProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Drag-to-scroll refs
  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollStart = useRef(0);
  const hasDragged = useRef(false);

  const checkScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setCanScrollLeft(scrollLeft > 2);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 2);
  }, []);

  useEffect(() => {
    checkScroll();
    window.addEventListener('resize', checkScroll);
    return () => window.removeEventListener('resize', checkScroll);
  }, [checkScroll, children]);

  // Scroll active item into view
  useEffect(() => {
    if (!activeId || !scrollRef.current) return;
    const activeEl = scrollRef.current.querySelector(`[data-dock-id="${activeId}"]`);
    if (activeEl) {
      activeEl.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
    }
  }, [activeId]);

  const handleScrollLeft = () => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollBy({ left: -220, behavior: 'smooth' });
    setTimeout(checkScroll, 250);
  };

  const handleScrollRight = () => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollBy({ left: 220, behavior: 'smooth' });
    setTimeout(checkScroll, 250);
  };

  const handleWheel = (e: React.WheelEvent) => {
    if (!scrollRef.current) return;
    if (e.deltaY !== 0) {
      e.currentTarget.scrollLeft += e.deltaY;
      checkScroll();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollRef.current) return;
    isDragging.current = true;
    hasDragged.current = false;
    startX.current = e.pageX;
    scrollStart.current = scrollRef.current.scrollLeft;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !scrollRef.current) return;
    const dx = e.pageX - startX.current;
    if (Math.abs(dx) > 3) hasDragged.current = true;
    scrollRef.current.scrollLeft = scrollStart.current - dx;
    checkScroll();
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', position: 'relative' }}>
      {/* Floating hint caption above the dock (never squeezes pills) */}
      {hintCaption && (
        <div
          className="dock-hint-caption"
          style={{
            marginBottom: 6,
            color: '#cbd5e1',
            fontSize: 10,
            letterSpacing: '0.04em',
            textShadow: '0 1px 4px rgba(0, 0, 0, 0.7)',
            pointerEvents: 'none'
          }}
        >
          {hintCaption}
        </div>
      )}

      {/* Dock Bar */}
      <div
        className={`scrollable-dock-bar ${className}`}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          width: '100%',
          maxWidth: '100%',
          background: 'rgba(23, 36, 33, 0.92)',
          border: '1px solid rgba(170, 183, 164, 0.45)',
          borderRadius: 10,
          padding: '6px 8px',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
          ...style
        }}
      >
        {/* Optional Prefix label */}
        {prefix && <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, marginRight: 4 }}>{prefix}</div>}

        {/* Left Arrow Button */}
        <button
          className="dock-arrow-btn left"
          onClick={handleScrollLeft}
          title="Scroll left"
          style={{
            flexShrink: 0,
            width: 24,
            height: 26,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: canScrollLeft ? '#23382f' : '#182420',
            border: `1px solid ${canScrollLeft ? '#527263' : '#33443b'}`,
            color: canScrollLeft ? '#72c8a0' : '#4d6156',
            borderRadius: 5,
            cursor: canScrollLeft ? 'pointer' : 'default',
            padding: 0,
            fontSize: 13,
            lineHeight: 1,
            userSelect: 'none',
            transition: 'all 0.15s ease'
          }}
        >
          ‹
        </button>

        {/* Horizontally scrollable track */}
        <div
          ref={scrollRef}
          className="dock-scroll-track"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onScroll={checkScroll}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            overflowX: 'auto',
            overflowY: 'hidden',
            whiteSpace: 'nowrap',
            scrollSnapType: 'none',
            scrollbarWidth: 'thin',
            scrollbarColor: '#475a50 rgba(20, 30, 27, 0.6)',
            cursor: isDragging.current ? 'grabbing' : 'default',
            userSelect: 'none',
            paddingBottom: 2
          }}
        >
          {children}
        </div>

        {/* Right Arrow Button */}
        <button
          className="dock-arrow-btn right"
          onClick={handleScrollRight}
          title="Scroll right"
          style={{
            flexShrink: 0,
            width: 24,
            height: 26,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: canScrollRight ? '#23382f' : '#182420',
            border: `1px solid ${canScrollRight ? '#527263' : '#33443b'}`,
            color: canScrollRight ? '#72c8a0' : '#4d6156',
            borderRadius: 5,
            cursor: canScrollRight ? 'pointer' : 'default',
            padding: 0,
            fontSize: 13,
            lineHeight: 1,
            userSelect: 'none',
            transition: 'all 0.15s ease'
          }}
        >
          ›
        </button>

        {/* Optional Suffix (e.g. StatsPill) */}
        {suffix && <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, marginLeft: 4 }}>{suffix}</div>}
      </div>
    </div>
  );
}


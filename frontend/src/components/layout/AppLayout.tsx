import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { useRef, useEffect, useState, useCallback } from 'react';
import gsap from 'gsap';

export function AppLayout() {
  const mainRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const [navVisible, setNavVisible] = useState(false);
  const isFullScreenPage = ['/editor', '/dashboard', '/evaluator', '/generator'].some(
    path => location.pathname.startsWith(path)
  );

  const show = useCallback(() => setNavVisible(true), []);
  const hide = useCallback(() => setNavVisible(false), []);

  // Page transition animation
  useEffect(() => {
    if (mainRef.current) {
      gsap.fromTo(mainRef.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' });
    }
  }, [location.pathname]);

  // Show nav when cursor is near the top of the screen
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (e.clientY < 8) {
        setNavVisible(true);
      } else if (e.clientY > 64 && !navRef.current?.matches(':hover')) {
        setNavVisible(false);
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Show nav when scrolled to top
  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    const handleScroll = () => {
      if (el.scrollTop < 20) setNavVisible(true);
      else setNavVisible(false);
    };
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden relative">
      {/* Invisible top trigger strip */}
      <div
        className="absolute top-0 left-0 right-0 h-4 z-50"
        onMouseEnter={show}
      />

      {/* Auto-hiding Navbar */}
      <div
        ref={navRef}
        className={`absolute top-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-sm border-b border-gray-100 shadow-sm transition-transform duration-200 ease-out ${
          navVisible ? 'translate-y-0' : '-translate-y-full'
        }`}
        onMouseEnter={show}
        onMouseLeave={hide}
      >
        <Navbar />
      </div>

      <main
        ref={mainRef}
        className={
          isFullScreenPage
            ? 'flex-1 flex flex-col overflow-hidden'
            : 'flex-1 overflow-auto px-4 sm:px-8 pb-8 pt-4'
        }
      >
        <Outlet />
      </main>
    </div>
  );
}

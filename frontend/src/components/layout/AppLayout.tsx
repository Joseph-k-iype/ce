import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { useRef, useEffect } from 'react';
import gsap from 'gsap';

export function AppLayout() {
  const mainRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const isEditorPage = location.pathname.startsWith('/editor');

  useEffect(() => {
    if (mainRef.current) {
      gsap.fromTo(mainRef.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' });
    }
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Navbar />
      <main ref={mainRef} className={isEditorPage ? 'flex-1 flex flex-col overflow-hidden' : 'flex-1 overflow-auto px-8 pb-8'}>
        <Outlet />
      </main>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

interface DarkModeToggleProps {
  className?: string;
}

const DarkModeToggle: React.FC<DarkModeToggleProps> = ({ className = '' }) => {
  const [isDark, setIsDark] = useState(false);

  // Check for saved theme preference or default to light mode
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      setIsDark(true);
    }
  };

  return (
    <button
      onClick={toggleDarkMode}
      className={`relative inline-flex h-12 w-20 items-center justify-center rounded-full p-1
        transition-all duration-500 ease-in-out transform hover:shadow-2xl
        ${isDark 
          ? 'bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 shadow-lg shadow-slate-900/30' 
          : 'bg-gradient-to-r from-yellow-300 via-orange-400 to-red-400 shadow-lg shadow-orange-500/30'
        } ${className}`}
      aria-label="Toggle dark mode"
    >
      {/* Animated background circle */}
      <div
        className={`absolute inset-1 rounded-full transition-all duration-500 ease-in-out
          ${isDark 
            ? 'bg-slate-900 shadow-inner' 
            : 'bg-white shadow-lg'
          }`}
      />
      
      {/* Toggle knob with enhanced animation */}
      <div
        className={`relative flex h-10 w-10 items-center justify-center rounded-full 
          transition-all duration-700 ease-theme-toggle transform
          ${isDark 
            ? 'translate-x-4 bg-slate-800 shadow-lg shadow-slate-900/50' 
            : 'translate-x-[-4px] bg-gradient-to-br from-yellow-100 to-orange-200 shadow-lg shadow-orange-300/50'
          }`}
        style={{
          animation: isDark ? 'slideToDark 0.7s ease-theme-toggle' : 'slideToLight 0.7s ease-theme-toggle'
        }}
      >
        {/* Icon container with rotation and scale */}
        <div
          className={`transition-all duration-700 ease-theme-toggle transform
            ${isDark ? 'rotate-180 scale-110' : 'rotate-0 scale-100'}
          `}
        >
          {isDark ? (
            <Moon 
              className="h-5 w-5 text-slate-300 drop-shadow-lg"
              style={{ animation: 'moonGlow 2s ease-in-out infinite alternate' }}
            />
          ) : (
            <Sun 
              className="h-5 w-5 text-orange-600 drop-shadow-lg"
              style={{ animation: 'sunPulse 2s ease-in-out infinite' }}
            />
          )}
        </div>
        
        {/* Sparkle effect for light mode */}
        {!isDark && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1 left-2 w-1 h-1 bg-yellow-300 rounded-full animate-ping opacity-75"></div>
            <div className="absolute top-3 right-1 w-0.5 h-0.5 bg-orange-300 rounded-full animate-ping opacity-60 animate-delay-500"></div>
            <div className="absolute bottom-2 left-3 w-0.5 h-0.5 bg-red-300 rounded-full animate-ping opacity-50 animate-delay-1000"></div>
          </div>
        )}
        
        {/* Star effect for dark mode */}
        {isDark && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1 right-1 w-0.5 h-0.5 bg-blue-300 rounded-full animate-pulse opacity-60"></div>
            <div className="absolute bottom-1 left-1 w-0.5 h-0.5 bg-indigo-300 rounded-full animate-pulse opacity-40 animate-delay-1000"></div>
          </div>
        )}
      </div>
    </button>
  );
};

export default DarkModeToggle;

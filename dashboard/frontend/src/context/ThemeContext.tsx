import React, { createContext, useContext, useState, useEffect } from 'react';

export type ThemeMode = 'mocha' | 'monochrome';

interface ThemeContextType {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('campusops_theme') as ThemeMode;
    return saved === 'monochrome' ? 'monochrome' : 'mocha';
  });

  const setTheme = (mode: ThemeMode) => {
    setThemeState(mode);
    localStorage.setItem('campusops_theme', mode);
  };

  const toggleTheme = () => {
    const next = theme === 'mocha' ? 'monochrome' : 'mocha';
    setTheme(next);
  };

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    if (theme === 'monochrome') {
      root.classList.add('theme-monochrome');
      root.classList.remove('theme-mocha');
    } else {
      root.classList.add('theme-mocha');
      root.classList.remove('theme-monochrome');
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};


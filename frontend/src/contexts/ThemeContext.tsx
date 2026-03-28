import { createContext, useContext, ReactNode } from 'react';

const ThemeContext = createContext({});
export function ThemeProvider({ children }: { children: ReactNode }) {
  return <ThemeContext.Provider value={{}}>{children}</ThemeContext.Provider>;
}
export function useTheme() { return useContext(ThemeContext); }

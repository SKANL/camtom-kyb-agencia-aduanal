"use client";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <SWRConfig
        value={{
          revalidateOnFocus: true,
          shouldRetryOnError: false,
        }}
      >
        {children}
      </SWRConfig>
    </ThemeProvider>
  );
}

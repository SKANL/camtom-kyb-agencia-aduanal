"use client";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <SWRConfig
        value={{
          dedupingInterval: 5000,
          focusThrottleInterval: 10000,
          revalidateOnFocus: true,
          errorRetryCount: 2,
        }}
      >
        {children}
      </SWRConfig>
    </ThemeProvider>
  );
}

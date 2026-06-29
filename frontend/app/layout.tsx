import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Camtom KYB",
  description: "Plataforma KYB para agencia aduanal — Regla 1.4.14 RGCE 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>
          <Header />
          <div className="flex-1">{children}</div>
          <Toaster richColors position="bottom-right" />
        </Providers>
      </body>
    </html>
  );
}

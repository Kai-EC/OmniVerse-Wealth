import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniVerse Wealth | AI Investment Assistant",
  description: "Multi-Agent AI Investment Assistant powered by AWS Bedrock & MAX Exchange",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW" className="h-full antialiased dark">
      <body className="min-h-screen bg-[#0a0e1a] text-slate-200 overflow-hidden font-sans">
        {children}
      </body>
    </html>
  );
}

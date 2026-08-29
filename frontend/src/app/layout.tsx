import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/providers/theme-provider";
import { QueryProvider } from "@/providers/query-provider";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://pysetu.io"),
  title: {
    default: "PySetu AI | Enterprise AI Governance, MCP Security & Agentic Safety",
    template: "%s | PySetu AI",
  },
  description:
    "Enterprise AI governance and control plane for LLM gateway traffic, MCP compliance, real-time GenAI DLP, governed RAG, OPA data-movement policy, and auditor-ready compliance evidence.",
  keywords: [
    "AI Governance",
    "Model Context Protocol",
    "MCP Security",
    "GenAI DLP",
    "AI Gateway",
    "Agentic Security",
    "LLM Router",
    "Governed RAG",
    "Open Policy Agent",
    "AI Compliance",
  ],
  authors: [{ name: "PySetu AI Research & Engineering" }],
  creator: "PySetu AI",
  publisher: "PySetu AI",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: "https://pysetu.io",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://pysetu.io",
    siteName: "PySetu AI",
    title: "PySetu AI | Govern Every Agent, Tool, and Byte from Prompt to Vector Store",
    description:
      "Enterprise AI governance platform for LLM gateway, MCP compliance, GenAI DLP, governed RAG, and automated compliance evidence.",
  },
  twitter: {
    card: "summary_large_image",
    title: "PySetu AI | Enterprise AI Governance & Agentic Security",
    description:
      "Enterprise AI governance and control plane for LLM gateway traffic, MCP compliance, real-time GenAI DLP, and governed RAG.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1120" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="min-h-full antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <QueryProvider>
            <AuthGuard>{children}</AuthGuard>
          </QueryProvider>
          <Toaster position="bottom-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}

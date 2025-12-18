import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { ThemeProvider } from "next-themes"
import "./globals.css"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "AI Fiesta — Multi-Provider AI Chat Platform",
  description: "Compare responses from multiple AI models side-by-side. Support for OpenAI, Anthropic, Gemini, Grok, and Perplexity with real-time streaming and usage tracking.",
  generator: "Next.js",
  icons: {
    icon: "/icons/openai.png", // Using OpenAI icon as placeholder - can be replaced with custom favicon
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  )
}


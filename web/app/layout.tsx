import type { Metadata } from "next";
import { Bricolage_Grotesque, Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { BucketProvider } from "@/components/bucket-context";
import { ClarificationProvider } from "@/components/clarification-context";
import { IngestProvider } from "@/components/ingest-context";
import { NotificationProvider } from "@/components/notification-context";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  display: "swap",
});

const sans = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const mono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AdaRag",
  description: "Adaptive multimodal RAG: profile every file, retrieve over a hybrid index, self-tune.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen antialiased">
        <NotificationProvider>
          <BucketProvider>
            <ClarificationProvider>
              <IngestProvider>
                <AppShell>{children}</AppShell>
              </IngestProvider>
            </ClarificationProvider>
          </BucketProvider>
        </NotificationProvider>
      </body>
    </html>
  );
}

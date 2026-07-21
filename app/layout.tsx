import type { Metadata, Viewport } from "next";
import { COMPANION_NAME } from "@/lib/companion";
import "./globals.css";

export const metadata: Metadata = {
  title: `${COMPANION_NAME} — your AI companion`,
  description: "A warm, thoughtful AI companion you can talk to.",
};

export const viewport: Viewport = {
  themeColor: "#0e0b1a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

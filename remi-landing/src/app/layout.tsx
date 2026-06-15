import type { Metadata } from "next";
import { Bricolage_Grotesque, Hanken_Grotesk } from "next/font/google";
import "./globals.css";

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
  variable: "--ff-display",
});

const sans = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--ff-sans",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://remi.pe"),
  title: "Remi · Tu asistente de matrícula por WhatsApp",
  description:
    "Remi es el asistente virtual que responde tus dudas de matrícula, carreras y trámites académicos al instante por WhatsApp.",
  icons: {
    icon: "/logo-remi.png",
    apple: "/logo-remi.png",
  },
  openGraph: {
    title: "Remi · Tu asistente de matrícula por WhatsApp",
    description:
      "Resuelve tus dudas de matrícula y trámites académicos al instante, directo en WhatsApp.",
    type: "website",
    locale: "es_PE",
    images: ["/logo-remi.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es-PE" className={`${display.variable} ${sans.variable}`}>
      <body>{children}</body>
    </html>
  );
}

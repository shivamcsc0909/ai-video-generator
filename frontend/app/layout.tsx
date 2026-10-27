import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Local AI Video Production Studio",
  description: "Modular, local-first AI video studio with intelligent API rotation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 min-h-screen">
        <Sidebar />
        <div className="ml-64 flex flex-col min-h-screen">
          <Navbar />
          <main className="flex-1 mt-16 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

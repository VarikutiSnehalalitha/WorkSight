import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { RealtimeProvider } from "@/lib/ws-context";

export const metadata: Metadata = {
  title: "WorkSight — Workplace Intelligence & Ethical Attendance Platform",
  description:
    "Enterprise employee attendance, anonymous CCTV occupancy intelligence, and privacy-first workplace governance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans bg-[#F6F4EE] text-[#19201C] antialiased">
        <AuthProvider>
          <RealtimeProvider>{children}</RealtimeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

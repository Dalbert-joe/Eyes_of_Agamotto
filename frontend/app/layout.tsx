import "../src/index.css";

export const metadata = {
  title: "AGAMOTTO",
  description: "Self-hosted hackathon management and verifiable judging platform",
};

export default function RootLayout({ children }: Readonly<{ children: import("react").ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

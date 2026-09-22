import { Link, useLocation } from "react-router-dom";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  const { pathname } = useLocation();
  return (
    <div className="min-h-screen">
      <Header />
      <main className="container flex max-w-xl flex-col items-start py-24">
        <p className="eyebrow">404</p>
        <h1 className="display mt-3 text-5xl">This page doesn't exist.</h1>
        <p className="mt-4 text-muted-foreground">
          Nothing lives at <code className="num rounded bg-muted px-1.5 py-0.5 text-sm">{pathname}</code>.
        </p>
        <div className="mt-8 flex gap-3">
          <Button asChild><Link to="/">Home</Link></Button>
          <Button asChild variant="outline"><Link to="/dashboard">Dashboard</Link></Button>
        </div>
      </main>
    </div>
  );
}

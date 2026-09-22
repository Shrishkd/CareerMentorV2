import { motion } from "framer-motion";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import DarkModeToggle from "@/components/DarkModeToggle";
import { cn } from "@/lib/utils";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/resume-upload", label: "Mock Interview" },
  { to: "/ats-checker", label: "ATS Checker" },
];

interface HeaderProps {
  /** Minimal header used during an interview: logo, theme toggle and exit only. */
  focus?: boolean;
  onExit?: () => void;
  className?: string;
}

export function Logo() {
  return (
    <Link to="/">
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2 }}
        className="flex cursor-pointer items-center space-x-3"
      >
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-lg bg-gradient-primary">
          <img src="/favicon.ico" alt="Career Mentor" className="h-full w-full object-contain" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Career Mentor</h1>
          <p className="text-sm text-muted-foreground">AI Interview Platform</p>
        </div>
      </motion.div>
    </Link>
  );
}

export default function Header({ focus = false, onExit, className = "" }: HeaderProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  return (
    <header className={`sticky top-0 z-50 border-b border-border bg-card ${className}`}>
      <div className="container mx-auto flex items-center justify-between px-6 py-4">
        <Logo />

        {focus ? (
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="sm" onClick={onExit ?? (() => navigate("/dashboard"))}>
              Exit interview
            </Button>
            <DarkModeToggle className="scale-75" />
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            <nav className="hidden items-center space-x-1 md:flex" aria-label="Main">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    cn(
                      "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground",
                    )
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </nav>
            <DarkModeToggle className="scale-75" />
            <button
              className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-muted md:hidden"
              onClick={() => setOpen((o) => !o)}
              aria-label="Toggle menu"
              aria-expanded={open}
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        )}
      </div>

      {open && !focus && (
        <nav className="border-t md:hidden" aria-label="Mobile">
          <div className="container mx-auto flex flex-col px-6 py-2">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cn("py-2.5 text-sm", isActive ? "font-semibold text-primary" : "text-muted-foreground")
                }
              >
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-border py-8">
      <div className="container mx-auto flex flex-col items-center gap-2 px-6 text-center text-sm text-muted-foreground">
        <div className="flex gap-6">
          <Link to="/vlog" className="hover:text-foreground">Founder Vlog</Link>
          <a href="https://shrishcraft.vercel.app" target="_blank" rel="noreferrer" className="hover:text-foreground">
            Built by Shrish Das
          </a>
        </div>
        <p>&copy; {new Date().getFullYear()} AI Interview Platform. All rights reserved.</p>
      </div>
    </footer>
  );
}

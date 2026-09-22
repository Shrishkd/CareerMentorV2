import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  User,
  LogOut,
  Settings,
  HelpCircle,
  Shield,
  Mail,
} from "lucide-react";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import { useUserStats } from "@/hooks/useUserStats";
import DarkModeToggle from "@/components/DarkModeToggle";

interface HeaderProps {
  showProfile?: boolean;
  className?: string;
}

export const Header = ({ showProfile = true, className = "" }: HeaderProps) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const { user, profile, loading, signOut } = useAuth();
  const {
    stats: userStats,
    loading: statsLoading,
    error: statsError,
  } = useUserStats(user ? user.id : null);

  const handleProfileOption = (option: string) => {
    setOpen(false);
    switch (option) {
      case "settings":
        console.log("Opening settings...");
        break;
      case "help":
        console.log("Opening help...");
        break;
      case "privacy":
        console.log("Opening privacy settings...");
        break;
      case "feedback":
        console.log("Opening feedback form...");
        break;
      default:
        break;
    }
  };

  return (
    <header className={`sticky top-0 z-50 border-b border-border bg-card ${className}`}>
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-center space-x-3 cursor-pointer"
          >
            <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center overflow-hidden">
              <img
                src="/favicon.ico"
                alt="Career Mentor"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h1 className="text-xl font-bold">Career Mentor</h1>
              <p className="text-sm text-muted-foreground">AI Interview Platform</p>
            </div>
          </motion.div>
        </Link>

        <div className="flex items-center space-x-4">
          {showProfile && user && (
            <>
              {/* Profile Dropdown */}
              <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="sm" className="relative">
                    <User className="h-4 w-4 mr-2" />
                    Profile
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                  </Button>
                </PopoverTrigger>
                {open && (
                  <PopoverContent className="w-80 p-0" align="end">
                    <div className="p-4">
                      <div className="flex items-center space-x-4 mb-4">
                        <Avatar className="h-12 w-12">
                          <AvatarImage
                            src={profile?.avatar_url || "https://github.com/shadcn.png"}
                          />
                          <AvatarFallback className="bg-gradient-primary text-primary-foreground">
                            {loading
                              ? "..."
                              : profile?.full_name
                              ? profile.full_name
                                  .split(" ")
                                  .map((n) => n[0])
                                  .join("")
                                  .toUpperCase()
                              : user?.email
                              ? user.email[0].toUpperCase()
                              : "U"}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <h3 className="font-semibold text-lg">
                            {profile?.full_name || user?.email?.split("@")[0] || "User"}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            {profile?.email || user?.email || "No email"}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Member since{" "}
                            {profile?.created_at
                              ? new Date(profile.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  year: "numeric",
                                })
                              : user?.created_at
                              ? new Date(user.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  year: "numeric",
                                })
                              : "Unknown"}
                          </p>
                          <div className="flex items-center mt-1">
                            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                            <span className="text-xs text-green-600 font-medium">Online</span>
                          </div>
                        </div>
                      </div>

                      {statsError && (
                        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                          <p className="text-xs text-destructive">{statsError}</p>
                        </div>
                      )}

                      {/* User Stats */}
                      <div className="grid grid-cols-3 gap-2 mb-4 p-3 bg-muted rounded-lg">
                        <div className="text-center">
                          <p className="text-lg font-bold text-primary">
                            {statsLoading ? "..." : userStats.interviewsCompleted}
                          </p>
                          <p className="text-xs text-muted-foreground">Interviews</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-success">
                            {statsLoading ? "..." : `${userStats.averageScore}%`}
                          </p>
                          <p className="text-xs text-muted-foreground">Avg Score</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-accent">
                            {statsLoading ? "..." : `${userStats.atsScore}%`}
                          </p>
                          <p className="text-xs text-muted-foreground">ATS Score</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-gradient-to-r from-primary/10 to-accent/10 rounded-lg border border-primary/20">
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          <span className="text-sm font-medium">Premium Plan</span>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          Active
                        </Badge>
                      </div>
                    </div>

                    <Separator />

                    <div className="p-2">
                      <div className="flex flex-col space-y-1">
                        <Button
                          variant="ghost"
                          className="w-full justify-start h-10 px-3 hover:bg-accent"
                          onClick={() => handleProfileOption("settings")}
                        >
                          <Settings className="h-4 w-4 mr-3" />
                          <span className="text-sm font-medium">Settings</span>
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start h-10 px-3 hover:bg-accent"
                          onClick={() => handleProfileOption("help")}
                        >
                          <HelpCircle className="h-4 w-4 mr-3" />
                          <span className="text-sm font-medium">Help & Support</span>
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start h-10 px-3 hover:bg-accent"
                          onClick={() => handleProfileOption("privacy")}
                        >
                          <Shield className="h-4 w-4 mr-3" />
                          <span className="text-sm font-medium">Privacy & Security</span>
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start h-10 px-3 hover:bg-accent"
                          onClick={() => handleProfileOption("feedback")}
                        >
                          <Mail className="h-4 w-4 mr-3" />
                          <span className="text-sm font-medium">Send Feedback</span>
                        </Button>
                      </div>
                    </div>

                    <Separator />

                    <div className="p-2">
                      <Button
                        variant="ghost"
                        className="w-full justify-start h-10 px-3 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={async () => {
                          await signOut();
                          navigate("/login");
                        }}
                      >
                        <LogOut className="h-4 w-4 mr-3" />
                        <span className="text-sm font-medium">Sign Out</span>
                      </Button>
                    </div>
                  </PopoverContent>
                )}
              </Popover>
            </>
          )}
          
          {/* Theme Toggle - Always positioned on the right */}
          <DarkModeToggle className="scale-75" />
        </div>
      </div>
    </header>
  );
};

export default Header;

import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./components/ThemeContext";

import Index from "./pages/Index";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword"; 
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import Interview from "./pages/Interview";
import ATSChecker from "./pages/ATSChecker";
import ResumeUpload from "./pages/ResumeUpload";
import GrantPermissions from "./pages/GrantPermissions";
import NotFound from "./pages/NotFound";
import InterviewResults from "./pages/InterviewResults";
import Vlog from "./pages/Vlog";
import ProtectedRoute from "./components/auth/ProtectedRoute";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Public / open routes */}
            <Route path="/" element={<Index />} />
            <Route path="/vlog" element={<Vlog />} />
            <Route
              path="/login"
              element={
                
                  <Login />
                
              }
            />
            <Route
              path="/signup"
              element={               
                  <Signup />               
              }
            />
            <Route
              path="/forgot-password" 
              element={            
                  <ForgotPassword />           
              } 
              />

             <Route 
                path="/reset-password" 
                element={        
                    <ResetPassword />     
                } 
                /> 

            {/* Protected routes (only when signed in) */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/resume-upload"
              element={
                <ProtectedRoute>
                  <ResumeUpload />
                </ProtectedRoute>
              }
            />
            <Route
              path="/grant-permissions"
              element={
                <ProtectedRoute>
                  <GrantPermissions />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interview"
              element={
                <ProtectedRoute>
                  <Interview />
                </ProtectedRoute>
              }
            />
            <Route
              path="/InterviewResults"
              element={
                <ProtectedRoute>
                  <InterviewResults />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ats-checker"
              element={
                <ProtectedRoute>
                  <ATSChecker />
                </ProtectedRoute>
              }
            />
            
            {/* Catch-all / 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;

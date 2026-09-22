import { motion } from "framer-motion";
import { ReactNode } from "react";
import Header from "@/components/Header";

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
  heroImage?: string;
}

export const AuthLayout = ({ children, title, subtitle, heroImage }: AuthLayoutProps) => {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <Header showProfile={false} />
      
      {/* Content */}
      <div className="flex-1 flex">
        {/* Left Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md space-y-8"
        >
          <div className="text-center">
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-4xl font-bold bg-gradient-primary bg-clip-text text-transparent"
            >
              {title}
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-muted-foreground mt-2"
            >
              {subtitle}
            </motion.p>
          </div>
          {children}
        </motion.div>
      </div>

      {/* Right Side - Hero */}
      <div 
        className="hidden lg:flex lg:flex-1 relative overflow-hidden"
        style={{
          backgroundImage: heroImage ? `url(${heroImage})` : undefined,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }}
      >
        {/* Text positioned at center bottom */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="absolute bottom-8 left-0 right-0 text-center text-primary-foreground px-8"
        >
          <h2 className="text-3xl font-bold mb-4">AI-Powered Interviews</h2>
          <p className="text-lg opacity-90">
            Experience the future of hiring with our advanced gesture analysis and 
            intelligent question generation system.
          </p>
        </motion.div>
      </div>
      </div>
    </div>
  );
};

export default AuthLayout;
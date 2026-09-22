// src/pages/GrantPermissions.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { useToast } from '@/hooks/use-toast';
import { safeFetch } from '@/lib/api';
import { Home } from 'lucide-react';

const GrantPermissions: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [sessionExists, setSessionExists] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('interview_session');
    if (!stored) {
      setSessionExists(false);
      toast({
        title: "No session found",
        description: "Please upload your resume first.",
        variant: "destructive"
      });
      navigate('/resume-upload');
    }
  }, [navigate, toast]);

  const requestPermissions = async () => {
    setLoading(true);
    try {
      // ask for both mic and camera
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });

      // If we got here, permissions are granted
      // Stop tracks immediately — we only needed permission
      try {
        stream.getTracks().forEach((t) => t.stop());
      } catch {}

      // Update localStorage interview_session object
      const raw = localStorage.getItem('interview_session');
      if (!raw) throw new Error('Session missing. Please upload resume first.');

      const session = JSON.parse(raw);
      session.permissions = { mic: true, camera: true };
      session.permissions_granted = true;
      localStorage.setItem('interview_session', JSON.stringify(session));

      toast({ title: 'Permissions granted', description: 'Microphone & camera access granted.' });

      // Optionally start server-side monitoring early (non-blocking)
      try {
        await safeFetch('/api/start-monitoring', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: session.session_id, duration: 180 })
        });
        console.log('✅ Server-side monitoring requested.');
      } catch (e) {
        // Not fatal — interview can proceed without it
        console.warn('Could not start server monitoring yet:', e);
      }

      // Navigate to interview page
      setTimeout(() => navigate('/interview'), 600);
    } catch (err) {
      console.error('Permission error:', err);
      toast({
        title: "Permissions required",
        description: "Please allow microphone and camera access to continue.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  if (!sessionExists) return null;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full">
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Card>
            <CardContent className="p-8 text-center">
              <h2 className="text-2xl font-bold mb-4">Grant Microphone & Camera Access</h2>
              <p className="text-muted-foreground mb-6">
                We need permission to access your microphone and camera to record your answers and monitor interview behaviour for coaching feedback.
                Your data is processed securely and temporary media files will be deleted after processing.
              </p>

              <div className="flex items-center justify-center gap-4">
                <Button onClick={requestPermissions} disabled={loading}>
                  {loading ? 'Requesting...' : 'Allow Microphone & Camera'}
                </Button>

                <Button variant="outline" onClick={() => navigate('/resume-upload')} disabled={loading}>
                  Back
                </Button>

                <Button variant="ghost" onClick={() => navigate('/dashboard')} disabled={loading}>
                  <Home className="h-4 w-4 mr-2" />
                  Home
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default GrantPermissions;

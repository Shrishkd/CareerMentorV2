// src/pages/ResumeUpload.tsx
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, ArrowLeft, ArrowRight, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { motion } from 'framer-motion';
import Header from '@/components/Header';

// ✅ Define API base correctly
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const ResumeUpload: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (uploadedFile: File) => {
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('resume', uploadedFile);

      console.log('📤 Uploading resume to backend:', `${API_BASE}/api/upload-resume`);

      const res = await fetch(`${API_BASE}/api/upload-resume`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} : ${await res.text()}`);
      }

      const data = await res.json();

      if (data && data.session_id) {
        console.log('✅ Resume uploaded successfully');

        // Normalize session object and store it
        const sessionObj = {
          session_id: data.session_id,
          questions: data.questions || [],
          question_count: data.question_count || (data.questions ? data.questions.length : 0),
          resume_path: data.resume_path || null,
          created_at: new Date().toISOString(),
          permissions: { mic: false, camera: false },
          permissions_granted: false,
        };

        localStorage.setItem('interview_session', JSON.stringify(sessionObj));

        toast({
          title: "Resume Uploaded Successfully",
          description: `Generated ${sessionObj.question_count} personalized questions!`,
        });

        navigate('/grant-permissions');
      } else {
        throw new Error('Invalid response from server - no session ID received');
      }
    } catch (err) {
      console.error('❌ Upload failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);

      toast({
        title: "Upload Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      if (rejectedFiles.length > 0) {
        setError('Please upload only PDF files (max 10MB)');
        toast({
          title: "Invalid File",
          description: "Please upload only PDF files (max 10MB)",
          variant: "destructive",
        });
        return;
      }

      if (acceptedFiles.length > 0) {
        const uploadedFile = acceptedFiles[0];
        setFile(uploadedFile);
        setError(null);
        handleUpload(uploadedFile);
      }
    },
    [toast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: uploading ? () => {} : onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false,
    disabled: uploading,
  });

  const removeFile = () => {
    setFile(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <Header />
      
      <div className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Card>
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold mb-4">Upload your Resume (PDF)</h2>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded p-6 text-center ${
                  uploading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                } ${
                  isDragActive ? 'border-primary' : 'border-muted'
                }`}
              >
                <input {...getInputProps()} />
                {!file ? (
                  <div>
                    <Upload className="mx-auto mb-4" />
                    <p className="text-muted-foreground">Drag & drop a PDF here, or click to select</p>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <FileText />
                      <span>{file.name}</span>
                    </div>
                    <Button variant="ghost" onClick={removeFile}>
                      <X />
                    </Button>
                  </div>
                )}
              </div>

              {error && <p className="text-sm text-destructive mt-4">{error}</p>}

              {uploading && (
                <div className="mt-4 flex items-center justify-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  <p className="text-sm text-muted-foreground">Processing resume and generating questions...</p>
                </div>
              )}

              <div className="flex justify-between items-center mt-8">
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    onClick={() => navigate(-1)}
                    disabled={uploading}
                    className="flex items-center"
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>
                  
                  <Button
                    variant="ghost"
                    onClick={() => navigate('/dashboard')}
                    disabled={uploading}
                    className="flex items-center"
                  >
                    <Home className="h-4 w-4 mr-2" />
                    Home
                  </Button>
                </div>

                {file && !uploading && !error && (
                  <Button
                    onClick={() => navigate('/grant-permissions')}
                    className="bg-gradient-to-r from-primary to-accent hover:opacity-90 flex items-center"
                  >
                    Continue to Permissions
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.3 }} className="mt-8 text-center">
          <div className="flex items-center justify-center space-x-4 text-sm text-muted-foreground">
            <span className="text-primary font-medium">1. Start Interview</span>
            <span>→</span>
            <span className="text-primary font-medium bg-primary/10 px-3 py-1 rounded-full">2. Upload Resume</span>
            <span>→</span>
            <span>3. Grant Permissions</span>
            <span>→</span>
            <span>4. Interview Begins</span>
          </div>
        </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ResumeUpload;

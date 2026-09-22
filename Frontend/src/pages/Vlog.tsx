import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Calendar, Clock, User, PlayCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Header from "@/components/Header";

const CLOUDINARY_VIDEO_URL = "https://res.cloudinary.com/dks0vhj0j/video/upload/v1771953469/f3c8f04a-e800-44ae-951f-33fc2fb79c82_v9oyga.mp4";
// ☝️ Replace with your actual Cloudinary video URL

const Vlog = () => {
  const navigate = useNavigate();
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="mb-8"
        >
          <Button 
            variant="ghost" 
            onClick={() => navigate("/")}
            className="group pl-0 hover:pl-2 transition-all"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Button>
        </motion.div>

        <article className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Hero Video / Thumbnail */}
            <div className="relative aspect-video w-full overflow-hidden rounded-2xl mb-10 shadow-2xl group">

              {isPlaying ? (
                /* ── VIDEO MODE ── */
                <video
                  src={CLOUDINARY_VIDEO_URL}
                  autoPlay
                  controls
                  preload="metadata"
                  className="w-full h-full object-cover"
                  onEnded={() => setIsPlaying(false)}
                />
              ) : (
                /* ── THUMBNAIL MODE ── */
                <>
                  <img 
                    src="https://res.cloudinary.com/dks0vhj0j/image/upload/v1771743950/2024-02-29-09-14-23-588_locxin.jpg" 
                    alt="Founder Journey" 
                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-700 scale-105 group-hover:scale-100"
                  />
                  <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors duration-500" />

                  {/* Play Button — clickable */}
                  <div
                    className="absolute inset-0 flex items-center justify-center cursor-pointer z-10"
                    onClick={() => setIsPlaying(true)}
                  >
                    <PlayCircle className="w-20 h-20 text-white opacity-80 group-hover:opacity-100 group-hover:scale-110 transition-all duration-300 drop-shadow-lg" />
                  </div>

                  {/* Bottom Meta */}
                  <div className="absolute bottom-0 left-0 p-8 text-white w-full bg-gradient-to-t from-black/80 to-transparent pointer-events-none">
                    <div className="flex items-center space-x-6 text-sm font-medium">
                      <span className="flex items-center"><User className="h-4 w-4 mr-2" /> Founder</span>
                      <span className="flex items-center"><Calendar className="h-4 w-4 mr-2" /> Oct 2023</span>
                      <span className="flex items-center"><Clock className="h-4 w-4 mr-2" /> 12 min watch</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <h1 className="text-4xl md:text-6xl font-bold mb-8 leading-tight tracking-tight">
              Why I Built Career Mentor — <br/>
              <span className="text-primary">And Why It Matters.</span>
            </h1>

            <div className="prose prose-lg dark:prose-invert max-w-none">
              <p className="text-xl text-muted-foreground leading-relaxed mb-8 font-medium">
                The journey from a struggling job seeker to building an AI platform that empowers thousands wasn't easy. It started with a simple realization: the interview process is broken, and talent often goes unnoticed due to a lack of preparation resources.
              </p>

              <h2 className="text-3xl font-bold mt-16 mb-6">The Struggle</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                Years ago, I found myself in the same position as many of you. Resume in hand, skills sharpened, yet facing rejection after rejection. It wasn't a lack of technical ability, but a lack of understanding of what interviewers were truly looking for. The anxiety of the unknown, the pressure of the moment, and the silence after the interview were deafening.
              </p>

              <h2 className="text-3xl font-bold mt-16 mb-6">The Vision</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                I realized that what was missing was a safe space to fail. A place to practice, receive instant feedback, and improve without the stakes being life-altering. That's when the idea for Career Mentor was born. I wanted to democratize access to high-quality interview coaching, making it accessible to everyone, everywhere.
              </p>

              <div className="my-12 p-8 bg-muted/50 rounded-2xl border border-border/50 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-primary"></div>
                <p className="text-2xl font-serif italic text-foreground">
                  "We believe that everyone deserves a chance to land their dream job. This platform is my contribution to that belief."
                </p>
              </div>

              <h2 className="text-3xl font-bold mt-16 mb-6">The Mission</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                Today, Career Mentor is more than just code; it's a mission. We are here to level the playing field. Whether you are a fresh graduate or a seasoned professional pivoting careers, our AI-driven insights are designed to highlight your strengths and shore up your weaknesses.
              </p>
              
              <p className="text-lg leading-relaxed text-muted-foreground">
                Thank you for being a part of this journey. Let's build the future of your career, together.
              </p>
            </div>
          </motion.div>
        </article>
      </main>
    </div>
  );
};

export default Vlog;
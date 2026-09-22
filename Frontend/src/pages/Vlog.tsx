import { useState } from "react";
import { ArrowLeft, Calendar, Clock, User, PlayCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Header, { Footer } from "@/components/Header";

const CLOUDINARY_VIDEO_URL = "https://res.cloudinary.com/dks0vhj0j/video/upload/v1771953469/f3c8f04a-e800-44ae-951f-33fc2fb79c82_v9oyga.mp4";

const Vlog = () => {
  const navigate = useNavigate();
  const [isPlaying, setIsPlaying] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-6 py-12">
        <button
          onClick={() => navigate("/")}
          className="mb-8 inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to home
        </button>

        <article className="max-w-4xl mx-auto">
          <div>
            {/* Hero Video / Thumbnail */}
            <div className="relative aspect-video w-full overflow-hidden rounded-md border mb-10 group">

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

            <p className="eyebrow mb-4">Founder vlog</p>
            <h1 className="display text-4xl md:text-6xl mb-8 leading-[1.05]">
              Why I Built Career Mentor — <br/>
              <em className="text-accent">And Why It Matters.</em>
            </h1>

            <div className="prose prose-lg dark:prose-invert max-w-none">
              <p className="text-xl leading-relaxed mb-8">
                The journey from a struggling job seeker to building an AI platform that empowers thousands wasn't easy. It started with a simple realization: the interview process is broken, and talent often goes unnoticed due to a lack of preparation resources.
              </p>

              <h2 className="display text-3xl mt-16 mb-4">The Struggle</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                Years ago, I found myself in the same position as many of you. Resume in hand, skills sharpened, yet facing rejection after rejection. It wasn't a lack of technical ability, but a lack of understanding of what interviewers were truly looking for. The anxiety of the unknown, the pressure of the moment, and the silence after the interview were deafening.
              </p>

              <h2 className="display text-3xl mt-16 mb-4">The Vision</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                I realized that what was missing was a safe space to fail. A place to practice, receive instant feedback, and improve without the stakes being life-altering. That's when the idea for Career Mentor was born. I wanted to democratize access to high-quality interview coaching, making it accessible to everyone, everywhere.
              </p>

              <div className="my-12 border-l-2 border-accent pl-6">
                <p className="display text-3xl leading-snug text-foreground">
                  "We believe that everyone deserves a chance to land their dream job. This platform is my contribution to that belief."
                </p>
              </div>

              <h2 className="display text-3xl mt-16 mb-4">The Mission</h2>
              <p className="mb-6 text-lg leading-relaxed text-muted-foreground">
                Today, Career Mentor is more than just code; it's a mission. We are here to level the playing field. Whether you are a fresh graduate or a seasoned professional pivoting careers, our AI-driven insights are designed to highlight your strengths and shore up your weaknesses.
              </p>
              
              <p className="text-lg leading-relaxed text-muted-foreground">
                Thank you for being a part of this journey. Let's build the future of your career, together.
              </p>
            </div>
          </div>
        </article>
      </main>
      <Footer />
    </div>
  );
};

export default Vlog;
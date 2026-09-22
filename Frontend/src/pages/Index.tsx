import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, CheckCircle, Star } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Header, { Footer } from "@/components/Header";
import WhyChoose from "@/components/WhyChoose";
import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";

const stats = [
  { value: "10K+", label: "Interviews Conducted" },
  { value: "95%", label: "Success Rate" },
  { value: "4.5+", label: "User Rating" },
  { value: "50+", label: "Companies Trust Us" }
];

const feedbacks = [
  {
    name: "Rakesh K. Mishra",
    role: "Full Stack Developer",
    avatar: "/avatars/Rakesh.jpg",
    text:
      "Career Mentor generated resume-based MERN questions aligned with real interview rounds. The mock coding sessions boosted my confidence and helped me clear my final technical round."
  },
  {
    name: "Lukesh D. Zade",
    role: "Aerospace Engineer",
    avatar: "/avatars/Lukesh.jpg",
    text:
      "The AI mock interviews strengthened my technical explanations and communication. The performance scoring helped me secure my aerospace role."
  },
  {
    name: "Saumya",
    role: "Designer",
    avatar: "/avatars/Saumya.jpg",
    text:
      "Portfolio-based design questions improved my presentation clarity. The mock interviews increased my confidence significantly."
  },
  {
    name: "Suvankar Nayak",
    role: "Full Stack Developer",
    avatar: "/avatars/Suvankar.jpg",
    text:
      "System design and backend questions were perfectly aligned with my resume. The simulations helped me perform under pressure."
  },
  {
    name: "Priyanshu",
    role: "Data Analyst",
    avatar: "/avatars/Priyanshu.jpg",
    text:
      "The SQL and analytics mock sessions were extremely practical. The feedback improved my data storytelling and helped me get selected."
  },
  {
    name: "Priyansh Singh",
    role: "ML Engineer",
    avatar: "/avatars/Priyansh.jpg",
    text:
      "Resume-driven ML and system design questions were spot on. The voice-based simulation prepared me for real interviews."
  },
  {
    name: "Ayush Rathi",
    role: "Software Developer",
    avatar: "/avatars/Rathi.jpg",
    text:
      "The coding mock environment felt realistic. Performance analytics improved my clarity and time management."
  },
  {
    name: "Aparna Vats",
    role: "Tech Role",
    avatar: "/avatars/Aparna.jpg",
    text:
      "Personalized technical and HR questions made preparation focused. The feedback report strengthened my communication skills."
  },
  {
    name: "Aayushi Jha",
    role: "Backend Engineer",
    avatar: "/avatars/Aayushi.jpg",
    text:
      "Backend architecture questions were realistic and challenging. After multiple mock sessions, I confidently cleared my interview."
  }
];

function FilledStar(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={props.className}>
      <path d="M12 .587l3.668 7.431L24 9.748l-6 5.847L19.335 24 12 19.897 4.665 24 6 15.595 0 9.748l8.332-1.73z" />
    </svg>
  );
}

function HalfStar(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={props.className}>
      <defs>
        <clipPath id="left-half">
          <rect x="0" y="0" width="12" height="24" />
        </clipPath>
      </defs>
      <g clipPath="url(#left-half)">
        <path d="M12 .587l3.668 7.431L24 9.748l-6 5.847L19.335 24 12 19.897 4.665 24 6 15.595 0 9.748l8.332-1.73z" />
      </g>
    </svg>
  );
}

/* ========================= RESPONSIVE ========================= */

function useCardsPerView() {
  const [cards, setCards] = useState(3);

  useEffect(() => {
    const update = () => {
      if (window.innerWidth < 640) setCards(1);
      else if (window.innerWidth < 1024) setCards(2);
      else setCards(3);
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return cards;
}

/* ========================= ULTRA CAROUSEL ========================= */

export type FeedbackCarouselHandle = {
  pause: () => void;
  scheduleResumeAfterInactivity: () => void;
};

const FeedbackCarousel = forwardRef<FeedbackCarouselHandle, object>(function FeedbackCarousel(_, ref) {
  const cardsPerView = useCardsPerView();
  const total = feedbacks.length;
  const pages = Math.ceil(total / cardsPerView);

  const [page, setPage] = useState(1);
  const [paused, setPaused] = useState(false);
  const [isAnimating, setIsAnimating] = useState(true);

  const autoRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resumeRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastWheelTime = useRef(0);

  const cardWidth = 320;
  const gap = 24;
  const pageWidth = (cardWidth + gap) * cardsPerView;
  const WHEEL_THROTTLE_MS = 400;
  const WHEEL_DELTA_THRESHOLD = 18;
  const AUTO_SCROLL_INTERVAL_MS = 4500;
  const INACTIVITY_RESUME_MS = 2500;

  const carouselRef = useRef<HTMLDivElement>(null);

  const extendedPages = [
    pages - 1,
    ...Array.from({ length: pages }, (_, i) => i),
    0
  ];

  /* ================= AUTO SCROLL ================= */

  useEffect(() => {
    if (paused) return;

    autoRef.current = setInterval(() => {
      setPage((p) => {
        if (p >= pages + 1) return 1;
        return p + 1;
      });
    }, AUTO_SCROLL_INTERVAL_MS);

    return () => {
      if (autoRef.current) clearInterval(autoRef.current);
    };
  }, [paused, pages, AUTO_SCROLL_INTERVAL_MS]);

  const stopAutoAndResumeAfterInactivity = useCallback(() => {
    setPaused(true);
    if (resumeRef.current) clearTimeout(resumeRef.current);
    resumeRef.current = setTimeout(() => {
      setPaused(false);
      resumeRef.current = null;
    }, INACTIVITY_RESUME_MS);
  }, []);

  const handleMouseEnter = useCallback(() => {
    setPaused(true);
    if (resumeRef.current) {
      clearTimeout(resumeRef.current);
      resumeRef.current = null;
    }
  }, []);

  const handleMouseLeave = () => {
    stopAutoAndResumeAfterInactivity();
  };

  useImperativeHandle(ref, () => ({
    pause: handleMouseEnter,
    scheduleResumeAfterInactivity: stopAutoAndResumeAfterInactivity
  }), [handleMouseEnter, stopAutoAndResumeAfterInactivity]);

  /* ================= WHEEL (RIGHT = NEXT, THROTTLED + CLAMPED) ================= */

  const handleWheel = useCallback(
    (e: WheelEvent) => {
      if (Math.abs(e.deltaX) < WHEEL_DELTA_THRESHOLD) return;
      const now = Date.now();
      if (now - lastWheelTime.current < WHEEL_THROTTLE_MS) return;
      lastWheelTime.current = now;

      e.preventDefault();
      stopAutoAndResumeAfterInactivity();
      const steps = Math.abs(e.deltaX) > 100 ? 2 : 1;

      if (e.deltaX > 0) {
        setPage((p) => Math.min(pages + 1, p + steps));
      } else {
        setPage((p) => Math.max(0, p - steps));
      }
    },
    [pages, stopAutoAndResumeAfterInactivity]
  );

  useEffect(() => {
    const el = carouselRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  /* ================= CLONE SNAP FIX ================= */

  const handleAnimationComplete = useCallback(() => {
    if (page === pages + 1) {
      setIsAnimating(false);
      setPage(1);
    }
    if (page === 0) {
      setIsAnimating(false);
      setPage(pages);
    }
  }, [page, pages]);

  useEffect(() => {
    if (!isAnimating) {
      const id = requestAnimationFrame(() => setIsAnimating(true));
      return () => cancelAnimationFrame(id);
    }
  }, [isAnimating]);

  const translateX = page * pageWidth;

  return (
    <div
      ref={carouselRef}
      className="w-full py-2 min-h-[320px]"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onTouchStart={stopAutoAndResumeAfterInactivity}
      onTouchEnd={stopAutoAndResumeAfterInactivity}
    >
      <div
        className="relative overflow-hidden mx-auto"
        style={{
          width: pageWidth + 140,
          perspective: "1600px"
        }}
        onMouseEnter={handleMouseEnter}
      >
      <motion.div
        className="flex"
        animate={{ x: -translateX }}
        transition={
          isAnimating
            ? { type: "spring", stiffness: 48, damping: 24 }
            : { duration: 0 }
        }
        style={{
          gap: `${gap}px`,
          padding: "0 70px"
        }}
        onAnimationComplete={handleAnimationComplete}
      >
        {extendedPages.map((pageIndex, pIndex) => {
          const start = pageIndex * cardsPerView;

          return Array.from({ length: cardsPerView }).map(
            (_, i) => {
              const actual =
                (start + i + total) % total;

              const isCenterPage = pIndex === page;

              return (
                <motion.div
                  key={`${pIndex}-${i}`}
                  style={{
                    minWidth: cardWidth,
                    height: 280
                  }}
                  animate={{
                    scale: isCenterPage ? 1 : 0.92,
                    rotateY: isCenterPage ? 0 : i === 0 ? 18 : -18,
                    opacity: isCenterPage ? 1 : 0.5
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 90,
                    damping: 20
                  }}
                  className="transform-gpu"
                >
                  <Card className="h-full shadow-2xl">
                    <CardContent className="p-6">
                      <div className="flex items-center mb-4">
                        <img
                          src={feedbacks[actual].avatar}
                          alt={feedbacks[actual].name}
                          className="w-12 h-12 rounded-full mr-3 object-cover"
                        />
                        <div>
                          <div className="font-semibold">
                            {feedbacks[actual].name}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {feedbacks[actual].role}
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {feedbacks[actual].text}
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            }
          );
        })}
      </motion.div>

      {/* DOTS */}
      <div className="flex justify-center mt-6 gap-3">
        {Array.from({ length: pages }).map((_, i) => {
          const active =
            ((page - 1 + pages) % pages) === i;

          return (
            <button
              key={i}
              type="button"
              onClick={() => {
                stopAutoAndResumeAfterInactivity();
                setPage(i + 1);
              }}
              className={`w-3 h-3 rounded-full transition-all ${
                active
                  ? "bg-accent scale-125"
                  : "bg-gray-300"
              }`}
              aria-label={`Go to page ${i + 1}`}
            />
          );
        })}
      </div>
      </div>
    </div>
  );
});

const Index = () => {
  const navigate = useNavigate();
  const feedbackCarouselRef = useRef<FeedbackCarouselHandle>(null);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <section className="relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{
            backgroundImage: 'url(https://res.cloudinary.com/dks0vhj0j/image/upload/v1763843867/Home_page_hgygpk.png)'
          }}
        >
        </div>
        <div className="relative container mx-auto px-6 py-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center text-primary-foreground max-w-4xl mx-auto"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="inline-flex items-center space-x-2 bg-primary-foreground/10 backdrop-blur-sm px-4 py-2 rounded-full mb-6"
            >
              <Star className="h-4 w-4 text-warning" />
              <span className="text-sm">Trusted by 50+ Companies Worldwide</span>
            </motion.div>

            <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
              Master Your{" "}
              <span className="bg-gradient-to-r from-primary-glow to-accent bg-clip-text text-transparent">
                AI Interview
              </span>{" "}
              Skills
            </h1>
            
            <p className="text-xl md:text-2xl mb-8 opacity-90 leading-relaxed">
              Practice with our advanced AI platform featuring real-time gesture analysis,
              intelligent question generation, and comprehensive performance insights.
            </p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4"
            >
              <Button 
                size="lg"
                onClick={() => navigate("/resume-upload")}
                className="bg-primary-foreground text-primary hover:bg-primary-foreground/90 shadow-glow px-8 py-4 text-lg"
              >
                Start Mock Interview
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
              <Button 
                variant="secondary" 
                size="lg"
                onClick={() => navigate("/ats-checker")}
                className="bg-white/20 backdrop-blur-sm text-white border-white/30 hover:bg-white/30 px-8 py-4 text-lg"
              >
                Check Resume Score
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      <section className="py-16 bg-muted/30">
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center"
          >
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1, duration: 0.6 }}
              >
                {stat.label === "User Rating" ? (
                  <>
                    <h3 className="text-4xl font-bold text-primary mb-2">{stat.value}</h3>
                    <div className="flex items-center justify-center mb-2 space-x-1 text-yellow-400">
                      <FilledStar className="h-5 w-5 text-yellow-400" />
                      <FilledStar className="h-5 w-5 text-yellow-400" />
                      <FilledStar className="h-5 w-5 text-yellow-400" />
                      <FilledStar className="h-5 w-5 text-yellow-400" />
                      <HalfStar className="h-5 w-5 text-yellow-400" />
                    </div>
                  </>
                ) : (
                  <h3 className="text-4xl font-bold text-primary mb-2">{stat.value}</h3>
                )}
                <p className="text-muted-foreground">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <WhyChoose />

      {/* Founder Vlog Section */}
      <section className="py-20 container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="relative rounded-[2rem] overflow-hidden min-h-[550px] flex items-center shadow-2xl"
        >
          {/* Background Image with Grayscale */}
          <div className="absolute inset-0">
            <img 
              src="https://res.cloudinary.com/dks0vhj0j/image/upload/v1771743950/2024-02-29-09-14-23-588_locxin.jpg" 
              alt="Founder" 
              className="w-full h-full object-cover grayscale"
            />
            {/* Gradient Overlay for Text Readability */}
            <div className="absolute inset-0 bg-gradient-to-r from-background via-background/95 to-transparent opacity-100" />
          </div>

          {/* Content */}
          <div className="relative z-10 max-w-2xl p-8 md:p-16">
            <Badge variant="outline" className="mb-6 border-primary text-primary bg-primary/10 px-4 py-1 text-xs tracking-widest uppercase">
              Founder Vlog
            </Badge>
            
            <h2 className="text-3xl md:text-5xl font-bold mb-6 leading-tight">
              Why I Built Career Mentor — <br/>And Why It Matters.
            </h2>
            
            <p className="text-lg text-muted-foreground mb-8 leading-relaxed max-w-lg">
              From personal struggles in the job market to building a platform that empowers thousands. 
              Discover the story behind our mission to democratize interview preparation and help you succeed.
            </p>

            <Button 
              size="lg"
              onClick={() => navigate("/vlog")}
              className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg group rounded-full px-8"
            >
              Watch My Journey
              <ArrowRight className="h-5 w-5 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </Button>
          </div>
        </motion.div>
      </section>

      <section className="py-16 bg-muted/10">
        <div className="container mx-auto px-6">
          <div
            onMouseEnter={() => feedbackCarouselRef.current?.pause()}
            onMouseLeave={() => feedbackCarouselRef.current?.scheduleResumeAfterInactivity()}
          >
            <div className="text-center mb-8">
              <h3 className="text-3xl font-bold">what they says..</h3>
            </div>

            <FeedbackCarousel ref={feedbackCarouselRef} />
          </div>
        </div>
      </section>

      <section className="py-20 bg-gradient-secondary">
        <div className="container mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl mx-auto text-primary-foreground"
          >
            <h2 className="text-4xl font-bold mb-6">
              Ready to Ace Your Next Interview?
            </h2>
            <p className="text-xl mb-8 opacity-90">
              Join thousands of professionals who have improved their interview skills
              with our AI-powered platform.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
              <Button 
                size="lg"
                onClick={() => navigate("/resume-upload")}
                className="bg-primary-foreground text-primary hover:bg-primary-foreground/90 px-8 py-4 text-lg"
              >
                Get Started Now
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
              <div className="flex items-center space-x-2 text-sm opacity-75">
                <CheckCircle className="h-4 w-4" />
                <span>No sign-up required</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Index;

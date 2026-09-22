import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Camera,
  TrendingUp,
  Award,
  BookOpen,
  FileText,
  Clock,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useUserStats } from "@/hooks/useUserStats";
import Header from "@/components/Header";

// Skeleton placeholder
const SkeletonBox = ({ className }: { className: string }) => (
  <div className={`animate-pulse bg-muted rounded-lg ${className}`} />
);

const getStatsData = (userStats: any, statsLoading: boolean) => [
  {
    title: "Interviews Completed",
    value: statsLoading ? "..." : userStats?.interviews_completed?.toString() || "0",
    icon: Clock,
    change: statsLoading
      ? "Loading..."
      : (userStats?.interviews_completed || 0) > 0
      ? "+1 this week"
      : "No interviews yet",
    color: "text-primary",
  },
  {
    title: "Average Score",
    value: statsLoading ? "..." : userStats?.average_score?.toString() || "0",
    icon: Award,
    change: statsLoading
      ? "Loading..."
      : (userStats?.average_score || 0) > 0
      ? "+5% improvement"
      : "Start your first interview",
    color: "text-success",
  },
  {
    title: "ATS Score",
    value: statsLoading ? "..." : `${userStats?.ats_score || 0}%`,
    icon: FileText,
    change: statsLoading
      ? "Loading..."
      : (userStats?.ats_score || 0) > 0
      ? "Excellent match"
      : "Upload resume to check",
    color: "text-accent",
  },
];

const getRecentInterviews = (userStats: any, statsLoading: boolean) => {
  if (statsLoading || !userStats?.recent_interviews?.length) {
    return [
      {
        date: "No interviews yet",
        score: 0,
        position: "Start your first interview",
        status: "pending",
      },
    ];
  }
  return userStats.recent_interviews.map((interview: any) => ({
    date: interview.date ? new Date(interview.date).toLocaleDateString() : "Unknown date",
    score: interview.score || 0,
    position: interview.position || "Interview",
    status: interview.status || "completed",
  }));
};

const suggestedCourses = [
  { title: "Advanced React Patterns", difficulty: "Intermediate", duration: "4 weeks" },
  { title: "System Design Fundamentals", difficulty: "Advanced", duration: "6 weeks" },
  { title: "TypeScript Mastery", difficulty: "Intermediate", duration: "3 weeks" },
];

export const Dashboard = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const {
    stats: userStats,
    loading: statsLoading,
    error: statsError,
  } = useUserStats(user ? user.id : null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      navigate("/login");
    }
  }, [user, loading, navigate]);

  // Skeleton layout while auth is loading
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center">
        <SkeletonBox className="h-32 w-32 mb-4" />
        <p className="text-muted-foreground">Loading your dashboard...</p>
      </div>
    );
  }

  // Don't render if not authenticated
  if (!user) {
    return null;
  }

  const handleStartInterview = () => navigate("/resume-upload");
  const handleATSCheck = () => navigate("/ats-checker");

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <Header />

      <div className="container mx-auto px-6 py-8">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card
              className="cursor-pointer transition-all duration-300 hover:shadow-primary hover:scale-105"
              onClick={handleStartInterview}
            >
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-primary rounded-lg flex items-center justify-center">
                    <Camera className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">Start AI Interview</h3>
                    <p className="text-muted-foreground">Begin your practice session</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card
              className="cursor-pointer transition-all duration-300 hover:shadow-primary hover:scale-105"
              onClick={handleATSCheck}
            >
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-primary rounded-lg flex items-center justify-center">
                    <FileText className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">ATS Score Checker</h3>
                    <p className="text-muted-foreground">Optimize your resume</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.1 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold mb-4">Performance Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {getStatsData(userStats, statsLoading).map((stat, index) => (
              <motion.div
                key={stat.title}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1 * index }}
              >
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">
                          {stat.title}
                        </p>
                        <div className="flex items-center space-x-2">
                          <p className="text-3xl font-bold">{stat.value}</p>
                          {stat.title === "Average Score" && (
                            <span className="text-lg">%</span>
                          )}
                        </div>
                        <p className="text-sm text-success">{stat.change}</p>
                      </div>
                      <stat.icon className={`h-8 w-8 ${stat.color}`} />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Interviews */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Recent Interviews</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {getRecentInterviews(userStats, statsLoading).map(
                    (interview, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-muted rounded-lg"
                      >
                        <div>
                          <p className="font-medium">{interview.position}</p>
                          <p className="text-sm text-muted-foreground">
                            {interview.date}
                          </p>
                        </div>
                        <div className="text-right">
                          {interview.score > 0 ? (
                            <Badge variant="secondary" className="mb-1">
                              {interview.score}%
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="mb-1">
                              No score
                            </Badge>
                          )}
                          <p className="text-xs text-muted-foreground capitalize">
                            {interview.status}
                          </p>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Suggested Courses */}
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BookOpen className="h-5 w-5" />
                  <span>Recommended Courses</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {suggestedCourses.map((course, index) => (
                    <div key={index} className="p-3 bg-muted rounded-lg">
                      <h4 className="font-medium mb-2">{course.title}</h4>
                      <div className="flex items-center justify-between text-sm">
                        <Badge variant="outline">{course.difficulty}</Badge>
                        <span className="text-muted-foreground">
                          {course.duration}
                        </span>
                      </div>
                      <Progress value={Math.random() * 100} className="mt-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

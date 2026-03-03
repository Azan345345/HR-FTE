import { useState, useCallback, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import {
  TopBar,
  LeftSidebar,
  ViewType,
  CenterPanel,
  RightSidebar,
  SettingsModal,
  JobsView,
  ObservabilityView,
  InterviewPrepView,
  SeeingInView
} from "@/components";
import { CommandPalette } from "@/components/CommandPalette";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { useAuthStore } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { listChatSessions, getProfile, saveProfile } from "@/services/api";

type AppState = "welcome" | "transitioning" | "onboarding" | "workspace";

const Index = () => {
  const [appState, setAppState] = useState<AppState>("welcome");
  const [firstMessage, setFirstMessage] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeView, setActiveView] = useState<ViewType>("chat");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [focusedJobId, setFocusedJobId] = useState<string | null>(null);

  const { isAuthenticated, signup, login, token } = useAuthStore();

  // Auto-transition after auth — check onboarding status first
  useEffect(() => {
    if (isAuthenticated && appState === "welcome") {
      getProfile()
        .then((profile) => {
          // Only show onboarding when explicitly set to false (new accounts).
          // null/undefined means an existing user — send straight to workspace.
          if (profile.onboarding_completed === false) {
            setAppState("onboarding");
          } else {
            setAppState("workspace");
          }
        })
        .catch(() => {
          // If profile fetch fails, go straight to workspace to avoid blocking login
          setAppState("workspace");
        });
    } else if (!isAuthenticated && (appState === "workspace" || appState === "onboarding")) {
      setAppState("welcome");
    }
  }, [isAuthenticated, appState]);

  const handleOnboardingComplete = useCallback(async () => {
    await saveProfile({ onboarding_completed: true }).catch(() => {});
    setAppState("workspace");
  }, []);

  // Connect to WebSocket for real-time observability
  const { isConnected: wsConnected } = useWebSocket(isAuthenticated && appState === "workspace" ? token : null);

  const fetchSessions = useCallback(() => {
    setLoadingSessions(true);
    listChatSessions()
      .then(data => {
        setSessions(data.sessions.slice(0, 5) || []);
        setLoadingSessions(false);
      })
      .catch(err => {
        console.error("Failed to fetch sessions:", err);
        setLoadingSessions(false);
      });
  }, []);

  useEffect(() => {
    if (isAuthenticated && appState === "workspace") {
      fetchSessions();
    }
  }, [isAuthenticated, appState, activeSessionId, fetchSessions]);

  // Listen for navigate-to-interview events fired by InterviewPrepCard's "Start Mock Interview" button
  useEffect(() => {
    const handler = (e: Event) => {
      const { jobId } = (e as CustomEvent).detail;
      if (jobId) setFocusedJobId(jobId);
      setActiveView("interview_prep");
    };
    window.addEventListener("navigate-to-interview", handler);
    return () => window.removeEventListener("navigate-to-interview", handler);
  }, []);

  const handleWelcomeSubmit = useCallback(() => {
    setAppState("transitioning");
    // After transition animation, the isAuthenticated effect will route to onboarding or workspace
    setTimeout(() => {
      getProfile()
        .then((profile) => {
          setAppState(profile.onboarding_completed === false ? "onboarding" : "workspace");
        })
        .catch(() => setAppState("workspace"));
    }, 1200);
  }, []);

  return (
    <div className="w-screen h-screen overflow-hidden bg-background">
      <AnimatePresence mode="wait">
        {(appState === "welcome" || appState === "transitioning") && (
          <WelcomeScreen
            key="welcome"
            onSubmit={handleWelcomeSubmit}
            isExiting={appState === "transitioning"}
          />
        )}
      </AnimatePresence>

      {appState === "onboarding" && (
        <OnboardingFlow onComplete={handleOnboardingComplete} />
      )}

      {appState === "workspace" && (
        <div className="flex flex-col h-full w-full">
          <TopBar />
          <div className="flex flex-1 overflow-hidden">
            <LeftSidebar
              onOpenSettings={() => setSettingsOpen(true)}
              activeView={activeView}
              onViewChange={(v) => { setActiveView(v); if (v !== "interview_prep") setFocusedJobId(null); }}
              activeSessionId={activeSessionId}
              onSessionChange={setActiveSessionId}
              sessions={sessions}
              loading={loadingSessions}
            />
            {activeView === "chat" ? (
              <>
                <div className="flex-1 min-w-0">
                  <CenterPanel
                    activeSessionId={activeSessionId}
                    onSessionCreated={setActiveSessionId}
                  />
                </div>
                <RightSidebar />
              </>
            ) : activeView === "jobs" ? (
              <div className="flex-1 min-w-0">
                <JobsView onNavigateToInterview={(jobId) => {
                  setFocusedJobId(jobId);
                  setActiveView("interview_prep");
                }} />
              </div>
            ) : activeView === "interview_prep" ? (
              <div className="flex-1 min-w-0">
                <InterviewPrepView focusedJobId={focusedJobId} />
              </div>
            ) : activeView === "seeing_in" ? (
              <div className="flex-1 min-w-0">
                <SeeingInView />
              </div>
            ) : (
              <div className="flex-1 min-w-0">
                <ObservabilityView />
              </div>
            )}
          </div>
          <CommandPalette
            onOpenSettings={() => setSettingsOpen(true)}
            onViewChange={setActiveView}
            onSessionChange={setActiveSessionId}
            recentSessions={sessions}
          />
          <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
        </div>
      )}
    </div>
  );
};

export default Index;

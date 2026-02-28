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
import { useAuthStore } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { listChatSessions } from "@/services/api";

type AppState = "welcome" | "transitioning" | "workspace";

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

  // Auto-transition to workspace if already authenticated on mount
  useEffect(() => {
    if (isAuthenticated && appState === "welcome") {
      setAppState("workspace");
    } else if (!isAuthenticated && appState === "workspace") {
      setAppState("welcome");
    }
  }, [isAuthenticated, appState]);

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

  const handleWelcomeSubmit = useCallback(() => {
    setAppState("transitioning");
    setTimeout(() => setAppState("workspace"), 1200);
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

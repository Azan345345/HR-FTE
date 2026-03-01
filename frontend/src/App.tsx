import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { toast } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import GmailSetupGuide from "./pages/GmailSetupGuide";

const queryClient = new QueryClient();

const GMAIL_ERROR_MESSAGES: Record<string, string> = {
  access_denied:          "You denied Gmail access. Connect again when you're ready.",
  missing_params:         "OAuth callback was missing required parameters. Please try again.",
  invalid_state:          "Session expired or security check failed. Please try connecting again.",
  user_not_found:         "Could not find your account. Please log in and try again.",
  token_exchange_failed:  "Google refused the token exchange. Please try again.",
  no_refresh_token:       "Google didn't return a refresh token. Revoke app access in your Google Account settings, then reconnect.",
};

/** Detects ?gmail_connected=1 or ?gmail_error=... after OAuth redirect and shows a toast. */
function GmailOAuthHandler() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const connected = params.get("gmail_connected");
    const error = params.get("gmail_error");

    if (connected === "1") {
      toast.success("Gmail connected!", {
        description: "CareerAgent can now send application emails on your behalf.",
        duration: 5000,
      });
      params.delete("gmail_connected");
      navigate({ search: params.toString() }, { replace: true });
    } else if (error) {
      toast.error("Gmail connection failed", {
        description: GMAIL_ERROR_MESSAGES[error] ?? `Error: ${error}`,
        duration: 8000,
      });
      params.delete("gmail_error");
      navigate({ search: params.toString() }, { replace: true });
    }
  }, [location.search, navigate]);

  return null;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <GmailOAuthHandler />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/gmail-setup" element={<GmailSetupGuide />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

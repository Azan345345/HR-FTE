import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exchangeGoogleCode } from "@/services/api";

/**
 * Handles the Google OAuth2 redirect after user grants Gmail permissions.
 * Google redirects here with ?code=... after consent.
 * We POST the code to the backend to exchange for tokens, then redirect home.
 */
export default function GoogleCallback() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const error = params.get("error");

    if (error) {
      setStatus("error");
      setErrorMsg(error === "access_denied" ? "You denied Gmail access." : `Google error: ${error}`);
      return;
    }

    if (!code) {
      setStatus("error");
      setErrorMsg("No authorization code received from Google.");
      return;
    }

    exchangeGoogleCode(code)
      .then(() => {
        setStatus("success");
        setTimeout(() => navigate("/"), 1500);
      })
      .catch((err) => {
        setStatus("error");
        setErrorMsg(err?.message || "Failed to exchange code for tokens.");
      });
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="bg-white rounded-2xl shadow-xl p-10 max-w-sm w-full text-center space-y-4">
        {status === "loading" && (
          <>
            <div className="w-10 h-10 border-4 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-slate-600 font-sans text-sm">Connecting your Gmail account...</p>
          </>
        )}
        {status === "success" && (
          <>
            <div className="text-4xl">✅</div>
            <p className="text-slate-800 font-semibold font-sans">Gmail Connected!</p>
            <p className="text-slate-400 text-xs font-sans">Redirecting you back...</p>
          </>
        )}
        {status === "error" && (
          <>
            <div className="text-4xl">❌</div>
            <p className="text-slate-800 font-semibold font-sans">Connection Failed</p>
            <p className="text-rose-500 text-xs font-sans">{errorMsg}</p>
            <button
              onClick={() => navigate("/")}
              className="mt-4 px-4 py-2 bg-rose-500 text-white rounded-lg text-sm font-bold hover:bg-rose-600 transition-colors"
            >
              Go Back
            </button>
          </>
        )}
      </div>
    </div>
  );
}

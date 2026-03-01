/**
 * Step-by-step guide on how to get Google OAuth credentials for Gmail.
 */
export default function GmailSetupGuide() {
  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <a
            href="/"
            className="text-sm text-slate-400 hover:text-slate-700 font-sans transition-colors mb-6 inline-block"
          >
            ← Back to CareerAgent
          </a>
          <h1 className="font-serif text-4xl font-bold text-slate-900 mb-3">
            How to Get Google OAuth Credentials
          </h1>
          <p className="text-slate-500 font-sans text-base">
            To connect your Gmail account, you need a Google Cloud OAuth 2.0 Client ID and Client Secret.
            This takes about 5–10 minutes and is completely free.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-6">

          {/* Step 1 */}
          <StepCard
            number={1}
            title="Create or open a Google Cloud project"
            description={
              <>
                <p>Go to the <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-rose-600 underline font-semibold">Google Cloud Console</a> and sign in with your Google account.</p>
                <ul className="list-disc list-inside mt-2 space-y-1 text-slate-600">
                  <li>Click the project dropdown at the top of the page.</li>
                  <li>Click <strong>New Project</strong>, give it a name (e.g. "CareerAgent"), and click <strong>Create</strong>.</li>
                  <li>Select the new project from the dropdown.</li>
                </ul>
              </>
            }
          />

          {/* Step 2 */}
          <StepCard
            number={2}
            title="Enable the Gmail API"
            description={
              <>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>In the left sidebar go to <strong>APIs &amp; Services → Library</strong>.</li>
                  <li>Search for <strong>"Gmail API"</strong> and click on it.</li>
                  <li>Click <strong>Enable</strong>.</li>
                </ul>
                <p className="mt-2 text-slate-500 text-sm">You may also want to enable the <strong>Google Drive API</strong> and <strong>Google Docs API</strong> for full functionality.</p>
              </>
            }
          />

          {/* Step 3 */}
          <StepCard
            number={3}
            title="Configure the OAuth consent screen"
            description={
              <>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>Go to <strong>APIs &amp; Services → OAuth consent screen</strong>.</li>
                  <li>Select <strong>External</strong> and click <strong>Create</strong>.</li>
                  <li>Fill in the required fields:
                    <ul className="list-disc list-inside ml-4 mt-1 space-y-1 text-slate-500">
                      <li><strong>App name:</strong> CareerAgent (or anything you like)</li>
                      <li><strong>User support email:</strong> your email</li>
                      <li><strong>Developer contact email:</strong> your email</li>
                    </ul>
                  </li>
                  <li>Click <strong>Save and Continue</strong> through the remaining screens (Scopes and Test users are optional at this stage).</li>
                </ul>
              </>
            }
          />

          {/* Step 4 */}
          <StepCard
            number={4}
            title="Create OAuth 2.0 credentials"
            description={
              <>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>Go to <strong>APIs &amp; Services → Credentials</strong>.</li>
                  <li>Click <strong>+ Create Credentials → OAuth client ID</strong>.</li>
                  <li>For <strong>Application type</strong>, select <strong>Web application</strong>.</li>
                  <li>Give it a name (e.g. "CareerAgent Web Client").</li>
                </ul>
              </>
            }
          />

          {/* Step 5 — Authorized redirect URIs */}
          <StepCard
            number={5}
            title="Add the authorized redirect URI"
            highlight
            description={
              <>
                <p className="text-slate-700 font-semibold mb-2">This step is critical.</p>
                <p className="text-slate-600 mb-3">Under <strong>Authorized redirect URIs</strong>, click <strong>+ Add URI</strong> and enter:</p>
                <div className="bg-slate-900 text-green-400 font-mono text-sm px-4 py-3 rounded-xl mb-3 break-all select-all">
                  {window.location.origin}/settings/google-callback
                </div>
                <p className="text-slate-500 text-sm">
                  This tells Google where to send users after they approve access.
                  The URL above is specific to <strong>your</strong> CareerAgent instance.
                </p>
                <ul className="list-disc list-inside mt-3 space-y-1 text-slate-600">
                  <li>Click <strong>Create</strong>.</li>
                  <li>A popup will show your <strong>Client ID</strong> and <strong>Client Secret</strong>. Copy both — you'll need them in the next step.</li>
                </ul>
              </>
            }
          />

          {/* Step 6 */}
          <StepCard
            number={6}
            title="Enter credentials in CareerAgent Settings"
            description={
              <>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>Open <strong>CareerAgent → Settings → Integrations</strong>.</li>
                  <li>Paste your <strong>Client ID</strong> and <strong>Client Secret</strong>.</li>
                  <li>Click <strong>Save Credentials</strong>.</li>
                  <li>Then click <strong>Connect Gmail</strong> to authorize your Gmail account.</li>
                </ul>
              </>
            }
          />

          {/* Step 7 — Add test user if app is in testing */}
          <StepCard
            number={7}
            title="(Optional) Add yourself as a test user"
            description={
              <>
                <p className="text-slate-600">
                  If your Google Cloud app is still in <strong>Testing</strong> mode (not published), only
                  accounts listed as test users can complete the OAuth flow.
                </p>
                <ul className="list-disc list-inside mt-2 space-y-1 text-slate-600">
                  <li>Go to <strong>OAuth consent screen → Test users</strong>.</li>
                  <li>Click <strong>+ Add users</strong> and add your Gmail address.</li>
                  <li>Click <strong>Save</strong>.</li>
                </ul>
              </>
            }
          />

        </div>

        {/* Footer CTA */}
        <div className="mt-10 p-6 bg-white border border-slate-100 rounded-2xl shadow-sm text-center">
          <p className="text-slate-700 font-semibold font-sans mb-3">Ready to connect?</p>
          <a
            href="/"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-rose-500 text-white rounded-xl text-sm font-bold hover:bg-rose-600 transition-colors"
          >
            Go to Settings → Integrations
          </a>
        </div>
      </div>
    </div>
  );
}


function StepCard({
  number,
  title,
  description,
  highlight = false,
}: {
  number: number;
  title: string;
  description: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={`bg-white rounded-2xl border p-6 shadow-sm ${highlight ? "border-rose-200" : "border-slate-100"}`}>
      <div className="flex gap-4">
        <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center text-sm font-bold ${highlight ? "bg-rose-500 text-white" : "bg-slate-100 text-slate-700"}`}>
          {number}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 font-sans mb-2">{title}</h3>
          <div className="text-sm font-sans space-y-1">{description}</div>
        </div>
      </div>
    </div>
  );
}

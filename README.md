# RDP Canary (Android)

An open-source, self-hosted synthetic monitor for RDP-reachable hosts — but running as
an Android app instead of a Windows/PowerShell script. It periodically opens a TCP
connection to your server's RDP port (3389 by default), times how long the handshake
takes, stores the result locally, and shows you a history / status list. On failure it
fires a local notification. You can export the log as CSV and share it straight to
Google Drive (or anywhere else) using Android's normal Share sheet — no Google API
credentials required.

**Important scope note:** Android has no supported way to perform a *full* RDP
protocol login (that requires an RDP client stack like FreeRDP, which is heavyweight
and not something to run headless in the background on a phone). This app instead does
a **TCP-level canary check** — it opens a socket to `host:3389` and measures how long
the handshake/connect takes, which is exactly what most "is RDP up" monitors actually
care about (the PowerShell version you referenced does the same thing under the hood).
If you need true login-level verification, keep a small always-on machine running the
PowerShell script from your original plan, and use this app as your on-the-go status
viewer instead — see "Optional: sync with the Windows script" below.

## Features
- Add one or more targets (`host:port`, defaults to port 3389)
- Background checks every 15 minutes via WorkManager (Android's minimum periodic
  interval — see note below if you want tighter intervals)
- Local Room database log: timestamp, target, status, response time (ms), error
- Local notification on failure
- Export full log to CSV and share (Drive, email, Files app, etc.)
- No cloud backend, no accounts, no telemetry

## Project layout
```
rdp-canary-android/
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/rdpcanary/app/
│       │   ├── MainActivity.kt
│       │   ├── data/            # Room entity, DAO, database
│       │   ├── work/            # WorkManager background checker
│       │   └── ui/              # RecyclerView adapter
│       └── res/                 # layouts, strings
├── build.gradle.kts
├── settings.gradle.kts
└── LICENSE
```

## Building it
1. Install [Android Studio](https://developer.android.com/studio) (free).
2. `File → Open` this folder.
3. Let Gradle sync (first sync downloads dependencies — needs internet).
4. Run on a device/emulator with `Run ▶`.
5. Or build a release APK: `Build → Generate Signed Bundle / APK`.

## Publishing to GitHub
```bash
cd rdp-canary-android
git init
git add .
git commit -m "Initial commit: RDP Canary Android monitor"
gh repo create rdp-canary-android --public --source=. --push
# or: git remote add origin https://github.com/<you>/rdp-canary-android.git
#     git push -u origin main
```
A permissive `LICENSE` (MIT) is included so others can freely fork/reuse it — change
it if you'd rather keep it private or use a different license.

## Notes on interval limits
Android's `WorkManager` enforces a **15-minute minimum** for periodic background work
(the OS does this for every app to protect battery life — there's no manifest
permission that overrides it). If you need 1–5 minute resolution, you have two
options:
1. Keep the original PowerShell script running on a always-on PC/VM as the
   high-frequency monitor, and use this Android app purely as a mobile viewer/alert
   channel (add a small pull step that reads the PC's CSV — see below).
2. Run a **foreground service** with your own timer instead of WorkManager. This can
   check more often, but Android will show a persistent notification the whole time
   it's running (required for foreground services) and it will still get throttled if
   the phone is idle/Doze for long periods. I didn't wire this up by default since it
   trades battery life for frequency — happy to add it if you want it.

## Optional: sync with the Windows PowerShell script
If you still want the high-frequency, full-RDP-handshake checks from a real Windows
box (as in your original plan) *and* a phone dashboard, the simplest bridge is:
have the PowerShell script also write its CSV into a folder synced by Google Drive
for Desktop, then add a small "Import from Drive" button in this app that reads that
file via the Storage Access Framework (Android's Drive app exposes synced files
through the normal file picker). That avoids needing any Google API key. Ask if you'd
like this wired up.

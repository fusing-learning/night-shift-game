#!/bin/zsh
# HOLLOW SHIFT launcher — double-click me in Finder.
cd "$(dirname "$0")" || exit 1
PORT=5273
# make node available when launched from Finder (nvm / Homebrew installs)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
[ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" >/dev/null 2>&1
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js was not found. Install it from https://nodejs.org and run this again."; read -r "?Press Return to close."; exit 1
fi
[ -d node_modules ] || { echo "Installing dependencies (first run only)…"; npm install || exit 1; }
echo "Building…"; npx vite build >/dev/null || { echo "Build failed."; read -r "?Press Return to close."; exit 1; }
# free the port if a previous copy is still running
lsof -ti tcp:$PORT | xargs kill 2>/dev/null
( sleep 1.2
  if [ -d "/Applications/Google Chrome.app" ]; then open -a "Google Chrome" "http://localhost:$PORT"; else open "http://localhost:$PORT"; fi ) &
echo "HOLLOW SHIFT is running at http://localhost:$PORT — close this window to stop it."
npx vite preview --port $PORT --strictPort

# ============================================================
# Digital FTE — Frontend Dockerfile
# Node.js 20 + Vite dev server
# ============================================================

FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source
COPY . .

# Vite dev server port (matches vite.config.ts)
EXPOSE 5173

# Run dev server — vite.config.ts sets host: "::" so it listens on all interfaces
CMD ["npm", "run", "dev"]

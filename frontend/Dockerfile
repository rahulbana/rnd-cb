# syntax=docker/dockerfile:1
# Multi-stage production image for the frontend.
#
#   builder  -- Node build of the Vite/React app into static assets
#   runtime  -- nginx serving the assets, proxying /api to the backend
#
# VITE_API_URL is baked at build time. Default "" makes the app call the API at
# a relative path (/api/v1), which nginx reverse-proxies to the API service --
# so the browser never needs to know the backend's address.

# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first for layer caching (use the lockfile when present).
COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY . .

ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

# SPA + API-proxy config.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8080/healthz >/dev/null 2>&1 || exit 1

# nginx runs in the foreground (container-native).
CMD ["nginx", "-g", "daemon off;"]

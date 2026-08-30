# syntax=docker/dockerfile:1

# ------------------------------------------------------------------------------
# Frontend image: build the Vite SPA, serve it with nginx.
# nginx also reverse-proxies /api to the backend service (see nginx.conf).
# ------------------------------------------------------------------------------

# --- Builder ------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


# --- Runtime ------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Replace the default site config with ours.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static assets.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]

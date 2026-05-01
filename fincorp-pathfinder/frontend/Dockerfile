# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_* vars are baked into the JS bundle at build time.
# Set these as Environment Variables in the Render dashboard for this service.
ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL
ARG VITE_EMAIL_SERVER_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL
ENV VITE_EMAIL_SERVER_URL=$VITE_EMAIL_SERVER_URL

RUN npm run build

# ── Stage 2: Serve static files with nginx ────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE ${PORT:-80}

CMD ["nginx", "-g", "daemon off;"]

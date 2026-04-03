# ──────────────────────────────────────────────────────────────────────────────
# Tornado History Tracker — static web app served by nginx
# Build context: project root  (docker build -f docker/Dockerfile .)
# ──────────────────────────────────────────────────────────────────────────────
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Remove default nginx placeholder
RUN rm -f index.html

# Copy only the files needed to serve the app
COPY index.html          ./index.html
COPY wv.html             ./wv.html
COPY src/                ./src/
COPY data/processed/     ./data/processed/

# Minimal nginx config: serve static files, correct MIME for JSON, no autoindex
COPY docker/nginx.conf   /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s \
  CMD curl -sf http://localhost/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

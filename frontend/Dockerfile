# Build stage
FROM node:20-bookworm-slim AS build

# Enterprise registry flexibility
ARG NPM_REGISTRY

WORKDIR /app
COPY package*.json ./

# Enterprise Auth/Registry: Copy .npmrc if it exists.
# This allows overriding registries or providing auth tokens seamlessly.
COPY .npmrc* ./

# Configure registry via argument if provided (acts as fallback/override to .npmrc)
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry $NPM_REGISTRY; fi

# Install dependencies - will auto-detect platform and install correct native bindings
# for @tailwindcss/oxide and lightningcss
# Remove lock file to force fresh platform-specific bindings installation
RUN rm -f package-lock.json && npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Include custom nginx.conf for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

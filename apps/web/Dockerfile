# Build stage
FROM node:20-alpine AS base

# Install pnpm
RUN npm install -g pnpm

# Dependencies stage
FROM base AS dependencies
WORKDIR /monorepo

# Copy workspace configuration
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./

# Copy apps/web package files
COPY apps/web/package.json ./apps/web/

# Install all dependencies (workspace-aware)
RUN pnpm install --frozen-lockfile --filter=web...

# Build stage
FROM base AS builder
WORKDIR /monorepo

# Accept API URL as build argument
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy installed dependencies
COPY --from=dependencies /monorepo/node_modules ./node_modules
COPY --from=dependencies /monorepo/apps/web/node_modules ./apps/web/node_modules

# Copy app source
COPY apps/web ./apps/web
WORKDIR /monorepo/apps/web
RUN pnpm build

# Production stage
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application from monorepo structure
COPY --from=builder --chown=nextjs:nodejs /monorepo/apps/web/.next/standalone ./
# Static files must be at .next/static (where server.js distDir config points)
COPY --from=builder --chown=nextjs:nodejs /monorepo/apps/web/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /monorepo/apps/web/public ./public

# Copy pnpm node_modules that symlinks in standalone point to
# Standalone creates symlinks like: ../../../node_modules/.pnpm/...
# So we need the monorepo node_modules at /node_modules
COPY --from=builder --chown=nextjs:nodejs /monorepo/node_modules /node_modules

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Standalone server.js is at root of standalone output
CMD ["node", "server.js"]

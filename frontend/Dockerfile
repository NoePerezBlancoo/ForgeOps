FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_SALES_EMAIL=contacto@forgeops.local
ARG NEXT_PUBLIC_DEMO_CREDENTIALS=true
ARG NEXT_PUBLIC_APP_VERSION=1.2.2
ARG NEXT_PUBLIC_BUILD_COMMIT=local
ARG RAILWAY_GIT_COMMIT_SHA
ARG NEXT_PUBLIC_ENVIRONMENT=development
ARG NEXT_PUBLIC_PWA_ENABLED=true
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SALES_EMAIL=$NEXT_PUBLIC_SALES_EMAIL
ENV NEXT_PUBLIC_DEMO_CREDENTIALS=$NEXT_PUBLIC_DEMO_CREDENTIALS
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION
ENV NEXT_PUBLIC_ENVIRONMENT=$NEXT_PUBLIC_ENVIRONMENT
ENV NEXT_PUBLIC_PWA_ENABLED=$NEXT_PUBLIC_PWA_ENABLED
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN NEXT_PUBLIC_BUILD_COMMIT="${RAILWAY_GIT_COMMIT_SHA:-$NEXT_PUBLIC_BUILD_COMMIT}" npm run build

FROM node:22-alpine AS runner
WORKDIR /app
LABEL org.opencontainers.image.title="ForgeOps Frontend" \
      org.opencontainers.image.description="ForgeOps industrial CMMS web application" \
      org.opencontainers.image.version="1.2.2" \
      org.opencontainers.image.source="https://github.com/NoePerezBlancoo/ForgeOps"
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]

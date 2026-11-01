FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build args for inlining at build time if provided
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_WS_URL="ws://localhost:8000"
ARG DJANGO_INTERNAL_URL="http://backend:8000"
ARG INTERNAL_API_URL="http://backend:8000"
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL} \
    DJANGO_INTERNAL_URL=${DJANGO_INTERNAL_URL} \
    INTERNAL_API_URL=${INTERNAL_API_URL} \
    NODE_ENV=production

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    DJANGO_INTERNAL_URL=http://backend:8000 \
    INTERNAL_API_URL=http://backend:8000

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/next.config.mjs ./

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-p", "3000"]


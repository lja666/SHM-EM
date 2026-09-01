ARG DOCKERHUB_PREFIX=

FROM ${DOCKERHUB_PREFIX}node:20.19.5-bookworm-slim AS dependencies
WORKDIR /workspace
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS test
COPY . ./
RUN npm run typecheck && npm run build

FROM ${DOCKERHUB_PREFIX}nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=test /workspace/dist /usr/share/nginx/html
EXPOSE 8080

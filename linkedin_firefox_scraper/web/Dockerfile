FROM node:20-alpine AS builder

ARG REACT_APP_API_URL=/api

WORKDIR /app

ENV REACT_APP_API_URL=${REACT_APP_API_URL}

COPY package.json ./
RUN npm install

COPY src/ ./src/
COPY public/ ./public/
RUN npm run build

FROM nginx:alpine

RUN apk add --no-cache gettext

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
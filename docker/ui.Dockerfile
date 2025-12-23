FROM node:18-alpine AS builder

WORKDIR /app

COPY web/package*.json ./
RUN npm install

COPY web/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY ui.nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]


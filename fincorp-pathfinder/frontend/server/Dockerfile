FROM node:20-alpine

WORKDIR /app

COPY package.json ./
# cache-bust: force fresh npm install
ARG CACHEBUST=1
RUN npm install --omit=dev

COPY index.js emailService.js email-template.html ./

EXPOSE 3001

CMD ["node", "index.js"]

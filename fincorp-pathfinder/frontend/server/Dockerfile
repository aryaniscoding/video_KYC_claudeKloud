FROM node:20-alpine

WORKDIR /app

# Install only production deps using the server-local package.json
COPY package.json ./
RUN npm install --omit=dev

# Copy server source files
COPY index.js emailService.js email-template.html ./

EXPOSE 3001

CMD ["node", "index.js"]

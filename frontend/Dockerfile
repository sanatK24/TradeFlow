FROM node:20-slim

WORKDIR /app

# Copy dependency files
COPY package.json ./
RUN npm install --legacy-peer-deps

# Copy frontend source files
COPY . .

EXPOSE 5173

# Start Vite dev server exposing all network hosts
CMD ["npm", "run", "dev", "--", "--host"]

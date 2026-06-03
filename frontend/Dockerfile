FROM node:20-alpine

WORKDIR /workspace

# Copy configurations
COPY package.json .

# Install dependencies
RUN npm install

# Copy frontend codebase
COPY . .

EXPOSE 5173

# Run Vite in host mode to allow mapping ports
CMD ["npm", "run", "dev"]

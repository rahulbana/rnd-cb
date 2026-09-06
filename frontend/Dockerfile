# Frontend dev image (Phase 1 scaffold). Production multi-stage build: Phase 10.
FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

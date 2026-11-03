FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
# npm ci (no install): instala exactamente el lockfile, igual que la CI y producción, y
# falla si package.json y package-lock.json no están en sync en vez de "arreglarlo" solo.
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

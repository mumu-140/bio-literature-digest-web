FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json* /app/
RUN npm install

COPY . /app
RUN npm run build

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "8601"]

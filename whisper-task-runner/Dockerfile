# Requires whisper-base:latest — run: ./docker/whisper-base/build.sh
FROM whisper-base:latest

USER root
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY src/ ./src/
RUN chown -R whisper:whisper /app

EXPOSE 3000

USER whisper
CMD ["node", "src/index.js"]

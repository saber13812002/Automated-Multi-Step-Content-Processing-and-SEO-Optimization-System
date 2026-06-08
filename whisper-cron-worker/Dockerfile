# Requires whisper-base:latest — run: ./docker/whisper-base/build.sh
FROM whisper-base:latest

USER root
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY src/ ./src/
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh && chown -R whisper:whisper /app

EXPOSE 3001

USER whisper
CMD ["node", "src/index.js"]

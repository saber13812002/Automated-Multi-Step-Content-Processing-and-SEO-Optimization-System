import { createServer } from 'http';

import { createApp } from './app';
import { appConfig } from './config';
import { logger } from './logger';

logger.info(
  {
    environment: appConfig.nodeEnv,
    port: appConfig.port,
    redis: {
      url: appConfig.redisUrl,
      ttlSeconds: appConfig.redisTtlSeconds
    },
    chroma: {
      baseUrl: appConfig.chroma.baseUrl,
      basePath: appConfig.chroma.basePath,
      collection: appConfig.chroma.collection,
      pageSize: appConfig.chroma.pageSize,
      maxPages: appConfig.chroma.maxPages,
      minDocLength: appConfig.chroma.minDocLength,
      apiKeyConfigured: Boolean(appConfig.chroma.apiKey)
    }
  },
  'Loaded application configuration'
);

const app = createApp();
const server = createServer(app);

server.listen(appConfig.port, () => {
  logger.info({ port: appConfig.port }, 'Server listening');
});

const gracefulShutdown = () => {
  logger.info('Shutting down server...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
};

process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);

import { createServer } from 'http';

import { createApp } from './app';
import { appConfig } from './config';
import { logger } from './logger';

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

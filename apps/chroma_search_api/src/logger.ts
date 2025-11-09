import pino from 'pino';
import pinoHttp from 'pino-http';

import { appConfig } from './config';

const baseLogger = pino({
  level: appConfig.nodeEnv === 'production' ? 'info' : 'debug',
  transport:
    appConfig.nodeEnv === 'production'
      ? undefined
      : {
          target: 'pino-pretty',
          options: {
            colorize: true,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname'
          }
        }
});

export const logger = baseLogger;

export const httpLogger = pinoHttp({
  logger: baseLogger,
  customLogLevel: (_req, res) => (res.statusCode >= 500 ? 'error' : 'info')
});


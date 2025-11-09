import type { IncomingMessage, ServerResponse } from 'http';

import pino, { type Logger as PinoLogger } from 'pino';
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

export const httpLogger = pinoHttp(
  {
    // Casting to any until upstream typings support logger with transport-enabled instance.
    logger: baseLogger as unknown as PinoLogger,
    customLogLevel: (_req: IncomingMessage, res: ServerResponse) =>
      res.statusCode >= 500 ? 'error' : 'info'
  } as any
);


import type { IncomingMessage, ServerResponse } from 'http';
import pino, { type Logger as PinoLogger } from 'pino';
import pinoHttp, { type Options as PinoHttpOptions } from 'pino-http';

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

const httpLoggerOptions: PinoHttpOptions<IncomingMessage, ServerResponse> = {
  customLogLevel: (_req: IncomingMessage, res: ServerResponse) =>
    res.statusCode >= 500 ? 'error' : 'info'
};

export const httpLogger = pinoHttp(httpLoggerOptions);

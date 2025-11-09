import cors from 'cors';
import express from 'express';
import helmet from 'helmet';

import { appConfig } from './config';
import { httpLogger, logger } from './logger';
import { searchRouter } from './routes/searchRouter';

export const createApp = () => {
  const app = express();

  app.use(helmet());
  app.use(cors());
  app.use(express.json());
  app.use(httpLogger);

  app.get('/health', (_req, res) => {
    res.json({
      status: 'ok',
      environment: appConfig.nodeEnv,
      timestamp: new Date().toISOString()
    });
  });

  app.use('/search', searchRouter);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use(
    (err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
      void _next;
      logger.error({ err }, 'Unhandled error');

      const status = 500;
      const message =
        err instanceof Error
          ? err.message
          : typeof err === 'string'
            ? err
            : 'An unexpected error occurred';

      res.status(status).json({
        error: {
          message
        }
      });
    }
  );

  return app;
};

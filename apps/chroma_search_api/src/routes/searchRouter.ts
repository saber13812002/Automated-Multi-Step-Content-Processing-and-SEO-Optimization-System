import { Router } from 'express';
import { z } from 'zod';

import { listChromaCollections } from '../clients/chromaClient';
import { getRedisClient } from '../clients/redisClient';
import { appConfig } from '../config';
import { searchWithCache } from '../services/searchService';

const querySchema = z.object({
  phrase: z.string().min(1, 'phrase is required'),
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().positive().max(appConfig.chroma.pageSize).optional()
});

export const searchRouter = Router();

searchRouter.get('/health', async (_req, res, next) => {
  try {
    const redis = getRedisClient();

    let redisStatus: 'ok' | 'error' = 'ok';
    let redisMessage: string | undefined;

    try {
      const pingResult = await redis.ping();
      if (pingResult !== 'PONG') {
        redisStatus = 'error';
        redisMessage = `Unexpected ping response: ${pingResult}`;
      }
    } catch (error) {
      redisStatus = 'error';
      redisMessage = error instanceof Error ? error.message : 'Unknown Redis error';
    }

    let chromaStatus: 'ok' | 'error' = 'ok';
    let chromaMessage: string | undefined;
    let collections: Awaited<ReturnType<typeof listChromaCollections>> = [];

    try {
      collections = await listChromaCollections();
      chromaStatus = 'ok';
    } catch (error) {
      chromaStatus = 'error';
      chromaMessage = error instanceof Error ? error.message : 'Unknown Chroma error';
    }

    const overallStatus = redisStatus === 'ok' && chromaStatus === 'ok' ? 'ok' : 'degraded';

    res.status(overallStatus === 'ok' ? 200 : 503).json({
      status: overallStatus,
      timestamp: new Date().toISOString(),
      redis: {
        status: redisStatus,
        message: redisMessage
      },
      chroma: {
        status: chromaStatus,
        message: chromaMessage,
        collectionCount: collections.length,
        collections
      }
    });
  } catch (error) {
    next(error);
  }
});

searchRouter.get('/', async (req, res, next) => {
  try {
    const { phrase, page, pageSize } = querySchema.parse(req.query);
    const redis = getRedisClient();

    const result = await searchWithCache({
      phrase,
      page,
      pageSize: pageSize ?? appConfig.chroma.pageSize,
      redis
    });

    res.json(result);
  } catch (error) {
    next(error);
  }
});

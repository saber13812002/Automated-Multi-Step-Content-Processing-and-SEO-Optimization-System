import { Router } from 'express';
import { z } from 'zod';

import { getRedisClient } from '../clients/redisClient';
import { appConfig } from '../config';
import { searchWithCache } from '../services/searchService';

const querySchema = z.object({
  phrase: z.string().min(1, 'phrase is required'),
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().positive().max(appConfig.chroma.pageSize).optional()
});

export const searchRouter = Router();

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

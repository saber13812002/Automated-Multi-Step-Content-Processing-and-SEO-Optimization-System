import type Redis from 'ioredis';

import { appConfig } from '../config';
import { logger } from '../logger';
import { queryChroma } from '../clients/chromaClient';

type SearchResultItem = {
  id: string;
  document: string;
  metadata: Record<string, unknown>;
  distance?: number;
};

export type SearchResponse = {
  items: SearchResultItem[];
  pagination: {
    page: number;
    pageSize: number;
    totalPages: number;
    totalResults: number;
  };
  source: 'cache' | 'chroma';
};

const buildCacheKey = (phrase: string, page: number, pageSize: number) => {
  return `search:${appConfig.chroma.collection}:${phrase.toLowerCase()}:page:${page}:size:${pageSize}`;
};

export const searchWithCache = async (params: {
  phrase: string;
  page: number;
  pageSize: number;
  redis: Redis;
}): Promise<SearchResponse> => {
  const { phrase, page, pageSize, redis } = params;
  const cacheKey = buildCacheKey(phrase, page, pageSize);

  try {
    const cachedValue = await redis.get(cacheKey);
    if (cachedValue) {
      logger.info({ cacheKey }, 'Cache hit');
      return { ...(JSON.parse(cachedValue) as Omit<SearchResponse, 'source'>), source: 'cache' };
    }
    logger.info({ cacheKey }, 'Cache miss');
  } catch (error) {
    logger.error({ err: error }, 'Failed to read from Redis');
  }

  const chromaResponse = await queryChroma(phrase);
  const documents = chromaResponse.documents?.[0] ?? [];
  const metadatas = chromaResponse.metadatas?.[0] ?? [];
  const ids = chromaResponse.ids?.[0] ?? [];
  const distances = chromaResponse.distances?.[0] ?? [];

  const combined = documents
    .map((document, index) => ({
      id: ids[index],
      document,
      metadata: (metadatas[index] ?? {}) as Record<string, unknown>,
      distance: distances[index]
    }))
    .filter((item) => item.document?.length >= appConfig.chroma.minDocLength);

  const totalResults = combined.length;
  const totalPages = totalResults === 0 ? 0 : Math.ceil(totalResults / pageSize);

  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, combined.length);

  if (totalPages > 0 && page > totalPages) {
    logger.warn({ page, totalPages }, 'Requested page beyond available results');
  }

  const items = combined.slice(startIndex, endIndex);

  const payload: Omit<SearchResponse, 'source'> = {
    items,
    pagination: {
      page,
      pageSize,
      totalPages,
      totalResults
    }
  };

  try {
    await redis.set(cacheKey, JSON.stringify(payload), 'EX', appConfig.redisTtlSeconds);
    logger.info({ cacheKey }, 'Stored results in cache');
  } catch (error) {
    logger.error({ err: error }, 'Failed to write to Redis');
  }

  return { ...payload, source: 'chroma' };
};


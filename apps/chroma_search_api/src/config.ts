import { config as loadEnv } from 'dotenv';
import { z } from 'zod';

loadEnv();

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(4000),
  REDIS_URL: z.string().default('redis://localhost:6379'),
  REDIS_TTL_SECONDS: z.coerce.number().int().positive().default(3600),
  CHROMA_API_BASE_URL: z.string().url().default('http://localhost:8000'),
  CHROMA_API_KEY: z.string().optional(),
  CHROMA_COLLECTION: z.string(),
  CHROMA_MIN_DOC_LENGTH: z.coerce.number().int().positive().default(200),
  CHROMA_PAGE_SIZE: z.coerce.number().int().positive().max(100).default(10),
  CHROMA_MAX_PAGES: z.coerce.number().int().positive().max(100).default(5),
  DEV_SCRAPE_URL: z.string().url().optional()
});

const env = envSchema.parse(process.env);

export const appConfig = {
  nodeEnv: env.NODE_ENV,
  port: env.PORT,
  redisUrl: env.REDIS_URL,
  redisTtlSeconds: env.REDIS_TTL_SECONDS,
  chroma: {
    baseUrl: env.CHROMA_API_BASE_URL,
    apiKey: env.CHROMA_API_KEY,
    collection: env.CHROMA_COLLECTION,
    minDocLength: env.CHROMA_MIN_DOC_LENGTH,
    pageSize: env.CHROMA_PAGE_SIZE,
    maxPages: env.CHROMA_MAX_PAGES
  },
  devScrapeUrl: env.DEV_SCRAPE_URL
};

export type AppConfig = typeof appConfig;


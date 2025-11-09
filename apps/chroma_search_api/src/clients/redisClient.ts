import Redis from 'ioredis';

import { appConfig } from '../config';
import { logger } from '../logger';

let redisInstance: Redis | null = null;

export const getRedisClient = (): Redis => {
  if (!redisInstance) {
    redisInstance = new Redis(appConfig.redisUrl, {
      maxRetriesPerRequest: null,
      enableReadyCheck: true
    });

    redisInstance.on('error', (err) => {
      logger.error({ err }, 'Redis error');
    });

    redisInstance.on('connect', () => {
      logger.info('Connected to Redis');
    });

    redisInstance.on('close', () => {
      logger.warn('Redis connection closed');
    });
  }

  return redisInstance;
};

export const disconnectRedis = async () => {
  if (redisInstance) {
    await redisInstance.quit();
    redisInstance = null;
  }
};

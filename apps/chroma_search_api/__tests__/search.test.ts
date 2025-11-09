/**
 * @jest-environment node
 */

import request from 'supertest';

import { createApp } from '../src/app';
import { getRedisClient } from '../src/clients/redisClient';
import { queryChroma } from '../src/clients/chromaClient';

jest.mock('ioredis', () => require('ioredis-mock'));

jest.mock('../src/clients/chromaClient', () => ({
  queryChroma: jest.fn()
}));

const mockedQueryChroma = queryChroma as jest.MockedFunction<typeof queryChroma>;

describe('GET /search', () => {
  const app = createApp();

  beforeEach(async () => {
    mockedQueryChroma.mockReset();
    const redis = getRedisClient();
    await redis.flushall();
  });

  afterAll(async () => {
    const redis = getRedisClient();
    await redis.quit();
  });

  it('returns results from Chroma and caches them', async () => {
    mockedQueryChroma.mockResolvedValue({
      ids: [['doc-1', 'doc-2', 'doc-3']],
      documents: [['First result', 'Second result is here', 'Third']],
      metadatas: [[{ source: 'A' }, { source: 'B' }, { source: 'C' }]],
      distances: [[0.1, 0.2, 0.3]]
    });

    const firstResponse = await request(app).get('/search').query({ phrase: 'hello world' });

    expect(firstResponse.status).toBe(200);
    expect(firstResponse.body.items).toHaveLength(2);
    expect(firstResponse.body.source).toBe('chroma');
    expect(firstResponse.body.pagination.totalResults).toBe(2);

    const secondResponse = await request(app).get('/search').query({ phrase: 'hello world' });

    expect(secondResponse.status).toBe(200);
    expect(secondResponse.body.source).toBe('cache');
    expect(mockedQueryChroma).toHaveBeenCalledTimes(1);
  });

  it('respects pagination parameter', async () => {
    mockedQueryChroma.mockResolvedValue({
      ids: [['doc-1', 'doc-2', 'doc-3', 'doc-4']],
      documents: [['document-one', 'document-two', 'document-three', 'document-four']],
      metadatas: [[{}, {}, {}, {}]],
      distances: [[0.1, 0.2, 0.3, 0.4]]
    });

    const response = await request(app).get('/search').query({ phrase: 'sample', page: 2, pageSize: 2 });

    expect(response.status).toBe(200);
    expect(response.body.items).toHaveLength(2);
    expect(response.body.pagination.page).toBe(2);
    expect(response.body.pagination.totalPages).toBe(2);
  });

  it('returns empty array when no documents satisfy minimum length', async () => {
    mockedQueryChroma.mockResolvedValue({
      ids: [['doc-1']],
      documents: [['short']],
      metadatas: [[{}]],
      distances: [[0.7]]
    });

    const response = await request(app).get('/search').query({ phrase: 'tiny' });

    expect(response.status).toBe(200);
    expect(response.body.items).toHaveLength(0);
    expect(response.body.pagination.totalResults).toBe(0);
    expect(response.body.pagination.totalPages).toBe(0);
  });
});


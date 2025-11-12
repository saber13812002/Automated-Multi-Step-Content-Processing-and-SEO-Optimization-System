import axios from 'axios';

import { appConfig } from '../config';
import { logger } from '../logger';

export type ChromaQueryResponse = {
  ids: string[][];
  documents: string[][];
  metadatas: Record<string, unknown>[][];
  distances?: number[][];
};

export type ChromaCollectionSummary = {
  id: string;
  name: string;
  metadata?: Record<string, unknown>;
};

const API_VERSION_PATH = '/api/v2';

const httpClient = axios.create({
  baseURL: appConfig.chroma.baseUrl,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 10_000
});

if (appConfig.chroma.apiKey) {
  httpClient.defaults.headers.common.Authorization = `Bearer ${appConfig.chroma.apiKey}`;
}

httpClient.interceptors.request.use((config) => {
  logger.debug(
    {
      method: config.method,
      url: config.url,
      data: config.data
    },
    'Chroma request'
  );
  return config;
});

httpClient.interceptors.response.use(
  (response) => {
    logger.debug(
      {
        status: response.status,
        dataKeys: Object.keys(response.data ?? {})
      },
      'Chroma response'
    );
    return response;
  },
  (error) => {
    logger.error({ err: error }, 'Chroma request failed');
    return Promise.reject(error);
  }
);

export const queryChroma = async (phrase: string): Promise<ChromaQueryResponse> => {
  const response = await httpClient.post(`${API_VERSION_PATH}/collections/${appConfig.chroma.collection}/query`, {
    query_texts: [phrase],
    n_results: appConfig.chroma.pageSize * appConfig.chroma.maxPages,
    include: ['documents', 'metadatas', 'distances']
  });

  return response.data as ChromaQueryResponse;
};

export const listChromaCollections = async (): Promise<ChromaCollectionSummary[]> => {
  const response = await httpClient.get(`${API_VERSION_PATH}/collections`);
  const data = response.data as { collections?: unknown } | unknown[];

  const collections = Array.isArray((data as { collections?: unknown[] }).collections)
    ? ((data as { collections?: unknown[] }).collections as Record<string, unknown>[])
    : Array.isArray(data)
      ? (data as Record<string, unknown>[])
      : [];

  return collections.map((collection) => ({
    id: String(collection.id ?? ''),
    name: String(collection.name ?? ''),
    metadata:
      collection.metadata && typeof collection.metadata === 'object'
        ? (collection.metadata as Record<string, unknown>)
        : undefined
  }));
};

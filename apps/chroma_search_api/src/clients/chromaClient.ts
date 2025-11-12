import axios, { type AxiosRequestConfig } from 'axios';

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

const API_PATH_CANDIDATES = ['/api/v2', '/api/v1', '/api', ''];

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

let cachedApiPath: string | null = null;

const shouldAttemptFallback = (error: unknown) => {
  if (!axios.isAxiosError(error)) {
    return false;
  }

  const status = error.response?.status;
  return status === 404 || status === 410 || status === 405;
};

const requestWithFallback = async <T>(
  buildConfig: (basePath: string) => AxiosRequestConfig
): Promise<T> => {
  const candidates = cachedApiPath
    ? [cachedApiPath, ...API_PATH_CANDIDATES.filter((path) => path !== cachedApiPath)]
    : API_PATH_CANDIDATES;

  let lastError: unknown;

  for (const basePath of candidates) {
    try {
      const response = await httpClient.request<T>(buildConfig(basePath));
      cachedApiPath = basePath;
      return response.data;
    } catch (error) {
      lastError = error;

      if (cachedApiPath === basePath && shouldAttemptFallback(error)) {
        cachedApiPath = null;
        continue;
      }

      if (shouldAttemptFallback(error)) {
        continue;
      }

      throw error;
    }
  }

  throw lastError ?? new Error('Unable to reach Chroma API');
};

export const queryChroma = async (phrase: string): Promise<ChromaQueryResponse> => {
  return requestWithFallback<ChromaQueryResponse>((basePath) => ({
    method: 'post',
    url: `${basePath}/collections/${appConfig.chroma.collection}/query`,
    data: {
      query_texts: [phrase],
      n_results: appConfig.chroma.pageSize * appConfig.chroma.maxPages,
      include: ['documents', 'metadatas', 'distances']
    }
  }));
};

const normalizeCollections = (payload: unknown): ChromaCollectionSummary[] => {
  const collections = Array.isArray((payload as { collections?: unknown[] }).collections)
    ? ((payload as { collections?: unknown[] }).collections as Record<string, unknown>[])
    : Array.isArray(payload)
      ? (payload as Record<string, unknown>[])
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

export const listChromaCollections = async (): Promise<ChromaCollectionSummary[]> => {
  const data = await requestWithFallback<unknown>((basePath) => ({
    method: 'get',
    url: `${basePath}/collections`
  }));

  return normalizeCollections(data);
};

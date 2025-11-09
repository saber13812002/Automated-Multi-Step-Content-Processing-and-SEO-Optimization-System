import axios from 'axios';

import { appConfig } from '../config';
import { logger } from '../logger';

export type ChromaQueryResponse = {
  ids: string[][];
  documents: string[][];
  metadatas: Record<string, unknown>[][];
  distances?: number[][];
};

const httpClient = axios.create({
  baseURL: `${appConfig.chroma.baseUrl}/api/v1`,
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
  const response = await httpClient.post(`/collections/${appConfig.chroma.collection}/query`, {
    query_texts: [phrase],
    n_results: appConfig.chroma.pageSize * appConfig.chroma.maxPages,
    include: ['documents', 'metadatas', 'distances']
  });

  return response.data as ChromaQueryResponse;
};

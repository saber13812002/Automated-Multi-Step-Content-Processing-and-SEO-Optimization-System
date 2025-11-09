process.env.NODE_ENV = process.env.NODE_ENV ?? 'test';
process.env.PORT = process.env.PORT ?? '4100';
process.env.REDIS_URL = process.env.REDIS_URL ?? 'redis://localhost:6379';
process.env.REDIS_TTL_SECONDS = process.env.REDIS_TTL_SECONDS ?? '60';
process.env.CHROMA_API_BASE_URL = process.env.CHROMA_API_BASE_URL ?? 'http://localhost:8000';
process.env.CHROMA_COLLECTION = process.env.CHROMA_COLLECTION ?? 'test-collection';
process.env.CHROMA_MIN_DOC_LENGTH = process.env.CHROMA_MIN_DOC_LENGTH ?? '10';
process.env.CHROMA_PAGE_SIZE = process.env.CHROMA_PAGE_SIZE ?? '3';
process.env.CHROMA_MAX_PAGES = process.env.CHROMA_MAX_PAGES ?? '2';

